# tests/test_md_confirm.py
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
from msa.services.md_confirm import confirm_main_draw, hard_regenerate_unseeded_md
from msa.services.seed_anchors import md_anchor_map
from tests.woorld_helpers import woorld_date


@pytest.mark.django_db
def test_confirm_main_draw_md16_s4_seeds_on_anchors_and_pairs_created():
    # základ
    s = Season.objects.create(
        name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12), best_n=16
    )
    c = Category.objects.create(name="World Tour")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD
    )

    # 16 hráčů s WR 1..16 (1 nejlepší)
    players = [Player.objects.create(name=f"P{i}") for i in range(1, 17)]
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )

    mapping = confirm_main_draw(t, rng_seed=12345)
    anchors = md_anchor_map(16)

    # seedy 1..4 musí sedět na kotevních slotech: ['1']→1, ['2']→16, ['3-4']→[9,8]
    # zjistí slot podle entry id (S1=entry s WR=1 == players[0])
    # najdi entry_id podle playera
    def eid_of_wr(wr: int) -> int:
        p = players[wr - 1]
        return TournamentEntry.objects.get(tournament=t, player=p).id

    assert mapping[1] == eid_of_wr(1)  # seed1
    assert mapping[16] == eid_of_wr(2)  # seed2
    s34 = {mapping[9], mapping[8]}
    assert s34 == {eid_of_wr(3), eid_of_wr(4)}  # seedy 3-4 v [9,8]

    # zkontroluj, že vznikly R1 zápasy
    r1 = list(Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16"))
    assert len(r1) == 8
    # zrcadlové páry musí být osazeny
    for m in r1:
        assert m.player_top_id is not None and m.player_bottom_id is not None
        assert m.state == MatchState.PENDING


@pytest.mark.django_db
def test_hard_regenerate_unseeded_changes_pool_keeps_seeds():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="World Tour")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD
    )

    players = [Player.objects.create(name=f"P{i}") for i in range(1, 17)]
    # WR: 1..4 budou seedy, 5..16 unseeded
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )

    m1 = confirm_main_draw(t, rng_seed=100)
    # pamatovat si seed sloty
    seed_ids = [
        TournamentEntry.objects.get(tournament=t, player=players[i - 1]).id for i in range(1, 5)
    ]
    seed_slots_before = {slot for slot, eid in m1.items() if eid in seed_ids}

    # změna RNG → přelosuje **jen unseeded**
    m2 = hard_regenerate_unseeded_md(t, rng_seed=999)
    seed_slots_after = {slot for slot, eid in m2.items() if eid in seed_ids}

    assert seed_slots_before == seed_slots_after  # kotvy seedů se nemění
    # a mapping se celkově změnil (alespoň někde u unseeded)
    assert any(m1[k] != m2[k] for k in m1.keys() if k not in seed_slots_before)
