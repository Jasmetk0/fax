from django.test import TestCase
from django.contrib.auth.models import User
import json

from msa.models import Match, Player, Tournament
from msa.services.scheduling import (
    parse_bulk_schedule_slots,
    apply_bulk_schedule_slots,
    swap_scheduled_matches,
    move_scheduled_match,
    find_conflicts_slots,
)


class SchedulingOpsTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 8)]
        self.t = Tournament.objects.create(name="T", slug="t")
        self.user = User.objects.create(username="u1")

    def _match(self, p1, p2):
        return Match.objects.create(
            tournament=self.t, player1=p1, player2=p2, round="R32"
        )

    def _sched(self, match):
        if not match.section:
            return None
        return json.loads(match.section).get("schedule")

    def test_swap_success_and_missing_schedule_fails(self):
        m1 = self._match(self.players[0], self.players[1])
        m2 = self._match(self.players[2], self.players[3])
        csv = f"{m1.id},2024-05-01,M,1\n{m2.id},2024-05-02,D,2"
        rows = parse_bulk_schedule_slots(csv)
        apply_bulk_schedule_slots(self.t, rows, user=self.user)
        m1.refresh_from_db()
        m2.refresh_from_db()
        sched1 = self._sched(m1)
        sched2 = self._sched(m2)
        ok = swap_scheduled_matches(self.t, m1.id, m2.id, user=self.user)
        self.assertTrue(ok)
        m1.refresh_from_db()
        m2.refresh_from_db()
        self.assertEqual(self._sched(m1), sched2)
        self.assertEqual(self._sched(m2), sched1)
        m3 = self._match(self.players[4], self.players[5])
        ok = swap_scheduled_matches(self.t, m1.id, m3.id, user=self.user)
        self.assertFalse(ok)
        m1.refresh_from_db()
        m3.refresh_from_db()
        self.assertEqual(self._sched(m1), sched2)
        self.assertIsNone(self._sched(m3))

    def test_move_normalizes_session_and_allows_double_book(self):
        m1 = self._match(self.players[0], self.players[1])
        m2 = self._match(self.players[2], self.players[3])
        csv = f"{m1.id},2024-07-01,M,1,C1\n{m2.id},2024-07-01,D,2,C1"
        rows = parse_bulk_schedule_slots(csv)
        apply_bulk_schedule_slots(self.t, rows, user=self.user)
        ok = move_scheduled_match(
            self.t,
            m2.id,
            {"date": "2024-07-01", "session": "e", "slot": 3, "court": "C1"},
            user=self.user,
        )
        self.assertTrue(ok)
        m2.refresh_from_db()
        self.assertEqual(self._sched(m2)["session"], "EVENING")
        ok = move_scheduled_match(
            self.t,
            m2.id,
            {"date": "2024-07-01", "session": "M", "slot": 1, "court": "C1"},
            user=self.user,
        )
        self.assertTrue(ok)
        m1.refresh_from_db()
        m2.refresh_from_db()
        self.assertEqual(self._sched(m2)["slot"], 1)
        self.assertEqual(self._sched(m1)["slot"], 3)
        conflicts = find_conflicts_slots(self.t)
        self.assertFalse(conflicts["court_double_booked"])

    def test_bulk_import_is_atomic(self):
        m1 = self._match(self.players[0], self.players[1])
        m2 = self._match(self.players[2], self.players[3])
        m3 = self._match(self.players[4], self.players[5])
        csv = (
            f"{m1.id},2024-08-01,M,1\n"
            f"{m2.id},2024-08-01,X,2\n"
            f"{m3.id},2024-08-01,D,3"
        )
        with self.assertRaises(ValueError) as cm:
            parse_bulk_schedule_slots(csv)
        self.assertIn("Line 2", str(cm.exception))
        for m in (m1, m2, m3):
            m.refresh_from_db()
            self.assertFalse(m.section)
