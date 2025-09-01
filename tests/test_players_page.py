from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from msa.models import (
    Player,
    Tournament,
    TournamentEntry,
    RankingSnapshot,
    RankingEntry,
)


class PlayersPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.staff = User.objects.create_user("admin", password="x", is_staff=True)
        self.user = User.objects.create_user("user", password="x")

    def _admin_client(self):
        self.client.force_login(self.staff)
        session = self.client.session
        session["admin_mode"] = True
        session.save()
        return self.client

    def test_alphabetical_ordering(self):
        t = Tournament.objects.create(name="T", slug="t")
        names = ["Dan", "Bob", "Ann", "Cara"]
        players = [Player.objects.create(name=n) for n in names]
        for p in players:
            TournamentEntry.objects.create(tournament=t, player=p)
        resp = self.client.get(reverse("msa:tournament-players", args=[t.slug]))
        content = resp.content.decode()
        order = [content.index(n) for n in sorted(names)]
        self.assertEqual(order, sorted(order))

    def test_ranking_ordering(self):
        t = Tournament.objects.create(
            name="T2", slug="t2", seeding_rank_date="2024-01-01"
        )
        players = {
            "Andy": Player.objects.create(name="Andy"),
            "Ben": Player.objects.create(name="Ben"),
            "Cara": Player.objects.create(name="Cara"),
            "Duke": Player.objects.create(name="Duke"),
        }
        for p in players.values():
            TournamentEntry.objects.create(tournament=t, player=p)
        snap = RankingSnapshot.objects.create(as_of="2024-01-01")
        RankingEntry.objects.create(
            snapshot=snap, player=players["Andy"], rank=1, points=100
        )
        RankingEntry.objects.create(
            snapshot=snap, player=players["Cara"], rank=2, points=80
        )
        resp = self.client.get(reverse("msa:tournament-players", args=[t.slug]))
        content = resp.content.decode()
        expected = ["Andy", "Cara", "Ben", "Duke"]
        order = [content.index(n) for n in expected]
        self.assertEqual(order, sorted(order))

    def test_add_players_get_permissions(self):
        t = Tournament.objects.create(name="T3", slug="t3")
        # staff with admin mode
        c = self._admin_client()
        resp = c.get(reverse("msa:tournament-players-add", args=[t.slug]))
        self.assertEqual(resp.status_code, 200)
        # non-staff
        self.client.force_login(self.user)
        session = self.client.session
        session["admin_mode"] = True
        session.save()
        resp = self.client.get(reverse("msa:tournament-players-add", args=[t.slug]))
        self.assertEqual(resp.status_code, 403)

    def test_bulk_add_post(self):
        t = Tournament.objects.create(name="T4", slug="t4")
        existing = Player.objects.create(name="Existing")
        TournamentEntry.objects.create(tournament=t, player=existing)
        p2 = Player.objects.create(name="P2")
        p3 = Player.objects.create(name="P3")
        c = self._admin_client()
        url = reverse("msa:tournament-players-add", args=[t.slug])
        c.post(url, {"player_ids": [existing.id, p2.id, p3.id]})
        self.assertEqual(TournamentEntry.objects.filter(tournament=t).count(), 3)
        # idempotent
        c.post(url, {"player_ids": [existing.id, p2.id]})
        self.assertEqual(TournamentEntry.objects.filter(tournament=t).count(), 3)

    def test_remove_post_permissions(self):
        t = Tournament.objects.create(name="T5", slug="t5")
        p = Player.objects.create(name="P")
        entry = TournamentEntry.objects.create(tournament=t, player=p)
        # non-staff
        self.client.force_login(self.user)
        session = self.client.session
        session["admin_mode"] = True
        session.save()
        url = reverse("msa:tournament-player-remove", args=[t.slug, entry.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 403)
        entry.refresh_from_db()
        self.assertEqual(entry.status, TournamentEntry.Status.ACTIVE)
        # staff
        c = self._admin_client()
        c.post(url)
        entry.refresh_from_db()
        self.assertEqual(entry.status, TournamentEntry.Status.WITHDRAWN)

    def test_button_visibility(self):
        t = Tournament.objects.create(name="T6", slug="t6")
        p = Player.objects.create(name="P")
        TournamentEntry.objects.create(tournament=t, player=p)
        # non-admin
        resp = self.client.get(reverse("msa:tournament-players", args=[t.slug]))
        self.assertNotContains(resp, "Add Players")
        self.assertNotContains(resp, "Remove")
        # admin
        c = self._admin_client()
        resp = c.get(reverse("msa:tournament-players", args=[t.slug]))
        self.assertContains(resp, "Add Players")
        self.assertContains(resp, "Remove")
