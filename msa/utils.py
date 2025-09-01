from .models import RankingSnapshot


TOUR_MAP = {"world": "world", "elite": "elite", "challenger": "challenger"}


def normalize_tour(val: str | None) -> str | None:
    """Normalize tour value to known keys."""  # MSA-REDESIGN
    if not val:
        return None
    v = str(val).lower().strip()
    return TOUR_MAP.get(v)


def filter_by_tour(qs, tour_field="category__name", tour=None):
    """Filter queryset by tour if provided."""  # MSA-REDESIGN
    t = normalize_tour(tour)
    if not t:
        return qs
    try:
        return qs.filter(**{f"{tour_field}__iexact": t})
    except Exception:  # pragma: no cover - safety
        return qs


def resolve_ranking_snapshot(date):
    """Return ranking snapshot for given date.

    Prefer the latest snapshot with ``as_of`` less than or equal to ``date``.
    If none exists, attempt to find a snapshot with the exact date. When no
    snapshot is found, return ``None``.
    """

    if not date:
        return None
    snap = RankingSnapshot.objects.filter(as_of__lte=date).order_by("-as_of").first()
    if snap:
        return snap
    return RankingSnapshot.objects.filter(as_of=date).first()
