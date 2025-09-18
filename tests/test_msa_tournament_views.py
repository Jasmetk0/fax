import pytest
from django.urls import reverse

from msa.models import Season, Tournament

pytestmark = pytest.mark.django_db


def create_tournament(**overrides):
    season = overrides.pop(
        "season",
        Season.objects.create(name="2024/01", start_date="2024-05-01", end_date="2025-04-20"),
    )
    defaults = {
        "name": "Test Tournament",
        "start_date": "2024-05-10",
        "end_date": "2024-05-15",
        "draw_size": 32,
        "qualifiers_count": 4,
    }
    defaults.update(overrides)
    return Tournament.objects.create(season=season, **defaults)


def test_tournament_program_view_smoke(client):
    tournament = create_tournament()

    url = reverse("msa:tournament_program", args=[tournament.id])
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert 'id="prog-order"' in content
    assert 'id="prog-table"' in content


def test_tournament_info_view_shows_range(client):
    tournament = create_tournament()

    url = reverse("msa:tournament_info", args=[tournament.id])
    response = client.get(url)

    assert response.status_code == 200
    assert "2024-05-10" in response.content.decode()
    assert "2024-05-15" in response.content.decode()


def test_tournament_matches_api_returns_empty_list(client):
    tournament = create_tournament()
    url = reverse("msa-tournament-matches-api", args=[tournament.id])

    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert data["matches"] == []


def test_tournament_courts_api_returns_empty_list(client):
    tournament = create_tournament()
    url = reverse("msa-tournament-courts-api", args=[tournament.id])

    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert "courts" in data
    assert data["courts"] == []
