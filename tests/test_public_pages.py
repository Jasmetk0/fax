import datetime as dt

import pytest
from django.test import Client

from msa.models import EntryType, Match, Schedule, TournamentEntry
from tests.factories import make_category_season, make_player, make_tournament

pytestmark = pytest.mark.legacy_msa_public


@pytest.mark.django_db
def test_public_views_smoke(client: Client):
    cs, season, _ = make_category_season(draw_size=4)
    t = make_tournament(cs=cs)
    p1 = make_player("A")
    p2 = make_player("B")
    p3 = make_player("C")
    p4 = make_player("D")
    TournamentEntry.objects.create(
        tournament=t, player=p1, entry_type=EntryType.DA, seed=1, wr_snapshot=1
    )
    TournamentEntry.objects.create(
        tournament=t, player=p2, entry_type=EntryType.DA, seed=2, wr_snapshot=2
    )
    TournamentEntry.objects.create(tournament=t, player=p3, entry_type=EntryType.DA, wr_snapshot=3)
    TournamentEntry.objects.create(tournament=t, player=p4, entry_type=EntryType.DA, wr_snapshot=4)
    m = Match.objects.create(tournament=t, round_name="R1", player_top=p1, player_bottom=p2)
    Schedule.objects.create(tournament=t, match=m, play_date=dt.date.today(), order=1)

    resp = client.get("/msa/")
    assert resp.status_code == 200 and "T" in resp.text

    resp = client.get(f"/msa/t/{t.slug}/")
    assert resp.status_code == 200 and "Registration" in resp.text

    for sub in ["registration", "qualification", "main-draw", "schedule", "results"]:
        resp = client.get(f"/msa/t/{t.slug}/{sub}/")
        assert resp.status_code == 200

    resp = client.get(f"/msa/standings/season/{season.id}/")
    assert resp.status_code == 200
    assert client.get("/msa/standings/rolling/").status_code == 200
    assert client.get("/msa/standings/rtf/").status_code == 200
