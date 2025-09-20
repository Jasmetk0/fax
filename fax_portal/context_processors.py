from __future__ import annotations

from django.conf import settings

MSA_TOURNAMENT_VIEWS = {
    "msa:tournament_info",
    "msa:tournament_program",
    "msa:tournament_draws",
    "msa:tournament_players",
    "msa:tournament_media",
}

TOURNAMENT_ADMIN_ACTIONS = [
    {"label": "Recalculate", "action": "recalculate"},
    {"label": "Confirm Qualification", "action": "confirm-qualification"},
    {"label": "Confirm Main Draw", "action": "confirm-main-draw"},
    {"label": "Regenerate Unseeded", "action": "regen-unseeded"},
    {"label": "Planning tools", "action": "planning-tools"},
    {"label": "Bulk Best-Of", "action": "bulk-best-of"},
    {"label": "Archive snapshot", "action": "archive-snapshot"},
    {"label": "Reopen MD", "action": "reopen-md"},
]

TOURNAMENTS_LIST_ACTIONS = [
    {"label": "New tournament", "action": "new-tournament"},
    {"label": "Bulk ops", "action": "bulk-ops"},
    {"label": "Export calendar", "action": "export-calendar"},
]

CALENDAR_ACTIONS = [
    {"label": "Normalize day", "action": "normalize-day"},
    {"label": "Clear day", "action": "clear-day"},
    {"label": "Export ICS", "action": "export-ics"},
]


def _toolbar_actions(request):
    match = getattr(request, "resolver_match", None)
    view_name = getattr(match, "view_name", "") if match else ""
    if view_name == "msa:tournaments_list":
        return [dict(item) for item in TOURNAMENTS_LIST_ACTIONS]
    if view_name == "msa:calendar":
        return [dict(item) for item in CALENDAR_ACTIONS]
    if view_name in MSA_TOURNAMENT_VIEWS:
        return [dict(item) for item in TOURNAMENT_ADMIN_ACTIONS]
    return []


def admin_flags(request):
    """Expose admin flags into templates.
    - admin_mode: bool (session 'admin_mode' overrides settings.MSA_ADMIN_MODE)
    - is_staff_user: bool
    - admin_readonly: bool (settings.MSA_ADMIN_READONLY, default True)
    """
    admin_mode = bool(getattr(settings, "MSA_ADMIN_MODE", False))
    try:
        if hasattr(request, "session") and request.session is not None:
            ses = request.session.get("admin_mode")
            if ses is not None:
                admin_mode = bool(ses)
    except Exception:
        pass
    is_staff = bool(getattr(getattr(request, "user", None), "is_staff", False))
    admin_readonly = bool(getattr(settings, "MSA_ADMIN_READONLY", True))
    return {
        "admin_mode": admin_mode,
        "is_staff_user": is_staff,
        "admin_toolbar_actions": _toolbar_actions(request),
        "admin_readonly": admin_readonly,
    }
