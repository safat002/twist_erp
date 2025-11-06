from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import WorkflowTemplate, WorkflowInstance
from .serializers import WorkflowTemplateSerializer, WorkflowInstanceSerializer
from apps.permissions.drf_permissions import HasPermission
from .services import WorkflowService


class WorkflowTemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = WorkflowTemplateSerializer
    permission_classes = [IsAuthenticated, HasPermission]
    permission_code = "can_edit_workflows"

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = WorkflowTemplate.objects.all().select_related("metadata")
        if company:
            qs = qs.filter(
                Q(scope_type="GLOBAL")
                | Q(scope_type="GROUP", company_group=company.company_group)
                | Q(scope_type="COMPANY", company=company)
            )
        return qs


class WorkflowInstanceCreateView(generics.ListCreateAPIView):
    serializer_class = WorkflowInstanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = WorkflowInstance.objects.select_related("template").all()
        company = getattr(self.request, "company", None)
        if company:
            qs = qs.filter(company=company)

        # Optional approver-targeting: limit to items in my queue
        my_queue_only = str(self.request.query_params.get("my_queue_only", "")).lower() in {"1", "true", "yes"}
        if my_queue_only and getattr(self.request, "user", None):
            user = self.request.user
            try:
                from apps.users.models import UserCompanyRole
                role_ids = list(
                    UserCompanyRole.objects.filter(user=user, company=company, is_active=True)
                    .values_list("role_id", flat=True)
                )
            except Exception:
                role_ids = []

            qs = qs.filter(
                Q(assigned_to=user)
                | (
                    Q(assigned_to__isnull=True)
                    & Q(approver_role_id__in=role_ids)
                )
            )

        return qs.order_by("-updated_at")


class WorkflowTransitionView(APIView):
    def post(self, request, pk):
        try:
            instance = WorkflowInstance.objects.select_related("template").get(pk=pk)
        except WorkflowInstance.DoesNotExist:
            return Response({"detail": "Workflow instance not found"}, status=status.HTTP_404_NOT_FOUND)

        to_state = request.data.get("to")
        if not to_state:
            return Response({"detail": "'to' state required"}, status=status.HTTP_400_BAD_REQUEST)

        definition = instance.template.definition or {}
        allowed = definition.get("transitions", {}).get(instance.state, [])
        if allowed and to_state not in allowed:
            return Response({"detail": f"Transition from {instance.state} to {to_state} not allowed"}, status=400)

        instance.state = to_state
        instance.save(update_fields=["state", "updated_at"])
        return Response(WorkflowInstanceSerializer(instance).data)


class WorkflowApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            instance = WorkflowInstance.objects.select_related("template").get(pk=pk)
        except WorkflowInstance.DoesNotExist:
            return Response({"detail": "Workflow instance not found"}, status=status.HTTP_404_NOT_FOUND)

        # Authorization: only assignee or user with approver role for this company can approve
        user = request.user
        company = getattr(request, "company", None)
        if getattr(instance, "assigned_to_id", None) and instance.assigned_to_id != user.id:
            return Response({"detail": "This workflow is assigned to another user."}, status=403)
        if getattr(instance, "approver_role_id", None):
            try:
                from apps.users.models import UserCompanyRole
                has_role = UserCompanyRole.objects.filter(
                    user=user, company=company or instance.company, role_id=instance.approver_role_id, is_active=True
                ).exists()
            except Exception:
                has_role = False
            if not has_role and not user.is_superuser:
                return Response({"detail": "You are not authorized to approve this workflow."}, status=403)

        definition = instance.template.definition or {}
        allowed = set(definition.get("transitions", {}).get(instance.state, []))
        if allowed and 'approved' not in allowed:
            return Response({"detail": f"Cannot approve from state '{instance.state}'"}, status=400)

        WorkflowService.trigger_transition(instance, 'approved')
        return Response(WorkflowInstanceSerializer(instance).data)
