import pytest

from msa.models import Match, MatchState, Phase
from msa.services.results import set_result
from msa.services.scoring import compute_md_points
from tests.factories import (
    make_category_season,
    make_player,
    make_tournament,
)


@pytest.mark.django_db
def test_bye_scoring_in_embed_template():
    cs, _, _ = make_category_season(
        draw_size=24,
        qualifiers_count=0,
        qual_rounds=0,
        scoring_md={
            "R32": 10,
            "R16": 20,
            "QF": 50,
            "SF": 120,
            "RunnerUp": 200,
            "Winner": 300,
        },
    )
    t = make_tournament(cs=cs)
    x = make_player("X")
    y = make_player("Y")

    m_r16 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=16,
        player_top_id=x.id,
        player_bottom_id=y.id,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )

    c = make_player("C")
    d = make_player("D")
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=2,
        slot_bottom=15,
        player_top_id=c.id,
        player_bottom_id=d.id,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )

    set_result(m_r16.id, mode="WIN_ONLY", winner="bottom")

    pts_true = compute_md_points(t, only_completed_rounds=True)
    pts_false = compute_md_points(t, only_completed_rounds=False)

    assert pts_true.get(x.id, 0) == 0
    assert pts_false.get(x.id, 0) == 10
