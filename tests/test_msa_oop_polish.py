import json

from django.test import TestCase

from msa.models import Match, Player, Tournament
from msa.services.scheduling import (
    parse_bulk_schedule_slots,
    apply_bulk_schedule_slots,
    find_conflicts_slots,
    swap_scheduled_matches,
    move_scheduled_match,
    export_schedule_csv,
)


class OOPPolishTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 6)]
        self.t = Tournament.objects.create(name="T", slug="t")

    def _match(self, p1, p2):
        return Match.objects.create(
            tournament=self.t, player1=p1, player2=p2, round="R32"
        )

    def test_section_merge_preserves_legacy_string(self):
        m = self._match(self.players[0], self.players[1])
        m.section = "R1-A"
        m.save(update_fields=["section"])
        csv_text = f"{m.id},2024-07-01,D,1"
        rows = parse_bulk_schedule_slots(csv_text)
        apply_bulk_schedule_slots(self.t, rows)
        m.refresh_from_db()
        data = json.loads(m.section)
        assert data["legacy_section"] == "R1-A"
        assert data["schedule"]["slot"] == 1

    def test_session_validation_and_normalization(self):
        m = self._match(self.players[0], self.players[1])
        rows = parse_bulk_schedule_slots(f"{m.id},2024-07-01,evening,1")
        assert rows[0]["session"] == "EVENING"
        with self.assertRaises(ValueError):
            parse_bulk_schedule_slots(f"{m.id},2024-07-01,foobar,1")

    def test_court_double_booking_detection(self):
        m1 = self._match(self.players[0], self.players[1])
        m2 = self._match(self.players[2], self.players[3])
        csv = f"{m1.id},2024-07-02,D,1,C1\n{m2.id},2024-07-02,D,1,C1"
        rows = parse_bulk_schedule_slots(csv)
        apply_bulk_schedule_slots(self.t, rows)
        conflicts = find_conflicts_slots(self.t)
        assert conflicts["court_double_booked"]
        entry = conflicts["court_double_booked"][0]
        assert set(entry["match_ids"]) == {m1.id, m2.id}

    def test_swap_and_move_preserve_integrity(self):
        m1 = self._match(self.players[0], self.players[1])
        m2 = self._match(self.players[2], self.players[3])
        rows = parse_bulk_schedule_slots(
            f"{m1.id},2024-07-03,D,1\n{m2.id},2024-07-03,D,2"
        )
        apply_bulk_schedule_slots(self.t, rows)
        swap_scheduled_matches(self.t, m1.id, m2.id)
        m1.refresh_from_db()
        m2.refresh_from_db()
        data1 = json.loads(m1.section)["schedule"]
        data2 = json.loads(m2.section)["schedule"]
        assert data1["slot"] == 2
        assert data2["slot"] == 1
        move_scheduled_match(
            self.t,
            m1.id,
            {"date": "2024-07-04", "session": "morning", "slot": 3},
        )
        m1.refresh_from_db()
        data1 = json.loads(m1.section)["schedule"]
        assert data1["date"] == "2024-07-04"
        assert data1["session"] == "MORNING"
        assert data1["slot"] == 3

    def test_export_schedule_csv_structure(self):
        m1 = self._match(self.players[0], self.players[1])
        csv = f"{m1.id},2024-07-05,D,1,C2"
        rows = parse_bulk_schedule_slots(csv)
        apply_bulk_schedule_slots(self.t, rows)
        out = export_schedule_csv(self.t)
        lines = out.splitlines()
        assert lines[0] == "match_id,date,session,slot,court,round,player1,player2"
        assert str(m1.id) in lines[1]
        assert "C2" in lines[1]
        assert self.players[0].name in lines[1]
