import threading

from django.db import OperationalError, close_old_connections
from django.test import TransactionTestCase

from msa.models import Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw, replace_slot


class ReplaceSlotIdempotentTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 80)]

    def _create_tournament(self):
        t = Tournament.objects.create(name="T", slug="t", draw_size=32)
        for i in range(32):
            TournamentEntry.objects.create(tournament=t, player=self.players[i])
        generate_draw(t)
        return t

    def test_sequential_and_parallel(self):
        t = self._create_tournament()
        alt = TournamentEntry.objects.create(
            tournament=t,
            player=self.players[70],
            entry_type=TournamentEntry.EntryType.ALT,
            status=TournamentEntry.Status.ACTIVE,
        )
        slot = 5

        ok1 = replace_slot(t, slot, alt.pk)
        ok2 = replace_slot(t, slot, alt.pk)
        self.assertTrue(ok1)
        self.assertFalse(ok2)

        def run():
            close_old_connections()
            try:
                replace_slot(t, slot, alt.pk)
            except OperationalError:
                pass

        threads = [threading.Thread(target=run) for _ in range(5)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        alt.refresh_from_db()
        self.assertEqual(alt.position, slot)
        self.assertEqual(
            TournamentEntry.objects.filter(tournament=t, position=slot).count(), 1
        )
