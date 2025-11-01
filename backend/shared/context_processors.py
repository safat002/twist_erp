from typing import Dict, List


POPULAR_THEMES: List[Dict[str, str]] = [
    {"id": "default", "name": "Default"},
    {"id": "flatly", "name": "Flatly"},
    {"id": "cosmo", "name": "Cosmo"},
    {"id": "cyborg", "name": "Cyborg (dark)"},
    {"id": "darkly", "name": "Darkly (dark)"},
    {"id": "journal", "name": "Journal"},
    {"id": "minty", "name": "Minty"},
    {"id": "pulse", "name": "Pulse"},
    {"id": "slate", "name": "Slate (dark)"},
    {"id": "solar", "name": "Solar (dark)"},
    {"id": "yeti", "name": "Yeti"},
]


def admin_theme(request):
    theme = request.session.get("admin_theme") or request.COOKIES.get("admin_theme")
    # Prefer user preference if available; sync to session
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False) and hasattr(user, "admin_theme"):
        if user.admin_theme:
            if theme != user.admin_theme:
                request.session["admin_theme"] = user.admin_theme
            theme = user.admin_theme
    if not theme:
        theme = "default"
    return {
        "admin_theme": theme,
        "available_themes": POPULAR_THEMES,
    }
