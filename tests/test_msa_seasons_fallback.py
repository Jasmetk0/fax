import pytest
from django.apps import apps
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_tournaments_view_handles_missing_season(client):
    Season = apps.get_model("msa", "Season")
    if Season:
        Season.objects.all().delete()
    url = reverse("msa:tournaments_list")
    r = client.get(url)
    assert r.status_code == 200
    assert b"Tournaments" in r.content
    assert b"Apply filters" in r.content
    assert (
        b"Pro zadan\xc3\xa9 filtry nebyly nalezeny \xc5\xbe\xc3\xa1dn\xc3\xa9 turnaje." in r.content
    )
