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
from msa.services.md_third_place import ensure_third_place_match
from msa.services.results import set_result
from tests.woorld_helpers import woorld_date


@pytest.mark.django_db
def test_auto_third_place_is_created_after_both_sf_done():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    cs.scoring_md = {"Winner": 1000, "RunnerUp": 600, "SF": 90, "Third": 200, "Fourth": 120}
    cs.save(update_fields=["scoring_md"])
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T",
        slug="t",
        state=TournamentState.MD,
        third_place_enabled=True,
    )

    A, B, C, D = [Player.objects.create(name=n) for n in ["A", "B", "C", "D"]]
    for p in [A, B, C, D]:
        TournamentEntry.objects.create(
            tournament=t, player=p, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
        )

    sf1 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )
    sf2 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=3,
        slot_bottom=4,
        player_top=C,
        player_bottom=D,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )

    # A porazí B, D porazí C
    set_result(sf1.id, mode="WIN_ONLY", winner="top")
    set_result(sf2.id, mode="WIN_ONLY", winner="bottom")

    m3p = Match.objects.filter(tournament=t, phase=Phase.MD, round_name="3P").first()
    assert m3p is not None
    assert set([m3p.player_top_id, m3p.player_bottom_id]) == set([B.id, C.id])
    assert m3p.state == MatchState.PENDING


@pytest.mark.django_db
def test_third_place_updates_players_if_pending_and_sf_changes():
    # Setup jako výše
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T2",
        slug="t2",
        state=TournamentState.MD,
        third_place_enabled=True,
    )
    A, B, C, D = [Player.objects.create(name=n) for n in ["A", "B", "C", "D"]]
    for p in [A, B, C, D]:
        TournamentEntry.objects.create(
            tournament=t, player=p, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
        )

    sf1 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )
    sf2 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=3,
        slot_bottom=4,
        player_top=C,
        player_bottom=D,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )

    # Původně: A> B, D > C => 3P = B vs C
    set_result(sf1.id, mode="WIN_ONLY", winner="top")
    set_result(sf2.id, mode="WIN_ONLY", winner="bottom")
    m3p = Match.objects.filter(tournament=t, phase=Phase.MD, round_name="3P").first()
    assert set([m3p.player_top_id, m3p.player_bottom_id]) == set([B.id, C.id])

    # Změna výsledku jednoho SF (B porazí A); 3P je PENDING → aktualizuje se na A vs C
    set_result(sf1.id, mode="WIN_ONLY", winner="bottom")
    m3p.refresh_from_db()
    assert set([m3p.player_top_id, m3p.player_bottom_id]) == set([A.id, C.id])


@pytest.mark.django_db
def test_third_place_removed_when_flag_off():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T3",
        slug="t3",
        state=TournamentState.MD,
        third_place_enabled=True,
    )
    A, B = Player.objects.create(name="A"), Player.objects.create(name="B")
    TournamentEntry.objects.create(
        tournament=t, player=A, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=t, player=B, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )

    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="3P",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )
    assert Match.objects.filter(tournament=t, phase=Phase.MD, round_name="3P").exists()

    t.third_place_enabled = False
    t.save(update_fields=["third_place_enabled"])
    ensure_third_place_match(t)

    assert not Match.objects.filter(tournament=t, phase=Phase.MD, round_name="3P").exists()


@pytest.mark.django_db
def test_third_place_idempotent_and_done_preserved():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T4",
        slug="t4",
        state=TournamentState.MD,
        third_place_enabled=True,
    )
    A, B, C, D = [Player.objects.create(name=n) for n in ["A", "B", "C", "D"]]
    for p in [A, B, C, D]:
        TournamentEntry.objects.create(
            tournament=t, player=p, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
        )

    sf1 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )
    sf2 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=3,
        slot_bottom=4,
        player_top=C,
        player_bottom=D,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )

    set_result(sf1.id, mode="WIN_ONLY", winner="top")
    set_result(sf2.id, mode="WIN_ONLY", winner="bottom")

    m3p = Match.objects.filter(tournament=t, phase=Phase.MD, round_name="3P").first()
    original_players = (m3p.player_top_id, m3p.player_bottom_id)
    first_id = m3p.id

    ensure_third_place_match(t)
    ensure_third_place_match(t)
    m3p.refresh_from_db()
    assert m3p.id == first_id
    assert (m3p.player_top_id, m3p.player_bottom_id) == original_players
    assert Match.objects.filter(tournament=t, phase=Phase.MD, round_name="3P").count() == 1

    set_result(m3p.id, mode="WIN_ONLY", winner="top")
    done_players = (m3p.player_top_id, m3p.player_bottom_id)

    set_result(sf1.id, mode="WIN_ONLY", winner="bottom")
    m3p.refresh_from_db()
    assert (m3p.player_top_id, m3p.player_bottom_id) == done_players
    assert m3p.state == MatchState.DONE
