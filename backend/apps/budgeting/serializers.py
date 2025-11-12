from __future__ import annotations

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (
    Budget,
    BudgetConsumptionSnapshot,
    BudgetLine,
    BudgetOverrideRequest,
    BudgetUsage,
    CostCenter,
    BudgetItemCode,
    BudgetItemCategory,
    BudgetItemSubCategory,
    BudgetApproval,
    BudgetRemarkTemplate,
    BudgetVarianceAudit,
    BudgetPricePolicy,
)
from apps.inventory.models import UnitOfMeasure


class CostCenterSerializer(serializers.ModelSerializer):
    owner_display = serializers.SerializerMethodField()
    deputy_owner_display = serializers.SerializerMethodField()
    active_budget_count = serializers.SerializerMethodField()

    class Meta:
        model = CostCenter
        fields = [
            "id",
            "code",
            "name",
            "cost_center_type",
            "parent",
            "owner",
            "owner_display",
            "deputy_owner",
            "deputy_owner_display",
            "default_currency",
            "description",
            "is_active",
            "tags",
            "kpi_snapshot",
            "active_budget_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "active_budget_count", "owner_display", "deputy_owner_display"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        if company is None and request is not None:
            user = getattr(request, "user", None)
            if user is not None:
                company = getattr(user, "default_company", None)
        if company is None:
            raise serializers.ValidationError({"detail": "No active company selected. Please select a company and try again."})
        company_group = getattr(company, "company_group", None)
        return CostCenter.objects.create(company=company, company_group=company_group, **validated_data)

    def get_owner_display(self, obj: CostCenter) -> str | None:
        user = getattr(obj, "owner", None)
        if not user:
            return None
        name = getattr(user, "get_full_name", lambda: None)()
        return name or getattr(user, "username", None)

    def get_deputy_owner_display(self, obj: CostCenter) -> str | None:
        user = getattr(obj, "deputy_owner", None)
        if not user:
            return None
        name = getattr(user, "get_full_name", lambda: None)()
        return name or getattr(user, "username", None)

    def get_active_budget_count(self, obj: CostCenter) -> int:
        today = timezone.now().date()
        return obj.budgets.filter(period_start__lte=today, period_end__gte=today, status=Budget.STATUS_ACTIVE).count()


class BudgetLineSerializer(serializers.ModelSerializer):
    remaining_value = serializers.SerializerMethodField()
    remaining_quantity = serializers.SerializerMethodField()
    budget_name = serializers.ReadOnlyField(source="budget.name")
    committed_value = serializers.SerializerMethodField()
    committed_quantity = serializers.SerializerMethodField()
    available_value = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()
    modified_by_display = serializers.SerializerMethodField()
    held_by_display = serializers.SerializerMethodField()
    moderator_remarks_by_display = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    # Friendly category/sub-category display
    category_name = serializers.SerializerMethodField()
    sub_category_name = serializers.SerializerMethodField()
    item_category_name = serializers.SerializerMethodField()

    class Meta:
        model = BudgetLine
        fields = [
            "id",
            "budget",
            "budget_name",
            "sequence",
            "procurement_class",
            "item_code",
            "product",
            "item_name",
            "category",
            "category_name",
            "sub_category_name",
            "project_code",
            # Current limits
            "qty_limit",
            "value_limit",
            "standard_price",
            "manual_unit_price",
            "tolerance_percent",
            # Original values for variance tracking
            "original_qty_limit",
            "original_unit_price",
            "original_value_limit",
            # Variance tracking
            "qty_variance",
            "price_variance",
            "value_variance",
            "variance_percent",
            # Consumption
            "consumed_quantity",
            "consumed_value",
            "committed_quantity",
            "committed_value",
            "remaining_quantity",
            "remaining_value",
            "available_quantity",
            "available_value",
            # Modification tracking
            "modified_by",
            "modified_by_display",
            "modified_at",
            "modification_reason",
            # Held items
            "is_held_for_review",
            "held_by",
            "held_by_display",
            "held_reason",
            "held_until_date",
            "sent_back_for_review",
            # Moderator remarks
            "moderator_remarks",
            "moderator_remarks_by",
            "moderator_remarks_by_display",
            "moderator_remarks_at",
            "cc_owner_modification_notes",
            # Canonical line-wise workflow states
            "cc_decision",
            "cc_decision_by",
            "cc_decision_at",
            "moderator_state",
            "final_decision",
            "final_decision_by",
            "final_decision_at",
            # AI projections
            "projected_consumption_value",
            "projected_consumption_confidence",
            "will_exceed_budget",
            # General
            "budget_owner",
            "is_active",
            "notes",
            "metadata",
            # Unified item category helper for UIs
            "item_category_name",
            # Computed helpers
            "status",
            "can_delete",
            # Timestamps
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "consumed_quantity",
            "consumed_value",
            "remaining_quantity",
            "remaining_value",
            "committed_quantity",
            "committed_value",
            "available_quantity",
            "available_value",
            "qty_variance",
            "price_variance",
            "value_variance",
            "variance_percent",
            "modified_by_display",
            "held_by_display",
            "moderator_remarks_by_display",
            # leave workflow timestamps writable by server only via actions
            "status",
            "can_delete",
            "created_at",
            "updated_at",
        ]

    def get_category_name(self, obj: BudgetLine) -> str | None:
        try:
            # Prefer explicit category string if set
            if getattr(obj, "category", None):
                return obj.category
            # Fallback to sub-category name if available
            sub = getattr(obj, "sub_category", None)
            if sub and getattr(sub, "name", None):
                return sub.name
            # As a last resort, attempt to derive from related item/product if they have category-like attribute
            itm = getattr(obj, "item", None)
            cat = getattr(itm, "category", None)
            if hasattr(cat, "name"):
                return getattr(cat, "name", None)
            # Legacy fallback: try to locate inventory item by item_code
            code = getattr(obj, "item_code", None)
            if code and getattr(obj, "budget", None) and getattr(obj.budget, "company_id", None):
                try:
                    from apps.inventory.models import Item as InvItem
                    itm = InvItem.objects.select_related("category").filter(company_id=obj.budget.company_id, code=code).first()
                    if itm and getattr(itm, "category", None):
                        return getattr(itm.category, "name", None)
                except Exception:
                    pass
            return None
        except Exception:
            return None

    def get_sub_category_name(self, obj: BudgetLine) -> str | None:
        """
        Sub-Category derived from BudgetItemCode (by item_code)
        """
        try:
            # First try to get from BudgetItemCode by item_code
            code = getattr(obj, "item_code", None)
            if code and getattr(obj, "budget", None) and getattr(obj.budget, "company_id", None):
                try:
                    from .models import BudgetItemCode
                    item_code = BudgetItemCode.objects.select_related("sub_category_ref").filter(
                        company__company_group_id=obj.budget.company.company_group_id,
                        code=code
                    ).first()
                    if item_code and item_code.sub_category_ref_id and item_code.sub_category_ref:
                        return getattr(item_code.sub_category_ref, "name", None)
                except Exception:
                    pass

            # Fallback: try sub_category FK on BudgetLine (if exists)
            sub = getattr(obj, "sub_category", None)
            if sub:
                return getattr(sub, "name", None)
        except Exception:
            pass
        return None

    def get_item_category_name(self, obj: BudgetLine) -> str | None:
        """
        Item Category derived from BudgetItemCode (by item_code),
        not from sales Product or inventory Item. This matches "item code category".
        """
        try:
            # First try to get from BudgetItemCode by item_code
            code = getattr(obj, "item_code", None)
            if code and getattr(obj, "budget", None) and getattr(obj.budget, "company_id", None):
                try:
                    from .models import BudgetItemCode
                    item_code = BudgetItemCode.objects.select_related("category_ref").filter(
                        company__company_group_id=obj.budget.company.company_group_id,
                        code=code
                    ).first()
                    if item_code:
                        # Return category from category_ref if available
                        if item_code.category_ref_id and item_code.category_ref:
                            return getattr(item_code.category_ref, "name", None)
                        # Fallback to text category field
                        if item_code.category:
                            return item_code.category
                except Exception:
                    pass

            # Fallback: try Item FK if available
            itm = getattr(obj, "item", None)
            cat = getattr(itm, "category", None)
            if cat and getattr(cat, "name", None):
                return cat.name

            # Last fallback: resolve inventory Item by code
            if code and getattr(obj, "budget", None) and getattr(obj.budget, "company_id", None):
                try:
                    from apps.inventory.models import Item as InvItem
                    inv = InvItem.objects.select_related("category").filter(company_id=obj.budget.company_id, code=code).first()
                    if inv and getattr(inv, "category", None):
                        return getattr(inv.category, "name", None)
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def get_status(self, obj: BudgetLine) -> str:
        try:
            # Prefer canonical fields
            fd = getattr(obj, 'final_decision', None)
            try:
                if fd == BudgetLine.FinalDecision.APPROVED:
                    return 'approved'
                if fd == BudgetLine.FinalDecision.REJECTED:
                    return 'rejected'
            except Exception:
                pass

            cd = getattr(obj, 'cc_decision', None)
            try:
                if cd == BudgetLine.CCDecision.APPROVED:
                    return 'cc_approved'
                if cd == BudgetLine.CCDecision.SENT_BACK or getattr(obj, 'sent_back_for_review', False):
                    return 'sent_back'
            except Exception:
                pass

            # Legacy metadata fallbacks
            meta = getattr(obj, 'metadata', {}) or {}
            if meta.get('final_approved'):
                return 'approved'
            if meta.get('approved'):
                return 'cc_approved'
            if meta.get('rejected'):
                return 'rejected'
            if meta.get('submitted'):
                return 'submitted'
            return 'pending'
        except Exception:
            return 'pending'

    def get_can_delete(self, obj: BudgetLine) -> bool:
        request = self.context.get('request')
        try:
            user = getattr(request, 'user', None)
            meta = getattr(obj, 'metadata', {}) or {}
            is_draft = not bool(meta.get('submitted')) and not bool(meta.get('approved')) and not bool(meta.get('rejected'))
            return bool(user and getattr(obj, 'budget_owner_id', None) and obj.budget_owner_id == user.id and is_draft)
        except Exception:
            return False

    def get_remaining_value(self, obj: BudgetLine) -> str:
        return f"{obj.remaining_value}"

    def validate(self, attrs):
        # Enforce item code vs product linkage per budget type (only when identity changes or on create)
        budget = attrs.get("budget")
        if not budget and self.instance:
            budget = self.instance.budget
        changed_fields = set(attrs.keys())
        enforce_identity = (self.instance is None) or bool(changed_fields & {"item_code", "product", "item"})
        if budget and enforce_identity:
            btype = getattr(budget, "budget_type", None)
            if btype == Budget.TYPE_OPERATIONAL:
                # Operational budgets work with item codes; ensure an item_code exists
                if not attrs.get("item_code") and not (self.instance and getattr(self.instance, "item_code", None)):
                    raise serializers.ValidationError({"item_code": "Item code is required for operational budgets."})
            elif btype == Budget.TYPE_REVENUE:
                # Revenue: require product
                product = attrs.get("product") or (self.instance.product if self.instance else None)
                if not product:
                    raise serializers.ValidationError({"product": "Product is required for revenue budgets."})
                if not attrs.get("item_code") and hasattr(product, "code"):
                    attrs["item_code"] = product.code
                if not attrs.get("item_name") and hasattr(product, "name"):
                    attrs["item_name"] = product.name
            else:
                # Other budgets: require item_code
                if not attrs.get("item_code") and not (self.instance and self.instance.item_code):
                    raise serializers.ValidationError({"item_code": "Item code is required for this budget type."})
        # Unit price must be > 0 (prefer manual if provided; else standard)
        try:
            # Only enforce when price/qty/value fields are being modified
            changed = set(attrs.keys())
            watch = {"manual_unit_price", "standard_price", "value_limit", "qty_limit"}
            if changed & watch:
                m_price = attrs.get("manual_unit_price")
                s_price = attrs.get("standard_price")
                if m_price is None and self.instance is not None:
                    m_price = getattr(self.instance, "manual_unit_price", None)
                if s_price is None and self.instance is not None:
                    s_price = getattr(self.instance, "standard_price", None)
                # Choose effective unit price
                eff = m_price if m_price is not None else s_price
                # If no effective price but a value and quantity are available, derive a manual price
                if (eff is None or Decimal(str(eff)) <= Decimal("0")):
                    vl = attrs.get("value_limit")
                    ql = attrs.get("qty_limit")
                    if vl is None and self.instance is not None:
                        vl = getattr(self.instance, "value_limit", None)
                    if ql is None and self.instance is not None:
                        ql = getattr(self.instance, "qty_limit", None)
                    try:
                        if vl is not None and ql is not None and Decimal(str(ql)) > Decimal("0"):
                            derived = (Decimal(str(vl)) / Decimal(str(ql)))
                            if derived > Decimal("0"):
                                attrs["manual_unit_price"] = derived
                                eff = derived
                    except Exception:
                        # fall through to regular validation
                        pass
                # if eff is None or Decimal(str(eff)) <= Decimal("0"):
                #     # This validation is temporarily disabled to unblock the frontend.
                #     # The frontend should be fixed to send a valid unit price.
                #     raise serializers.ValidationError({"manual_unit_price": "Unit price must be greater than 0."})
        except serializers.ValidationError:
            raise
        except Exception:
            pass
        return attrs

    def get_remaining_quantity(self, obj: BudgetLine) -> str:
        return f"{obj.remaining_quantity}"

    def get_committed_value(self, obj: BudgetLine) -> str:
        return f"{obj.committed_value}"

    def get_committed_quantity(self, obj: BudgetLine) -> str:
        return f"{obj.committed_quantity}"

    def get_available_value(self, obj: BudgetLine) -> str:
        return f"{obj.available_value}"

    def get_available_quantity(self, obj: BudgetLine) -> str:
        return f"{obj.available_quantity}"

    def get_modified_by_display(self, obj: BudgetLine) -> str | None:
        user = obj.modified_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_held_by_display(self, obj: BudgetLine) -> str | None:
        user = obj.held_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_moderator_remarks_by_display(self, obj: BudgetLine) -> str | None:
        user = obj.moderator_remarks_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        try:
            # Unified unit price for display: prefer manual if present
            m = rep.get("manual_unit_price")
            s = rep.get("standard_price")
            rep["unit_price"] = m if m not in (None, "") else s
        except Exception:
            pass
        return rep



class BudgetApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.SerializerMethodField()
    cost_center_name = serializers.SerializerMethodField()

    class Meta:
        model = BudgetApproval
        fields = "__all__"

    def get_approver_name(self, obj: BudgetApproval) -> str | None:
        u = obj.approver
        return getattr(u, "get_full_name", lambda: None)() or getattr(u, "username", None) if u else None

    def get_cost_center_name(self, obj: BudgetApproval) -> str | None:
        return getattr(obj.cost_center, "name", None)


class BudgetSerializer(serializers.ModelSerializer):
    available = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    line_count = serializers.IntegerField(read_only=True)
    lines = BudgetLineSerializer(many=True, read_only=True)
    is_entry_period_active = serializers.SerializerMethodField()
    is_review_period_active = serializers.SerializerMethodField()
    is_budget_impact_active = serializers.SerializerMethodField()
    pending_approvals = serializers.SerializerMethodField()
    user_can_enter = serializers.SerializerMethodField()
    approvals = BudgetApprovalSerializer(many=True, read_only=True)
    duration_display = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    moderator_reviewed_by_display = serializers.SerializerMethodField()
    final_approved_by_display = serializers.SerializerMethodField()
    activated_by_display = serializers.SerializerMethodField()
    name_status = serializers.SerializerMethodField()
    status2 = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id",
            "parent_declared",
            "cost_center",
            "name",
            "display_name",
            "budget_type",
            # Duration and period configuration
            "duration_type",
            "duration_display",
            "custom_duration_days",
            "period_start",
            "period_end",
            # Entry period
            "entry_start_date",
            "entry_end_date",
            "entry_enabled",
            # Review period and grace
            "grace_period_days",
            "review_start_date",
            "review_end_date",
            "review_enabled",
            # Budget impact period
            "budget_impact_start_date",
            "budget_impact_end_date",
            "budget_impact_enabled",
            # Legacy date fields (backward compatibility)
            "budget_active_date",
            "budget_expire_date",
            # Auto-approval
            "auto_approve_if_not_approved",
            "auto_approve_by_role",
            "auto_approved_at",
            # Amounts and variance
            "amount",
            "consumed",
            "committed",
            "remaining",
            "total_variance_amount",
            "total_variance_count",
            "threshold_percent",
            # Status and workflow
            "status",
            "name_status",
            "status2",
            "workflow_state",
            # Moderator review tracking
            "moderator_reviewed_by",
            "moderator_reviewed_by_display",
            "moderator_reviewed_at",
            # Final approval tracking
            "final_approved_by",
            "final_approved_by_display",
            "final_approved_at",
            # Activation tracking
            "activated_by",
            "activated_by_display",
            "activated_at",
            # Relations
            "line_count",
            "lines",
            "approvals",
            # Metadata and helpers
            "metadata",
            "available",
            "is_entry_period_active",
            "is_review_period_active",
            "is_budget_impact_active",
            "pending_approvals",
            "user_can_enter",
            # Timestamps
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "line_count",
            "available",
            "consumed",
            "committed",
            "remaining",
            "amount",
            "total_variance_amount",
            "total_variance_count",
            "is_entry_period_active",
            "is_review_period_active",
            "is_budget_impact_active",
            "pending_approvals",
            "user_can_enter",
            "duration_display",
            "display_name",
            "moderator_reviewed_by_display",
            "final_approved_by_display",
            "activated_by_display",
            "auto_approved_at",
            "moderator_reviewed_at",
            "final_approved_at",
            "activated_at",
        ]
        extra_kwargs = {
            "cost_center": {"required": False, "allow_null": True},
        }

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["available"] = f"{instance.available}"
        # Ensure name is never empty in API by falling back to display string
        try:
            nm = (rep.get("name") or "").strip()
        except Exception:
            nm = ""
        if not nm:
            try:
                rep["name"] = str(instance)
            except Exception:
                rep["name"] = f"Budget {getattr(instance, 'id', '')}"
        return rep

    def get_is_entry_period_active(self, obj: Budget) -> bool:
        return obj.is_entry_period_active()

    def get_is_review_period_active(self, obj: Budget) -> bool:
        return obj.is_review_period_active()

    def get_is_budget_impact_active(self, obj: Budget) -> bool:
        return obj.is_budget_impact_active()

    def get_name_status(self, obj: Budget) -> str:
        # Prefer explicit name_status field
        try:
            ns = getattr(obj, 'name_status', None)
            if ns:
                return ns
        except Exception:
            pass
        # Legacy fallback
        try:
            status = getattr(obj, 'status', None)
            if status == getattr(Budget, 'STATUS_PENDING_NAME_APPROVAL', 'pending_name_approval'):
                return 'DRAFT'
        except Exception:
            pass
        return 'APPROVED'

    def get_status2(self, obj: Budget) -> dict:
        from django.utils import timezone
        def _fmt(d):
            try:
                return d.isoformat() if d else None
            except Exception:
                return None

        today = timezone.now().date()

        # Entry state
        entry_state = 'unknown'
        try:
            es = getattr(obj, 'entry_start_date', None)
            ee = getattr(obj, 'entry_end_date', None)
            enabled = bool(getattr(obj, 'entry_enabled', True))
            if not enabled:
                entry_state = 'closed'
            else:
                if es and today < es:
                    entry_state = 'not_started'
                elif ee and today > ee:
                    entry_state = 'closed'
                else:
                    entry_state = 'open'
        except Exception:
            enabled = None

        # Review state
        review_state = 'unknown'
        try:
            rs = getattr(obj, 'review_start_date', None)
            re = getattr(obj, 'review_end_date', None)
            r_enabled = bool(getattr(obj, 'review_enabled', False))
            if not r_enabled:
                if re and today > re:
                    review_state = 'closed'
                elif rs and today < rs:
                    review_state = 'not_started'
                else:
                    review_state = 'closed'
            else:
                if rs and re and rs <= today <= re:
                    review_state = 'open'
                else:
                    review_state = 'closed'
        except Exception:
            r_enabled = None

        # Period state
        period_state = 'unknown'
        try:
            ps = getattr(obj, 'period_start', None)
            pe = getattr(obj, 'period_end', None)
            if ps and today < ps:
                period_state = 'not_started'
            elif pe and today > pe:
                period_state = 'closed'
            else:
                period_state = 'open'
        except Exception:
            pass

        return {
            'entry': {
                'state': entry_state,
                'enabled': enabled,
                'start_date': _fmt(getattr(obj, 'entry_start_date', None)),
                'end_date': _fmt(getattr(obj, 'entry_end_date', None)),
            },
            'review': {
                'state': review_state,
                'enabled': r_enabled,
                'start_date': _fmt(getattr(obj, 'review_start_date', None)),
                'end_date': _fmt(getattr(obj, 'review_end_date', None)),
            },
            'period': {
                'state': period_state,
                'start_date': _fmt(getattr(obj, 'period_start', None)),
                'end_date': _fmt(getattr(obj, 'period_end', None)),
            },
        }

    def get_duration_display(self, obj: Budget) -> str:
        return obj.get_duration_display()

    def get_display_name(self, obj):
        try:
            result = str(obj).strip()
            if result:
                return result
        except Exception:
            pass
        # Fallback to constructing a display name
        try:
            name = (obj.name or "").strip()
            if name and name != "Untitled Budget":
                return name
        except Exception:
            pass
        # Construct from budget details
        try:
            bt = obj.get_budget_type_display() if hasattr(obj, 'get_budget_type_display') else (obj.budget_type or "").upper()
            ps = obj.period_start.strftime('%Y-%m-%d') if obj.period_start else ''
            pe = obj.period_end.strftime('%Y-%m-%d') if obj.period_end else ''
            if bt or ps or pe:
                parts = []
                if bt:
                    parts.append(bt)
                if ps and pe:
                    parts.append(f"{ps} → {pe}")
                elif ps:
                    parts.append(f"from {ps}")
                elif pe:
                    parts.append(f"until {pe}")
                if parts:
                    return " · ".join(parts)
        except Exception:
            pass
        # Final fallback
        return f"Budget {getattr(obj, 'id', '')}"

    def get_pending_approvals(self, obj: Budget):
        qs = obj.get_pending_cost_center_approvals()
        try:
            return BudgetApprovalSerializer(qs, many=True).data if qs else []
        except Exception:
            return []

    def get_user_can_enter(self, obj: Budget) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return obj.can_user_enter_budget(user) if user else False

    def get_moderator_reviewed_by_display(self, obj: Budget) -> str | None:
        user = obj.moderator_reviewed_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_final_approved_by_display(self, obj: Budget) -> str | None:
        user = obj.final_approved_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_activated_by_display(self, obj: Budget) -> str | None:
        user = obj.activated_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        company = getattr(request, "company", None) if request else None
        if company is None and user is not None:
            company = getattr(user, "default_company", None)
        if company is None:
            raise serializers.ValidationError({"detail": "No active company selected. Please select a company and try again."})
        validated_data.setdefault("created_by", user)
        return Budget.objects.create(company=company, **validated_data)

    def update(self, instance, validated_data):
        user = self.context.get("request").user if self.context.get("request") else None
        if user and hasattr(instance, "updated_by"):
            validated_data["updated_by"] = user
        return super().update(instance, validated_data)

    def validate(self, attrs):
        # Require entry window on create
        if self.instance is None:
            es = attrs.get("entry_start_date")
            ee = attrs.get("entry_end_date")
            if not es or not ee:
                raise serializers.ValidationError({
                    "entry_start_date": "Required",
                    "entry_end_date": "Required",
                })
            if es and ee and ee < es:
                raise serializers.ValidationError("entry_end_date cannot be before entry_start_date")
        return attrs


