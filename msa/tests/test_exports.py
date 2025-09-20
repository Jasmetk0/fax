import csv
import io
import re
from datetime import datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from msa.models import (
    Category,
    CategorySeason,
    EntryType,
    Player,
    PlayerLicense,
    Season,
    Tour,
    Tournament,
    TournamentEntry,
)
from tests.woorld_helpers import woorld_date


@pytest.mark.django_db
def test_export_tournaments_csv_respects_filters(client):
    season1 = Season.objects.create(
        name="2030", start_date=woorld_date(2030, 1, 1), end_date=woorld_date(2030, 12, 1)
    )
    season2 = Season.objects.create(
        name="2031", start_date=woorld_date(2031, 1, 1), end_date=woorld_date(2031, 12, 1)
    )
    tour = Tour.objects.create(name="World Tour", rank=1, code="WT")
    category1 = Category.objects.create(name="Diamond 1000", tour=tour, rank=1)
    category2 = Category.objects.create(name="Emerald 500", tour=tour, rank=2)
    CategorySeason.objects.create(category=category1, season=season1, draw_size=32, qual_rounds=2)
    CategorySeason.objects.create(category=category2, season=season1, draw_size=32, qual_rounds=2)

    Tournament.objects.create(
        season=season1,
        category=category1,
        name="Alpha Cup",
        start_date=woorld_date(2099, 1, 10),
        end_date=woorld_date(2099, 1, 17),
        draw_size=32,
        qualifiers_count=4,
    )
    Tournament.objects.create(
        season=season1,
        category=category2,
        name="Beta Cup",
        start_date=woorld_date(2099, 3, 10),
        end_date=woorld_date(2099, 3, 17),
        draw_size=16,
        qualifiers_count=2,
    )
    Tournament.objects.create(
        season=season2,
        category=category1,
        name="Gamma Cup",
        start_date=woorld_date(2000, 1, 10),
        end_date=woorld_date(2000, 1, 17),
        draw_size=16,
        qualifiers_count=2,
    )

    url = reverse("msa:export_tournaments_csv")
    query = f"?season={season1.id}&category={category1.id}&status=planned&q=Alpha"
    response = client.get(f"{url}{query}")

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    assert 'attachment; filename="tournaments.csv"' in response["Content-Disposition"]

    reader = csv.reader(io.StringIO(response.content.decode("utf-8")))
    rows = list(reader)
    assert rows[0] == [
        "id",
        "name",
        "season",
        "tour",
        "category",
        "start_date",
        "end_date",
        "draw_size",
        "qualifiers",
        "location",
        "status",
    ]
    assert len(rows) == 2
    data = dict(zip(rows[0], rows[1], strict=False))
    assert data["name"] == "Alpha Cup"
    assert data["season"] == "2030"
    assert data["tour"] == "World Tour"
    assert data["category"] == "Diamond 1000"
    assert data["status"] == "planned"


@pytest.mark.django_db
def test_export_calendar_ics_has_events(client):
    season = Season.objects.create(
        name="2040",
        start_date=woorld_date(2040, 1, 1),
        end_date=woorld_date(2040, 12, 1),
    )
    tour = Tour.objects.create(name="Elite Tour, Stage; Finals", rank=2, code="ET")
    category = Category.objects.create(name="Emerald 500; Finals", tour=tour, rank=2)
    CategorySeason.objects.create(category=category, season=season, draw_size=16, qual_rounds=1)
    start_date = woorld_date(2040, 2, 5)
    end_date = woorld_date(2040, 2, 11)
    tournament = Tournament.objects.create(
        season=season,
        category=category,
        name="Delta Open, Stage; Finals",
        start_date=start_date,
        end_date=end_date,
        draw_size=16,
    )

    url = reverse("msa:export_calendar_ics")
    response = client.get(f"{url}?season={season.id}")

    assert response.status_code == 200
    assert response["Content-Type"] == "text/calendar; charset=utf-8"
    body = response.content.decode("utf-8")
    assert "BEGIN:VCALENDAR" in body
    assert "BEGIN:VEVENT" in body
    assert re.search(r"DTSTAMP:\d{8}T\d{6}Z", body)
    assert "SUMMARY:Delta Open\\, Stage\\; Finals" in body
    expected_start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y%m%d")
    expected_end = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
    assert f"DTSTART;VALUE=DATE:{expected_start}" in body
    assert f"DTEND;VALUE=DATE:{expected_end}" in body
    assert "CATEGORIES:Elite Tour\\, Stage\\; Finals,Emerald 500\\; Finals" in body
    assert f"UID:msa-tournament-{tournament.id}@fax" in body


