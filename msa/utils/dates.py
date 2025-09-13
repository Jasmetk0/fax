from __future__ import annotations

from datetime import date, datetime

from django.apps import apps

FMTS = ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d")


def _parse_date(value: str) -> date | None:
    """Try to parse *value* using multiple date formats."""
    if not value:
        return None
    for fmt in FMTS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except Exception:
            pass
    return None


def get_active_date(request) -> date:
    """Return active date from request or today.

    Order of sources:
    - query param ``d`` or ``date``
    - session keys ``global_date`` or ``woorld_today``
    - cookie ``global_date``
    Fallback to ``date.today()``.
    """

    # query params first
    for key in ("d", "date"):
        if key in request.GET:
            d = _parse_date(request.GET.get(key))
            if d:
                return d

    # session values
    session = getattr(request, "session", {})
    for key in ("global_date", "woorld_today"):
        value = session.get(key)
        if isinstance(value, date):
            return value
        d = _parse_date(str(value))
        if d:
            return d

    # cookies
    cookie_val = request.COOKIES.get("global_date")
    d = _parse_date(cookie_val)
    if d:
        return d

    return date.today()


def find_season_for_date(d: date):
    """Return Season object that includes date ``d``.

    The function is tolerant to various season schemas and returns ``None`` when
    the model is unavailable or no season matches the given date.
    """

    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    if not Season:
        return None

    fields = {f.name for f in Season._meta.get_fields()}
    qs = Season.objects.all()

    if {"start_date", "end_date"}.issubset(fields):
        return qs.filter(start_date__lte=d, end_date__gte=d).order_by("id").first()
    if {"from_date", "to_date"}.issubset(fields):
        return qs.filter(from_date__lte=d, to_date__gte=d).order_by("id").first()
    if "year" in fields:
        return qs.filter(year=d.year).order_by("id").first()
    if {"start_year", "end_year"}.issubset(fields):
        return qs.filter(start_year__lte=d.year, end_year__gte=d.year).order_by("id").first()

    # last resort: guess by season name
    return qs.filter(name__icontains=str(d.year)).order_by("id").first()
