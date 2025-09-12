# tests/test_ll_prefix.py
import pytest
from django.utils import timezone

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Player,
    Season,
    Tournament,
    TournamentEntry,
    TournamentState,
)
from msa.services.ll_prefix import (
    enforce_ll_prefix_in_md,
    fill_vacant_slot_prefer_ll_then_alt,
    get_ll_queue,
    reinstate_original_player,
)
from tests.woorld_helpers import woorld_date


@pytest.mark.django_db
def test_ll_queue_ordering_nr_last():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="World Tour")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=32)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD
    )

    # LL s různými WR (None = NR jde na konec)
    p = [Player.objects.create(name=f"P{i}") for i in range(6)]
    vals = [10, 2, None, 5, None, 3]
    for i, wr in enumerate(vals):
        TournamentEntry.objects.create(
            tournament=t,
            player=p[i],
            entry_type=EntryType.LL,
            status=EntryStatus.ACTIVE,
            wr_snapshot=wr,
        )
    q = get_ll_queue(t)
    # očekávané pořadí WR: 2,3,5,10,None,None
    ordered_wr = [x.wr_snapshot for x in q]
    assert ordered_wr[:4] == [2, 3, 5, 10]
    assert ordered_wr[4:] == [None, None]


@pytest.mark.django_db
def test_fill_vacant_slot_prefers_ll_then_alt():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="World Tour")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=32)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD
    )

    P = [Player.objects.create(name=f"P{i}") for i in range(8)]

    # ALT do zásoby
    TournamentEntry.objects.create(
        tournament=t, player=P[6], entry_type=EntryType.ALT, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=t, player=P[7], entry_type=EntryType.ALT, status=EntryStatus.ACTIVE
    )

    # LL fronta: (wr 4) je první, pak (wr 9)
    TournamentEntry.objects.create(
        tournament=t, player=P[0], entry_type=EntryType.LL, status=EntryStatus.ACTIVE, wr_snapshot=9
    )
    TournamentEntry.objects.create(
        tournament=t, player=P[1], entry_type=EntryType.LL, status=EntryStatus.ACTIVE, wr_snapshot=4
    )

    # Vzniknou 2 díry v MD: slot 5 a slot 9
    te1 = fill_vacant_slot_prefer_ll_then_alt(t, slot=5)
    te2 = fill_vacant_slot_prefer_ll_then_alt(t, slot=9)

    # Oba by měli být LL (ne ALT), a správné pořadí podle WR
    assert te1.entry_type == EntryType.LL
    assert te2.entry_type == EntryType.LL
    assert te1.position == 5
    assert te2.position == 9

    # Další díra → už nejsou LL, padá to na ALT
    te3 = fill_vacant_slot_prefer_ll_then_alt(t, slot=12)
    assert te3.entry_type == EntryType.ALT
    assert te3.position == 12


@pytest.mark.django_db
def test_enforce_ll_prefix_swaps_out_wrong_ll():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="World Tour")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=32)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD
    )

    P = [Player.objects.create(name=f"P{i}") for i in range(6)]

    # LL fronta dle WR: A(1), B(3), C(8)
    A = TournamentEntry.objects.create(
        tournament=t, player=P[0], entry_type=EntryType.LL, status=EntryStatus.ACTIVE, wr_snapshot=1
    )
    B = TournamentEntry.objects.create(
        tournament=t, player=P[1], entry_type=EntryType.LL, status=EntryStatus.ACTIVE, wr_snapshot=3
    )
    C = TournamentEntry.objects.create(
        tournament=t, player=P[2], entry_type=EntryType.LL, status=EntryStatus.ACTIVE, wr_snapshot=8
    )

    # Špatný stav: v MD sedí B a C; A chybí
    B.position = 5
    B.save(update_fields=["position"])
    C.position = 9
    C.save(update_fields=["position"])

    enforce_ll_prefix_in_md(t)

    # Teď musí sedět A a B (prefix 2), C musí ven
    ids_in_md = set(
        TournamentEntry.objects.filter(
            tournament=t, entry_type=EntryType.LL, position__isnull=False
        ).values_list("id", flat=True)
    )
    assert ids_in_md == set([A.id, B.id])


@pytest.mark.django_db
def test_reinstate_original_pops_worst_ll_and_swaps_slots_if_needed():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="World Tour")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=32)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD
    )

    # Původní hráč měl slot 7
    orig_p = Player.objects.create(name="ORIG")
    orig = TournamentEntry.objects.create(
        tournament=t, player=orig_p, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    # Byl nahrazen LL → ztratil position (necháme None), slot 7 dočasně obsadil LLx
    LL_best_p = Player.objects.create(name="LL_best")
    LL_worst_p = Player.objects.create(name="LL_worst")

    # Fronta: LL_best (wr 2) je lepší, LL_worst (wr 100) je nejhorší
    ll_best = TournamentEntry.objects.create(
        tournament=t,
        player=LL_best_p,
        entry_type=EntryType.LL,
        status=EntryStatus.ACTIVE,
        wr_snapshot=2,
    )
    ll_worst = TournamentEntry.objects.create(
        tournament=t,
        player=LL_worst_p,
        entry_type=EntryType.LL,
        status=EntryStatus.ACTIVE,
        wr_snapshot=100,
    )

    # Nasazení LL do MD: slot 7 (obsadil LL_best) a slot 12 (obsadil LL_worst)
    ll_best.position = 7
    ll_best.save(update_fields=["position"])
    ll_worst.position = 12
    ll_worst.save(update_fields=["position"])

    # Reinstat původního do slotu 7:
    reinstate_original_player(t, original_entry_id=orig.id, slot=7)

    # Očekávání:
    # - ORIG je v 7
    # - LL_best se přesunul do slotu nejhoršího (12)
    # - LL_worst byl vyhozen z MD (position=None)
    orig.refresh_from_db()
    ll_best.refresh_from_db()
    ll_worst.refresh_from_db()
    assert orig.position == 7
    assert ll_best.position == 12
    assert ll_worst.position is None

    # Prefix invariant zůstal (v MD je jen nejlepší LL)
    enforce_ll_prefix_in_md(t)
    ids_in_md = set(
        TournamentEntry.objects.filter(
            tournament=t, entry_type=EntryType.LL, position__isnull=False
        ).values_list("id", flat=True)
    )
    assert ids_in_md == {ll_best.id}
