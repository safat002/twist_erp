from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from shared.context_processors import POPULAR_THEMES


@staff_member_required
def admin_appearance(request: HttpRequest) -> HttpResponse:
    current = request.session.get("admin_theme", "default")
    ctx = {
        "available_themes": POPULAR_THEMES,
        "current_theme": current,
    }
    return render(request, "admin/appearance.html", ctx)


@staff_member_required
def set_admin_theme(request: HttpRequest, theme: str) -> HttpResponse:
    allowed = {t["id"] for t in POPULAR_THEMES}
    if theme in allowed:
        request.session["admin_theme"] = theme
        user = request.user
        if getattr(user, "is_authenticated", False):
            try:
                if hasattr(user, "admin_theme"):
                    user.admin_theme = theme
                    user.save(update_fields=["admin_theme"])
            except Exception:
                # Fail soft; session value still applies
                pass
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or reverse("admin:index")
    response = redirect(next_url)
    try:
        # Store theme in long-lived cookie so login page can style before auth
        response.set_cookie("admin_theme", request.session.get("admin_theme", "default"), max_age=60*60*24*365)
    except Exception:
        pass
    return response
