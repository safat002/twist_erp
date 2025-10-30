from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import WorkflowTemplate, WorkflowInstance
from .serializers import WorkflowTemplateSerializer, WorkflowInstanceSerializer
from apps.permissions.drf_permissions import HasPermission


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


class WorkflowInstanceCreateView(generics.CreateAPIView):
    serializer_class = WorkflowInstanceSerializer


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
