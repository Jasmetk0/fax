from __future__ import annotations

from django.conf import settings


def admin_mode_on(request) -> bool:
    try:
        ses = request.session.get("admin_mode")
    except Exception:
        ses = None
    base = bool(getattr(settings, "MSA_ADMIN_MODE", False))
    return bool(ses) if ses is not None else base
