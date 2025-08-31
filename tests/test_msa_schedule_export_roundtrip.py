from django.test import TestCase
import json

from msa.models import Match, Player, Tournament
from msa.services.scheduling import (
    parse_bulk_schedule_slots,
    apply_bulk_schedule_slots,
    export_schedule_csv,
)


class ScheduleExportRoundtripTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 6)]
        self.t = Tournament.objects.create(name="T", slug="t")

    def _match(self, p1, p2):
        return Match.objects.create(
            tournament=self.t, player1=p1, player2=p2, round="R32"
        )

    def _sched(self, match):
        if not match.section:
            return None
        return json.loads(match.section).get("schedule")

    def test_export_then_reimport_roundtrip(self):
        m1 = self._match(self.players[0], self.players[1])
        m2 = self._match(self.players[2], self.players[3])
        csv_in = f"{m1.id},2024-09-01,M,1,C1\n{m2.id},2024-09-02,E,2"
        rows = parse_bulk_schedule_slots(csv_in)
        apply_bulk_schedule_slots(self.t, rows)
        exported = export_schedule_csv(self.t)
        for m in (m1, m2):
            m.section = ""
            m.save(update_fields=["section"])
        rows_round = parse_bulk_schedule_slots(exported)
        apply_bulk_schedule_slots(self.t, rows_round)
        m1.refresh_from_db()
        m2.refresh_from_db()
        self.assertEqual(
            self._sched(m1),
            {"date": "2024-09-01", "session": "MORNING", "slot": 1, "court": "C1"},
        )
        self.assertEqual(
            self._sched(m2),
            {"date": "2024-09-02", "session": "EVENING", "slot": 2},
        )

    def test_export_header_and_order(self):
        m1 = self._match(self.players[0], self.players[1])
        m2 = self._match(self.players[2], self.players[3])
        csv_in = f"{m1.id},2024-10-01,M,1,C1\n" f"{m2.id},2024-10-01,D,2,C2"
        rows = parse_bulk_schedule_slots(csv_in)
        apply_bulk_schedule_slots(self.t, rows)
        exported = export_schedule_csv(self.t)
        lines = exported.splitlines()
        self.assertEqual(
            lines[0],
            "match_id,date,session,slot,court,round,player1,player2",
        )
        self.assertEqual(len(lines) - 1, 2)
