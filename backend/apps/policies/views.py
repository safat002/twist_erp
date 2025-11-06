from __future__ import annotations

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import PolicyDocument, PolicyAcknowledgement, PolicyCategory, PolicyChangeLog
from .serializers import PolicyDocumentSerializer, PolicyAcknowledgementSerializer, PolicyCategorySerializer
from apps.notifications.models import Notification, NotificationSeverity
from django.db import models
from apps.permissions.permissions import has_permission
from apps.users.models import UserCompanyRole


class CompanyScopedQuerysetMixin:
    permission_classes = [IsAuthenticated]

    def get_company(self):
        return getattr(self.request, "company", None)

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        return qs

    def get_serializer_context(self):  # type: ignore[override]
        ctx = super().get_serializer_context()
        ctx.setdefault("request", self.request)
        return ctx


class PolicyDocumentViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PolicyDocument.objects.all().order_by("-updated_at")
    serializer_class = PolicyDocumentSerializer

    def _require_perm(self, request, code: str):
        company = self.get_company()
        if not has_permission(request.user, code, company):
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def perform_create(self, serializer):
        denied = self._require_perm(self.request, "policies.create")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        instance = serializer.save()
        try:
            PolicyChangeLog.objects.create(
                policy=instance,
                version=instance.version or 1,
                change_type="created",
                notes=self.request.data.get("_change_note", ""),
                changed_by=self.request.user,
            )
        except Exception:
            pass

    def perform_update(self, serializer):
        denied = self._require_perm(self.request, "policies.update")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        instance = serializer.save()
        try:
            PolicyChangeLog.objects.create(
                policy=instance,
                version=instance.version or 1,
                change_type="updated",
                notes=self.request.data.get("_change_note", ""),
                changed_by=self.request.user,
            )
        except Exception:
            pass

    def perform_destroy(self, instance):
        denied = self._require_perm(self.request, "policies.delete")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        instance.delete()

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        policy: PolicyDocument = self.get_object()
        # Permission: specific code OR owner/system admin
        if not (has_permission(request.user, "policies.publish", policy.company) or getattr(request.user, "is_system_admin", False) or policy.owner_id == request.user.id):
            return Response({"detail": "You are not allowed to publish this policy."}, status=status.HTTP_403_FORBIDDEN)
        # Increment version on publish
        latest = (
            PolicyDocument.objects.filter(company=policy.company, code=policy.code)
            .order_by("-version")
            .first()
        )
        next_version = (latest.version + 1) if latest else (policy.version or 1)
        policy.version = next_version
        policy.status = PolicyDocument.Status.ACTIVE
        policy.published_at = timezone.now()
        policy.save(update_fields=["version", "status", "published_at", "updated_at"])
        try:
            PolicyChangeLog.objects.create(
                policy=policy,
                version=policy.version or 1,
                change_type="published",
                notes=self.request.data.get("_change_note", ""),
                changed_by=self.request.user,
            )
        except Exception:
            pass
        # Notifications for acknowledgement-required
        if policy.requires_acknowledgement:
            try:
                # Optional: audience_roles (list of role IDs) to target notifications
                audience_roles = request.data.get("audience_roles") or []
                if isinstance(audience_roles, list) and audience_roles:
                    role_user_ids = list(
                        UserCompanyRole.objects.filter(company=policy.company, role_id__in=audience_roles, is_active=True)
                        .values_list("user_id", flat=True)
                    )
                    users = policy.company.users.filter(id__in=role_user_ids)
                else:
                    users = policy.company.users.all()
                Notification.objects.bulk_create(
                    [
                        Notification(
                            company=policy.company,
                            user=u,
                            title=f"Policy {policy.code} v{policy.version} requires acknowledgement",
                            body=policy.title,
                            severity=NotificationSeverity.INFO,
                            entity_type="PolicyDocument",
                            entity_id=str(policy.id),
                            group_key=f"POL_ACK_{policy.code}",
                        )
                        for u in users
                    ]
                )
            except Exception:  # noqa: BLE001
                pass
        return Response(self.get_serializer(policy).data)

    @action(detail=True, methods=["post"], url_path="acknowledge")
    def acknowledge(self, request, pk=None):
        policy: PolicyDocument = self.get_object()
        if not policy.requires_acknowledgement:
            return Response({"detail": "Acknowledgement not required for this policy."}, status=status.HTTP_400_BAD_REQUEST)
        ack, created = PolicyAcknowledgement.objects.get_or_create(
            company=self.get_company(),
            policy=policy,
            user=request.user,
            version=policy.version,
            defaults={"note": request.data.get("note", "")},
        )
        if not created and request.data.get("note"):
            ack.note = request.data.get("note")
            ack.save(update_fields=["note", "acknowledged_at"])
        return Response(PolicyAcknowledgementSerializer(ack).data)

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, pk=None):
        policy: PolicyDocument = self.get_object()
        qs = (
            PolicyDocument.objects.filter(company=policy.company, code=policy.code)
            .order_by("-version")
        )
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=False, methods=["get"], url_path="my-pending")
    def my_pending(self, request):
        company = self.get_company()
        user = request.user
        required = PolicyDocument.objects.filter(company=company, requires_acknowledgement=True, status=PolicyDocument.Status.ACTIVE)
        pending = required.exclude(acknowledgements__user=user, acknowledgements__version=models.F("version"))
        page = self.paginate_queryset(pending)
        serializer = self.get_serializer(page or pending, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class PolicyAcknowledgementViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PolicyAcknowledgement.objects.all().order_by("-acknowledged_at")
    serializer_class = PolicyAcknowledgementSerializer

    @action(detail=False, methods=["get"], url_path="my-acks")
    def my_acks(self, request):
        qs = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)


class PolicyCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = PolicyCategory.objects.filter(is_active=True).order_by("code")
    serializer_class = PolicyCategorySerializer

    def _require_manage(self, request):
        from apps.permissions.permissions import has_permission
        # Categories are global; use company from request context if any
        company = getattr(request, "company", None)
        if not has_permission(request.user, "policies.manage_categories", company):
            return Response({"detail": "You do not have permission to manage categories."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def perform_create(self, serializer):
        denied = self._require_manage(self.request)
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_update(self, serializer):
        denied = self._require_manage(self.request)
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_destroy(self, instance):
        denied = self._require_manage(self.request)
        if denied:
            raise PermissionError(denied.data.get("detail"))
        instance.delete()
