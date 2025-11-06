from datetime import timedelta
import secrets

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.core import signing
from django.contrib.auth import get_user_model
from apps.companies.models import Company
import requests
from urllib.parse import quote_plus

from .models import TaskItem, TaskStatus, TaskVisibility, TaskType, UserCalendarLink, UserCalendarCredential
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


class CalendarEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = _resolve_company(request)
        days = int(request.query_params.get("days") or 7)
        days = max(1, min(days, 60))
        end = timezone.now() + timedelta(days=days)
        qs = TaskItem.objects.filter(assigned_to=request.user, due_date__isnull=False, due_date__lte=end)
        if company:
            qs = qs.filter(company=company)
        events = [
            {
                "id": t.id,
                "title": t.title,
                "start": t.due_date.isoformat(),
                "end": t.due_date.isoformat(),
                "status": t.status,
                "priority": t.priority,
            }
            for t in qs.order_by("due_date")[:100]
        ]
        # Merge Outlook events if linked and credentials present
        try:
            link = UserCalendarLink.objects.filter(user=request.user, company=company, provider="outlook", is_enabled=True).first()
            cred = UserCalendarCredential.objects.filter(user=request.user, company=company, provider="outlook").first()
            if link and cred:
                ext = _fetch_outlook_events(cred, end)
                events.extend(ext)
        except Exception:
            # Soft-fail to avoid breaking dashboard
            pass
        return Response({"results": events})


class CalendarMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = _resolve_company(request)
        link = UserCalendarLink.objects.filter(user=request.user, company=company).first()
        ics_url = None
        if link and link.is_enabled:
            base = request.build_absolute_uri("/").rstrip("/")
            ics_url = f"{base}/api/v1/tasks/calendar.ics?token={link.ics_token}"
        return Response(
            {
                "enabled": bool(link and link.is_enabled),
                "email": link.email if link else "",
                "provider": link.provider if link else "google",
                "ics_url": ics_url,
            }
        )

    def post(self, request):
        company = _resolve_company(request)
        if not company:
            return Response({"detail": "Active company context is required."}, status=400)
        enabled = bool(request.data.get("enabled", True))
        email = (request.data.get("email") or "").strip()
        provider = (request.data.get("provider") or "google").lower()
        link, _ = UserCalendarLink.objects.get_or_create(
            user=request.user,
            company=company,
            company_group=company.company_group if company else None,
            defaults={
                "provider": provider,
                "email": email,
                "is_enabled": enabled,
                "ics_token": secrets.token_hex(32),
                },
        )
        # Update
        changed = False
        if link.provider != provider:
            link.provider = provider
            changed = True
        if link.email != email:
            link.email = email
            changed = True
        if link.is_enabled != enabled:
            link.is_enabled = enabled
            changed = True
        if not link.ics_token:
            link.ics_token = timezone.now().strftime("%s%f")
            changed = True
        if changed:
            link.save(update_fields=["provider", "email", "is_enabled", "ics_token", "updated_at"])
        base = request.build_absolute_uri("/").rstrip("/")
        ics_url = f"{base}/api/v1/tasks/calendar.ics?token={link.ics_token}" if link.is_enabled else None
        return Response({"enabled": link.is_enabled, "email": link.email, "provider": link.provider, "ics_url": ics_url})


class CalendarFeedICSView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            return Response("Missing token", status=400)
        try:
            link = UserCalendarLink.objects.select_related("user", "company").get(ics_token=token, is_enabled=True)
        except UserCalendarLink.DoesNotExist:
            return Response("Not found", status=404)
        # Build ICS
        now = timezone.now()
        end = now + timedelta(days=30)
        qs = TaskItem.objects.filter(company=link.company, assigned_to=link.user, due_date__isnull=False, due_date__lte=end).order_by("due_date")[:500]
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Twist ERP//Tasks//EN",
            "CALSCALE:GREGORIAN",
            f"X-WR-CALNAME:Twist Tasks ({link.company.code})",
        ]
        for t in qs:
            dt = t.due_date.strftime("%Y%m%dT%H%M%SZ")
            uid = f"task-{t.id}@twist"
            summary = t.title.replace("\n", " ")
            desc = (t.description or "").replace("\n", " ")[:500]
            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now.strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{dt}",
                f"DTEND:{dt}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc}",
                f"STATUS:{'CONFIRMED' if t.status == 'done' else 'TENTATIVE'}",
                "END:VEVENT",
            ]
        lines.append("END:VCALENDAR")
        content = "\r\n".join(lines) + "\r\n"
        from django.http import HttpResponse
        response = HttpResponse(content, content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="twist-tasks.ics"'
        return response


def _fetch_outlook_events(cred: UserCalendarCredential, end_dt):
    """Fetch upcoming Outlook events via Microsoft Graph. Soft-fails on config/network errors."""
    client_id = getattr(settings, "OUTLOOK_CLIENT_ID", None)
    client_secret = getattr(settings, "OUTLOOK_CLIENT_SECRET", None)
    tenant = getattr(settings, "OUTLOOK_TENANT", "common")
    if not client_id or not client_secret:
        return []
    # Refresh token if needed
    if cred.expires_at and cred.expires_at <= timezone.now():
        try:
            token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": cred.refresh_token,
                "scope": "offline_access Calendars.Read",
            }
            r = requests.post(token_url, data=data, timeout=10)
            if r.ok:
                tok = r.json()
                cred.access_token = tok.get("access_token", cred.access_token)
                cred.refresh_token = tok.get("refresh_token", cred.refresh_token)
                expires_in = int(tok.get("expires_in", 3600))
                cred.expires_at = timezone.now() + timedelta(seconds=expires_in - 60)
                cred.save(update_fields=["access_token", "refresh_token", "expires_at", "updated_at"])
        except Exception:
            return []
    # Query calendarView for window
    try:
        headers = {"Authorization": f"Bearer {cred.access_token}"}
        start_iso = timezone.now().isoformat()
        end_iso = end_dt.isoformat()
        url = f"https://graph.microsoft.com/v1.0/me/calendarView?startDateTime={start_iso}&endDateTime={end_iso}&$select=subject,start,end,webLink,organizer&$top=50&$orderby=start/dateTime"
        r = requests.get(url, headers=headers, timeout=10)
        if not r.ok:
            return []
        data = r.json()
        items = data.get("value", [])
        events = []
        for it in items:
            start = (it.get("start") or {}).get("dateTime")
            end = (it.get("end") or {}).get("dateTime")
            subject = it.get("subject") or "(No title)"
            web_link = it.get("webLink")
            events.append({
                "id": web_link or subject,
                "title": subject,
                "start": start,
                "end": end,
                "source": "outlook",
                "url": web_link,
            })
        return events
    except Exception:
        return []


