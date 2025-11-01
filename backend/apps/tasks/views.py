from datetime import timedelta

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TaskItem, TaskStatus, TaskVisibility, TaskType
from .serializers import TaskItemSerializer, TaskStatusUpdateSerializer


def _resolve_company(request):
    company = getattr(request, "company", None)
    if company:
        return company
    if request.user and request.user.is_authenticated:
        return request.user.companies.filter(is_active=True).first()
    return None


class TaskListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskItemSerializer

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = TaskItem.objects.select_related("assigned_to", "assigned_by")
        if company:
            qs = qs.filter(company=company)
        assigned_to = self.request.query_params.get("assigned_to")
        if assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)
        my_only = self.request.query_params.get("mine")
        if my_only in {"1", "true", "yes"}:
            qs = qs.filter(assigned_to=self.request.user)
        status_value = self.request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs.order_by("status", "due_date")


class MyTasksView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskItemSerializer

    def get_queryset(self):
        company = _resolve_company(self.request)
        now = timezone.now()
        qs = TaskItem.objects.filter(assigned_to=self.request.user)
        if company:
            qs = qs.filter(company=company)
        # Overdue + due today + due tomorrow + upcoming + no due date ordering
        tomorrow = now + timedelta(days=1)
        return qs.order_by(
            "-priority",
            "status",
            "due_date",
            "-id",
        )


class TeamTasksView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskItemSerializer

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = TaskItem.objects.filter(assigned_by=self.request.user)
        if company:
            qs = qs.filter(company=company)
        return qs.order_by("status", "due_date")


class TaskStatusUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskStatusUpdateSerializer
    queryset = TaskItem.objects.all()


class TaskSnoozeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        minutes = int(request.data.get("minutes") or 60)
        task = TaskItem.objects.get(pk=pk)
        if task.assigned_to_id != request.user.id and task.assigned_by_id != request.user.id:
            return Response({"detail": "Not allowed"}, status=403)
        new_due = (task.due_date or timezone.now()) + timedelta(minutes=minutes)
        task.due_date = new_due
        task.save(update_fields=["due_date", "updated_at"])
        return Response({"due_date": task.due_date})


class TaskEscalateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        task = TaskItem.objects.get(pk=pk)
        if task.assigned_by_id != request.user.id:
            return Response({"detail": "Only assigner can escalate"}, status=403)
        # Simple escalate policy: manager -> team -> exec
        order = [TaskVisibility.MANAGER_VISIBLE, TaskVisibility.TEAM_VISIBLE, TaskVisibility.EXEC_VISIBLE]
        try:
            idx = order.index(task.visibility_scope)
        except ValueError:
            idx = -1
        if idx + 1 < len(order):
            task.visibility_scope = order[idx + 1]
            task.save(update_fields=["visibility_scope", "updated_at"])
        return Response({"visibility_scope": task.visibility_scope})


class TaskCalendarSyncView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # Placeholder: mark as "pending"; real integration via MS Graph can be added later
        task = TaskItem.objects.get(pk=pk)
        task.calendar_sync_status = "pending"
        task.save(update_fields=["calendar_sync_status", "updated_at"])
        return Response({"status": task.calendar_sync_status})

