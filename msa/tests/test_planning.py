# tests/test_planning.py
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
from msa.services.planning import (
    clear_day,
    insert_match,
    list_day_order,
    normalize_day,
    restore_planning_snapshot,
    save_planning_snapshot,
    swap_matches,
)


@pytest.mark.django_db
def test_insert_compacts_and_positions_correctly():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD
    )

    P = [Player.objects.create(name=f"P{i}") for i in range(1, 5)]
    m1 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=16,
        player_top=P[0],
        player_bottom=P[1],
    )
    m2 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=2,
        slot_bottom=15,
        player_top=P[2],
        player_bottom=P[3],
    )

    insert_match(t, m1.id, "2025-08-01", 1)
    insert_match(t, m2.id, "2025-08-01", 1)  # m1 se posune na 2

    items = list_day_order(t, "2025-08-01")
    assert [x.match_id for x in items] == [m2.id, m1.id]
    assert [x.order for x in items] == [1, 2]


@pytest.mark.django_db
def test_swap_across_days_and_normalize_and_clear():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T2", slug="t2", state=TournamentState.MD
    )

    P = [Player.objects.create(name=f"P{i}") for i in range(1, 5)]
    m1 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=16,
        player_top=P[0],
        player_bottom=P[1],
    )
    m2 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=2,
        slot_bottom=15,
        player_top=P[2],
        player_bottom=P[3],
    )

    insert_match(t, m1.id, "2025-08-01", 1)
    insert_match(t, m2.id, "2025-08-02", 1)

    # swap napříč dny
    swap_matches(t, m1.id, m2.id)
    items1 = list_day_order(t, "2025-08-01")
    items2 = list_day_order(t, "2025-08-02")
    assert [x.match_id for x in items1] == [m2.id]
    assert [x.match_id for x in items2] == [m1.id]

    # normalize (no-op, ale otestujeme volání)
    normalize_day(t, "2025-08-01")
    items1b = list_day_order(t, "2025-08-01")
    assert [x.order for x in items1b] == [1]

    # clear day
    clear_day(t, "2025-08-02")
    assert len(list_day_order(t, "2025-08-02")) == 0


@pytest.mark.django_db
def test_save_and_restore_planning_snapshot():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T3", slug="t3", state=TournamentState.MD
    )

    P = [Player.objects.create(name=f"P{i}") for i in range(1, 5)]
    m1 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=16,
        player_top=P[0],
        player_bottom=P[1],
    )
    m2 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=2,
        slot_bottom=15,
        player_top=P[2],
        player_bottom=P[3],
    )

    insert_match(t, m1.id, "2025-08-01", 1)
    insert_match(t, m2.id, "2025-08-01", 2)

    snap_id = save_planning_snapshot(t, label="before-change")

    # změna plánu
    clear_day(t, "2025-08-01")
    insert_match(t, m2.id, "2025-08-02", 1)

    # restore
    restore_planning_snapshot(t, snap_id)
    items = list_day_order(t, "2025-08-01")
    assert [x.match_id for x in items] == [m1.id, m2.id]
    assert [x.order for x in items] == [1, 2]
