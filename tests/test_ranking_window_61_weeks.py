from datetime import date, timedelta

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
)
from msa.services.standings import rolling_standings
from msa.services.standings_snapshot import activation_monday
from tests.woorld_helpers import woorld_date


def _make_tournament(end_date: date) -> tuple[Tournament, Player]:
    season = Season.objects.create(
        name="2024",
        start_date=date(2024, 1, 1),
        end_date=woorld_date(2024, 12),
        best_n=10,
    )
    category = Category.objects.create(name="M")
    cs = CategorySeason.objects.create(
        category=category,
        season=season,
        draw_size=16,
        scoring_md={"Winner": 100},
    )
    t = Tournament.objects.create(
        season=season,
        category=category,
        category_season=cs,
        name="T",
        slug="t",
        start_date=end_date - timedelta(days=6),
        end_date=end_date,
    )
    pa = Player.objects.create(name="A")
    pb = Player.objects.create(name="B")
    for p in (pa, pb):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
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
    return t, pa


@pytest.mark.django_db
def test_points_active_from_activation_monday_for_exact_61_mondays():
    t, pa = _make_tournament(date(2024, 1, 7))
    act = activation_monday(t.end_date)
    # within 61 weeks
    monday60 = act + timedelta(weeks=60)
    rows60 = rolling_standings(monday60)
    assert any(r.player_id == pa.id for r in rows60)
    monday61 = act + timedelta(weeks=61)
    rows61 = rolling_standings(monday61)
    assert all(r.player_id != pa.id for r in rows61)


@pytest.mark.django_db
def test_finish_on_monday_activates_next_monday():
    t, pa = _make_tournament(date(2024, 1, 8))
    act = activation_monday(t.end_date)
    assert act == date(2024, 1, 15)
    rows_act = rolling_standings(act)
    assert any(r.player_id == pa.id for r in rows_act)
    rows_prev = rolling_standings(date(2024, 1, 8))
    assert all(r.player_id != pa.id for r in rows_prev)


@pytest.mark.django_db
def test_midweek_edits_do_not_shift_window():
    t, pa = _make_tournament(date(2024, 1, 7))
    act = activation_monday(t.end_date)
    wednesday = act + timedelta(days=2)
    assert activation_monday(wednesday) == act + timedelta(weeks=1)
