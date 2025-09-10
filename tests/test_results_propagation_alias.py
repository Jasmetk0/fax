import pytest

from msa.models import Match, MatchState, Phase
from msa.services.results import set_result
from tests.factories import make_player, make_tournament


@pytest.mark.django_db
def test_propagation_to_alias_round_qf():
    t = make_tournament()
    a = make_player("A")
    b = make_player("B")

    m_r16 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=16,
        player_top_id=a.id,
        player_bottom_id=b.id,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )

    m_qf = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="QF",
        slot_top=1,
        slot_bottom=8,
        player_top_id=None,
        player_bottom_id=None,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )

    set_result(m_r16.id, mode="WIN_ONLY", winner="top")
    m_qf.refresh_from_db()
    assert m_qf.player_top_id == a.id
    assert not m_qf.needs_review

    set_result(m_r16.id, mode="WIN_ONLY", winner="bottom")
    m_qf.refresh_from_db()
    assert m_qf.player_top_id == b.id
    assert m_qf.needs_review is True
