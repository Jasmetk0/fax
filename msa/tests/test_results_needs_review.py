# tests/test_results_needs_review.py
import pytest
from msa.models import (
    Season, Category, CategorySeason, Tournament, Player, TournamentEntry,
    EntryType, EntryStatus, Phase, Match, MatchState, TournamentState
)
from msa.services.md_confirm import confirm_main_draw
from msa.services.results import set_result, resolve_needs_review


@pytest.mark.django_db
def test_set_result_win_only_and_needs_review_propagation():
    # Setup: MD16 se 4 seed
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD)

    # 16 hráčů, WR 1..16
    P = [Player.objects.create(name=f"P{i}") for i in range(1, 17)]
    for i, p in enumerate(P, start=1):
        TournamentEntry.objects.create(tournament=t, player=p, entry_type=EntryType.DA, status=EntryStatus.ACTIVE, wr_snapshot=i)

    confirm_main_draw(t, rng_seed=1)

    # vezmeme první R1 zápas
    m = Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16").order_by("slot_top").first()
    assert m.state == MatchState.PENDING

    # vytvoříme ručně R8 zápas, kde (zatím) počítáme s výhercem TOP z R1
    r8 = Match.objects.create(
        tournament=t, phase=Phase.MD, round_name="R8",
        slot_top=1, slot_bottom=8,  # jen symbolicky
        player_top_id=m.player_top_id, player_bottom_id=None,
        best_of=5, win_by_two=True, state=MatchState.PENDING
    )

    # nastav R1 výsledek WIN_ONLY: vyhrál TOP
    set_result(m.id, mode="WIN_ONLY", winner="top")
    m.refresh_from_db()
    assert m.state == MatchState.DONE and m.winner_id == m.player_top_id

    # Změň vítěze na BOTTOM → musí se propsat do R8 a nastavit needs_review=True
    set_result(m.id, mode="WIN_ONLY", winner="bottom")
    r8.refresh_from_db()
    assert r8.player_top_id == m.winner_id
    assert r8.needs_review is True

    # potvrzení review
    resolve_needs_review(r8.id)
    r8.refresh_from_db()
    assert r8.needs_review is False


@pytest.mark.django_db
def test_set_result_sets_validation_bo5_win_by_two():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.MD)

    P1 = Player.objects.create(name="A")
    P2 = Player.objects.create(name="B")
    # ruční zápas
    m = Match.objects.create(tournament=t, phase=Phase.MD, round_name="R16",
                             slot_top=1, slot_bottom=16,
                             player_top=P1, player_bottom=P2,
                             best_of=5, win_by_two=True)

    # validní BO5: 3:1 (11:9, 9:11, 11:9, 11:7)
    set_result(m.id, mode="SETS", sets=[(11,9),(9,11),(11,9),(11,7)])
    m.refresh_from_db()
    assert m.state == MatchState.DONE and m.winner_id == P1.id

    # nevalidní (chybí rozdíl 2) → chyba
    m2 = Match.objects.create(tournament=t, phase=Phase.MD, round_name="R16",
                              slot_top=2, slot_bottom=15,
                              player_top=P1, player_bottom=P2,
                              best_of=3, win_by_two=True)
    with pytest.raises(Exception):
        set_result(m2.id, mode="SETS", sets=[(11,10),(10,12),(11,9)])

    # SPECIAL: WO pro B
    m3 = Match.objects.create(tournament=t, phase=Phase.MD, round_name="R16",
                              slot_top=3, slot_bottom=14,
                              player_top=P1, player_bottom=P2,
                              best_of=3, win_by_two=True)
    set_result(m3.id, mode="SPECIAL", winner="bottom", special="WO")
    m3.refresh_from_db()
    assert m3.winner_id == P2.id and m3.state == MatchState.DONE
