"""Context processors for Woorld calendar."""


def woorld_date(request):
    # WOORLD_SAFE_GUARD: respektuj již zvolená data v session/cookies a nic nepřepisuj
    """Add current Woorld date stored in session to templates."""
    return {"WOORLD_CURRENT_DATE": request.session.get("woorld_current_date", "")}


def woorld_calendar_meta(request):
    """Expose calendar metadata for the current session year.

    The year is taken from the stored session date if present; otherwise
    year 1 is assumed.
    """

    import json

    from . import core
    from .utils import parse_woorld_date

    date_str = request.session.get("woorld_current_date", "")
    try:
        year, _, _ = parse_woorld_date(date_str)
        if year is None:
            raise ValueError
    except Exception:
        year = 1
    meta = {
        "year": year,
        "E": core.E(year),
        "month_lengths": core.month_lengths(year),
        "anchors": core.anchors(year),
        "weekday_names": core.WEEKDAY_NAMES,
    }
    return {
        "WOORLD_CALENDAR_META": meta,
        "WOORLD_CALENDAR_MONTH_LENGTHS_JSON": json.dumps(meta["month_lengths"]),
        "WOORLD_CALENDAR_ANCHORS_JSON": json.dumps(meta["anchors"]),
        "WOORLD_TODAY": request.session.get("woorld_today"),
    }
