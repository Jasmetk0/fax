import pytest
from django.core.management import call_command

from msa.models import EntryStatus, EntryType, Match, MatchState, Phase, Player
from msa.services.scoring import compute_md_points
from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_awarding_prefers_W_and_F_over_legacy():
    cs, _, _ = make_category_season(draw_size=4, scoring_md={}, scoring_qual_win={})
    cs.refresh_from_db()
    tbl = cs.scoring_md.copy()
    tbl.update({"W": 100, "F": 60})
    cs.scoring_md = tbl
    cs.save(update_fields=["scoring_md"])

    t = make_tournament(cs=cs)
    A = Player.objects.create(name="A")
    B = Player.objects.create(name="B")
    for p in (A, B):
        t.tournamententry_set.create(player=p, entry_type=EntryType.DA, status=EntryStatus.ACTIVE)

    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="F",
        player_top=A,
        player_bottom=B,
        winner=A,
        state=MatchState.DONE,
        best_of=5,
        win_by_two=True,
    )
    pts = compute_md_points(t, only_completed_rounds=False)
    assert pts.get(A.id, 0) == 100
    assert pts.get(B.id, 0) == 60


@pytest.mark.django_db
def test_awarding_falls_back_to_legacy_when_new_missing():
    cs, _, _ = make_category_season(draw_size=4, scoring_md={}, scoring_qual_win={})
    cs.refresh_from_db()
    cs.scoring_md = {"Winner": 90, "RunnerUp": 45}
    cs.save(update_fields=["scoring_md"])

    t = make_tournament(cs=cs)
    A = Player.objects.create(name="A2")
    B = Player.objects.create(name="B2")
    for p in (A, B):
        t.tournamententry_set.create(player=p, entry_type=EntryType.DA, status=EntryStatus.ACTIVE)

    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="F",
        player_top=A,
        player_bottom=B,
        winner=A,
        state=MatchState.DONE,
        best_of=5,
        win_by_two=True,
    )
    pts = compute_md_points(t, only_completed_rounds=False)
    assert pts.get(A.id, 0) == 90
    assert pts.get(B.id, 0) == 45


@pytest.mark.django_db
def test_backfill_maps_legacy_keys_to_new_including_third_place():
    cs, _, _ = make_category_season(
        draw_size=16, scoring_md={}, scoring_qual_win={}, third_place=True
    )
    cs.scoring_md = {"Winner": 777, "RunnerUp": 444, "SF": 111}
    cs.save(update_fields=["scoring_md"])

    t = make_tournament(cs=cs, third_place=True)
    call_command("msa_fix_points_backfill", "--dry-run")
    t.refresh_from_db()
    assert "W" not in t.scoring_md
    assert t.scoring_md.get("Winner") == 777

    call_command("msa_fix_points_backfill")
    t.refresh_from_db()
    assert t.scoring_md.get("W") == 777
    assert t.scoring_md.get("F") == 444
    assert t.scoring_md.get("3rd") == 111
    assert t.scoring_md.get("4th") == 111
