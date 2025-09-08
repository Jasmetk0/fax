"""Tests for winner propagation in msa.services.results."""

from __future__ import annotations

import pytest

from msa.models import (
    Category,
    CategorySeason,
    Match,
    Phase,
    Player,
    Season,
    Tournament,
    TournamentState,
)
from msa.services.results import resolve_needs_review, set_result


def _tournament(phase: Phase) -> Tournament:
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    return Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T",
        slug="t",
        state=TournamentState.MD if phase == Phase.MD else TournamentState.QUAL,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slot_top,slot_bottom,is_top,prefilled",
    [
        (1, 8, True, True),
        (1, 8, True, False),
        (4, 5, False, True),
        (4, 5, False, False),
    ],
)
def test_md_parent_overwrite(slot_top, slot_bottom, is_top, prefilled):
    """Winner from R8 is placed into correct R4 slot with needs_review rules."""
    t = _tournament(Phase.MD)
    p1, p2, intruder = [Player.objects.create(name=f"P{i}") for i in range(1, 4)]

    r8 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R8",
        slot_top=slot_top,
        slot_bottom=slot_bottom,
        player_top=p1,
        player_bottom=p2,
        best_of=5,
        win_by_two=True,
    )

    from msa.services.results import _parent_pair_for_child

    next_round, parent_top, parent_bottom, is_top_calc = _parent_pair_for_child(r8)
    assert next_round == "R4" and is_top_calc is is_top

    parent_kwargs: dict[str, int | Player | None] = dict(
        tournament=t,
        phase=Phase.MD,
        round_name=next_round,
        slot_top=parent_top,
        slot_bottom=parent_bottom,
        best_of=5,
        win_by_two=True,
    )
    if prefilled:
        if is_top:
            parent_kwargs["player_top"] = intruder
        else:
            parent_kwargs["player_bottom"] = intruder
    r4 = Match.objects.create(**parent_kwargs)

    set_result(r8.id, mode="WIN_ONLY", winner="top")
    r4.refresh_from_db()

    expected = p1.id
    if is_top:
        assert r4.player_top_id == expected
    else:
        assert r4.player_bottom_id == expected
    assert r4.needs_review is prefilled


@pytest.mark.django_db
def test_qual_parent_propagation_with_base_1000():
    """Two Q8 children propagate to Q4 parent with correct slots."""
    t = _tournament(Phase.QUAL)
    p1, p2, p3, p4 = [Player.objects.create(name=f"P{i}") for i in range(1, 5)]

    q8a = Match.objects.create(
        tournament=t,
        phase=Phase.QUAL,
        round_name="Q8",
        slot_top=1001,
        slot_bottom=1008,
        player_top=p1,
        player_bottom=p2,
        best_of=5,
        win_by_two=True,
    )
    q8b = Match.objects.create(
        tournament=t,
        phase=Phase.QUAL,
        round_name="Q8",
        slot_top=1004,
        slot_bottom=1005,
        player_top=p3,
        player_bottom=p4,
        best_of=5,
        win_by_two=True,
    )

    parent = Match.objects.create(
        tournament=t,
        phase=Phase.QUAL,
        round_name="Q4",
        slot_top=1001,
        slot_bottom=1004,
        best_of=5,
        win_by_two=True,
    )

    set_result(q8a.id, mode="WIN_ONLY", winner="top")
    parent.refresh_from_db()
    assert parent.player_top_id == p1.id and parent.needs_review is False

    set_result(q8b.id, mode="WIN_ONLY", winner="top")
    parent.refresh_from_db()
    assert parent.player_bottom_id == p3.id and parent.needs_review is False


@pytest.mark.django_db
def test_propagation_no_parent_in_final():
    """R2 match has no parent, so propagation should do nothing."""
    t = _tournament(Phase.MD)
    p1, p2 = [Player.objects.create(name=f"P{i}") for i in range(1, 3)]

    final = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R2",
        slot_top=1,
        slot_bottom=2,
        player_top=p1,
        player_bottom=p2,
        best_of=5,
        win_by_two=True,
    )

    set_result(final.id, mode="WIN_ONLY", winner="top")
    assert Match.objects.count() == 1


@pytest.mark.django_db
def test_idempotent_set_result_same_winner():
    """Saving same winner twice does not flag needs_review again."""
    t = _tournament(Phase.MD)
    p1, p2 = [Player.objects.create(name=f"P{i}") for i in range(1, 3)]

    r8 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R8",
        slot_top=1,
        slot_bottom=8,
        player_top=p1,
        player_bottom=p2,
        best_of=5,
        win_by_two=True,
    )
    r4 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R4",
        slot_top=1,
        slot_bottom=4,
        best_of=5,
        win_by_two=True,
    )

    set_result(r8.id, mode="WIN_ONLY", winner="top")
    r4.refresh_from_db()
    assert r4.player_top_id == p1.id and r4.needs_review is False

    set_result(r8.id, mode="WIN_ONLY", winner="top")
    r4.refresh_from_db()
    assert r4.player_top_id == p1.id and r4.needs_review is False


@pytest.mark.django_db
def test_downstream_cascade_when_winner_changes():
    """Changing winner propagates to all downstream matches and flags review."""
    t = _tournament(Phase.MD)
    p1, p2, p3, p4 = [Player.objects.create(name=f"P{i}") for i in range(1, 5)]

    r8 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R8",
        slot_top=1,
        slot_bottom=8,
        player_top=p1,
        player_bottom=p2,
        best_of=5,
        win_by_two=True,
    )
    r4 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R4",
        slot_top=1,
        slot_bottom=4,
        player_top=None,
        player_bottom=p3,
        best_of=5,
        win_by_two=True,
    )
    r2 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R2",
        slot_top=1,
        slot_bottom=2,
        player_top=None,
        player_bottom=p4,
        best_of=5,
        win_by_two=True,
    )

    set_result(r8.id, mode="WIN_ONLY", winner="top")
    set_result(r4.id, mode="WIN_ONLY", winner="top")
    set_result(r2.id, mode="WIN_ONLY", winner="top")
    r4.refresh_from_db()
    r2.refresh_from_db()
    assert r4.winner_id == p1.id and r2.winner_id == p1.id

    set_result(r8.id, mode="WIN_ONLY", winner="bottom")
    r4.refresh_from_db()
    r2.refresh_from_db()

    assert r4.player_top_id == p2.id and r4.needs_review is True
    assert r2.player_top_id == p2.id and r2.needs_review is True
    assert r4.winner_id == p1.id and r2.winner_id == p1.id


@pytest.mark.django_db
def test_resolve_only_clears_needs_review():
    """resolve_needs_review resets flag without altering players or winner."""
    t = _tournament(Phase.MD)
    p1, p2, p3 = [Player.objects.create(name=f"P{i}") for i in range(1, 4)]

    r8 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R8",
        slot_top=1,
        slot_bottom=8,
        player_top=p1,
        player_bottom=p2,
        best_of=5,
        win_by_two=True,
    )
    r4 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R4",
        slot_top=1,
        slot_bottom=4,
        player_top=p3,
        best_of=5,
        win_by_two=True,
    )

    set_result(r8.id, mode="WIN_ONLY", winner="top")
    r4.refresh_from_db()
    assert r4.needs_review is True

    resolve_needs_review(r4.id)
    r4.refresh_from_db()
    assert r4.needs_review is False
    assert r4.player_top_id == p1.id
    assert r4.winner_id is None
