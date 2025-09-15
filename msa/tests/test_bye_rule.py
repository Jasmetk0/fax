import pytest

from msa.models import EntryStatus, EntryType, Match, MatchState, Phase, TournamentEntry
from msa.services.scoring import compute_md_points
from tests.factories import make_category_season, make_player, make_tournament


def _reg2(t, A, B):
    TournamentEntry.objects.create(
        tournament=t, player=A, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=t, player=B, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )


@pytest.mark.django_db
def test_bye_then_loss_in_first_played_awards_previous_round_points():
    cs, _, _ = make_category_season(draw_size=32, scoring_md={}, scoring_qual_win={})
    cs.refresh_from_db()
    tbl = cs.scoring_md.copy()
    tbl.update({"R32": 10, "R16": 20, "QF": 40, "SF": 80, "F": 160, "W": 300})
    cs.scoring_md = tbl
    cs.save(update_fields=["scoring_md"])

    t = make_tournament(cs=cs)
    A = make_player("A")
    B = make_player("B")
    _reg2(t, A, B)

    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        player_top=A,
        player_bottom=B,
        winner=B,
        state=MatchState.DONE,
        best_of=5,
        win_by_two=True,
    )

    pts = compute_md_points(t, only_completed_rounds=False)
    assert pts.get(A.id, 0) == 10


@pytest.mark.django_db
def test_bye_then_win_then_later_loss_awards_actual_round_points():
    cs, _, _ = make_category_season(draw_size=32, scoring_md={}, scoring_qual_win={})
    cs.refresh_from_db()
    tbl = cs.scoring_md.copy()
    tbl.update({"R32": 10, "R16": 20, "QF": 40, "SF": 80, "F": 160, "W": 300})
    cs.scoring_md = tbl
    cs.save(update_fields=["scoring_md"])

    t = make_tournament(cs=cs)
    A = make_player("A")
    B = make_player("B")
    C = make_player("C")
    for p in (A, B, C):
        TournamentEntry.objects.create(
            tournament=t, player=p, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
        )

    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        player_top=A,
        player_bottom=B,
        winner=A,
        state=MatchState.DONE,
        best_of=5,
        win_by_two=True,
    )
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="QF",
        player_top=A,
        player_bottom=C,
        winner=C,
        state=MatchState.DONE,
        best_of=5,
        win_by_two=True,
    )

    pts = compute_md_points(t, only_completed_rounds=False)
    assert pts.get(A.id, 0) == 40


@pytest.mark.django_db
def test_bye_then_loss_in_final_awards_runnerup_with_F_alias():
    cs, _, _ = make_category_season(draw_size=4, scoring_md={}, scoring_qual_win={})
    cs.refresh_from_db()
    cs.scoring_md.update({"W": 100, "F": 60})
    cs.save(update_fields=["scoring_md"])

    t = make_tournament(cs=cs)
    A = make_player("A")
    B = make_player("B")
    _reg2(t, A, B)

    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="F",
        player_top=A,
        player_bottom=B,
        winner=B,
        state=MatchState.DONE,
        best_of=5,
        win_by_two=True,
    )

    pts = compute_md_points(t, only_completed_rounds=False)
    assert pts.get(A.id, 0) == 60