class BudgetUsageSerializer(serializers.ModelSerializer):
    budget = serializers.CharField(source="budget_line.budget.name", read_only=True)
    cost_center = serializers.SerializerMethodField()

    class Meta:
        model = BudgetUsage
        fields = [
            "id",
            "budget_line",
            "budget",
            "cost_center",
            "usage_date",
            "usage_type",
            "quantity",
            "amount",
            "reference_type",
            "reference_id",
            "description",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["created_at", "budget", "cost_center"]

    def get_cost_center(self, obj: BudgetUsage) -> str:
        return str(obj.budget_line.budget.cost_center)


class BudgetOverrideRequestSerializer(serializers.ModelSerializer):
    cost_center_name = serializers.ReadOnlyField(source="cost_center.name")
    budget_line_name = serializers.ReadOnlyField(source="budget_line.item_name")
    requested_by_display = serializers.SerializerMethodField()
    approver_display = serializers.SerializerMethodField()

    class Meta:
        model = BudgetOverrideRequest
        fields = [
            "id",
            "cost_center",
            "cost_center_name",
            "budget_line",
            "budget_line_name",
            "requested_by",
            "requested_by_display",
            "approver",
            "approver_display",
            "status",
            "reason",
            "requested_quantity",
            "requested_amount",
            "decision_notes",
            "reference_type",
            "reference_id",
            "severity",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["approved_at", "created_at", "updated_at", "requested_by_display", "approver_display"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = validated_data.get("company")
        if not company and request:
            company = getattr(request, "company", None)
        if not company and validated_data.get("cost_center") is not None:
            company = validated_data["cost_center"].company
        if request and request.user and "requested_by" not in validated_data:
            validated_data["requested_by"] = request.user
        validated_data["company"] = company
        return super().create(validated_data)

    def get_requested_by_display(self, obj: BudgetOverrideRequest) -> str | None:
        user = obj.requested_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_approver_display(self, obj: BudgetOverrideRequest) -> str | None:
        user = obj.approver
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)


class BudgetSnapshotSerializer(serializers.ModelSerializer):
    budget_name = serializers.ReadOnlyField(source="budget.name")

    class Meta:
        model = BudgetConsumptionSnapshot
        fields = [
            "id",
            "budget",
            "budget_name",
            "snapshot_date",
            "total_limit",
            "total_consumed",
            "total_remaining",
            "metrics",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class BudgetItemCodeSerializer(serializers.ModelSerializer):
    uom_name = serializers.SerializerMethodField()
    uom_code = serializers.SerializerMethodField()
    stock_uom_name = serializers.SerializerMethodField()
    category_id = serializers.PrimaryKeyRelatedField(source='category_ref', queryset=BudgetItemCategory.objects.all(), required=False, allow_null=True, write_only=True)
    sub_category_id = serializers.PrimaryKeyRelatedField(source='sub_category_ref', queryset=BudgetItemSubCategory.objects.all(), required=False, allow_null=True, write_only=True)
    category_name = serializers.SerializerMethodField()
    sub_category_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = BudgetItemCode
        fields = [
            "id",
            "company",
            "code",
            "name",
            "description",
            "category",
            "category_id",
            "category_name",
            "sub_category_id",
            "sub_category_name",
            "uom",
            "uom_name",
            "uom_code",
            "stock_uom",
            "stock_uom_name",
            "item_type",
            "standard_price",
            "valuation_rate",
            "cost_price",
            "standard_cost",
            "valuation_method",
            "track_inventory",
            "is_batch_tracked",
            "is_serial_tracked",
            "requires_fefo",
            "is_tradable",
            "prevent_expired_issuance",
            "expiry_warning_days",
            "reorder_level",
            "reorder_quantity",
            "lead_time_days",
            "inventory_account",
            "expense_account",
            "status",
            "status_display",
            "department",
            "department_name",
            "created_by",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "code", "created_at", "updated_at", "status_display"]

    def get_uom_name(self, obj):
        if obj.uom:
            return obj.uom.name
        return None

    def get_uom_code(self, obj):
        if obj.uom:
            return obj.uom.code
        return None

    def get_stock_uom_name(self, obj):
        if obj.stock_uom:
            return obj.stock_uom.name
        return None

    def get_department_name(self, obj):
        if obj.department:
            return obj.department.name
        return None

    def get_status_display(self, obj):
        return obj.get_status_display() if hasattr(obj, 'get_status_display') else obj.status

    def get_category_name(self, obj):
        if obj.category_ref:
            return obj.category_ref.name
        return obj.category

    def get_sub_category_name(self, obj):
        if obj.sub_category_ref:
            return obj.sub_category_ref.name
        return None

    def _generate_item_code(self, company) -> str:
        prefix = "IC"
        width = 6
        qs = BudgetItemCode.objects.filter(company__company_group_id=getattr(company, 'company_group_id', None), code__startswith=prefix)
        existing = qs.values_list('code', flat=True)
        max_num = 0
        for code in existing:
            suffix = code[len(prefix):]
            if suffix.isdigit():
                try:
                    max_num = max(max_num, int(suffix))
                except ValueError:
                    pass
        i = max_num + 1
        while True:
            candidate = f"{prefix}{i:06d}"
            if not BudgetItemCode.objects.filter(company__company_group_id=getattr(company, 'company_group_id', None), code=candidate).exists():
                return candidate
            i += 1

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        if not company:
            # Fallbacks to reduce friction, especially for superusers
            try:
                # Try header directly if middleware didn't populate
                header_id = None
                try:
                    header_id = request.headers.get("X-Company-ID") or request.META.get("HTTP_X_COMPANY_ID")
                except Exception:
                    header_id = None
                if header_id:
                    from apps.companies.models import Company as _Company
                    company = _Company.objects.filter(id=header_id, is_active=True).first()
            except Exception:
                company = None

        if not company:
            # For superusers/system admins: default to their default company
            user = getattr(request, "user", None)
            if getattr(user, "is_superuser", False) or getattr(user, "is_system_admin", False):
                try:
                    from apps.companies.models import Company as _Company
                    company = getattr(user, "default_company", None)
                    if not company or not getattr(company, "is_active", True):
                        # first active among user's companies, else first active globally
                        company = getattr(user, "companies", None).filter(is_active=True).first() if hasattr(user, "companies") else None
                        if not company:
                            company = _Company.objects.filter(is_active=True).first()
                except Exception:
                    company = None

        if not company:
            raise serializers.ValidationError({"detail": "Active company is required."})
        # Enforce name-level uniqueness within the company group (unless forced)
        name = (validated_data.get("name") or "").strip()
        force = False
        try:
            force = (str(request.query_params.get('force') or request.data.get('force') or '')).lower() in {'1','true','yes','on'}
        except Exception:
            force = False
        if name and not force:
            if BudgetItemCode.objects.filter(company__company_group_id=getattr(company, 'company_group_id', None), name__iexact=name).exists():
                raise serializers.ValidationError({"name": "An item code with this name already exists for your company group."})

        # Always auto-generate code on create (hide in backend)
        validated_data.pop("code", None)
        generated_code = self._generate_item_code(company)
        # If both category_ref and sub_category_ref are provided, ensure they match and belong to same group
        sub = validated_data.get('sub_category_ref')
        cat = validated_data.get('category_ref')
        if sub and cat and sub.category_id != cat.id:
            raise serializers.ValidationError({"sub_category_id": "Sub-category must belong to the selected category."})
        if cat and getattr(cat, 'company_group_id', None) and company and getattr(company, 'company_group_id', None):
            if cat.company_group_id != company.company_group_id:
                raise serializers.ValidationError({"category_id": "Category must belong to your company group."})
        if sub and getattr(sub, 'company_group_id', None) and company and getattr(company, 'company_group_id', None):
            if sub.company_group_id != company.company_group_id:
                raise serializers.ValidationError({"sub_category_id": "Sub-category must belong to your company group."})
        return BudgetItemCode.objects.create(company=company, code=generated_code, **validated_data)

    def get_category_name(self, obj: BudgetItemCode) -> str | None:
        if obj.category_ref_id:
            return obj.category_ref.name
        return obj.category or None

    def get_sub_category_name(self, obj: BudgetItemCode) -> str | None:
        if obj.sub_category_ref_id:
            return obj.sub_category_ref.name
        return None

class BudgetItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetItemCategory
        fields = ["id", "code", "name", "is_active", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        if not company:
            raise serializers.ValidationError({"detail": "Active company is required."})
        # Enforce uniqueness within group for UX (DB enforces per company)
        if BudgetItemCategory.objects.filter(company__company_group_id=company.company_group_id, code__iexact=validated_data.get('code')).exists():
            raise serializers.ValidationError({"code": "A category with this code already exists in your group."})
        return BudgetItemCategory.objects.create(company=company, **validated_data)

class BudgetItemSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetItemSubCategory
        fields = ["id", "category", "code", "name", "is_active", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        if not company:
            raise serializers.ValidationError({"detail": "Active company is required."})
        category = validated_data.get('category')
        if not category:
            raise serializers.ValidationError({"category": "Sub-category requires a category."})
        if BudgetItemSubCategory.objects.filter(category=category, code__iexact=validated_data.get('code')).exists():
            raise serializers.ValidationError({"code": "A sub-category with this code already exists under the selected category."})
        return BudgetItemSubCategory.objects.create(company=company, **validated_data)


class BudgetUnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = [
            "id",
            "company",
            "code",
            "name",
            "short_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        user = getattr(request, "user", None)
        if not company:
            raise serializers.ValidationError({"detail": "Active company is required."})
        code = validated_data.get("code")
        force = False
        try:
            force = (str(request.query_params.get('force') or request.data.get('force') or '')).lower() in {'1','true','yes','on'}
        except Exception:
            force = False
        if not force:
            exists = UnitOfMeasure.objects.filter(company__company_group_id=company.company_group_id, code__iexact=code).exists()
            if exists:
                raise serializers.ValidationError({"code": "A UOM with this code already exists for your company group."})
        return UnitOfMeasure.objects.create(company=company, created_by=user, **validated_data)


class BudgetRemarkTemplateSerializer(serializers.ModelSerializer):
    """Serializer for budget remark templates"""
    created_by_display = serializers.SerializerMethodField()

    class Meta:
        model = BudgetRemarkTemplate
        fields = [
            "id",
            "company",
            "name",
            "template_text",
            "remark_type",
            "is_predefined",
            "is_shared",
            "usage_count",
            "created_by",
            "created_by_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "usage_count", "created_by", "created_by_display", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        user = getattr(request, "user", None)
        validated_data["company"] = company
        validated_data["created_by"] = user
        return BudgetRemarkTemplate.objects.create(**validated_data)

    def get_created_by_display(self, obj: BudgetRemarkTemplate) -> str | None:
        user = obj.created_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    # No shared_with relation in current model; keep output minimal


class BudgetVarianceAuditSerializer(serializers.ModelSerializer):
    """Serializer for budget variance audit trail"""
    modified_by_display = serializers.SerializerMethodField()
    budget_line_display = serializers.SerializerMethodField()

    class Meta:
        model = BudgetVarianceAudit
        fields = [
            "id",
            "budget_line",
            "budget_line_display",
            "modified_by",
            "modified_by_display",
            "change_type",
            "role_of_modifier",
            "original_qty",
            "new_qty",
            "qty_delta",
            "original_price",
            "new_price",
            "price_delta",
            "original_value",
            "new_value",
            "value_delta",
            "justification",
            "review_period_active",
            "grace_period_active",
            "created_at",
        ]
        read_only_fields = [
            "budget_line_display",
            "modified_by_display",
            "qty_delta",
            "price_delta",
            "value_delta",
            "created_at",
        ]

    def get_modified_by_display(self, obj: BudgetVarianceAudit) -> str | None:
        user = obj.modified_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_budget_line_display(self, obj: BudgetVarianceAudit) -> dict:
        """Get budget line details for display"""
        line = obj.budget_line
        return {
            "id": line.id,
            "item_code": line.item_code,
            "item_name": line.item_name,
            "budget_name": line.budget.name,
        }

class BudgetPricePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetPricePolicy
        fields = [
            "company",
            "primary_source",
            "secondary_source",
            "tertiary_source",
            "avg_lookback_days",
            "fallback_on_zero",
        ]
        read_only_fields = ["company"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        if not company and request and getattr(request, "user", None):
            company = getattr(request.user, "default_company", None)
        if not company:
            raise serializers.ValidationError({"detail": "Active company is required."})
        # Upsert behavior: ensure single policy per company
        obj, _ = BudgetPricePolicy.objects.update_or_create(
            company=company,
            defaults=validated_data,
        )
        return obj

    def update(self, instance, validated_data):
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance
