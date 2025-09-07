# tests/test_qual_confirm.py
import pytest
from msa.models import (
    Season, Category, CategorySeason, Tournament, Player, TournamentEntry,
    EntryType, EntryStatus, Phase, Match, MatchState, TournamentState
)
from msa.services.qual_confirm import confirm_qualification, update_ll_after_qual_finals


@pytest.mark.django_db
def test_confirm_qualification_creates_full_tree_and_seeds_on_tiers():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="World Tour")
    # K=2 kvalifikanti, R=3 → každá větev má 8 hráčů, seeds_per_bracket=2
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=32, qualifiers_count=2, qual_rounds=3)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.QUAL)

    # 16 hráčů do kvaldy (Q), WR: 1..16
    P = [Player.objects.create(name=f"P{i}") for i in range(1, 17)]
    for i, p in enumerate(P, start=1):
        TournamentEntry.objects.create(
            tournament=t, player=p, entry_type=EntryType.Q, status=EntryStatus.ACTIVE, wr_snapshot=i
        )

    branches = confirm_qualification(t, rng_seed=123)
    # Zkontroluj, že máme Q8, Q4 i Q2 zápasy a že počet odpovídá K větvím
    q8 = list(Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name="Q8"))
    q4 = list(Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name="Q4"))
    q2 = list(Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name="Q2"))
    assert len(q8) == 2 * 4   # K * (8/2) zápasů v prvním kole
    assert len(q4) == 2 * 2
    assert len(q2) == 2 * 1

    # Ověř, že první semeno (globální WR=1) je v TOP kotvě větve 0 (local_slot 1),
    # a druhé semeno (WR=2) v TOP kotvě větve 1 (local_slot 1) – Tier1→TOP.
    # Najdeme hráče s WR=1 a WR=2:
    wr1 = TournamentEntry.objects.get(tournament=t, player=P[0]).player_id
    wr2 = TournamentEntry.objects.get(tournament=t, player=P[1]).player_id
    # Z Q8 zápasů, slot_top == base+1 (TOP) musí obsahovat WR1 ve větvi 0 a WR2 ve větvi 1
    tops = sorted([m.player_top_id for m in q8 if m.slot_top % 1000 == 1])
    assert tops == [wr1, wr2]


@pytest.mark.django_db
def test_update_ll_after_qual_finals_promotes_final_losers():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="World Tour")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=32, qualifiers_count=2, qual_rounds=2)  # K=2, R=2 → Q4,Q2
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.QUAL)

    # 8 hráčů do kvaldy (Q)
    P = [Player.objects.create(name=f"P{i}\") for i in range(1, 9)]
    for p in P:
        TournamentEntry.objects.create(tournament=t, player=p, entry_type=EntryType.Q, status=EntryStatus.ACTIVE, wr_snapshot=50)

    confirm_qualification(t, rng_seed=7)

    # Vytvoř 2 finále výhry: v každém zápase nastav vítěze na player_top
    finals = list(Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name="Q2"))
    assert len(finals) == 2
    for m in finals:
        m.winner_id = m.player_top_id
        m.state = MatchState.DONE
        m.save(update_fields=["winner", "state"])

    promoted = update_ll_after_qual_finals(t)
    # Dva poražení finalisté mají být převedeni na LL
    assert promoted == 2
    ll_count = TournamentEntry.objects.filter(tournament=t, entry_type=EntryType.LL, status=EntryStatus.ACTIVE).count()
    assert ll_count == 2
