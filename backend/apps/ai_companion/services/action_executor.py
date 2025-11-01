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


@dataclass
class PendingAction:
    """Action awaiting user confirmation"""
    action_type: str
    action_params: Dict[str, Any]
    summary: str
    confirmation_token: str
    created_at: Any
    expires_at: Any


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
            company: Company object
        """
        self.user = user
        self.company = company
        self._pending_actions = {}  # In-memory pending confirmations (TODO: move to Redis/DB)

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
        import uuid

        try:
            # Validate action
            validator = self._get_action_validator(action_type)
            if not validator:
                return ActionResult(
                    success=False,
                    message=f"Unknown action type: {action_type}"
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

            # Create confirmation token
            token = str(uuid.uuid4())

            # Store pending action (expires in 5 minutes)
            self._pending_actions[token] = PendingAction(
                action_type=action_type,
                action_params=params,
                summary=summary,
                confirmation_token=token,
                created_at=timezone.now(),
                expires_at=timezone.now() + timezone.timedelta(minutes=5)
            )

            return ActionResult(
                success=True,
                message=summary,
                requires_confirmation=True,
                confirmation_token=token
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
        # Get pending action
        pending = self._pending_actions.get(confirmation_token)
        if not pending:
            return ActionResult(
                success=False,
                message="Invalid or expired confirmation token"
            )

        # Check expiration
        if timezone.now() > pending.expires_at:
            del self._pending_actions[confirmation_token]
            return ActionResult(
                success=False,
                message="Confirmation token expired. Please try again."
            )

        try:
            # Execute the action
            result = self._execute_action(pending.action_type, pending.action_params)

            # Remove from pending
            del self._pending_actions[confirmation_token]

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
        """Create a sales order"""
        # TODO: Implement sales order creation
        return ActionResult(
            success=False,
            message="Sales order creation not yet implemented"
        )

    def _post_ar_invoice(self, params: Dict[str, Any]) -> ActionResult:
        """Post an AR invoice"""
        # TODO: Implement AR invoice posting
        return ActionResult(
            success=False,
            message="AR invoice posting not yet implemented"
        )

    def _issue_payment(self, params: Dict[str, Any]) -> ActionResult:
        """Issue a payment"""
        # TODO: Implement payment issuance
        return ActionResult(
            success=False,
            message="Payment issuance not yet implemented"
        )

    # ================================================================
    # VALIDATORS
    # ================================================================

    def _get_action_validator(self, action_type: str):
        """Get validator function for action type"""
        validators = {
            "approve_purchase_order": self._validate_approve_po,
            "reject_purchase_order": self._validate_reject_po,
            "create_sales_order": self._validate_create_so,
        }
        return validators.get(action_type)

    def _validate_approve_po(self, params: Dict[str, Any]) -> tuple:
        """Validate PO approval parameters"""
        if "po_id" not in params:
            return False, "Missing po_id"
        try:
            int(params["po_id"])
            return True, None
        except ValueError:
            return False, "Invalid po_id format"

    def _validate_reject_po(self, params: Dict[str, Any]) -> tuple:
        """Validate PO rejection parameters"""
        if "po_id" not in params:
            return False, "Missing po_id"
        if "reason" not in params:
            return False, "Missing rejection reason"
        return True, None

    def _validate_create_so(self, params: Dict[str, Any]) -> tuple:
        """Validate SO creation parameters"""
        required = ["customer_id", "items"]
        for field in required:
            if field not in params:
                return False, f"Missing required field: {field}"
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
                return f"Create new sales order for customer {params.get('customer_id')}"

            else:
                return f"Execute action: {action_type}"

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Execute action: {action_type}"
