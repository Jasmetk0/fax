# tests/test_recalculate.py
import pytest

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Player,
    Season,
    SeedingSource,
    Snapshot,
    Tournament,
    TournamentEntry,
    TournamentState,
)
from msa.services.recalculate import (
    brutal_reset_to_registration,
    confirm_recalculate_registration,
    preview_recalculate_registration,
)


@pytest.mark.django_db
def test_preview_and_confirm_apply_groups_and_seeds_with_wc_respected():
    # MD32, qualifiers=4 → D=28; S=8
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(
        category=c,
        season=s,
        draw_size=32,
        md_seeds_count=8,
        qual_rounds=3,
        wc_slots_default=1,
    )
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="Tour A",
        slug="tour-a",
        state=TournamentState.REG,
        seeding_source=SeedingSource.SNAPSHOT,
        qualifiers_count=4,
    )

    # 40 registrací podle WR 1..40 (1 nejlepší)
    P = [Player.objects.create(name=f"P{i}") for i in range(1, 41)]
    E = []
    for i, p in enumerate(P, start=1):
        E.append(
            TournamentEntry.objects.create(
                tournament=t,
                player=p,
                entry_type=EntryType.ALT,
                status=EntryStatus.ACTIVE,
                wr_snapshot=i,
            )
        )

    # WC pro hráče pod čarou: WR=30 -> povýšený by měl v DA zůstat i po recalc
    e_wc = E[29]
    e_wc.promoted_by_wc = True
    e_wc.is_wc = True
    e_wc.entry_type = EntryType.DA
    e_wc.save(update_fields=["promoted_by_wc", "is_wc", "entry_type"])

    prev = preview_recalculate_registration(t)
    # navržené počty
    assert prev.counters["S"] == 8
    assert prev.counters["D"] == 28
    assert prev.counters["Q_draw_size"] == 4 * (2**3)

    # Najdi skupinu WR=30 (index 29)
    eid_wc = e_wc.id
    new_group = next(r.group for r in prev.proposed if r.entry_id == eid_wc)
    assert new_group in ("SEED", "DA")  # podle WR by byl pod čarou, ale WC promotion ho drží v DA

    # Aplikace
    confirm_recalculate_registration(t, prev)

    # Seedy 1..8 jsou DA se seed 1..8
    seeds = (
        TournamentEntry.objects.filter(tournament=t, entry_type=EntryType.DA)
        .exclude(seed=None)
        .order_by("seed")
    )
    assert seeds.count() == 8
    assert [te.seed for te in seeds] == list(range(1, 9))

    # WR=30 je DA (díky WC)
    e_wc.refresh_from_db()
    assert e_wc.entry_type == EntryType.DA

    # Q velikost = 4*8 = 32 hráčů v Q/ALT? Pozor: Q_draw_size je počet **slotů v kvaldě** (hráčů v Q),
    # zbytek je RESERVE. Ověříme, že první Q_draw_size v navrženém poolu je Q.
    q_ids = [r.entry_id for r in prev.proposed if r.group == "Q"]
    assert len(q_ids) == prev.counters["Q_draw_size"]
    qs_after = TournamentEntry.objects.filter(pk__in=q_ids)
    assert all(te.entry_type == EntryType.Q for te in qs_after)


@pytest.mark.django_db
def test_confirm_blocks_when_wc_or_qwc_limit_exceeded():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(
        category=c,
        season=s,
        draw_size=32,
        qual_rounds=2,
        wc_slots_default=0,
        q_wc_slots_default=0,
    )
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="Tour C",
        slug="tour-c",
        state=TournamentState.REG,
        seeding_source=SeedingSource.SNAPSHOT,
        wc_slots=0,
        q_wc_slots=0,
        qualifiers_count=2,
    )

    # 40 registrations WR 1..40
    players = [Player.objects.create(name=f"P{i}") for i in range(1, 41)]
    entries = []
    for i, p in enumerate(players, start=1):
        entries.append(
            TournamentEntry.objects.create(
                tournament=t,
                player=p,
                entry_type=EntryType.ALT,
                status=EntryStatus.ACTIVE,
                wr_snapshot=i,
            )
        )

    # WC promotion for WR=30
    e_wc = entries[29]
    e_wc.promoted_by_wc = True
    e_wc.is_wc = True
    e_wc.entry_type = EntryType.DA
    e_wc.save(update_fields=["promoted_by_wc", "is_wc", "entry_type"])

    # QWC promotion for WR=40 (would normally be reserve)
    e_qwc = entries[39]
    e_qwc.promoted_by_qwc = True
    e_qwc.is_qwc = True
    e_qwc.entry_type = EntryType.Q
    e_qwc.save(update_fields=["promoted_by_qwc", "is_qwc", "entry_type"])

    prev = preview_recalculate_registration(t)
    assert prev.counters["WC_used"] == 1 and prev.counters["WC_limit"] == 0
    assert prev.counters["QWC_used"] == 1 and prev.counters["QWC_limit"] == 0

    with pytest.raises(Exception):
        confirm_recalculate_registration(t, prev)


@pytest.mark.django_db
def test_brutal_reset_snapshots_and_clears_matches_and_slots():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="Tour B",
        slug="tour-b",
        state=TournamentState.MD,
    )

    P1 = Player.objects.create(name="A")
    P2 = Player.objects.create(name="B")
    e1 = TournamentEntry.objects.create(
        tournament=t,
        player=P1,
        entry_type=EntryType.DA,
        status=EntryStatus.ACTIVE,
        wr_snapshot=1,
        seed=1,
        position=1,
    )
    e2 = TournamentEntry.objects.create(
        tournament=t,
        player=P2,
        entry_type=EntryType.DA,
        status=EntryStatus.ACTIVE,
        wr_snapshot=2,
        seed=None,
        position=16,
    )

    # nějaký „zápas“
    from msa.models import Match, Phase

    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=16,
        player_top=P1,
        player_bottom=P2,
    )

    brutal_reset_to_registration(t, reason="TEST")

    # Snapshot vytvořen
    assert Snapshot.objects.filter(tournament=t, type="BRUTAL").exists()

    # Zápasy pryč
    assert Match.objects.filter(tournament=t).count() == 0

    # Sloty/seed vynulovány
    e1.refresh_from_db()
    e2.refresh_from_db()
    assert e1.position is None and e1.seed is None
    assert e2.position is None and e2.seed is None

    # Turnaj v REG
    t.refresh_from_db()
    assert t.state == TournamentState.REG
