import pytest
from django.urls import reverse

from msa.models import Category, Season, Tournament

pytestmark = pytest.mark.django_db


def test_tournaments_api_serializes_category_string(client):
    season = Season.objects.create(
        name="2024/25",
        start_date="2024-01-01",
        end_date="2024-12-28",
    )
    category = Category.objects.create(name="Masters 1000")
    tournament = Tournament.objects.create(
        name="Example Open",
        season=season,
        category=category,
        start_date="2024-05-01",
        end_date="2024-05-15",
    )

    response = client.get(reverse("msa-tournaments-api"), {"season": season.id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["tournaments"], "Expected at least one tournament in response"

    returned = next((item for item in payload["tournaments"] if item["id"] == tournament.id), None)
    assert returned is not None
    assert returned["category"] == category.name


def test_tournaments_api_uses_tier_when_category_missing(client, monkeypatch):
    season = Season.objects.create(
        name="2025/26",
        start_date="2025-11-01",
        end_date="2026-11-01",
    )

    monkeypatch.setattr(
        Tournament,
        "tier",
        property(lambda self: getattr(self, "snapshot_label", None)),
        raising=False,
    )

    tournament = Tournament.objects.create(
        name="Tier Masters",
        season=season,
        snapshot_label="Gold",
        start_date="2025-11-05",
        end_date="2025-11-12",
    )

    response = client.get(reverse("msa-tournaments-api"), {"season": season.id})

    assert response.status_code == 200
    payload = response.json()
    returned = next((item for item in payload["tournaments"] if item["id"] == tournament.id), None)
    assert returned is not None
    assert returned["category"] == "Gold"


def test_tournaments_api_returns_empty_category_without_category_and_tier(client):
    season = Season.objects.create(
        name="2026/27",
        start_date="2026-11-01",
        end_date="2027-11-01",
    )
    tournament = Tournament.objects.create(
        name="Mystery Open",
        season=season,
        start_date="2026-12-10",
        end_date="2026-12-18",
    )

    response = client.get(reverse("msa-tournaments-api"), {"season": season.id})

    assert response.status_code == 200
    payload = response.json()
    returned = next((item for item in payload["tournaments"] if item["id"] == tournament.id), None)
    assert returned is not None
    assert returned["category"] == ""


def test_tournaments_api_is_sorted_by_start_date_then_name(client):
    season = Season.objects.create(
        name="2027/28",
        start_date="2027-11-01",
        end_date="2028-11-01",
    )
    t1 = Tournament.objects.create(
        name="Zeta Championship",
        season=season,
        start_date="2028-01-20",
        end_date="2028-01-25",
    )
    t2 = Tournament.objects.create(
        name="Alpha Cup",
        season=season,
        start_date="2028-01-05",
        end_date="2028-01-09",
    )
    t3 = Tournament.objects.create(
        name="Beta Cup",
        season=season,
        start_date="2028-01-05",
        end_date="2028-01-12",
    )

    response = client.get(reverse("msa-tournaments-api"), {"season": season.id})

    assert response.status_code == 200
    payload = response.json()
    order = [item["id"] for item in payload["tournaments"]]
    assert order == [t2.id, t3.id, t1.id]
