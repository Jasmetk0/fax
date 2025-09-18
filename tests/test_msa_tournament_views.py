import pytest
from django.urls import reverse

from msa.models import Match, Player, Schedule, Season, Tournament

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
    assert data["count"] == 0
    assert data["limit"] == 100
    assert data["offset"] == 0
    assert data["next_offset"] is None


def test_tournament_courts_api_returns_empty_list(client):
    tournament = create_tournament()
    url = reverse("msa-tournament-courts-api", args=[tournament.id])

    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert "courts" in data
    assert data["courts"] == []


def test_tournament_matches_api_filters_and_response_shape(client):
    tournament = create_tournament()
    alice = Player.objects.create(full_name="Alice Example")
    bob = Player.objects.create(full_name="Bob Example")
    cara = Player.objects.create(full_name="Cara Example")
    dan = Player.objects.create(full_name="Dan Example")

    match_finished = Match.objects.create(
        tournament=tournament,
        phase="MD",
        round_name="R32",
        player1=alice,
        player2=bob,
        state="DONE",
        best_of=5,
        score={
            "sets": [[11, 9], [11, 7], [11, 8]],
            "court": {"id": "court-1", "name": "Center Court"},
        },
    )
    Schedule.objects.create(
        tournament=tournament,
        match=match_finished,
        play_date="2024-05-10",
        order=1,
    )

    match_live = Match.objects.create(
        tournament=tournament,
        phase="MD",
        round_name="R32",
        player1=cara,
        player2=dan,
        state="SCHEDULED",
        best_of=5,
        score={
            "sets": [
                {"a": 11, "b": 8},
                {"a": 5, "b": None, "status": "IN_PROGRESS"},
            ],
            "court": {"id": "court-2", "name": "Court Two"},
        },
    )
    Schedule.objects.create(
        tournament=tournament,
        match=match_live,
        play_date="2024-05-10",
        order=2,
    )

    match_other = Match.objects.create(
        tournament=tournament,
        phase="QUAL",
        round_name="Q1",
        player1=alice,
        player2=cara,
        state="SCHEDULED",
        best_of=3,
        score={"sets": [[11, 3], [11, 5]]},
    )
    Schedule.objects.create(
        tournament=tournament,
        match=match_other,
        play_date="2024-05-11",
        order=1,
    )

    url = reverse("msa-tournament-matches-api", args=[tournament.id])
    response = client.get(
        url,
        {
            "fax_day": "2024-05-10",
            "phase": "md",
            "status": "finished",
            "court": "court-1",
            "q": "alice",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["limit"] == 100
    assert data["offset"] == 0
    assert data["next_offset"] is None
    assert [item["id"] for item in data["matches"]] == [match_finished.id]
    match_data = data["matches"][0]
    assert match_data["court"] == {"id": "court-1", "name": "Center Court"}
    assert match_data["status"] == "finished"

    live_response = client.get(url, {"status": "live"})
    assert live_response.status_code == 200
    live_data = live_response.json()
    live_ids = [item["id"] for item in live_data["matches"]]
    assert match_live.id in live_ids
    assert all(item["status"] == "live" for item in live_data["matches"])


def test_tournament_matches_api_orders_and_includes_court(client):
    tournament = create_tournament()
    player_a = Player.objects.create(full_name="Player A")
    player_b = Player.objects.create(full_name="Player B")
    player_c = Player.objects.create(full_name="Player C")
    player_d = Player.objects.create(full_name="Player D")

    match_b = Match.objects.create(
        tournament=tournament,
        phase="MD",
        round_name="R16",
        player1=player_a,
        player2=player_b,
        state="SCHEDULED",
        score={"sets": [], "court": {"id": "b", "name": "Court B"}},
    )
    Schedule.objects.create(
        tournament=tournament,
        match=match_b,
        play_date="2024-05-10",
        order=2,
    )

    match_a = Match.objects.create(
        tournament=tournament,
        phase="MD",
        round_name="R16",
        player1=player_c,
        player2=player_d,
        state="SCHEDULED",
        score={"sets": [], "court": {"id": "a", "name": "Court A"}},
    )
    Schedule.objects.create(
        tournament=tournament,
        match=match_a,
        play_date="2024-05-10",
        order=1,
    )

    match_c = Match.objects.create(
        tournament=tournament,
        phase="MD",
        round_name="SF",
        player1=player_a,
        player2=player_c,
        state="SCHEDULED",
        score={"sets": [], "court": {"id": "c", "name": "Court C"}},
    )
    Schedule.objects.create(
        tournament=tournament,
        match=match_c,
        play_date="2024-05-11",
        order=1,
    )

    url = reverse("msa-tournament-matches-api", args=[tournament.id])
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    ordered_ids = [item["id"] for item in data["matches"]]
    assert ordered_ids == [match_a.id, match_b.id, match_c.id]
    for item in data["matches"]:
        assert isinstance(item["court"], dict)
        assert item["court"]["name"]


def test_tournament_matches_api_limit_clamped(client):
    tournament = create_tournament()
    player = Player.objects.create(full_name="Limit Player")

    for index in range(2):
        match = Match.objects.create(
            tournament=tournament,
            phase="MD",
            round_name=f"R{index}",
            player1=player,
            player2=player,
            state="SCHEDULED",
            score={"sets": [], "court": {"id": f"court-{index}", "name": f"Court {index}"}},
        )
        Schedule.objects.create(
            tournament=tournament,
            match=match,
            play_date="2024-05-10",
            order=index + 1,
        )

    url = reverse("msa-tournament-matches-api", args=[tournament.id])
    response = client.get(url, {"limit": 999})

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 500
    assert data["count"] == 2
    assert len(data["matches"]) == 2
