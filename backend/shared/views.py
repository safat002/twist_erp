from __future__ import annotations

import datetime
import platform
from typing import Dict

from django.db import connections
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

START_TIME = datetime.datetime.utcnow()


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        db_payload = self._database_status()
        uptime_seconds = int((datetime.datetime.utcnow() - START_TIME).total_seconds())
        payload = {
            "status": "ok" if db_payload["ok"] else "degraded",
            "uptime_seconds": uptime_seconds,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "application": {
                "version": getattr(request, "version", None),
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "database": db_payload,
        }
        http_status = status.HTTP_200_OK if db_payload["ok"] else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=http_status)

    def _database_status(self) -> Dict:
        payload = {"ok": True, "details": {}}
        for alias in connections:
            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                payload["details"][alias] = "connected"
            except Exception as exc:
                payload["ok"] = False
                payload["details"][alias] = f"error: {exc}"
        return payload
