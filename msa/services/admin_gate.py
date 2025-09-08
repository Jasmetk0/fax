from __future__ import annotations

from functools import wraps

from django.conf import settings
from django.core.exceptions import ValidationError


def require_admin_mode(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not bool(getattr(settings, "MSA_ADMIN_MODE", False)):
            raise ValidationError("Admin Mode is OFF. Enable settings.MSA_ADMIN_MODE to proceed.")
        return fn(*args, **kwargs)

    return wrapper
