from __future__ import annotations

from msa.utils.dates import get_active_date


def active_date_ctx(request):
    """Expose active_date and ISO representation to templates."""
    d = get_active_date(request)
    return {"active_date": d, "active_date_iso": d.isoformat()}
