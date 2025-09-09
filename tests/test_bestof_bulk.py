import pytest
from django.conf import settings

from msa.models import Match, Phase, Player, Tournament
from msa.services.bestof_tools import bulk_set_best_of
from msa.services.results import set_result


@pytest.mark.django_db
def test_bulk_set_best_of_updates_only_unplayed():
    settings.MSA_ADMIN_MODE = True
    t = Tournament.objects.create(name="T", slug="t")
    p1 = Player.objects.create(name="A")
    p2 = Player.objects.create(name="B")
    p3 = Player.objects.create(name="C")
    p4 = Player.objects.create(name="D")

    m1 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        player_top=p1,
        player_bottom=p2,
        best_of=3,
    )
    m2 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        player_top=p3,
        player_bottom=p4,
        best_of=3,
    )
    m3 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        player_top=p1,
        player_bottom=p3,
        best_of=3,
    )

    set_result(m2.id, mode="WIN_ONLY", winner="top")
    set_result(m3.id, mode="SETS", sets=[(11, 9), (9, 11), (11, 7)])

    summary = bulk_set_best_of(t, phase=Phase.MD, mode="BO5", only_unplayed=True)

    m1.refresh_from_db()
    m2.refresh_from_db()
    m3.refresh_from_db()

    assert m1.best_of == 5
    assert m2.best_of == 3
    assert m3.best_of == 3
    assert summary == {
        "target_best_of": 5,
        "matches_scanned": 3,
        "matches_updated": 1,
        "matches_skipped_played": 2,
        "matches_skipped_filtered": 0,
    }


@pytest.mark.django_db
def test_bulk_set_best_of_respects_round_filters():
    settings.MSA_ADMIN_MODE = True
    t = Tournament.objects.create(name="T", slug="t2")
    p1 = Player.objects.create(name="A")
    p2 = Player.objects.create(name="B")
    p3 = Player.objects.create(name="C")
    p4 = Player.objects.create(name="D")

    m_r16 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        player_top=p1,
        player_bottom=p2,
        best_of=3,
    )
    m_qf = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="QF",
        player_top=p3,
        player_bottom=p4,
        best_of=3,
    )

    summary = bulk_set_best_of(t, phase=Phase.MD, rounds={"QF"}, mode="BO5")

    m_r16.refresh_from_db()
    m_qf.refresh_from_db()

    assert m_r16.best_of == 3
    assert m_qf.best_of == 5
    assert summary == {
        "target_best_of": 5,
        "matches_scanned": 1,
        "matches_updated": 1,
        "matches_skipped_played": 0,
        "matches_skipped_filtered": 0,
    }


@pytest.mark.django_db
def test_bulk_set_best_of_idempotent():
    settings.MSA_ADMIN_MODE = True
    t = Tournament.objects.create(name="T", slug="t3")
    p1 = Player.objects.create(name="A")
    p2 = Player.objects.create(name="B")

    m = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        player_top=p1,
        player_bottom=p2,
        best_of=3,
    )

    summary1 = bulk_set_best_of(t, phase=Phase.MD, mode="BO5")
    summary2 = bulk_set_best_of(t, phase=Phase.MD, mode="BO5")

    m.refresh_from_db()
    assert m.best_of == 5
    assert summary1["matches_updated"] == 1
    assert summary2["matches_updated"] == 0
