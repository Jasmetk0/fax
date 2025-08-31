from django.test import TestCase

from msa.models import Match, Player, Tournament
from msa.services.scheduling import (
    parse_bulk_schedule_slots,
    apply_bulk_schedule_slots,
    find_conflicts_slots,
    generate_tournament_ics_date_only,
)


class OOPSlotsOnlyTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 10)]
        self.t = Tournament.objects.create(name="T", slug="t")

    def _match(self, p1, p2):
        return Match.objects.create(
            tournament=self.t, player1=p1, player2=p2, round="R32"
        )

    def test_bulk_schedule_slots_and_hard_conflict(self):
        m1 = self._match(self.players[0], self.players[1])
        m2 = self._match(self.players[0], self.players[2])
        csv_text = f"{m1.id},2024-05-01,D,1\n{m2.id},2024-05-01,D,1"
        rows = parse_bulk_schedule_slots(csv_text)
        apply_bulk_schedule_slots(self.t, rows)
        conflicts = find_conflicts_slots(self.t)
        self.assertEqual(len(conflicts["hard"]), 1)
        entry = conflicts["hard"][0]
        self.assertEqual(entry["player_id"], self.players[0].id)
        self.assertCountEqual([m1.id, m2.id], [m[0] for m in entry["matches"]])

    def test_back_to_back_by_slots(self):
        p1 = self.players[0]
        m1 = self._match(p1, self.players[1])
        m2 = self._match(p1, self.players[2])
        p2 = self.players[3]
        m3 = self._match(p2, self.players[4])
        m4 = self._match(p2, self.players[5])
        csv_text = (
            f"{m1.id},2024-05-02,D,3\n"
            f"{m2.id},2024-05-02,D,4\n"
            f"{m3.id},2024-05-02,D,3\n"
            f"{m4.id},2024-05-02,D,5"
        )
        rows = parse_bulk_schedule_slots(csv_text)
        apply_bulk_schedule_slots(self.t, rows)
        conflicts = find_conflicts_slots(self.t)
        self.assertEqual(len(conflicts["b2b"]), 1)
        b2b = conflicts["b2b"][0]
        self.assertEqual(b2b["player_id"], p1.id)
        self.assertEqual({b2b["prev_id"], b2b["next_id"]}, {m1.id, m2.id})

    def test_ics_date_only_contains_entries(self):
        m1 = self._match(self.players[0], self.players[1])
        m2 = self._match(self.players[2], self.players[3])
        csv_text = f"{m1.id},2024-06-01,M,1\n" f"{m2.id},2024-06-02,E,2"
        rows = parse_bulk_schedule_slots(csv_text)
        apply_bulk_schedule_slots(self.t, rows)
        ics = generate_tournament_ics_date_only(self.t)
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("DTSTART;VALUE=DATE:20240601", ics)
        self.assertIn(
            f"SUMMARY:{m1.player1.name} vs {m1.player2.name} — {self.t.name}", ics
        )
