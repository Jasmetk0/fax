import pytest

from msa.models import Match, MatchState, Phase
from msa.services.results import set_result
from msa.services.scoring import compute_md_points
from tests.factories import make_category_season, make_player, make_tournament


@pytest.mark.django_db
def test_final_alias_awards_winner_points():
    cs, _, _ = make_category_season(
        draw_size=2,
        qualifiers_count=0,
        qual_rounds=0,
        scoring_md={"RunnerUp": 50, "Winner": 100},
    )
    t = make_tournament(cs=cs)
    x = make_player("X")
    y = make_player("Y")
    m_final = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="F",
        slot_top=1,
        slot_bottom=2,
        player_top_id=x.id,
        player_bottom_id=y.id,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )
    set_result(m_final.id, mode="WIN_ONLY", winner="top")

    pts = compute_md_points(t, only_completed_rounds=True)
    assert pts.get(x.id, 0) == 100
    assert pts.get(y.id, 0) == 50


@pytest.mark.django_db
def test_alias_round_names_respected_for_last_full_round():
    cs, _, _ = make_category_season(
        draw_size=8,
        qualifiers_count=0,
        qual_rounds=0,
        scoring_md={
            "QF": 50,
            "SF": 120,
            "RunnerUp": 200,
            "Winner": 300,
        },
    )
    t = make_tournament(cs=cs)
    players = [make_player(f"P{i}") for i in range(1, 9)]

    qf_matches = []
    for i in range(4):
        m = Match.objects.create(
            tournament=t,
            phase=Phase.MD,
            round_name="QF",
            slot_top=i + 1,
            slot_bottom=8 - i,
            player_top_id=players[2 * i].id,
            player_bottom_id=players[2 * i + 1].id,
            best_of=5,
            win_by_two=True,
            state=MatchState.PENDING,
        )
        qf_matches.append(m)
    for m in qf_matches:
        set_result(m.id, mode="WIN_ONLY", winner="top")

    sf1 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=1,
        slot_bottom=4,
        player_top_id=players[0].id,
        player_bottom_id=players[2].id,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )
    set_result(sf1.id, mode="WIN_ONLY", winner="top")
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=2,
        slot_bottom=3,
        player_top_id=players[4].id,
        player_bottom_id=players[6].id,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )

    pts_true = compute_md_points(t, only_completed_rounds=True)
    pts_false = compute_md_points(t, only_completed_rounds=False)

    assert pts_true.get(players[1].id, 0) == 50
    assert pts_false.get(players[1].id, 0) == 50

    assert pts_true.get(players[2].id, 0) == 0
    assert pts_false.get(players[2].id, 0) == 120