class OutlookAuthURLView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        client_id = getattr(settings, "OUTLOOK_CLIENT_ID", None)
        tenant = getattr(settings, "OUTLOOK_TENANT", "common")
        redirect_uri = getattr(settings, "OUTLOOK_REDIRECT_URI", None)
        missing = []
        if not client_id:
            missing.append("OUTLOOK_CLIENT_ID")
        if not redirect_uri:
            missing.append("OUTLOOK_REDIRECT_URI")
        if missing:
            return Response({"detail": f"Outlook OAuth is not configured (missing: {', '.join(missing)})"}, status=400)
        scope = "offline_access Calendars.Read"
        # Signed state to bind callback to user/company
        company = _resolve_company(request)
        state_payload = {"u": request.user.id, "c": getattr(company, 'id', None)}
        state = signing.dumps(state_payload, salt="outlook-oauth")
        auth_url = (
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?"
            f"client_id={client_id}&response_type=code&redirect_uri={quote_plus(redirect_uri)}&response_mode=query&scope={quote_plus(scope)}&state={quote_plus(state)}"
        )
        return Response({"auth_url": auth_url})


class OutlookAuthCallbackView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        client_id = getattr(settings, "OUTLOOK_CLIENT_ID", None)
        client_secret = getattr(settings, "OUTLOOK_CLIENT_SECRET", None)
        tenant = getattr(settings, "OUTLOOK_TENANT", "common")
        redirect_uri = getattr(settings, "OUTLOOK_REDIRECT_URI", None)
        missing = []
        if not client_id:
            missing.append("OUTLOOK_CLIENT_ID")
        if not client_secret:
            missing.append("OUTLOOK_CLIENT_SECRET")
        if not redirect_uri:
            missing.append("OUTLOOK_REDIRECT_URI")
        if not code:
            missing.append("code")
        if not state:
            missing.append("state")
        if missing:
            return Response(f"Missing configuration or parameters: {', '.join(missing)}", status=400)
        try:
            token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "scope": "offline_access Calendars.Read",
            }
            r = requests.post(token_url, data=data, timeout=10)
            if not r.ok:
                return Response("Token exchange failed", status=400)
            tok = r.json()
            access_token = tok.get("access_token")
            refresh_token = tok.get("refresh_token")
            expires_in = int(tok.get("expires_in", 3600))
            try:
                payload = signing.loads(state, salt="outlook-oauth")
                user_id = int(payload.get("u"))
                company_id = int(payload.get("c")) if payload.get("c") is not None else None
            except Exception:
                return Response("Invalid state", status=400)
            User = get_user_model()
            try:
                user = User.objects.get(pk=user_id)
                company = Company.objects.get(pk=company_id) if company_id else None
            except User.DoesNotExist:
                return Response("User not found for state", status=400)
            if not company:
                return Response("Company context missing", status=400)
            # Persist credentials
            expires_at = timezone.now() + timedelta(seconds=expires_in - 60)
            cred, _ = UserCalendarCredential.objects.get_or_create(
                user=user,
                company=company,
                company_group=company.company_group,
                provider="outlook",
                defaults={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_at": expires_at,
                    "scope": "offline_access Calendars.Read",
                },
            )
            if cred.access_token != access_token or cred.refresh_token != refresh_token:
                cred.access_token = access_token
                cred.refresh_token = refresh_token
                cred.expires_at = expires_at
                cred.scope = "offline_access Calendars.Read"
                cred.save(update_fields=["access_token", "refresh_token", "expires_at", "scope", "updated_at"])
            html = "<html><body><h3>Outlook connected.</h3><p>You can close this window and return to Twist ERP.</p></body></html>"
            return Response(html)
        except Exception:
            return Response("Auth error", status=400)
