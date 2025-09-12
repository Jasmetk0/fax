import pytest

from msa.models import (
    Category,
    CategorySeason,
    Match,
    MatchState,
    Phase,
    Player,
    Season,
    Tournament,
    TournamentState,
)
from msa.services.results import set_result
from tests.woorld_helpers import woorld_date


def _mk_tournament(phase: Phase) -> Tournament:
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
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
def test_sets_mode_propagates_and_overwrite_marks_review():
    t = _mk_tournament(Phase.MD)
    p1, p2, intruder = [Player.objects.create(name=f"P{i}") for i in range(1, 4)]

    # R8 dítě + R4 rodič (rodič má už obsazený TOP "intruderem")
    r8 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R8",
        slot_top=1,
        slot_bottom=8,
        player_top=p1,
        player_bottom=p2,
        best_of=3,
        win_by_two=True,
    )
    r4 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R4",
        slot_top=1,
        slot_bottom=4,
        player_top=intruder,  # bude přepsán → needs_review=True
        best_of=5,
        win_by_two=True,
    )

    # P1 vyhraje na sety → dosadí se do TOP v R4 a označí review (protože slot byl obsazen)
    set_result(r8.id, mode="SETS", sets=[(11, 7), (11, 6)])
    r4.refresh_from_db()
    assert r4.player_top_id == p1.id
    assert r4.needs_review is True

    # Změna vítěze v R8 (SETS) → přepíše na P2 a zůstane needs_review=True
    set_result(r8.id, mode="SETS", sets=[(7, 11), (8, 11)])
    r4.refresh_from_db()
    assert r4.player_top_id == p2.id
    assert r4.needs_review is True


@pytest.mark.django_db
def test_special_mode_propagates_without_touching_parent_winner_or_state():
    t = _mk_tournament(Phase.MD)
    p1, p2, intr1, intr2 = [Player.objects.create(name=f"P{i}") for i in range(1, 5)]

    # Dítě R8
    r8 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R8",
        slot_top=4,
        slot_bottom=5,
        player_top=p1,
        player_bottom=p2,
        best_of=3,
        win_by_two=True,
    )

    # Rodič R4 má předvyplněné oba sloty jinými hráči
    r4 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R4",
        slot_top=1,
        slot_bottom=4,
        player_top=intr1,
        player_bottom=intr2,
        best_of=5,
        win_by_two=True,
    )

    # SPECIAL: WO pro bottom → vítěz je p2, dosadí se do správného (BOTTOM) slotu
    set_result(r8.id, mode="SPECIAL", winner="bottom", special="WO")
    r4.refresh_from_db()
    assert r4.player_bottom_id == p2.id
    # needs_review=True, protože jsme přepsali obsazený slot
    assert r4.needs_review is True
    # winner/score/stav rodiče se nemění
    assert r4.winner_id is None and r4.state == MatchState.PENDING


@pytest.mark.django_db
def test_parent_both_slots_prefilled_only_changed_slot_is_replaced():
    t = _mk_tournament(Phase.MD)
    p1, p2, intr1, intr2 = [Player.objects.create(name=f"P{i}") for i in range(1, 5)]

    r8 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R8",
        slot_top=1,
        slot_bottom=8,
        player_top=p1,
        player_bottom=p2,
        best_of=3,
        win_by_two=True,
    )
    r4 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R4",
        slot_top=1,
        slot_bottom=4,
        player_top=intr1,  # bude přepsán
        player_bottom=intr2,  # zůstane nedotčen
    )

    set_result(r8.id, mode="WIN_ONLY", winner="top")
    r4.refresh_from_db()
    assert r4.player_top_id == p1.id
    assert r4.player_bottom_id == intr2.id
    assert r4.needs_review is True


@pytest.mark.django_db
def test_qual_parent_propagation_second_branch_base_2000():
    """Druhá kvalifikační větev (base 2000) – děti Q8 → rodič Q4 správně dosazeny."""
    t = _mk_tournament(Phase.QUAL)
    p1, p2, p3, p4 = [Player.objects.create(name=f"P{i}") for i in range(1, 5)]

    # Dvě děti v druhé větvi (base 2000)
    q8a = Match.objects.create(
        tournament=t,
        phase=Phase.QUAL,
        round_name="Q8",
        slot_top=2001,
        slot_bottom=2008,
        player_top=p1,
        player_bottom=p2,
        best_of=5,
        win_by_two=True,
    )
    q8b = Match.objects.create(
        tournament=t,
        phase=Phase.QUAL,
        round_name="Q8",
        slot_top=2004,
        slot_bottom=2005,
        player_top=p3,
        player_bottom=p4,
        best_of=5,
        win_by_two=True,
    )

    parent = Match.objects.create(
        tournament=t,
        phase=Phase.QUAL,
        round_name="Q4",
        slot_top=2001,
        slot_bottom=2004,
        best_of=5,
        win_by_two=True,
    )

    set_result(q8a.id, mode="WIN_ONLY", winner="top")
    parent.refresh_from_db()
    assert parent.player_top_id == p1.id and parent.needs_review is False

    set_result(q8b.id, mode="WIN_ONLY", winner="top")
    parent.refresh_from_db()
    assert parent.player_bottom_id == p3.id and parent.needs_review is False
