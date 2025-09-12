import pytest
from django.core.exceptions import ValidationError
from django.db.models import Q

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Match,
    MatchState,
    Phase,
    Player,
    PlayerLicense,
    Season,
    Tournament,
    TournamentEntry,
    TournamentState,
)
from msa.services.qual_confirm import confirm_qualification
from msa.services.qual_edit import swap_slots_in_qualification
from tests.woorld_helpers import woorld_date


def _mk_base(K=2, R=3, pool=None):
    # R=3 → size=8, seed kotvy: 1 (TOP), 8 (BOTTOM)
    size = 2**R
    pool = pool or (K * size + 6)
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, qual_rounds=R)
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T",
        slug="t",
        state=TournamentState.QUAL,
        qualifiers_count=K,
    )

    ps = [Player.objects.create(name=f"P{i}") for i in range(pool)]
    for p in ps:
        PlayerLicense.objects.create(player=p, season=s)
    need = K * size
    for i in range(need):
        TournamentEntry.objects.create(
            tournament=t,
            player=ps[i],
            entry_type=EntryType.Q,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )
    confirm_qualification(t, rng_seed=7)
    return t, size


def _match_for_slot(t, size, slot):
    return (
        Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name=f"Q{size}")
        .filter(Q(slot_top=slot) | Q(slot_bottom=slot))
        .first()
    )


@pytest.mark.django_db
def test_seed_to_seed_same_tier_across_branches_swaps_ok():
    t, size = _mk_base(K=2, R=3)  # branches base: 0 and 1000; anchors local 1 and 8
    slot_top_b0 = 1
    slot_top_b1 = 1001  # TOP v druhé větvi (stejný tier → OK)

    ma_before = _match_for_slot(t, size, slot_top_b0)
    mb_before = _match_for_slot(t, size, slot_top_b1)
    pa0 = (
        ma_before.player_top_id if ma_before.slot_top == slot_top_b0 else ma_before.player_bottom_id
    )
    pb0 = (
        mb_before.player_top_id if mb_before.slot_top == slot_top_b1 else mb_before.player_bottom_id
    )

    res = swap_slots_in_qualification(t, slot_top_b0, slot_top_b1)
    assert res.slot_a == slot_top_b0 and res.slot_b == slot_top_b1
    assert res.player_a_before == pa0 and res.player_b_before == pb0

    ma_after = _match_for_slot(t, size, slot_top_b0)
    mb_after = _match_for_slot(t, size, slot_top_b1)
    pa = ma_after.player_top_id if ma_after.slot_top == slot_top_b0 else ma_after.player_bottom_id
    pb = mb_after.player_top_id if mb_after.slot_top == slot_top_b1 else mb_after.player_bottom_id
    assert pa == pb0 and pb == pa0
    assert ma_after.state == MatchState.PENDING and mb_after.state == MatchState.PENDING
    assert ma_after.winner_id is None and mb_after.winner_id is None


@pytest.mark.django_db
def test_unseeded_to_unseeded_swaps_ok():
    t, size = _mk_base(K=2, R=2)  # size=4, anchor = local 1 (TOP)
    # vybereme dva nenasazené sloty (např. local 2 a 3 napříč větvemi)
    slot_a = 2
    slot_b = 1003

    res = swap_slots_in_qualification(t, slot_a, slot_b)
    assert res.slot_a == slot_a and res.slot_b == slot_b

    ma = _match_for_slot(t, size, slot_a)
    mb = _match_for_slot(t, size, slot_b)
    assert ma.state == MatchState.PENDING and mb.state == MatchState.PENDING


@pytest.mark.django_db
def test_block_seed_vs_unseeded():
    t, size = _mk_base(K=1, R=3)  # size=8, anchor local 1 a 8
    with pytest.raises(ValidationError):
        # TOP anchor vs unseeded local 2
        _ = swap_slots_in_qualification(t, 1, 2)


@pytest.mark.django_db
def test_block_cross_tier_seed_swap():
    t, size = _mk_base(K=2, R=3)
    # TOP (local 1) vs BOTTOM (local 8) — oba anchor, ale jiný tier → blok
    with pytest.raises(ValidationError):
        _ = swap_slots_in_qualification(t, 1, 1008)


@pytest.mark.django_db
def test_block_when_result_exists():
    t, size = _mk_base(K=1, R=2)
    # nastavíme výsledek v jednom z dotčených zápasů
    ma = _match_for_slot(t, size, 1)
    ma.winner_id = ma.player_top_id or ma.player_bottom_id
    ma.state = MatchState.DONE
    ma.save()

    with pytest.raises(ValidationError):
        _ = swap_slots_in_qualification(t, 1, 2)


@pytest.mark.django_db
def test_r1_swaps_without_anchors_allowed_any_slots():
    t, size = _mk_base(K=2, R=1)
    slot_a = 1
    slot_b = 1002
    ma_before = _match_for_slot(t, size, slot_a)
    mb_before = _match_for_slot(t, size, slot_b)
    pa = ma_before.player_top_id if ma_before.slot_top == slot_a else ma_before.player_bottom_id
    pb = mb_before.player_top_id if mb_before.slot_top == slot_b else mb_before.player_bottom_id
    res = swap_slots_in_qualification(t, slot_a, slot_b)
    assert res.slot_a == slot_a and res.slot_b == slot_b
    ma_after = _match_for_slot(t, size, slot_a)
    mb_after = _match_for_slot(t, size, slot_b)
    pa_after = ma_after.player_top_id if ma_after.slot_top == slot_a else ma_after.player_bottom_id
    pb_after = mb_after.player_top_id if mb_after.slot_top == slot_b else mb_after.player_bottom_id
    assert pa_after == pb and pb_after == pa
