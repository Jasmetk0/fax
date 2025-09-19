import pytest
from django.contrib.auth import get_user_model
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


def test_tournament_program_view_data_attributes(client):
    tournament = create_tournament()

    url = reverse("msa:tournament_program", args=[tournament.id])
    response = client.get(url, {"limit": 5, "offset": 10})

    assert response.status_code == 200
    content = response.content.decode()
    assert 'data-limit="5"' in content
    assert 'data-offset="10"' in content


def test_tournament_info_view_shows_range(client):
    tournament = create_tournament()

    url = reverse("msa:tournament_info", args=[tournament.id])
    response = client.get(url)

    assert response.status_code == 200
    assert "2024-05-10" in response.content.decode()
    assert "2024-05-15" in response.content.decode()


def test_tournament_info_contains_scoring_points(client):
    tournament = create_tournament(
        scoring_md={"Winner": 100, "RunnerUp": 60},
        scoring_qual_win={"Q1": 10},
    )

    url = reverse("msa:tournament_info", args=[tournament.id])
    response = client.get(url)

    assert response.status_code == 200
    html = response.content.decode()
    assert ("Main draw points" in html) or ("Qualification points" in html)
    assert "Winner" in html
    assert "100" in html


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


def test_tournament_matches_api_fax_day_null_when_missing(client):
    tournament = create_tournament()
    player_a = Player.objects.create(full_name="No Date A")
    player_b = Player.objects.create(full_name="No Date B")

    Match.objects.create(
        tournament=tournament,
        phase="MD",
        round_name="R1",
        player1=player_a,
        player2=player_b,
        state="SCHEDULED",
        score={"sets": []},
    )

    url = reverse("msa-tournament-matches-api", args=[tournament.id])
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["matches"][0]["fax_day"] is None


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


def test_tournament_matches_api_meta_live_and_empty_sets_scheduled(client):
    tournament = create_tournament()
    player_a = Player.objects.create(full_name="Meta Live A")
    player_b = Player.objects.create(full_name="Meta Live B")
    player_c = Player.objects.create(full_name="Meta Live C")
    player_d = Player.objects.create(full_name="Meta Live D")

    live_match = Match.objects.create(
        tournament=tournament,
        phase="MD",
        round_name="R16",
        player1=player_a,
        player2=player_b,
        state="SCHEDULED",
        score={"sets": [], "meta": {"status": "live"}},
    )
    Schedule.objects.create(
        tournament=tournament,
        match=live_match,
        play_date="2024-05-12",
        order=1,
    )

    scheduled_match = Match.objects.create(
        tournament=tournament,
        phase="MD",
        round_name="R16",
        player1=player_c,
        player2=player_d,
        state="SCHEDULED",
        score={"sets": [{"a": None, "b": None}]},
    )
    Schedule.objects.create(
        tournament=tournament,
        match=scheduled_match,
        play_date="2024-05-12",
        order=2,
    )

    url = reverse("msa-tournament-matches-api", args=[tournament.id])
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    statuses = {item["id"]: item["status"] for item in data["matches"]}
    assert statuses[live_match.id] == "live"
    assert statuses[scheduled_match.id] == "scheduled"


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
    assert all(item["status"] == "scheduled" for item in data["matches"])
    for item in data["matches"]:
        assert isinstance(item["court"], dict)
        assert item["court"]["name"]


def test_tournament_matches_api_fax_month_13_ok(client):
    tournament = create_tournament()
    player_a = Player.objects.create(full_name="Player Month A")
    player_b = Player.objects.create(full_name="Player Month B")
    player_c = Player.objects.create(full_name="Player Month C")
    player_d = Player.objects.create(full_name="Player Month D")

    match_month_13 = Match.objects.create(
        tournament=tournament,
        phase="MD",
        round_name="R64",
        player1=player_a,
        player2=player_b,
        state="SCHEDULED",
        score={"sets": []},
    )
    Schedule.objects.create(
        tournament=tournament,
        match=match_month_13,
        play_date="2024-13-05",
        order=1,
    )

    match_month_12 = Match.objects.create(
        tournament=tournament,
        phase="MD",
        round_name="R32",
        player1=player_c,
        player2=player_d,
        state="SCHEDULED",
        score={"sets": []},
    )
    Schedule.objects.create(
        tournament=tournament,
        match=match_month_12,
        play_date="2024-12-15",
        order=2,
    )

    url = reverse("msa-tournament-matches-api", args=[tournament.id])

    response_month_13 = client.get(url, {"fax_month": 13})
    assert response_month_13.status_code == 200
    data_month_13 = response_month_13.json()
    ids_month_13 = [item["id"] for item in data_month_13["matches"]]
    assert match_month_13.id in ids_month_13
    assert match_month_12.id not in ids_month_13

    response_month_12 = client.get(url, {"fax_month": 12})
    assert response_month_12.status_code == 200
    data_month_12 = response_month_12.json()
    ids_month_12 = [item["id"] for item in data_month_12["matches"]]
    assert match_month_12.id in ids_month_12
    assert match_month_13.id not in ids_month_12


