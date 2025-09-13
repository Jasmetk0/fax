from __future__ import annotations

from datetime import date, datetime
from importlib import import_module

from django.apps import apps

FMTS = ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y", "%Y.%m.%d")


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


def _woorld_to_gregorian(value):
    """
    Best-effort převod „woorld“ data (string/dict) na gregoriánský ``date``.
    """

    # 1) Pokud je to už parsovatelný string, zkus standardní formáty
    if isinstance(value, str):
        d = _parse_date(value)
        if d:
            return d

    # 2) Zkus konverzi přes fax_calendar (pokud je nainstalován)
    try:
        candidates = [
            (
                "fax_calendar.utils",
                (
                    "woorld_to_gregorian",
                    "to_gregorian",
                    "to_gregorian_date",
                    "as_gregorian",
                    "convert_to_gregorian",
                ),
            ),
            ("fax_calendar.api", ("woorld_to_gregorian", "to_gregorian", "convert")),
            ("fax_calendar.convert", ("woorld_to_gregorian", "to_gregorian")),
        ]

        for mod_name, fn_names in candidates:
            try:
                mod = import_module(mod_name)
            except Exception:
                continue
            for fn in fn_names:
                f = getattr(mod, fn, None)
                if not f:
                    continue
                try:
                    res = f(value)
                except Exception:
                    continue

                if hasattr(res, "date"):
                    return res.date()
                if hasattr(res, "year") and hasattr(res, "month") and hasattr(res, "day"):
                    return date(int(res.year), int(res.month), int(res.day))
                if isinstance(res, str):
                    d = _parse_date(res)
                    if d:
                        return d
    except Exception:
        pass

    # 3) dict {year,month,day} nebo {y,m,d}
    try:
        if isinstance(value, dict):
            y = value.get("year") or value.get("y")
            m = value.get("month") or value.get("m")
            d = value.get("day") or value.get("d")
            if all(isinstance(x, int) for x in (y, m, d)):
                return date(y, m, d)
    except Exception:
        pass

    return None


def get_active_date(request) -> date:
    """Return active date from request or today.

    Order of sources:
    - query param ``d`` or ``date``
    - session keys ``global_date``, ``woorld_today``, ``woorld_date``, ``topbar_date``
    - corresponding cookies (``global_date``, ``topbar_date``, ``woorld_today``, ``woorld_date``)
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
    for key in ("global_date", "woorld_today", "woorld_date", "topbar_date"):
        value = session.get(key)
        if isinstance(value, date):
            return value
        d = _parse_date(str(value))
        if d:
            return d
        d2 = _woorld_to_gregorian(value)
        if d2:
            return d2

    # cookies
    cookie_val = (
        request.COOKIES.get("global_date")
        or request.COOKIES.get("topbar_date")
        or request.COOKIES.get("woorld_today")
        or request.COOKIES.get("woorld_date")
    )
    d = _parse_date(cookie_val)
    if d:
        return d
    d2 = _woorld_to_gregorian(cookie_val)
    if d2:
        return d2

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
