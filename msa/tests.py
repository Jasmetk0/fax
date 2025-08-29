from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError

from .models import (
    Category,
    CategorySeason,
    BracketPolicy,
    PointsRow,
    PointsTable,
    Match,
    Player,
    RankingEntry,
    RankingSnapshot,
    Season,
    Tournament,
)


class MSAViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_public_pages(self):
        urls = [
            reverse("msa:home"),
            reverse("msa:tournament-list"),
            reverse("msa:rankings"),
            reverse("msa:player-list"),
            reverse("msa:h2h"),
            reverse("msa:squashtv"),
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)

    def _admin_client(self):
        User = get_user_model()
        user = User.objects.create_user("staff", password="x", is_staff=True)
        self.client.force_login(user)
        session = self.client.session
        session["admin_mode"] = True
        session.save()
        return self.client

    def test_admin_buttons_no_forms(self):
        c = self._admin_client()
        resp = c.get(reverse("msa:tournament-list"))
        self.assertContains(resp, "Add Tournament")
        self.assertNotContains(resp, "<form")

    def test_manage_routes_have_form(self):
        c = self._admin_client()
        resp = c.get(reverse("msa:player-create"))
        self.assertContains(resp, "<form", html=False)
        Player.objects.create(name="A", slug="a", country="C")
        resp = c.get(reverse("msa:player-edit", args=["a"]))
        self.assertContains(resp, "<form", html=False)

    def test_h2h_record(self):
        a = Player.objects.create(name="A", slug="a", country="C")
        b = Player.objects.create(name="B", slug="b", country="C")
        t = Tournament.objects.create(
            name="T",
            slug="t",
            category="Cat",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            city="X",
            country="C",
            status="finished",
        )
        Match.objects.create(
            tournament=t, round="R", best_of=5, player1=a, player2=b, winner=a
        )
        Match.objects.create(
            tournament=t, round="R", best_of=5, player1=b, player2=a, winner=a
        )
        Match.objects.create(
            tournament=t, round="R", best_of=5, player1=a, player2=b, winner=b
        )
        resp = self.client.get(reverse("msa:h2h"), {"a": "a", "b": "b"})
        self.assertContains(resp, "2-1")

    def test_rankings_snapshot(self):
        p1 = Player.objects.create(name="A", slug="a", country="C")
        p2 = Player.objects.create(name="B", slug="b", country="C")
        snap = RankingSnapshot.objects.create(as_of=timezone.now().date())
        RankingEntry.objects.create(snapshot=snap, player=p1, rank=2, points=900)
        RankingEntry.objects.create(snapshot=snap, player=p2, rank=1, points=1000)
        resp = self.client.get(reverse("msa:rankings"))
        entries = resp.context["entries"]
        self.assertEqual(entries[0].player, p2)

    def test_tournament_filtering(self):
        today = timezone.now().date()
        Tournament.objects.create(
            name="Up",
            slug="up",
            category="Cat",
            start_date=today,
            end_date=today,
            city="X",
            country="C",
            status="upcoming",
        )
        Tournament.objects.create(
            name="Fin",
            slug="fin",
            category="Cat",
            start_date=today,
            end_date=today,
            city="X",
            country="C",
            status="finished",
        )
        resp = self.client.get(reverse("msa:tournament-list"), {"status": "upcoming"})
        self.assertContains(resp, "Up")
        self.assertNotContains(resp, "Fin")

    def test_api_players_tournaments_seasons(self):
        Player.objects.create(name="A", slug="a", country="C")
        today = timezone.now().date()
        Tournament.objects.create(
            name="T",
            slug="t",
            category="Cat",
            start_date=today,
            end_date=today,
            city="X",
            country="C",
            status="upcoming",
        )
        Season.objects.create(name="2024")
        resp = self.client.get(reverse("msa:api_players"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)
        resp = self.client.get(reverse("msa:api_tournaments"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)
        resp = self.client.get(reverse("msa:api_seasons"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)

    def test_api_category_seasons(self):
        season = Season.objects.create(name="2025")
        cat = Category.objects.create(name="World Tour")
        CategorySeason.objects.create(season=season, category=cat, label="WT")
        resp = self.client.get(reverse("msa:api_category_seasons", args=[season.pk]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["label"], "WT")

    def test_categoryseason_unique(self):
        season = Season.objects.create(name="2025")
        cat = Category.objects.create(name="World Tour")
        CategorySeason.objects.create(season=season, category=cat, label="WT")
        with self.assertRaises(IntegrityError):
            CategorySeason.objects.create(season=season, category=cat, label="WT2")

    def test_api_category_season_points(self):
        season = Season.objects.create(name="2025")
        cat = Category.objects.create(name="World Tour")
        table = PointsTable.objects.create(name="Main")
        cs = CategorySeason.objects.create(
            season=season, category=cat, label="WT", points_table=table
        )
        PointsRow.objects.create(points_table=table, round_code="R32", points=100)
        resp = self.client.get(reverse("msa:api_category_season_points", args=[cs.pk]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["round_code"], "R32")


class BracketPolicyTests(TestCase):
    def test_generate_round_labels(self):
        policy = BracketPolicy.objects.create(name="Test", draw_size=96)
        self.assertEqual(
            policy.generate_round_labels(),
            [
                (1, "Round of 96"),
                (2, "Round of 64"),
                (3, "Round of 32"),
                (4, "Round of 16"),
                (5, "Quarter Final"),
                (6, "Semi Final"),
                (7, "Final"),
                (8, "Winner"),
            ],
        )


def test_admin_index_lists_msa_models(admin_client):
    response = admin_client.get(reverse("admin:index"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "MSA" in content
    for model in [
        "player",
        "season",
        "tournament",
        "match",
        "rankingsnapshot",
        "rankingentry",
        "newspost",
        "mediaitem",
        "category",
        "categoryseason",
    ]:
        assert f"msa/{model}/" in content
