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

    def _accepted_order(self, content):
        return content.split("Accepted Players", 1)[1]

    def test_accepted_seed_priority(self):
        t = Tournament.objects.create(
            name="TA", slug="ta", seeds_count=4, seeding_rank_date="2024-01-01"
        )
        names = ["SeedA", "SeedB", "SeedC", "Alpha", "Beta", "Gamma"]
        players = {n: Player.objects.create(name=n) for n in names}
        entries = [
            ("SeedA", 1, TournamentEntry.EntryType.DA),
            ("SeedB", 2, TournamentEntry.EntryType.WC),
            ("SeedC", 3, TournamentEntry.EntryType.Q),
            ("Alpha", None, TournamentEntry.EntryType.DA),
            ("Beta", None, TournamentEntry.EntryType.WC),
            ("Gamma", None, TournamentEntry.EntryType.LL),
        ]
        for name, seed, etype in entries:
            TournamentEntry.objects.create(
                tournament=t, player=players[name], seed=seed, entry_type=etype
            )
        snap = RankingSnapshot.objects.create(as_of="2024-01-01")
        for idx, n in enumerate(
            ["Alpha", "Beta", "Gamma", "SeedA", "SeedB", "SeedC"], start=1
        ):
            RankingEntry.objects.create(
                snapshot=snap, player=players[n], rank=idx, points=100 - idx
            )
        resp = self.client.get(reverse("msa:tournament-players", args=[t.slug]))
        segment = self._accepted_order(resp.content.decode())
        expected = ["SeedA", "SeedB", "SeedC", "Alpha", "Beta", "Gamma"]
        order = [segment.index(n) for n in expected]
        self.assertEqual(order, sorted(order))

    def test_accepted_ranking_fallback(self):
        t = Tournament.objects.create(name="TB", slug="tb", seeds_count=2)
        data = [
            ("SeedA", 1),
            ("SeedB", 2),
            ("Charlie", None),
            ("Alpha", None),
            ("Bravo", None),
        ]
        for name, seed in data:
            p = Player.objects.create(name=name)
            TournamentEntry.objects.create(
                tournament=t,
                player=p,
                seed=seed,
                entry_type=TournamentEntry.EntryType.DA,
            )
        resp = self.client.get(reverse("msa:tournament-players", args=[t.slug]))
        segment = self._accepted_order(resp.content.decode())
        expected = ["SeedA", "SeedB", "Alpha", "Bravo", "Charlie"]
        order = [segment.index(n) for n in expected]
        self.assertEqual(order, sorted(order))

    def test_accepted_ranking_snapshot(self):
        t = Tournament.objects.create(
            name="TC", slug="tc", seeding_rank_date="2024-01-01"
        )
        players = {
            n: Player.objects.create(name=n) for n in ["Seed", "Alice", "Bob", "Carl"]
        }
        TournamentEntry.objects.create(
            tournament=t,
            player=players["Seed"],
            seed=1,
            entry_type=TournamentEntry.EntryType.DA,
        )
        TournamentEntry.objects.create(
            tournament=t,
            player=players["Alice"],
            entry_type=TournamentEntry.EntryType.WC,
        )
        TournamentEntry.objects.create(
            tournament=t,
            player=players["Bob"],
            entry_type=TournamentEntry.EntryType.Q,
        )
        TournamentEntry.objects.create(
            tournament=t,
            player=players["Carl"],
            entry_type=TournamentEntry.EntryType.LL,
        )
        snap = RankingSnapshot.objects.create(as_of="2024-01-01")
        RankingEntry.objects.create(
            snapshot=snap, player=players["Alice"], rank=2, points=80
        )
        RankingEntry.objects.create(
            snapshot=snap, player=players["Bob"], rank=1, points=90
        )
        resp = self.client.get(reverse("msa:tournament-players", args=[t.slug]))
        segment = self._accepted_order(resp.content.decode())
        expected = ["Seed", "Bob", "Alice", "Carl"]
        order = [segment.index(n) for n in expected]
        self.assertEqual(order, sorted(order))

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

    def test_ui_elements(self):
        t = Tournament.objects.create(name="T6", slug="t6")
        p = Player.objects.create(name="P")
        TournamentEntry.objects.create(
            tournament=t, player=p, seed=1, entry_type=TournamentEntry.EntryType.WC
        )
        resp = self.client.get(reverse("msa:tournament-players", args=[t.slug]))
        self.assertContains(resp, "Registered Players")
        self.assertContains(resp, "Accepted Players")
        self.assertContains(resp, "badge badge-seed")
        self.assertContains(resp, "badge badge-type")
        self.assertNotContains(resp, "Add Players")
        self.assertNotContains(resp, "Remove")
        c = self._admin_client()
        resp = c.get(reverse("msa:tournament-players", args=[t.slug]))
        self.assertContains(resp, "Add Players")
        self.assertContains(resp, "Remove")

    def test_layout_classes(self):
        t = Tournament.objects.create(name="T7", slug="t7")
        resp = self.client.get(reverse("msa:tournament-players", args=[t.slug]))
        self.assertContains(resp, "players-grid")
        self.assertContains(resp, "card")
