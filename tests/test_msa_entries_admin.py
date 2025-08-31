from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db import transaction
from django.test import TestCase
from django.urls import reverse

from msa.models import Player, Tournament, TournamentEntry
from msa.services.entries import compute_capacity


class EntriesAdminTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 20)]
        User = get_user_model()
        self.staff = User.objects.create_user("admin", password="x", is_staff=True)
        self.client.force_login(self.staff)
        session = self.client.session
        session["admin_mode"] = True
        session.save()

    def _url(self, tournament):
        return reverse("msa:tournament-players", args=[tournament.slug])

    def test_entry_add_with_capacity_enforced(self):
        t = Tournament.objects.create(name="T", slug="t1", draw_size=2)
        TournamentEntry.objects.create(tournament=t, player=self.players[0])
        TournamentEntry.objects.create(tournament=t, player=self.players[1])
        url = self._url(t)
        res = self.client.post(
            url,
            {
                "action": "entry_add",
                "player": self.players[2].id,
                "entry_type": "DA",
            },
            follow=True,
        )
        entry = TournamentEntry.objects.get(tournament=t, player=self.players[2])
        self.assertEqual(entry.entry_type, TournamentEntry.EntryType.ALT)
        with transaction.atomic():
            cap = compute_capacity(t)
        self.assertEqual(cap["active_main"], t.draw_size)
        messages = [m.message for m in get_messages(res.wsgi_request)]
        self.assertTrue(any("ALT" in m for m in messages))

    def test_entry_update_type_capacity_enforced(self):
        t = Tournament.objects.create(name="T2", slug="t2", draw_size=1)
        TournamentEntry.objects.create(tournament=t, player=self.players[0])
        alt = TournamentEntry.objects.create(
            tournament=t,
            player=self.players[1],
            entry_type=TournamentEntry.EntryType.ALT,
        )
        url = self._url(t)
        res = self.client.post(
            url,
            {
                "action": "entry_update_type",
                "entry_id": alt.id,
                "entry_type": "DA",
            },
            follow=True,
        )
        alt.refresh_from_db()
        self.assertEqual(alt.entry_type, TournamentEntry.EntryType.ALT)
        messages = [m.message for m in get_messages(res.wsgi_request)]
        self.assertTrue(any("ALT" in m for m in messages))

    def test_entry_reactivate_capacity_enforced(self):
        t = Tournament.objects.create(name="T3", slug="t3", draw_size=1)
        TournamentEntry.objects.create(tournament=t, player=self.players[0])
        withdrawn = TournamentEntry.objects.create(
            tournament=t,
            player=self.players[1],
            entry_type=TournamentEntry.EntryType.DA,
            status=TournamentEntry.Status.WITHDRAWN,
        )
        url = self._url(t)
        res = self.client.post(
            url,
            {"action": "entry_reactivate", "entry_id": withdrawn.id},
            follow=True,
        )
        withdrawn.refresh_from_db()
        self.assertEqual(withdrawn.status, TournamentEntry.Status.ACTIVE)
        self.assertEqual(withdrawn.entry_type, TournamentEntry.EntryType.ALT)
        messages = [m.message for m in get_messages(res.wsgi_request)]
        self.assertTrue(any("ALT" in m for m in messages))

    def test_entry_bulk_add_partial_success(self):
        t = Tournament.objects.create(name="T4", slug="t4", draw_size=4)
        csv = (
            f"{self.players[0].id}\n"
            f"{self.players[0].id}\n"  # duplicate
            f"{self.players[1].id},wc\n"
            "999\n"  # invalid id
            "#comment\n"
            f"{self.players[2].id},bad\n"
        )
        url = self._url(t)
        res = self.client.post(
            url,
            {"action": "entry_bulk_add", "rows": csv},
            follow=True,
        )
        self.assertEqual(TournamentEntry.objects.filter(tournament=t).count(), 2)
        self.assertEqual(
            TournamentEntry.objects.filter(
                tournament=t, player=self.players[0]
            ).count(),
            1,
        )
        messages = [m.message for m in get_messages(res.wsgi_request)]
        self.assertTrue(any("added 2" in m for m in messages))

    def test_entries_blocked_in_locked_state_except_withdraw(self):
        t = Tournament.objects.create(
            name="T5", slug="t5", draw_size=2, state=Tournament.State.ENTRY_LOCKED
        )
        e1 = TournamentEntry.objects.create(tournament=t, player=self.players[0])
        e2 = TournamentEntry.objects.create(
            tournament=t,
            player=self.players[1],
            entry_type=TournamentEntry.EntryType.ALT,
        )
        e3 = TournamentEntry.objects.create(
            tournament=t,
            player=self.players[2],
            status=TournamentEntry.Status.WITHDRAWN,
        )
        url = self._url(t)
        res_add = self.client.post(
            url,
            {
                "action": "entry_add",
                "player": self.players[3].id,
                "entry_type": "DA",
            },
            follow=True,
        )
        self.assertFalse(
            TournamentEntry.objects.filter(
                tournament=t, player=self.players[3]
            ).exists()
        )
        messages = [m.message for m in get_messages(res_add.wsgi_request)]
        self.assertTrue(any("locked" in m for m in messages))
        self.client.post(
            url,
            {
                "action": "entry_update_type",
                "entry_id": e2.id,
                "entry_type": "DA",
            },
            follow=True,
        )
        e2.refresh_from_db()
        self.assertEqual(e2.entry_type, TournamentEntry.EntryType.ALT)
        self.client.post(
            url,
            {"action": "entry_reactivate", "entry_id": e3.id},
            follow=True,
        )
        e3.refresh_from_db()
        self.assertEqual(e3.status, TournamentEntry.Status.WITHDRAWN)
        self.client.post(
            url,
            {"action": "entry_withdraw", "entry_id": e1.id},
            follow=True,
        )
        e1.refresh_from_db()
        self.assertEqual(e1.status, TournamentEntry.Status.WITHDRAWN)

    def test_no_duplicate_entries_user_message(self):
        t = Tournament.objects.create(name="T6", slug="t6", draw_size=4)
        TournamentEntry.objects.create(tournament=t, player=self.players[0])
        url = self._url(t)
        res = self.client.post(
            url,
            {
                "action": "entry_add",
                "player": self.players[0].id,
                "entry_type": "DA",
            },
            follow=True,
        )
        count = TournamentEntry.objects.filter(
            tournament=t, player=self.players[0]
        ).count()
        self.assertEqual(count, 1)
        messages = [m.message for m in get_messages(res.wsgi_request)]
        self.assertTrue(any("already" in m.lower() for m in messages))
