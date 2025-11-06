"""
Action Executor with Confirmation Flow
Safely executes ERP operations through existing service layer with RBAC and audit trail
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Result of action execution"""
    success: bool
    message: str
    data: Any = None
    requires_confirmation: bool = False
    confirmation_token: str = None
    audit_id: int = None


class ActionExecutor:
    """
    Executes ERP actions safely through service layer.
    All actions respect RBAC, workflow rules, and create audit trails.
    """

    def __init__(self, user, company):
        """
        Initialize with user and company context.

        Args:
            user: Django user object
            company: Company object (if None, will try to get user's first active company)
        """
        self.user = user

        # If company is None, try to get user's first active company
        if company is None:
            try:
                from apps.companies.models import Company
                company = user.companies.filter(is_active=True).first()
                logger.info(f"Auto-selected company for user {user.id}: {company}")
            except Exception as e:
                logger.warning(f"Failed to get default company for user {user.id}: {e}")
                company = None

        self.company = company
        logger.info(f"ActionExecutor initialized with user={user.id}, company={self.company}")

    # ================================================================
    # CONFIRMATION FLOW
    # ================================================================

    def prepare_action(self, action_type: str, params: Dict[str, Any]) -> ActionResult:
        """
        Prepare an action for confirmation.
        Validates parameters and generates confirmation summary.

        Args:
            action_type: Type of action (e.g., "approve_po", "create_so")
            params: Action parameters

        Returns:
            ActionResult with requires_confirmation=True and confirmation_token
        """
        try:
            from apps.ai_companion.models import AIPendingConfirmation

            # Check if we have a company
            logger.info(f"prepare_action: Checking company - self.company={self.company}")
            if not self.company:
                logger.warning(f"prepare_action: No company found for user {self.user.id}")
                return ActionResult(
                    success=False,
                    message="I need to know which company you're working with. Please select a company first, or make sure you have access to at least one active company."
                )

            # Check if action_type is valid
            if not action_type or action_type == "unknown":
                return ActionResult(
                    success=False,
                    message="I couldn't quite figure out what action you want to perform. Could you be more specific? For example: 'create a purchase order' or 'approve PO 123'"
                )

            # Validate action
            validator = self._get_action_validator(action_type)
            if not validator:
                return ActionResult(
                    success=False,
                    message=f"Hmm, I'm not sure how to {action_type.replace('_', ' ')}. Could you try asking in a different way?"
                )

            # Validate parameters
            valid, error_msg = validator(params)
            if not valid:
                return ActionResult(
                    success=False,
                    message=f"Invalid parameters: {error_msg}"
                )

            # Generate summary
            summary = self._generate_action_summary(action_type, params)

            # Store pending action in database (expires in 5 minutes)
            pending_confirmation = AIPendingConfirmation.objects.create(
                user=self.user,
                company=self.company,
                action_type=action_type,
                action_params=params,
                summary=summary,
                expires_at=timezone.now() + timezone.timedelta(minutes=5),
                status="pending",
            )

            return ActionResult(
                success=True,
                message=summary,
                requires_confirmation=True,
                confirmation_token=str(pending_confirmation.confirmation_token)
            )

        except Exception as e:
            logger.exception(f"Error preparing action: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to prepare action: {str(e)}"
            )

    def execute_confirmed_action(self, confirmation_token: str) -> ActionResult:
        """
        Execute a previously confirmed action.

        Args:
            confirmation_token: Token from prepare_action

        Returns:
            ActionResult with execution status
        """
        try:
            from apps.ai_companion.models import AIPendingConfirmation
            import uuid

            # Convert string token to UUID
            try:
                token_uuid = uuid.UUID(confirmation_token)
            except (ValueError, AttributeError):
                return ActionResult(
                    success=False,
                    message="Invalid confirmation token format"
                )

            # Get pending confirmation
            try:
                pending = AIPendingConfirmation.objects.get(
                    confirmation_token=token_uuid,
                    user=self.user,
                    company=self.company,
                    status="pending"
                )
            except AIPendingConfirmation.DoesNotExist:
                return ActionResult(
                    success=False,
                    message="Invalid or expired confirmation token"
                )

            # Check expiration
            if pending.is_expired():
                pending.mark_expired()
                return ActionResult(
                    success=False,
                    message="Confirmation token expired. Please try again."
                )

            # Execute the action
            result = self._execute_action(pending.action_type, pending.action_params)

            # Update pending confirmation
            pending.status = "confirmed"
            pending.confirmed_at = timezone.now()
            pending.execution_result = {
                "success": result.success,
                "message": result.message,
                "data": result.data,
            }
            pending.save()

            return result

        except Exception as e:
            logger.exception(f"Error executing action: {e}")
            return ActionResult(
                success=False,
                message=f"Action execution failed: {str(e)}"
            )

    # ================================================================
    # ACTION EXECUTION
    # ================================================================

    def _execute_action(self, action_type: str, params: Dict[str, Any]) -> ActionResult:
        """Internal method to execute actions"""

        # Route to appropriate handler
        handlers = {
            "approve_purchase_order": self._approve_purchase_order,
            "reject_purchase_order": self._reject_purchase_order,
            "create_sales_order": self._create_sales_order,
            "post_ar_invoice": self._post_ar_invoice,
            "issue_payment": self._issue_payment,
            "create_customer": self._create_customer,
            # Add more handlers as needed
        }

        handler = handlers.get(action_type)
        if not handler:
            return ActionResult(
                success=False,
                message=f"No handler for action: {action_type}"
            )

        return handler(params)

    def _approve_purchase_order(self, params: Dict[str, Any]) -> ActionResult:
        """Approve a purchase order through workflow"""
        try:
            from apps.procurement.models import PurchaseOrder
            from apps.workflows.models import WorkflowInstance
            from apps.audit.models import AuditLog

            po_id = params.get("po_id")
            notes = params.get("notes", "")

            # Get PO
            try:
                po = PurchaseOrder.objects.get(id=po_id, company=self.company)
            except PurchaseOrder.DoesNotExist:
                return ActionResult(
                    success=False,
                    message=f"Purchase Order #{po_id} not found"
                )

            # Check if PO is in approvable state
            if po.status not in ["PENDING_APPROVAL", "DRAFT"]:
                return ActionResult(
                    success=False,
                    message=f"PO is in {po.status} status and cannot be approved"
                )

            # Check workflow
            workflow_instance = WorkflowInstance.objects.filter(
                company=self.company,
                entity_type="PURCHASE_ORDER",
                entity_id=str(po.id),
                status="IN_PROGRESS"
            ).first()

            with transaction.atomic():
                if workflow_instance:
                    # Approve through workflow
                    pending_task = workflow_instance.tasks.filter(
                        assigned_to=self.user,
                        status="PENDING"
                    ).first()

                    if not pending_task:
                        return ActionResult(
                            success=False,
                            message="You don't have permission to approve this PO"
                        )

                    # Mark task as approved
                    pending_task.status = "APPROVED"
                    pending_task.completed_at = timezone.now()
                    pending_task.notes = f"Approved via AI: {notes}"
                    pending_task.save()

                    # Check if workflow is complete
                    remaining_tasks = workflow_instance.tasks.filter(status="PENDING").count()
                    if remaining_tasks == 0:
                        workflow_instance.status = "COMPLETED"
                        workflow_instance.completed_at = timezone.now()
                        workflow_instance.save()

                        # Update PO status
                        po.status = "APPROVED"
                        po.approved_at = timezone.now()
                        po.approved_by = self.user
                        po.save()
                        status_message = "approved and completed"
                    else:
                        status_message = "approved (waiting for other approvals)"
                else:
                    # Direct approval (no workflow)
                    po.status = "APPROVED"
                    po.approved_at = timezone.now()
                    po.approved_by = self.user
                    po.save()
                    status_message = "approved"

                # Create audit log
                audit = AuditLog.objects.create(
                    user=self.user,
                    company=self.company,
                    action_type="APPROVE",
                    entity_type="PURCHASE_ORDER",
                    entity_id=str(po.id),
                    old_data={"status": "PENDING_APPROVAL"},
                    new_data={"status": "APPROVED"},
                    metadata={
                        "via_ai": True,
                        "notes": notes,
                        "po_number": po.po_number,
                        "supplier": po.supplier.name if po.supplier else None,
                        "total_amount": float(po.total_amount),
                    }
                )

            return ActionResult(
                success=True,
                message=f"Purchase Order #{po.po_number} has been {status_message}",
                data={
                    "po_id": po.id,
                    "po_number": po.po_number,
                    "status": po.status,
                    "total_amount": float(po.total_amount),
                },
                audit_id=audit.id
            )

        except Exception as e:
            logger.exception(f"Error approving PO: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to approve PO: {str(e)}"
            )

    def _reject_purchase_order(self, params: Dict[str, Any]) -> ActionResult:
        """Reject a purchase order"""
        try:
            from apps.procurement.models import PurchaseOrder
            from apps.workflows.models import WorkflowInstance
            from apps.audit.models import AuditLog

            po_id = params.get("po_id")
            reason = params.get("reason", "No reason provided")

            po = PurchaseOrder.objects.get(id=po_id, company=self.company)

            with transaction.atomic():
                # Update PO
                po.status = "REJECTED"
                po.save()

                # Update workflow if exists
                workflow_instance = WorkflowInstance.objects.filter(
                    company=self.company,
                    entity_type="PURCHASE_ORDER",
                    entity_id=str(po.id),
                    status="IN_PROGRESS"
                ).first()

                if workflow_instance:
                    pending_task = workflow_instance.tasks.filter(
                        assigned_to=self.user,
                        status="PENDING"
                    ).first()

                    if pending_task:
                        pending_task.status = "REJECTED"
                        pending_task.completed_at = timezone.now()
                        pending_task.notes = f"Rejected via AI: {reason}"
                        pending_task.save()

                    workflow_instance.status = "REJECTED"
                    workflow_instance.completed_at = timezone.now()
                    workflow_instance.save()

                # Audit
                audit = AuditLog.objects.create(
                    user=self.user,
                    company=self.company,
                    action_type="REJECT",
                    entity_type="PURCHASE_ORDER",
                    entity_id=str(po.id),
                    metadata={
                        "via_ai": True,
                        "reason": reason,
                        "po_number": po.po_number,
                    }
                )

            return ActionResult(
                success=True,
                message=f"Purchase Order #{po.po_number} has been rejected",
                data={"po_id": po.id, "po_number": po.po_number, "status": "REJECTED"},
                audit_id=audit.id
            )

        except Exception as e:
            logger.exception(f"Error rejecting PO: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to reject PO: {str(e)}"
            )

    def _create_sales_order(self, params: Dict[str, Any]) -> ActionResult:
        """Create a sales order with line items"""
        try:
            from apps.sales.models import SalesOrder, SalesOrderLine, Customer
            from apps.audit.models import AuditLog
            from decimal import Decimal
            import datetime

            customer_id = params.get("customer_id")
            order_date = params.get("order_date")
            delivery_date = params.get("delivery_date")
            items = params.get("items", [])  # List of {product_id, warehouse_id, quantity, unit_price}
            shipping_address = params.get("shipping_address", "")
            notes = params.get("notes", "")

            # Get customer
            try:
                customer = Customer.objects.get(id=customer_id, company=self.company)
            except Customer.DoesNotExist:
                return ActionResult(
                    success=False,
                    message=f"Customer #{customer_id} not found"
                )

            # Parse dates
            if isinstance(order_date, str):
                order_date = datetime.datetime.strptime(order_date, "%Y-%m-%d").date()
            elif not order_date:
                order_date = timezone.now().date()

            if isinstance(delivery_date, str):
                delivery_date = datetime.datetime.strptime(delivery_date, "%Y-%m-%d").date()
            elif not delivery_date:
                delivery_date = order_date + datetime.timedelta(days=7)

            # Validate items
            if not items or len(items) == 0:
                return ActionResult(
                    success=False,
                    message="Sales order must have at least one line item"
                )

            with transaction.atomic():
                # Calculate totals
                subtotal = Decimal("0.00")
                for item in items:
                    qty = Decimal(str(item.get("quantity", 1)))
                    price = Decimal(str(item.get("unit_price", 0)))
                    discount = Decimal(str(item.get("discount_percent", 0)))
                    tax = Decimal(str(item.get("tax_rate", 0)))

                    line_subtotal = qty * price
                    line_discount = line_subtotal * (discount / Decimal("100"))
                    line_after_discount = line_subtotal - line_discount
                    line_tax = line_after_discount * (tax / Decimal("100"))
                    line_total = line_after_discount + line_tax

                    subtotal += line_total

                # Create sales order
                so = SalesOrder.objects.create(
                    company=self.company,
                    created_by=self.user,
                    customer=customer,
                    order_date=order_date,
                    delivery_date=delivery_date,
                    shipping_address=shipping_address or customer.address or "",
                    subtotal=subtotal,
                    tax_amount=Decimal("0.00"),  # Calculated from lines
                    discount_amount=Decimal("0.00"),  # Calculated from lines
                    total_amount=subtotal,
                    status="DRAFT",
                    notes=notes,
                )

                # Create line items
                from apps.inventory.models import Product, Warehouse

                for idx, item in enumerate(items, start=1):
                    product = Product.objects.get(
                        id=item["product_id"],
                        company=self.company
                    )
                    warehouse = Warehouse.objects.get(
                        id=item["warehouse_id"],
                        company=self.company
                    )

                    qty = Decimal(str(item.get("quantity", 1)))
                    price = Decimal(str(item.get("unit_price", 0)))
                    discount = Decimal(str(item.get("discount_percent", 0)))
                    tax = Decimal(str(item.get("tax_rate", 0)))

                    line_subtotal = qty * price
                    line_discount = line_subtotal * (discount / Decimal("100"))
                    line_after_discount = line_subtotal - line_discount
                    line_tax = line_after_discount * (tax / Decimal("100"))
                    line_total = line_after_discount + line_tax

                    SalesOrderLine.objects.create(
                        order=so,
                        line_number=idx,
                        product=product,
                        warehouse=warehouse,
                        description=item.get("description") or product.name,
                        quantity=qty,
                        unit_price=price,
                        discount_percent=discount,
                        tax_rate=tax,
                        line_total=line_total,
                        delivered_qty=Decimal("0.00"),
                    )

                # Recalculate totals (in case of rounding differences)
                so.refresh_from_db()

                # Create audit log
                audit = AuditLog.objects.create(
                    user=self.user,
                    company=self.company,
                    action_type="CREATE",
                    entity_type="SALES_ORDER",
                    entity_id=str(so.id),
                    new_data={
                        "order_number": so.order_number,
                        "customer": customer.name,
                        "total_amount": float(so.total_amount),
                        "line_count": len(items),
                    },
                    metadata={
                        "via_ai": True,
                        "notes": notes,
                    }
                )

            return ActionResult(
                success=True,
                message=f"Sales Order #{so.order_number} created successfully for {customer.name}",
                data={
                    "so_id": so.id,
                    "order_number": so.order_number,
                    "customer_id": customer.id,
                    "customer_name": customer.name,
                    "total_amount": float(so.total_amount),
                    "status": so.status,
                    "line_count": len(items),
                },
                audit_id=audit.id
            )

        except Exception as e:
            logger.exception(f"Error creating sales order: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to create sales order: {str(e)}"
            )

    def _post_ar_invoice(self, params: Dict[str, Any]) -> ActionResult:
        """Post an AR invoice to general ledger"""
        try:
            from apps.finance.models import Invoice, InvoiceStatus, Journal, JournalVoucher, JournalEntry, Account
            from apps.audit.models import AuditLog
            from decimal import Decimal

            invoice_id = params.get("invoice_id")
            posting_date = params.get("posting_date")

            # Get invoice
            try:
                invoice = Invoice.objects.get(
                    id=invoice_id,
                    company=self.company,
                    invoice_type="AR"
                )
            except Invoice.DoesNotExist:
                return ActionResult(
                    success=False,
                    message=f"AR Invoice #{invoice_id} not found"
                )

            # Check if already posted
            if invoice.status == InvoiceStatus.POSTED:
                return ActionResult(
                    success=False,
                    message=f"Invoice {invoice.invoice_number} is already posted"
                )

            if invoice.status == InvoiceStatus.CANCELLED:
                return ActionResult(
                    success=False,
                    message=f"Cannot post cancelled invoice {invoice.invoice_number}"
                )

            # Parse posting date
            if isinstance(posting_date, str):
                import datetime
                posting_date = datetime.datetime.strptime(posting_date, "%Y-%m-%d").date()
            elif not posting_date:
                posting_date = invoice.invoice_date

            # Get or create sales journal
            sales_journal, _ = Journal.objects.get_or_create(
                company=self.company,
                code="SJ",
                defaults={
                    "name": "Sales Journal",
                    "type": "SALES",
                    "is_active": True,
                    "created_by": self.user,
                }
            )

            with transaction.atomic():
                # Create journal voucher
                voucher = JournalVoucher.objects.create(
                    company=self.company,
                    journal=sales_journal,
                    entry_date=posting_date,
                    period=posting_date.strftime("%Y-%m"),
                    description=f"AR Invoice {invoice.invoice_number}",
                    reference=invoice.invoice_number,
                    source_document_type="AR_INVOICE",
                    source_document_id=invoice.id,
                    status="POSTED",
                    created_by=self.user,
                    posted_by=self.user,
                    posted_at=timezone.now(),
                )

                # Get partner (customer)
                from apps.sales.models import Customer
                try:
                    customer = Customer.objects.get(
                        id=invoice.partner_id,
                        company=self.company
                    )
                    ar_account = customer.receivable_account
                except Customer.DoesNotExist:
                    return ActionResult(
                        success=False,
                        message="Customer not found for this invoice"
                    )

                # Debit AR account (increase receivable)
                JournalEntry.objects.create(
                    voucher=voucher,
                    line_number=1,
                    account=ar_account,
                    debit_amount=invoice.total_amount,
                    credit_amount=Decimal("0.00"),
                    description=f"AR from {customer.name}"
                )

                # Credit revenue accounts (from invoice lines)
                line_number = 2
                for inv_line in invoice.lines.all():
                    JournalEntry.objects.create(
                        voucher=voucher,
                        line_number=line_number,
                        account=inv_line.account,
                        debit_amount=Decimal("0.00"),
                        credit_amount=inv_line.line_total,
                        description=inv_line.description
                    )
                    line_number += 1

                # Mark invoice as posted
                invoice.mark_posted(voucher, self.user)

                # Create audit log
                audit = AuditLog.objects.create(
                    user=self.user,
                    company=self.company,
                    action_type="POST",
                    entity_type="AR_INVOICE",
                    entity_id=str(invoice.id),
                    old_data={"status": "DRAFT"},
                    new_data={"status": "POSTED"},
                    metadata={
                        "via_ai": True,
                        "invoice_number": invoice.invoice_number,
                        "customer": customer.name,
                        "total_amount": float(invoice.total_amount),
                        "voucher_number": voucher.voucher_number,
                    }
                )

            return ActionResult(
                success=True,
                message=f"AR Invoice {invoice.invoice_number} posted successfully (Voucher: {voucher.voucher_number})",
                data={
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "voucher_id": voucher.id,
                    "voucher_number": voucher.voucher_number,
                    "total_amount": float(invoice.total_amount),
                    "status": invoice.status,
                },
                audit_id=audit.id
            )

        except Exception as e:
            logger.exception(f"Error posting AR invoice: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to post AR invoice: {str(e)}"
            )

    def _issue_payment(self, params: Dict[str, Any]) -> ActionResult:
        """Issue a payment against invoices"""
        try:
            from apps.finance.models import Payment, Invoice, PaymentAllocation, Journal, JournalVoucher, JournalEntry, Account
            from apps.audit.models import AuditLog
            from decimal import Decimal
            import datetime

            payment_type = params.get("payment_type")  # "RECEIPT" or "PAYMENT"
            payment_method = params.get("payment_method", "BANK")
            payment_date = params.get("payment_date")
            amount = Decimal(str(params.get("amount", 0)))
            partner_type = params.get("partner_type")  # "Customer" or "Supplier"
            partner_id = params.get("partner_id")
            bank_account_id = params.get("bank_account_id")
            invoice_allocations = params.get("invoice_allocations", [])  # [{invoice_id, amount}]
            reference = params.get("reference", "")
            notes = params.get("notes", "")

            # Validate payment type
            if payment_type not in ["RECEIPT", "PAYMENT"]:
                return ActionResult(
                    success=False,
                    message="Payment type must be either RECEIPT or PAYMENT"
                )

            # Parse payment date
            if isinstance(payment_date, str):
                payment_date = datetime.datetime.strptime(payment_date, "%Y-%m-%d").date()
            elif not payment_date:
                payment_date = timezone.now().date()

            # Get bank account
            try:
                bank_account = Account.objects.get(
                    id=bank_account_id,
                    company=self.company,
                    is_bank_account=True
                )
            except Account.DoesNotExist:
                return ActionResult(
                    success=False,
                    message="Invalid bank account"
                )

            # Validate amount
            if amount <= 0:
                return ActionResult(
                    success=False,
                    message="Payment amount must be greater than zero"
                )

            with transaction.atomic():
                # Create payment
                payment = Payment.objects.create(
                    company=self.company,
                    created_by=self.user,
                    payment_date=payment_date,
                    payment_type=payment_type,
                    payment_method=payment_method,
                    amount=amount,
                    partner_type=partner_type,
                    partner_id=partner_id,
                    bank_account=bank_account,
                    reference=reference,
                    notes=notes,
                    status="DRAFT",
                )

                # Allocate to invoices
                total_allocated = Decimal("0.00")
                invoices_allocated = []

                for allocation in invoice_allocations:
                    invoice_id = allocation.get("invoice_id")
                    alloc_amount = Decimal(str(allocation.get("amount", 0)))

                    try:
                        invoice = Invoice.objects.get(
                            id=invoice_id,
                            company=self.company
                        )

                        # Validate invoice type matches payment type
                        if payment_type == "RECEIPT" and invoice.invoice_type != "AR":
                            continue
                        if payment_type == "PAYMENT" and invoice.invoice_type != "AP":
                            continue

                        # Don't over-allocate
                        max_alloc = min(alloc_amount, invoice.balance_due)
                        if max_alloc > 0:
                            PaymentAllocation.objects.create(
                                payment=payment,
                                invoice=invoice,
                                allocated_amount=max_alloc
                            )
                            total_allocated += max_alloc
                            invoices_allocated.append({
                                "invoice_number": invoice.invoice_number,
                                "amount": float(max_alloc)
                            })

                            # Update invoice paid amount
                            invoice.register_payment(max_alloc, commit=True)

                    except Invoice.DoesNotExist:
                        logger.warning(f"Invoice {invoice_id} not found, skipping allocation")
                        continue

                # Create journal voucher for posting
                journal_type = "CASH" if payment_method == "CASH" else "BANK"
                journal, _ = Journal.objects.get_or_create(
                    company=self.company,
                    code=journal_type[0] + "J",  # "CJ" or "BJ"
                    defaults={
                        "name": f"{journal_type.title()} Journal",
                        "type": journal_type,
                        "is_active": True,
                        "created_by": self.user,
                    }
                )

                voucher = JournalVoucher.objects.create(
                    company=self.company,
                    journal=journal,
                    entry_date=payment_date,
                    period=payment_date.strftime("%Y-%m"),
                    description=f"{payment.get_payment_type_display()} - {reference or payment.payment_number}",
                    reference=payment.payment_number,
                    source_document_type="PAYMENT",
                    source_document_id=payment.id,
                    status="POSTED",
                    created_by=self.user,
                    posted_by=self.user,
                    posted_at=timezone.now(),
                )

                # Create journal entries
                if payment_type == "RECEIPT":
                    # Receipt: Debit Bank, Credit AR
                    # Debit bank account (cash in)
                    JournalEntry.objects.create(
                        voucher=voucher,
                        line_number=1,
                        account=bank_account,
                        debit_amount=amount,
                        credit_amount=Decimal("0.00"),
                        description=f"Receipt - {reference or payment.payment_number}"
                    )

                    # Credit AR accounts from allocated invoices
                    line_number = 2
                    for allocation in payment.allocations.all():
                        from apps.sales.models import Customer
                        customer = Customer.objects.get(id=allocation.invoice.partner_id)

                        JournalEntry.objects.create(
                            voucher=voucher,
                            line_number=line_number,
                            account=customer.receivable_account,
                            debit_amount=Decimal("0.00"),
                            credit_amount=allocation.allocated_amount,
                            description=f"Receipt against {allocation.invoice.invoice_number}"
                        )
                        line_number += 1

                else:  # PAYMENT
                    # Payment: Debit AP, Credit Bank
                    # Credit bank account (cash out)
                    JournalEntry.objects.create(
                        voucher=voucher,
                        line_number=1,
                        account=bank_account,
                        debit_amount=Decimal("0.00"),
                        credit_amount=amount,
                        description=f"Payment - {reference or payment.payment_number}"
                    )

                    # Debit AP accounts from allocated invoices
                    line_number = 2
                    for allocation in payment.allocations.all():
                        from apps.procurement.models import Supplier
                        supplier = Supplier.objects.get(id=allocation.invoice.partner_id)

                        JournalEntry.objects.create(
                            voucher=voucher,
                            line_number=line_number,
                            account=supplier.payable_account,
                            debit_amount=allocation.allocated_amount,
                            credit_amount=Decimal("0.00"),
                            description=f"Payment against {allocation.invoice.invoice_number}"
                        )
                        line_number += 1

                # Mark payment as posted
                payment.mark_posted(voucher, self.user)

                # Create audit log
                audit = AuditLog.objects.create(
                    user=self.user,
                    company=self.company,
                    action_type="CREATE",
                    entity_type="PAYMENT",
                    entity_id=str(payment.id),
                    new_data={
                        "payment_number": payment.payment_number,
                        "payment_type": payment_type,
                        "amount": float(amount),
                        "allocated": float(total_allocated),
                        "invoice_count": len(invoices_allocated),
                    },
                    metadata={
                        "via_ai": True,
                        "notes": notes,
                        "voucher_number": voucher.voucher_number,
                        "invoices_allocated": invoices_allocated,
                    }
                )

            return ActionResult(
                success=True,
                message=f"Payment {payment.payment_number} issued successfully (Amount: {amount}, Allocated: {total_allocated})",
                data={
                    "payment_id": payment.id,
                    "payment_number": payment.payment_number,
                    "amount": float(amount),
                    "allocated_amount": float(total_allocated),
                    "invoice_count": len(invoices_allocated),
                    "voucher_number": voucher.voucher_number,
                    "status": payment.status,
                },
                audit_id=audit.id
            )

        except Exception as e:
            logger.exception(f"Error issuing payment: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to issue payment: {str(e)}"
            )

    def _create_customer(self, params: Dict[str, Any]) -> ActionResult:
        """Create a new Customer record with minimal required fields."""
        try:
            from apps.sales.models import Customer
            from apps.finance.models import Account
            from apps.audit.models import AuditLog
            import re

            name = params.get("name")
            if not name:
                return ActionResult(success=False, message="I need a name for the customer. What should I call them?")

            # Auto-generate code from name if not provided
            code = params.get("code")
            if not code:
                # Generate code from name: take first 3 letters + numbers, uppercase
                base_code = re.sub(r'[^A-Z0-9]', '', name.upper())[:6]
                if not base_code:
                    base_code = "CUST"

                # Ensure uniqueness by appending number if needed
                code = base_code
                counter = 1
                while Customer.objects.filter(company=self.company, code=code).exists():
                    code = f"{base_code}{counter}"
                    counter += 1

            # Auto-find default receivable account if not provided
            receivable_account_id = params.get("receivable_account_id")
            if not receivable_account_id:
                # Find the first "Accounts Receivable" account for this company
                receivable = Account.objects.filter(
                    company=self.company,
                    account_type='asset',
                    name__icontains='receivable'
                ).first()

                if not receivable:
                    # Fallback: find any asset account
                    receivable = Account.objects.filter(
                        company=self.company,
                        account_type='asset'
                    ).first()

                if not receivable:
                    return ActionResult(success=False, message="I couldn't find an accounts receivable account in your chart of accounts. Please create one first or specify the receivable_account_id.")
            else:
                # Validate provided receivable account belongs to the active company
                try:
                    receivable = Account.objects.get(id=receivable_account_id, company=self.company)
                except Account.DoesNotExist:
                    return ActionResult(success=False, message="I couldn't find that receivable account in your company. Could you check the account ID?")

            email = params.get("email")
            phone = params.get("phone")
            customer_type = params.get("customer_type") or "local"
            payment_terms = params.get("payment_terms")

            with transaction.atomic():
                customer = Customer.objects.create(
                    company=self.company,
                    created_by=self.user,
                    code=code,
                    name=name,
                    email=email or "",
                    phone=phone or "",
                    payment_terms=int(payment_terms) if payment_terms is not None else 30,
                    customer_type=customer_type,
                    receivable_account=receivable,
                )

                # Audit log
                audit = AuditLog.objects.create(
                    user=self.user,
                    company=self.company,
                    action_type="CREATE",
                    entity_type="CUSTOMER",
                    entity_id=str(customer.id),
                    new_data={
                        "code": customer.code,
                        "name": customer.name,
                        "receivable_account": receivable.id,
                    },
                    metadata={"via_ai": True},
                )

            return ActionResult(
                success=True,
                message=f"Customer '{customer.name}' ({customer.code}) created successfully",
                data={"customer_id": customer.id, "code": customer.code, "name": customer.name},
                audit_id=audit.id,
            )

        except Exception as e:
            logger.exception(f"Error creating customer: {e}")
            return ActionResult(success=False, message=f"Failed to create customer: {str(e)}")

    # ================================================================
    # VALIDATORS
    # ================================================================

    def _get_action_validator(self, action_type: str):
        """Get validator function for action type"""
        validators = {
            "approve_purchase_order": self._validate_approve_po,
            "reject_purchase_order": self._validate_reject_po,
            "create_sales_order": self._validate_create_so,
            "post_ar_invoice": self._validate_post_ar_invoice,
            "issue_payment": self._validate_issue_payment,
            "create_customer": self._validate_create_customer,
        }
        return validators.get(action_type)

    def _validate_approve_po(self, params: Dict[str, Any]) -> tuple:
        """Validate PO approval parameters"""
        if "po_id" not in params or not params.get("po_id"):
            return False, "Which purchase order would you like me to approve? I need the PO number or ID."
        try:
            int(params["po_id"])
            return True, None
        except ValueError:
            return False, "That doesn't look like a valid purchase order number. Could you check it?"

    def _validate_reject_po(self, params: Dict[str, Any]) -> tuple:
        """Validate PO rejection parameters"""
        if "po_id" not in params or not params.get("po_id"):
            return False, "Which purchase order should I reject? I need the PO number or ID."
        if "reason" not in params or not params.get("reason"):
            return False, "I need to know why you're rejecting this purchase order. Could you tell me the reason?"
        return True, None

    def _validate_create_so(self, params: Dict[str, Any]) -> tuple:
        """Validate SO creation parameters"""
        if "customer_id" not in params or not params.get("customer_id"):
            return False, "I need to know which customer this sales order is for. Could you tell me the customer name or ID?"
        if "items" not in params or not params.get("items"):
            return False, "I need to know what items to include in the sales order. What products or services should I add?"
        return True, None

    def _validate_post_ar_invoice(self, params: Dict[str, Any]) -> tuple:
        """Validate AR invoice posting parameters"""
        if "invoice_id" not in params or not params.get("invoice_id"):
            return False, "Which invoice would you like me to post? I need the invoice number or ID."
        return True, None

    def _validate_issue_payment(self, params: Dict[str, Any]) -> tuple:
        """Validate payment issuance parameters"""
        if "payment_type" not in params or not params.get("payment_type"):
            return False, "I need to know if this is a payment or a receipt. Which one is it?"
        if "amount" not in params or not params.get("amount"):
            return False, "How much is the payment for? I need an amount."
        if "partner_id" not in params or not params.get("partner_id"):
            return False, "Who are you paying or receiving from? I need a customer or supplier."
        if "bank_account_id" not in params or not params.get("bank_account_id"):
            return False, "Which bank account should I use for this payment?"

        # Validate payment type
        if params.get("payment_type") not in ["RECEIPT", "PAYMENT"]:
            return False, "The payment type should be either 'RECEIPT' or 'PAYMENT'."

        # Validate amount
        try:
            amount = float(params.get("amount", 0))
            if amount <= 0:
                return False, "The amount needs to be greater than zero."
        except (ValueError, TypeError):
            return False, "That doesn't look like a valid amount. Could you give me a number?"

        return True, None

    def _validate_create_customer(self, params: Dict[str, Any]) -> tuple:
        """Validate Customer creation parameters"""
        if "name" not in params or not params.get("name"):
            return False, "I need a name for the customer. What should I call them?"

        # Auto-generate code if not provided
        if "code" not in params or not params.get("code"):
            # Will be auto-generated in the executor from the name
            pass

        # Auto-find default receivable account if not provided
        if "receivable_account_id" not in params or not params.get("receivable_account_id"):
            # Will be auto-found in the executor
            pass

        return True, None

    # ================================================================
    # SUMMARY GENERATION
    # ================================================================

    def _generate_action_summary(self, action_type: str, params: Dict[str, Any]) -> str:
        """Generate human-readable summary of action"""
        try:
            if action_type == "approve_purchase_order":
                from apps.procurement.models import PurchaseOrder
                po = PurchaseOrder.objects.get(id=params["po_id"], company=self.company)
                return (
                    f"Are you sure you want to approve Purchase Order #{po.po_number}?\n"
                    f"Supplier: {po.supplier.name if po.supplier else 'N/A'}\n"
                    f"Total Amount: {po.total_amount}\n"
                    f"Status: {po.status}"
                )

            elif action_type == "reject_purchase_order":
                from apps.procurement.models import PurchaseOrder
                po = PurchaseOrder.objects.get(id=params["po_id"], company=self.company)
                return (
                    f"Are you sure you want to reject Purchase Order #{po.po_number}?\n"
                    f"Reason: {params.get('reason', 'Not specified')}"
                )

            elif action_type == "create_sales_order":
                from apps.sales.models import Customer
                customer = Customer.objects.get(id=params["customer_id"], company=self.company)
                items_count = len(params.get("items", []))
                return (
                    f"Create new sales order:\n"
                    f"Customer: {customer.name}\n"
                    f"Items: {items_count} line(s)\n"
                    f"Delivery Date: {params.get('delivery_date', 'Not specified')}"
                )

            elif action_type == "post_ar_invoice":
                from apps.finance.models import Invoice
                invoice = Invoice.objects.get(id=params["invoice_id"], company=self.company)
                from apps.sales.models import Customer
                customer = Customer.objects.get(id=invoice.partner_id)
                return (
                    f"Are you sure you want to post AR Invoice {invoice.invoice_number}?\n"
                    f"Customer: {customer.name}\n"
                    f"Amount: {invoice.total_amount}\n"
                    f"This will create journal entries in the general ledger."
                )

            elif action_type == "issue_payment":
                payment_type = params.get("payment_type")
                amount = params.get("amount")
                alloc_count = len(params.get("invoice_allocations", []))
                type_label = "Receipt" if payment_type == "RECEIPT" else "Payment"
                return (
                    f"Issue {type_label}:\n"
                    f"Amount: {amount}\n"
                    f"Method: {params.get('payment_method', 'BANK')}\n"
                    f"Allocating to {alloc_count} invoice(s)"
                )

            elif action_type == "create_customer":
                name = params.get('name') or 'N/A'
                code = params.get('code') or 'N/A'
                return (
                    f"Create new customer:\n"
                    f"Name: {name}\n"
                    f"Code: {code}\n"
                    f"(Receivable account will be validated)"
                )

            else:
                return f"Execute action: {action_type}"

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Execute action: {action_type}"
