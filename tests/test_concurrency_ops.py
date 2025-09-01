import threading

from django.db import OperationalError, close_old_connections
from django.test import TransactionTestCase

from msa.models import Match, Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw, replace_slot
from msa.services.scheduling import (
    move_scheduled_match,
    put_schedule,
    swap_scheduled_matches,
    _extract_schedule,
)


class ConcurrencyOpsTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 80)]

    def _create_tournament(self):
        t = Tournament.objects.create(name="T", slug="t", draw_size=32)
        for i in range(32):
            TournamentEntry.objects.create(tournament=t, player=self.players[i])
        generate_draw(t)
        return t

    def test_replace_slot_concurrent(self):
        t = self._create_tournament()
        alt = TournamentEntry.objects.create(
            tournament=t,
            player=self.players[70],
            entry_type=TournamentEntry.EntryType.ALT,
            status=TournamentEntry.Status.ACTIVE,
        )
        slot = 5

        def run():
            close_old_connections()
            try:
                replace_slot(t, slot, alt.pk)
            except OperationalError:
                pass

        threads = [threading.Thread(target=run) for _ in range(2)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        alt.refresh_from_db()
        self.assertEqual(alt.position, slot)
        self.assertEqual(
            TournamentEntry.objects.filter(tournament=t, position=slot).count(), 1
        )

    def test_schedule_ops_concurrent(self):
        t = self._create_tournament()
        m1, m2 = list(Match.objects.filter(tournament=t, round="R32")[:2])
        put_schedule(m1, {"date": "2024-01-01", "session": "DAY", "slot": 1})
        put_schedule(m2, {"date": "2024-01-01", "session": "DAY", "slot": 2})

        def swap_run():
            close_old_connections()
            try:
                swap_scheduled_matches(t, m1.id, m2.id)
            except OperationalError:
                pass

        th1 = threading.Thread(target=swap_run)
        th2 = threading.Thread(target=swap_run)
        th1.start()
        th2.start()
        th1.join()
        th2.join()
        m1.refresh_from_db()
        m2.refresh_from_db()
        s1 = _extract_schedule(m1)
        s2 = _extract_schedule(m2)
        self.assertEqual({s1["slot"], s2["slot"]}, {1, 2})

        def move_run():
            close_old_connections()
            try:
                move_scheduled_match(
                    t,
                    m1.id,
                    {"date": "2024-01-01", "session": "DAY", "slot": 3},
                )
            except OperationalError:
                pass

        th3 = threading.Thread(target=move_run)
        th4 = threading.Thread(target=move_run)
        th3.start()
        th4.start()
        th3.join()
        th4.join()
        m1.refresh_from_db()
        self.assertEqual(_extract_schedule(m1)["slot"], 3)
