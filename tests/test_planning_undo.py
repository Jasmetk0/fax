import json

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from msa.models import (
    Category,
    CategorySeason,
    Match,
    Phase,
    PlanningUndoState,
    Player,
    Schedule,
    Season,
    Snapshot,
    Tournament,
    TournamentState,
)
from msa.services.planning import list_day_order, save_planning_snapshot
from msa.services.planning_undo import redo_planning_day, undo_planning_day
from tests.test_admin_gate import expect_admin_block

DAY = "2025-08-01"


def _setup_tournament():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD
    )
    return t


@pytest.mark.django_db
def test_snapshot_limit_enforced_by_count_and_size():
    t = _setup_tournament()
    p1 = Player.objects.create(name="P1")
    p2 = Player.objects.create(name="P2")
    m = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=2,
        player_top=p1,
        player_bottom=p2,
    )
    Schedule.objects.create(tournament=t, match=m, play_date=DAY, order=1)
    for i in range(30):
        save_planning_snapshot(t, DAY, label=f"snap-{i}")
    state = PlanningUndoState.objects.get(tournament=t, day=DAY)
    assert len(state.undo_stack) <= 20
    assert state.redo_stack == []
    snaps = Snapshot.objects.filter(pk__in=state.undo_stack)
    total = sum(len(json.dumps(s.payload, ensure_ascii=False)) for s in snaps)
    assert total <= 1 * 1024 * 1024


@pytest.mark.django_db
def test_undo_redo_roundtrip_restores_day_order():
    t = _setup_tournament()
    players = [Player.objects.create(name=f"P{i}") for i in range(1, 7)]
    matches = [
        Match.objects.create(
            tournament=t,
            phase=Phase.MD,
            round_name="R16",
            slot_top=i,
            slot_bottom=32 - i,
            player_top=players[2 * (i - 1)],
            player_bottom=players[2 * (i - 1) + 1],
        )
        for i in range(1, 4)
    ]
    for i, m in enumerate(matches, start=1):
        Schedule.objects.create(tournament=t, match=m, play_date=DAY, order=i)
    snap_a = save_planning_snapshot(t, DAY, label="A")
    for m in matches:
        Schedule.objects.filter(match=m).update(order=None)
    for m, o in zip(matches, [3, 1, 2], strict=False):
        Schedule.objects.filter(match=m).update(order=o)
    snap_b = save_planning_snapshot(t, DAY, label="B")
    for m in matches:
        Schedule.objects.filter(match=m).update(order=None)
    for m, o in zip(matches, [2, 3, 1], strict=False):
        Schedule.objects.filter(match=m).update(order=o)
    snap_c = save_planning_snapshot(t, DAY, label="C")
    items = list_day_order(t, DAY)
    assert [x.match_id for x in items] == [matches[2].id, matches[0].id, matches[1].id]
    state = PlanningUndoState.objects.get(tournament=t, day=DAY)
    assert state.undo_stack == [snap_a, snap_b, snap_c]
    assert state.redo_stack == []
    undo_planning_day(t, DAY)
    items = list_day_order(t, DAY)
    assert [x.match_id for x in items] == [matches[1].id, matches[2].id, matches[0].id]
    undo_planning_day(t, DAY)
    items = list_day_order(t, DAY)
    assert [x.match_id for x in items] == [m.id for m in matches]
    state.refresh_from_db()
    assert len(state.undo_stack) == 1
    assert len(state.redo_stack) == 2
    redo_planning_day(t, DAY)
    items = list_day_order(t, DAY)
    assert [x.match_id for x in items] == [matches[1].id, matches[2].id, matches[0].id]
    redo_planning_day(t, DAY)
    items = list_day_order(t, DAY)
    assert [x.match_id for x in items] == [matches[2].id, matches[0].id, matches[1].id]
    state.refresh_from_db()
    assert len(state.undo_stack) == 3
    assert len(state.redo_stack) == 0


@pytest.mark.django_db
def test_undo_without_stack_raises():
    t = _setup_tournament()
    with pytest.raises(ValidationError) as exc:
        undo_planning_day(t, DAY)
    assert "undo" in str(exc.value).lower()


@pytest.mark.django_db
def test_admin_off_blocks_undo_redo():
    t = _setup_tournament()
    p1 = Player.objects.create(name="P1")
    p2 = Player.objects.create(name="P2")
    m = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=2,
        player_top=p1,
        player_bottom=p2,
    )
    Schedule.objects.create(tournament=t, match=m, play_date=DAY, order=1)
    save_planning_snapshot(t, DAY)
    with override_settings(MSA_ADMIN_MODE=False):
        expect_admin_block(undo_planning_day, t, DAY)
        expect_admin_block(redo_planning_day, t, DAY)
