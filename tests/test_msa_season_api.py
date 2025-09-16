import pytest
from django.urls import reverse

from msa.models import Season

pytestmark = pytest.mark.django_db


def test_season_api_month_sequence(client):
    season = Season.objects.create(
        name="2000/01",
        start_date="2000-11-03",
        end_date="2001-11-01",
    )

    response = client.get(reverse("msa-season-api"), {"season": season.id})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == season.id
    assert data["month_sequence"] == [11, 12, 13, 14, 15, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
