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
    RankingAdjustment,
    RankingScope,
    Season,
    Tournament,
    TournamentEntry,
)
from msa.services.standings import rolling_standings, season_standings


@pytest.mark.django_db
def test_season_adjustment_points_and_penalty():
    season = Season.objects.create(
        name="2024",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        best_n=2,
    )
    category = Category.objects.create(name="M")
    cs = CategorySeason.objects.create(
        category=category,
        season=season,
        draw_size=16,
        scoring_md={"Winner": 100, "RunnerUp": 60, "SF": 30},
    )
    t1 = Tournament.objects.create(
        season=season,
        category=category,
        category_season=cs,
        name="T1",
        slug="t1",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 1),
    )
    t2 = Tournament.objects.create(
        season=season,
        category=category,
        category_season=cs,
        name="T2",
        slug="t2",
        start_date=date(2024, 4, 1),
        end_date=date(2024, 6, 1),
    )
    pa = Player.objects.create(name="A")
    pb = Player.objects.create(name="B")
    for t in (t1, t2):
        TournamentEntry.objects.create(
            tournament=t,
            player=pa,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
        )
        TournamentEntry.objects.create(
            tournament=t,
            player=pb,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
        )
        Match.objects.create(
            tournament=t,
            phase=Phase.MD,
            round_name="R2",
            player_top=pa,
            player_bottom=pb,
            winner=pa,
            state=MatchState.DONE,
        )
    RankingAdjustment.objects.create(
        player=pa,
        scope=RankingScope.SEASON,
        start_monday=date(2024, 1, 1),
        duration_weeks=52,
        points_delta=50,
        best_n_penalty=-1,
    )
    rows = season_standings(season)
    row = next(r for r in rows if r.player_id == pa.id)
    assert row.counted == [100]
    assert row.dropped == [100]
    assert row.total == 150
    assert row.average == 100.0


@pytest.mark.django_db
def test_rolling_adjustment_active_at_snapshot():
    season = Season.objects.create(
        name="2024",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        best_n=2,
    )
    category = Category.objects.create(name="M")
    cs = CategorySeason.objects.create(
        category=category,
        season=season,
        draw_size=16,
        scoring_md={"Winner": 100, "RunnerUp": 60, "SF": 30},
    )
    t1 = Tournament.objects.create(
        season=season,
        category=category,
        category_season=cs,
        name="T1",
        slug="rt1",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 7),
    )
    t2 = Tournament.objects.create(
        season=season,
        category=category,
        category_season=cs,
        name="T2",
        slug="rt2",
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 7),
    )
    pa = Player.objects.create(name="A")
    pb = Player.objects.create(name="B")
    for t in (t1, t2):
        TournamentEntry.objects.create(
            tournament=t,
            player=pa,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
        )
        TournamentEntry.objects.create(
            tournament=t,
            player=pb,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
        )
    Match.objects.create(
        tournament=t1,
        phase=Phase.MD,
        round_name="R2",
        player_top=pb,
        player_bottom=pa,
        winner=pb,
        state=MatchState.DONE,
    )
    Match.objects.create(
        tournament=t2,
        phase=Phase.MD,
        round_name="R8",
        player_top=pa,
        player_bottom=pb,
        winner=pa,
        state=MatchState.DONE,
    )
    RankingAdjustment.objects.create(
        player=pb,
        scope=RankingScope.ROLLING_ONLY,
        start_monday=date(2024, 1, 1),
        duration_weeks=52,
        points_delta=-20,
        best_n_penalty=-1,
    )
    snap = date(2024, 7, 1)
    rows = rolling_standings(snap)
    row = next(r for r in rows if r.player_id == pb.id)
    assert row.counted == [100]
    assert row.dropped == [0]
    assert row.total == 80
    assert row.average == 100.0
    assert row.best_n_used == 1