def test_tournament_courts_api_sorted(client):
    tournament = create_tournament()
    player_a = Player.objects.create(full_name="Court Player A")
    player_b = Player.objects.create(full_name="Court Player B")

    def make_match(identifier, name, order, play_date="2024-05-10"):
        match = Match.objects.create(
            tournament=tournament,
            phase="MD",
            round_name=f"R{order}",
            round=f"R{order}",
            position=order,
            player1=player_a,
            player2=player_b,
            state="SCHEDULED",
            score={"court": {"id": identifier, "name": name}},
        )
        Schedule.objects.create(
            tournament=tournament,
            match=match,
            play_date=play_date,
            order=order,
        )
        return match

    make_match("court-beta", "Beta Court", 1, "2024-05-10")
    make_match("court-alpha", "Alpha Court", 2, "2024-05-11")
    make_match("court-alpha", "Alpha Court", 3, "2024-05-12")
    make_match("c-0", None, 4, "2024-05-13")
    make_match("c-1", "", 5, "2024-05-14")

    url = reverse("msa-tournament-courts-api", args=[tournament.id])
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    courts = data["courts"]
    assert courts == [
        {"id": "c-0", "name": None},
        {"id": "c-1", "name": ""},
        {"id": "court-alpha", "name": "Alpha Court"},
        {"id": "court-beta", "name": "Beta Court"},
    ]


def test_matches_api_pagination_next_offset(client):
    tournament = create_tournament()
    player_one = Player.objects.create(full_name="Paging A")
    player_two = Player.objects.create(full_name="Paging B")

    for index in range(60):
        match = Match.objects.create(
            tournament=tournament,
            phase="MD",
            round_name=f"R{index}",
            round=f"R{index}",
            position=index,
            player1=player_one,
            player2=player_two,
            state="SCHEDULED",
            score={"sets": []},
        )
        Schedule.objects.create(
            tournament=tournament,
            match=match,
            play_date="2024-05-10",
            order=index + 1,
        )

    url = reverse("msa-tournament-matches-api", args=[tournament.id])

    first_page = client.get(url, {"limit": 50})
    assert first_page.status_code == 200
    first_data = first_page.json()
    assert first_data["count"] == 60
    assert len(first_data["matches"]) == 50
    assert first_data["next_offset"] == 50

    second_page = client.get(url, {"limit": 50, "offset": 50})
    assert second_page.status_code == 200
    second_data = second_page.json()
    assert second_data["count"] == 60
    assert len(second_data["matches"]) == 10
    assert second_data["next_offset"] is None
    first_ids = {item["id"] for item in first_data["matches"]}
    second_ids = {item["id"] for item in second_data["matches"]}
    assert not first_ids & second_ids


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
    response = client.get(url, {"limit": 10000, "offset": -5})

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 500
    assert data["offset"] == 0
    assert data["count"] == 2


def test_tournament_draws_admin_section_controls(client):
    tournament = create_tournament()
    staff_model = get_user_model()
    staff_user = staff_model.objects.create_user("draws-staff", "draws@example.com", "x")
    staff_user.is_staff = True
    staff_user.save()
    client.force_login(staff_user)
    session = client.session
    session["admin_mode"] = True
    session.save()

    url = reverse("msa:tournament_draws", args=[tournament.id])
    response = client.get(url)
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-admin-section="draws-md"' in html
