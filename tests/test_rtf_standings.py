import pytest

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Match,
    MatchState,
    Phase,
    Player,
    Season,
    Tournament,
    TournamentEntry,
    TournamentState,
)
from msa.services.standings import rolling_standings, rtf_standings, season_standings


def _mk_tournament(season, category, name, end_date_str, scoring_md=None):
    cs = CategorySeason.objects.filter(category=category, season=season).first()
    if not cs:
        cs = CategorySeason.objects.create(
            category=category, season=season, draw_size=16, md_seeds_count=4
        )
        if scoring_md:
            cs.scoring_md = scoring_md
            cs.save(update_fields=["scoring_md"])
    t = Tournament.objects.create(
        season=season,
        category=category,
        category_season=cs,
        name=name,
        slug=name.lower(),
        state=TournamentState.MD,
        end_date=end_date_str,
    )
    return t


@pytest.mark.django_db
def test_rtf_order_differs_from_season_and_rolling():
    """RtF pins auto-top winners above season/rolling order."""
    scoring = {"Winner": 100, "RunnerUp": 60}
    cat_auto = Category.objects.create(name="WT Platinum")
    cat_regular = Category.objects.create(name="WT 250")

    # Season to evaluate
    season = Season.objects.create(
        name="2025", start_date="2025-01-01", end_date="2025-12-31", best_n=2
    )
    t_auto = _mk_tournament(season, cat_auto, "Platinum", "2025-03-15", scoring_md=scoring)
    t_regular = _mk_tournament(season, cat_regular, "Challenger", "2025-06-01", scoring_md=scoring)

    # Tournament from previous season should be ignored
    prev = Season.objects.create(
        name="2024", start_date="2024-01-01", end_date="2024-12-31", best_n=2
    )
    _mk_tournament(prev, cat_auto, "Old", "2024-03-10", scoring_md=scoring)

    A = Player.objects.create(name="A")
    B = Player.objects.create(name="B")
    C = Player.objects.create(name="C")

    # Platinum: B beats A
    for p in (A, B):
        TournamentEntry.objects.create(
            tournament=t_auto, player=p, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
        )
    Match.objects.create(
        tournament=t_auto,
        phase=Phase.MD,
        round_name="R2",
        slot_top=1,
        slot_bottom=2,
        player_top=B,
        player_bottom=A,
        best_of=5,
        win_by_two=True,
        winner=B,
        state=MatchState.DONE,
    )

    # Challenger: A beats C
    for p in (A, C):
        TournamentEntry.objects.create(
            tournament=t_regular,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
        )
    Match.objects.create(
        tournament=t_regular,
        phase=Phase.MD,
        round_name="R2",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=C,
        best_of=5,
        win_by_two=True,
        winner=A,
        state=MatchState.DONE,
    )

    season_rows = season_standings(season)
    rolling_rows = rolling_standings("2025-06-10")
    rtf_rows = rtf_standings(season, auto_top_categories=["WT Platinum"])

    # Season and rolling agree
    assert [(r.player_id, r.total) for r in season_rows[:3]] == [
        (A.id, 160),
        (B.id, 100),
        (C.id, 60),
    ]
    assert [(r.player_id, r.total) for r in rolling_rows[:3]] == [
        (A.id, 160),
        (B.id, 100),
        (C.id, 60),
    ]

    # RtF pins auto-top winner B to first place
    top3 = [(r.player_id, r.total, r.pinned_category) for r in rtf_rows[:3]]
    assert top3 == [
        (B.id, 100, "WT Platinum"),
        (A.id, 160, None),
        (C.id, 60, None),
    ]

    # Tournament from previous season ignored – A total is only from 2025 events
    assert rtf_rows[1].total == 160