@pytest.mark.django_db
def test_export_tournament_players_csv(client):
    season = Season.objects.create(
        name="2050",
        start_date=woorld_date(2050, 1, 1),
        end_date=woorld_date(2050, 12, 1),
    )
    tour = Tour.objects.create(name="Challenger Tour", rank=3, code="CT")
    category = Category.objects.create(name="Bronze 250", tour=tour, rank=3)
    CategorySeason.objects.create(category=category, season=season, draw_size=8, qual_rounds=1)
    tournament = Tournament.objects.create(
        season=season,
        category=category,
        name="Future Masters",
        start_date=woorld_date(2050, 3, 1),
        end_date=woorld_date(2050, 3, 7),
        draw_size=8,
        qualifiers_count=2,
    )

    players = [
        Player.objects.create(name="Seeded One"),
        Player.objects.create(name="Wildcard Player"),
        Player.objects.create(name="Qualifier One"),
        Player.objects.create(name="Lucky Loser"),
    ]
    PlayerLicense.objects.create(player=players[0], season=season)
    PlayerLicense.objects.create(player=players[2], season=season)

    TournamentEntry.objects.create(
        tournament=tournament,
        player=players[0],
        entry_type=EntryType.DA,
        seed=1,
        wr_snapshot=10,
        position=1,
    )
    TournamentEntry.objects.create(
        tournament=tournament,
        player=players[1],
        entry_type=EntryType.WC,
        is_wc=True,
        position=2,
    )
    TournamentEntry.objects.create(
        tournament=tournament,
        player=players[2],
        entry_type=EntryType.Q,
        is_qwc=False,
        wr_snapshot=50,
    )
    TournamentEntry.objects.create(
        tournament=tournament,
        player=players[3],
        entry_type=EntryType.LL,
    )

    url = reverse("msa:export_tournament_players_csv", args=[tournament.id])
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    assert f'filename="tournament-{tournament.id}-players.csv"' in response["Content-Disposition"]

    reader = csv.DictReader(io.StringIO(response.content.decode("utf-8")))
    rows = list(reader)
    assert rows[0]["slot"].startswith("Seeds-")
    assert rows[0]["type"] == "Seeds"
    assert rows[0]["seed"] == "1"
    assert rows[0]["license_ok"] == "true"
    assert rows[1]["type"] == "DA"
    assert rows[1]["is_wc"] == "true"
    assert rows[1]["license_ok"] == "false"
    assert rows[2]["type"] == "Q"
    assert rows[2]["is_qwc"] == "false"
    assert rows[2]["license_ok"] == "true"
    assert rows[3]["type"] == "Reserve"


@override_settings(MSA_ADMIN_READONLY=False)
@pytest.mark.django_db
def test_admin_action_rejects_unknown_action(client):
    staff_model = get_user_model()
    staff_user = staff_model.objects.create_user("staffer", "staff@example.com", "pass")
    staff_user.is_staff = True
    staff_user.save()
    client.force_login(staff_user)
    session = client.session
    session["admin_mode"] = True
    session.save()

    url = reverse("msa:admin_action")
    response = client.post(url, {"action": "__nope__"})

    assert response.status_code == 400
    data = response.json()
    assert data["ok"] is False
    assert data["error"] == "Unknown action"
