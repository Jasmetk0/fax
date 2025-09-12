from datetime import date

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
from msa.services.standings import rolling_standings
from tests.woorld_helpers import woorld_date


@pytest.mark.django_db
def test_rolling_best_n_fallback_to_last_season():
    s = Season.objects.create(
        name="2025",
        start_date=date(2025, 1, 1),
        end_date=woorld_date(2025, 12),
        best_n=1,
    )
    cat = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(
        category=cat,
        season=s,
        draw_size=16,
        md_seeds_count=4,
        scoring_md={"Winner": 100, "RunnerUp": 60},
    )
    t1 = Tournament.objects.create(
        season=s,
        category=cat,
        category_season=cs,
        name="T1",
        slug="t1",
        state=TournamentState.MD,
        end_date=date(2025, 5, 1),
    )
    t2 = Tournament.objects.create(
        season=s,
        category=cat,
        category_season=cs,
        name="T2",
        slug="t2",
        state=TournamentState.MD,
        end_date=date(2025, 7, 1),
    )
    A = Player.objects.create(name="A")
    B = Player.objects.create(name="B")
    for t in (t1, t2):
        TournamentEntry.objects.create(
            tournament=t,
            player=A,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
        )
        TournamentEntry.objects.create(
            tournament=t,
            player=B,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
        )
    Match.objects.create(
        tournament=t1,
        phase=Phase.MD,
        round_name="R2",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        winner=A,
        state=MatchState.DONE,
    )
    Match.objects.create(
        tournament=t2,
        phase=Phase.MD,
        round_name="R2",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        winner=B,
        state=MatchState.DONE,
    )

    snap = date(2026, 1, 5)
    rows = rolling_standings(snap)
    rowA = next(r for r in rows if r.player_id == A.id)
    assert rowA.total == 100
    assert rowA.counted == [100]
    assert rowA.dropped == [60]
    assert rowA.best_n_used == 1
