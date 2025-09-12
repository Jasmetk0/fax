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
    RankingSnapshot,
    Season,
    Tournament,
    TournamentEntry,
)
from msa.services.standings_snapshot import (
    StalePreviewError,
    activation_monday,
    build_preview,
    confirm_snapshot,
)
from tests.woorld_helpers import woorld_date


def _prepare_basic_tournament():
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
        scoring_md={"Winner": 100, "RunnerUp": 60},
    )
    t = Tournament.objects.create(
        season=season,
        category=category,
        category_season=cs,
        name="T",
        slug="t",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 7),
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
    return t, pa, pb


@pytest.mark.django_db
def test_build_and_confirm_monday_snapshot_is_stable():
    t, pa, _ = _prepare_basic_tournament()
    monday = activation_monday(t.end_date)
    preview = build_preview(RankingSnapshot.Type.ROLLING, monday)
    snap = confirm_snapshot(RankingSnapshot.Type.ROLLING, monday, preview["hash"])
    preview2 = build_preview(RankingSnapshot.Type.ROLLING, monday)
    assert preview2["hash"] == snap.hash
    assert snap.payload[0]["player_id"] == pa.id


@pytest.mark.django_db
def test_no_change_week_creates_alias_not_payload():
    t, _, _ = _prepare_basic_tournament()
    monday = activation_monday(t.end_date)
    preview = build_preview(RankingSnapshot.Type.ROLLING, monday)
    confirm_snapshot(RankingSnapshot.Type.ROLLING, monday, preview["hash"])
    monday2 = monday + timedelta(weeks=1)
    preview2 = build_preview(RankingSnapshot.Type.ROLLING, monday2)
    snap2 = confirm_snapshot(RankingSnapshot.Type.ROLLING, monday2, preview2["hash"])
    assert snap2.is_alias is True
    assert snap2.payload is None
    assert snap2.alias_of is not None


@pytest.mark.django_db
def test_confirm_fails_on_stale_preview():
    t, _, _ = _prepare_basic_tournament()
    monday = activation_monday(t.end_date)
    with pytest.raises(StalePreviewError):
        confirm_snapshot(RankingSnapshot.Type.ROLLING, monday, "deadbeef")
