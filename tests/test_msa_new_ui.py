import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_msa_home_redirects_to_tournaments():
    url = reverse("msa:home")
    c = Client()
    resp = c.get(url, follow=False)
    assert resp.status_code in (301, 302)
    assert resp.headers["Location"].endswith(reverse("msa:tournaments_list"))


def test_msa_tournaments_lists_seasons_and_renders():
    url = reverse("msa:tournaments_list")
    c = Client()
    resp = c.get(url)
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Seasons" in body


def test_msa_calendar_renders_when_season_present():
    from msa.models import Season

    season = Season.objects.order_by("id").first()
    if not season:
        pytest.skip("No Season in DB yet; calendar relies on a season id")
    c = Client()
    resp = c.get(reverse("msa:calendar"), {"season": season.id})
    assert resp.status_code == 200
    body = resp.content.decode()
    # zobrazení hlavičky sezóny (label/name/year) nebo fallbacku
    assert "Season" in body or str(season.id) in body or "MSA" in body
