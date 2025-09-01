from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase

from msa.models import Player, Tournament, TournamentEntry
from msa.services.entries import (
    add_entry,
    update_entry_type,
    set_entry_status,
    compute_capacity,
    bulk_add_entries_csv,
)


class EntriesAdminTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 20)]
        User = get_user_model()
        self.staff = User.objects.create_user("admin", password="x", is_staff=True)

    def test_entry_add_with_capacity_enforced(self):
        t = Tournament.objects.create(name="T", slug="t1", draw_size=2)
        TournamentEntry.objects.create(tournament=t, player=self.players[0])
        TournamentEntry.objects.create(tournament=t, player=self.players[1])
        ok, msg = add_entry(t, self.players[2], "DA", self.staff)
        self.assertTrue(ok)
        entry = TournamentEntry.objects.get(tournament=t, player=self.players[2])
        self.assertEqual(entry.entry_type, TournamentEntry.EntryType.ALT)
        with transaction.atomic():
            cap = compute_capacity(t)
        self.assertEqual(cap["active_main"], t.draw_size)
        self.assertIn("ALT", msg)

    def test_entry_update_type_capacity_enforced(self):
        t = Tournament.objects.create(name="T2", slug="t2", draw_size=1)
        TournamentEntry.objects.create(tournament=t, player=self.players[0])
        alt = TournamentEntry.objects.create(
            tournament=t,
            player=self.players[1],
            entry_type=TournamentEntry.EntryType.ALT,
        )
        ok, msg = update_entry_type(alt, "DA", self.staff)
        self.assertTrue(ok)
        alt.refresh_from_db()
        self.assertEqual(alt.entry_type, TournamentEntry.EntryType.ALT)
        self.assertIn("ALT", msg)

    def test_entry_reactivate_capacity_enforced(self):
        t = Tournament.objects.create(name="T3", slug="t3", draw_size=1)
        TournamentEntry.objects.create(tournament=t, player=self.players[0])
        withdrawn = TournamentEntry.objects.create(
            tournament=t,
            player=self.players[1],
            entry_type=TournamentEntry.EntryType.DA,
            status=TournamentEntry.Status.WITHDRAWN,
        )
        ok, msg = set_entry_status(withdrawn, TournamentEntry.Status.ACTIVE, self.staff)
        self.assertTrue(ok)
        withdrawn.refresh_from_db()
        self.assertEqual(withdrawn.status, TournamentEntry.Status.ACTIVE)
        self.assertEqual(withdrawn.entry_type, TournamentEntry.EntryType.ALT)
        self.assertIn("ALT", msg)

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
        result = bulk_add_entries_csv(t, csv, self.staff)
        self.assertEqual(TournamentEntry.objects.filter(tournament=t).count(), 2)
        self.assertEqual(
            TournamentEntry.objects.filter(
                tournament=t, player=self.players[0]
            ).count(),
            1,
        )
        self.assertEqual(result["added"], 2)

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
        ok, msg = add_entry(t, self.players[3], "DA", self.staff)
        self.assertFalse(ok)
        self.assertIn("locked", msg.lower())
        self.assertFalse(
            TournamentEntry.objects.filter(
                tournament=t, player=self.players[3]
            ).exists()
        )
        ok, _ = update_entry_type(e2, "DA", self.staff)
        self.assertFalse(ok)
        e2.refresh_from_db()
        self.assertEqual(e2.entry_type, TournamentEntry.EntryType.ALT)
        ok, _ = set_entry_status(e3, TournamentEntry.Status.ACTIVE, self.staff)
        self.assertFalse(ok)
        e3.refresh_from_db()
        self.assertEqual(e3.status, TournamentEntry.Status.WITHDRAWN)
        ok, _ = set_entry_status(e1, TournamentEntry.Status.WITHDRAWN, self.staff)
        self.assertTrue(ok)
        e1.refresh_from_db()
        self.assertEqual(e1.status, TournamentEntry.Status.WITHDRAWN)

    def test_no_duplicate_entries_user_message(self):
        t = Tournament.objects.create(name="T6", slug="t6", draw_size=4)
        TournamentEntry.objects.create(tournament=t, player=self.players[0])
        ok, msg = add_entry(t, self.players[0], "DA", self.staff)
        self.assertFalse(ok)
        count = TournamentEntry.objects.filter(
            tournament=t, player=self.players[0]
        ).count()
        self.assertEqual(count, 1)
        self.assertIn("already", msg.lower())
