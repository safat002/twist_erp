from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, NotificationStatus, EmailAwarenessState
from .serializers import NotificationSerializer, NotificationStatusSerializer, EmailAwarenessSerializer


def _resolve_company(request):
    company = getattr(request, "company", None)
    if company:
        return company
    if request.user and request.user.is_authenticated:
        return request.user.companies.filter(is_active=True).first()
    return None


class NotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = Notification.objects.filter(user=self.request.user)
        if company:
            qs = qs.filter(company=company)
        return qs.order_by("-created_at")[:50]


class NotificationCenterView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = Notification.objects.filter(user=self.request.user)
        if company:
            qs = qs.filter(company=company)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        severity = self.request.query_params.get("severity")
        if severity:
            qs = qs.filter(severity=severity)
        return qs.order_by("-created_at")


class NotificationMarkView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationStatusSerializer
    queryset = Notification.objects.all()


class NotificationClearAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        company = _resolve_company(request)
        qs = Notification.objects.filter(user=request.user)
        if company:
            qs = qs.filter(company=company)
        qs.update(status=NotificationStatus.CLEARED)
        return Response({"status": "ok"})


class EmailAwarenessView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = _resolve_company(request)
        qs = EmailAwarenessState.objects.filter(user=request.user)
        if company:
            qs = qs.filter(company=company)
        state = qs.first()
        count = state.unread_count if state else 0
        return Response({"unread": count})

    def post(self, request):
        serializer = EmailAwarenessSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response({"unread": instance.unread_count})
