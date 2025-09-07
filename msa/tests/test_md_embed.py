# tests/test_md_embed.py
import pytest

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Match,
    Phase,
    Player,
    Season,
    Tournament,
    TournamentEntry,
    TournamentState,
)
from msa.services.md_confirm import confirm_main_draw
from msa.services.md_embed import effective_template_size_for_md, r1_name_for_md
from msa.services.seed_anchors import md_anchor_map


@pytest.mark.django_db
def test_confirm_main_draw_draw24_embeds_into_r32_with_byes_for_top8():
    # MD24 → šablona 32, S=8, 8 BYE párů (top8 seed má volno v R32)
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=24, md_seeds_count=8)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T24", slug="t24", state=TournamentState.MD
    )

    # 24 hráčů (DA), WR 1..24
    players = [Player.objects.create(name=f"P{i}") for i in range(1, 25)]
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )

    mapping = confirm_main_draw(t, rng_seed=777)

    # Šablona a R1 název
    assert effective_template_size_for_md(t) == 32
    assert r1_name_for_md(t) == "R32"

    anchors = md_anchor_map(32)
    # kotvy seedů 1..8 jsou v bandech: '1','2','3-4','5-8'
    seed_anchor_slots = [anchors["1"][0], anchors["2"][0]] + anchors["3-4"] + anchors["5-8"]

    # entry_id pro WR 1..8:
    def eid_wr(k: int) -> int:
        return TournamentEntry.objects.get(tournament=t, player=players[k - 1]).id

    # seedy sedí na svých kotvách
    assert {mapping[s] for s in seed_anchor_slots} == {eid_wr(k) for k in range(1, 9)}

    # oponentní sloty seedů 1..8 jsou BYE (v mappingu nejsou)
    opp = {33 - s for s in seed_anchor_slots}  # R32 mirror
    for os in opp:
        assert os not in mapping  # prázdný slot

    # R1 „R32“ má jen 8 zápasů (32-24 = 8 BYE párů, původních 16 párů − 8 = 8 zápasů)
    r1 = list(Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R32"))
    assert len(r1) == 8
    # V žádném R1 zápase nesmí figurovat hráč s WR 1..8 (ti mají BYE)
    top8_ids = {players[i - 1].id for i in range(1, 9)}
    for m in r1:
        assert m.player_top_id not in top8_ids
        assert m.player_bottom_id not in top8_ids
