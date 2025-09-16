import pytest
from django.urls import reverse

from tests.factories import make_category_season

pytestmark = pytest.mark.django_db


def test_calendar_page_includes_script(client):
    _, season, _ = make_category_season()
    resp = client.get(reverse("msa:calendar"), {"season": season.id})
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "msa/js/calendar.js" in html  # script je na stránce
    assert 'id="month-filter"' in html  # select existuje
