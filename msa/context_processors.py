from __future__ import annotations

from django.conf import settings


def msa_admin_mode(request):
    return {"MSA_ADMIN_MODE": bool(getattr(settings, "MSA_ADMIN_MODE", False))}
