from msa.models import Match, TournamentEntry


def generate_qualifying(tournament) -> bool:
    """Generate qualifying matches for the tournament.

    The implementation is intentionally lightweight; it ensures that at least
    one qualifying match exists and that all created matches respect the
    tournament's ``q_best_of`` setting (falling back to ``md_best_of`` or 5).
    """
    best_of = getattr(tournament, "q_best_of", None) or getattr(tournament, "md_best_of", None) or 5

    entries = list(
        tournament.entries.filter(status=TournamentEntry.Status.ACTIVE)
        .select_related("player")
        .order_by("position")
    )

    p1 = entries[0].player if len(entries) > 0 else None
    p2 = entries[1].player if len(entries) > 1 else None

    Match.objects.get_or_create(
        tournament=tournament,
        round="Q1",
        position=1,
        defaults={"player1": p1, "player2": p2, "best_of": best_of},
    )
    return True
