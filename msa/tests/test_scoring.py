# tests/test_scoring.py
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
from msa.services.md_confirm import confirm_main_draw
from msa.services.md_embed import effective_template_size_for_md
from msa.services.qual_confirm import confirm_qualification
from msa.services.scoring import compute_md_points, compute_q_wins_points, compute_tournament_points


@pytest.mark.django_db
def test_q_wins_and_md_points_with_bye_rule_draw24():
    # MD24 embed do R32, S=8 → top8 má BYE v "R32"
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=24, md_seeds_count=8)

    # scoring tabulky jen v paměti (měkké modely)
    cs.scoring_md = {"Winner": 1000, "RunnerUp": 600, "SF": 360, "QF": 180, "R16": 90, "R32": 45}
    cs.scoring_qual_win = {"Q4": 10, "Q2": 20}

    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T24", slug="t24", state=TournamentState.MD
    )

    # 24 hráčů, WR 1..24 (1 nejlepší). Seedy 1..8, zbytek nenasazení.
    players = [Player.objects.create(name=f"P{i}") for i in range(1, 25)]
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )

    mapping = confirm_main_draw(t, rng_seed=42)
    assert effective_template_size_for_md(t) == 32

    # Najdi nějakého z top8 (má BYE) – necháme ho prohrát v prvním odehraném zápase (R16).
    # Vezmeme seed #1 = WR=1 (players[0]).
    top1 = players[0]
    # Jeho první zápas bude v R16: vytvoříme 1 zápas R16, kde prohraje
    m = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=16,  # symbolicky
        player_top=top1,
        player_bottom=players[9],  # nějaký soupeř
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )
    # nechť prohraje
    m.winner_id = players[9].id
    m.state = MatchState.DONE
    m.save(update_fields=["winner", "state"])

    md_pts = compute_md_points(t, only_completed_rounds=False)
    # BYE rule: prohra v prvním odehraném zápase po BYE → body za R32 (ne R16)
    assert md_pts.get(top1.id, 0) == cs.scoring_md["R32"]


@pytest.mark.django_db
def test_q_wins_accumulate_and_total_combines_with_md():
    # kvalda K=1, R=2 (Q4 -> Q2), jednoduché body za výhry: Q4=10, Q2=20
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(
        category=c, season=s, draw_size=16, md_seeds_count=4, qual_rounds=2
    )

    cs.scoring_md = {"Winner": 100, "RunnerUp": 60, "SF": 36, "QF": 18, "R16": 9}
    cs.scoring_qual_win = {"Q4": 10, "Q2": 20}

    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T16",
        slug="t16",
        state=TournamentState.QUAL,
        qualifiers_count=1,
    )

    # 4 hráči do kvaldy
    QP = [Player.objects.create(name=f"Q{i}") for i in range(1, 5)]
    for p in QP:
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.Q,
            status=EntryStatus.ACTIVE,
            wr_snapshot=50,
        )

    # potvrď kvaldu a odehraj ji – ať vyhraje Q1 (QP[0]) oba zápasy Q4 i Q2
    confirm_qualification(t, rng_seed=7)
    q4 = list(Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name="Q4"))
    q2 = list(Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name="Q2"))
    # Q1 vyhraje oba
    for m in q4 + q2:
        m.winner_id = QP[0].id
        m.state = MatchState.DONE
        m.save(update_fields=["winner", "state"])

    # Q-wins body: 10 + 20 = 30
    q_pts = compute_q_wins_points(t)
    assert q_pts.get(QP[0].id, 0) == 30

    # Přidej pár MD zápasů – simulace, že kvalifikant prohrál v R16
    t.state = TournamentState.MD
    t.save(update_fields=["state"])
    m = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=16,
        player_top=QP[0],
        player_bottom=QP[1],
        best_of=5,
        win_by_two=True,
        state=MatchState.DONE,
        winner=QP[1],
    )
    # Celkem = Q(30) + MD(R16=9) = 39
    totals = compute_tournament_points(t, only_completed_rounds=False)
    assert totals[QP[0].id].q_wins == 30
    assert totals[QP[0].id].md_points == cs.scoring_md["R16"]
    assert totals[QP[0].id].total == 30 + cs.scoring_md["R16"]
