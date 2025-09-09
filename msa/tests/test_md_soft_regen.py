# tests/test_md_soft_regen.py
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
    Schedule,
    Season,
    Tournament,
    TournamentEntry,
    TournamentState,
)
from msa.services.md_confirm import confirm_main_draw
from msa.services.md_soft_regen import soft_regenerate_unseeded_md
from msa.services.seed_anchors import md_anchor_map


@pytest.mark.django_db
def test_soft_regen_only_moves_unseeded_in_unfinished_r1():
    # Setup turnaje
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="World Tour")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD
    )

    # 16 hráčů s WR 1..16 → S=4 seedy, zbytek nenasazení
    players = [Player.objects.create(name=f"P{i}") for i in range(1, 17)]
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )

    # Potvrď MD a vytvoř R1
    initial = confirm_main_draw(t, rng_seed=123)
    draw_size = cs.draw_size

    # Označ jeden R1 zápas jako hotový → ten musí zůstat beze změny
    m_done = (
        Match.objects.filter(tournament=t, phase=Phase.MD, round_name=f"R{draw_size}")
        .order_by("slot_top")
        .first()
    )
    # „odehraj“: nastav vítěze
    m_done.winner_id = m_done.player_top_id
    m_done.state = MatchState.DONE
    m_done.save(update_fields=["winner", "state"])

    # U jiného R1 bez výsledku přidáme plán, abychom otestovali, že se při změně smaže
    m_sched = (
        Match.objects.filter(
            tournament=t, phase=Phase.MD, round_name=f"R{draw_size}", state=MatchState.PENDING
        )
        .exclude(pk=m_done.pk)
        .first()
    )
    Schedule.objects.create(tournament=t, play_date="2025-08-01", order=1, match=m_sched)
    assert Schedule.objects.filter(match=m_sched).exists()

    # Uchovej původní dvojice
    old_pairs = {
        (m.slot_top, m.slot_bottom): (m.player_top_id, m.player_bottom_id)
        for m in Match.objects.filter(tournament=t, phase=Phase.MD, round_name=f"R{draw_size}")
    }

    # Proveď soft regen s jiným RNG (mění jen nenasazené v unfinished)
    after = soft_regenerate_unseeded_md(t, rng_seed=999)

    # 1) Zápas označený DONE se nesmí změnit
    m_done.refresh_from_db()
    assert (m_done.player_top_id, m_done.player_bottom_id) == old_pairs[
        (m_done.slot_top, m_done.slot_bottom)
    ]

    # 2) Nějaká změna u unfinished párů by měla nastat (alespoň u některého)
    changed_any = False
    for m in Match.objects.filter(tournament=t, phase=Phase.MD, round_name=f"R{draw_size}"):
        if m.pk == m_done.pk:
            continue
        if (m.player_top_id, m.player_bottom_id) != old_pairs[(m.slot_top, m.slot_bottom)]:
            changed_any = True
            break
    assert changed_any, "Soft regen nic nezměnil – očekáváme změnu unseeded v unfinished R1."

    # 3) Schedule u m_sched se měl smazat, pokud se pár změnil
    m_sched.refresh_from_db()
    if (m_sched.player_top_id, m_sched.player_bottom_id) != old_pairs[
        (m_sched.slot_top, m_sched.slot_bottom)
    ]:
        assert not Schedule.objects.filter(match=m_sched).exists()


@pytest.mark.django_db
def test_soft_regen_unseeded_changes_with_rng_seed_active():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="World Tour")
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

    initial = confirm_main_draw(t, rng_seed=5)
    draw_size = cs.draw_size

    m_done = (
        Match.objects.filter(tournament=t, phase=Phase.MD, round_name=f"R{draw_size}")
        .order_by("slot_top")
        .first()
    )
    m_done.winner_id = m_done.player_top_id
    m_done.state = MatchState.DONE
    m_done.save(update_fields=["winner", "state"])

    anchors = md_anchor_map(draw_size)
    seed_slots = [anchors["1"][0], anchors["2"][0]] + anchors["3-4"]
    seed_ids = {initial[s] for s in seed_slots}

    mutable_slots: list[int] = []
    for m in Match.objects.filter(tournament=t, phase=Phase.MD, round_name=f"R{draw_size}"):
        if (m.winner_id is None) and (m.state != MatchState.DONE):
            if initial[m.slot_top] not in seed_ids:
                mutable_slots.append(m.slot_top)
            if initial[m.slot_bottom] not in seed_ids:
                mutable_slots.append(m.slot_bottom)

    t.rng_seed_active = 123
    mapping1 = soft_regenerate_unseeded_md(t)
    t.rng_seed_active = 456
    mapping2 = soft_regenerate_unseeded_md(t)

    order1 = [mapping1[s] for s in sorted(mutable_slots)]
    order2 = [mapping2[s] for s in sorted(mutable_slots)]
    assert order1 != order2

    seeds_after1 = [mapping1[s] for s in seed_slots]
    seeds_after2 = [mapping2[s] for s in seed_slots]
    assert seeds_after1 == seeds_after2

    assert mapping1[m_done.slot_top] == initial[m_done.slot_top]
    assert mapping1[m_done.slot_bottom] == initial[m_done.slot_bottom]
    assert mapping2[m_done.slot_top] == initial[m_done.slot_top]
    assert mapping2[m_done.slot_bottom] == initial[m_done.slot_bottom]
