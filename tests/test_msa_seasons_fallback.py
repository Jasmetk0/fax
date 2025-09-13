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
    assert b"Seasons" in r.content
