TOUR_MAP = {"world": "world", "elite": "elite", "challenger": "challenger"}


def normalize_tour(val: str | None) -> str | None:
    """Normalize tour value to known keys."""  # MSA-REDESIGN
    if not val:
        return None
    v = str(val).lower().strip()
    return TOUR_MAP.get(v)


def filter_by_tour(qs, tour_field="category", tour=None):
    """Filter queryset by tour if provided."""  # MSA-REDESIGN
    t = normalize_tour(tour)
    if not t:
        return qs
    try:
        return qs.filter(**{f"{tour_field}__iexact": t})
    except Exception:  # pragma: no cover - safety
        return qs
