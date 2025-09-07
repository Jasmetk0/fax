# tests/test_md_band_regen.py
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
from msa.services.md_band_regen import regenerate_md_band
from msa.services.md_confirm import confirm_main_draw
from msa.services.seed_anchors import md_anchor_map


@pytest.mark.django_db
def test_regenerate_seed_band_5_8_permutates_only_that_band():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=32, md_seeds_count=8)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD
    )

    players = [Player.objects.create(name=f"P{i}") for i in range(1, 33)]
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )

    mapping_before = confirm_main_draw(t, rng_seed=123)
    anchors = md_anchor_map(32)
    band_slots = anchors["5-8"]
    # entry_ids seedů 5..8
    band_eids_before = {mapping_before[s] for s in band_slots}
    # jiné seedy (1..4) sloty
    top_seed_slots = [anchors["1"][0], anchors["2"][0]] + anchors["3-4"]
    top_eids_before = {mapping_before[s] for s in top_seed_slots}

    mapping_after = regenerate_md_band(t, band="5-8", rng_seed=999, mode="SOFT")

    # Sloty bandu se nemění, ale přiřazení seedů uvnitř by se mělo (alespoň někde) změnit
    band_eids_after = {mapping_after[s] for s in band_slots}
    assert band_eids_after == band_eids_before
    # alespoň jeden seed v bandu změnil kotvu
    moved = any(mapping_before[s] != mapping_after[s] for s in band_slots)
    assert moved

    # ostatní top seedy zůstaly tam, kde byly
    top_eids_after = {mapping_after[s] for s in top_seed_slots}
    assert top_eids_after == top_eids_before


@pytest.mark.django_db
def test_regenerate_unseeded_soft_does_not_touch_done_pairs():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD
    )

    players = [Player.objects.create(name=f"P{i}") for i in range(1, 17)]
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )

    confirm_main_draw(t, rng_seed=1)

    # označ první R1 jako DONE
    m = (
        Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16")
        .order_by("slot_top")
        .first()
    )
    m.winner_id = m.player_top_id
    m.state = MatchState.DONE
    m.save(update_fields=["winner", "state"])

    mapping_before = {
        m.slot_top: TournamentEntry.objects.get(tournament=t, position=m.slot_top).id
        for m in Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16")
    }

    mapping_after = regenerate_md_band(t, band="Unseeded", rng_seed=999, mode="SOFT")

    # DONE pár se nesmí změnit
    eid_top_before = mapping_before[m.slot_top]
    eid_bot_before = mapping_before[m.slot_bottom]
    eid_top_after = mapping_after[m.slot_top]
    eid_bot_after = mapping_after[m.slot_bottom]
    assert eid_top_before == eid_top_after and eid_bot_before == eid_bot_after
