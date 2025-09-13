from __future__ import annotations

from django.conf import settings


def admin_flags(request):
    """Expose admin flags into templates.
    - admin_mode: bool (session 'admin_mode' overrides settings.MSA_ADMIN_MODE)
    - is_staff_user: bool
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
    return {
        "admin_mode": admin_mode,
        "is_staff_user": is_staff,
    }
