import threading

from django.db import OperationalError, close_old_connections
from django.test import TransactionTestCase

from msa.models import Match, Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw, progress_bracket


class ProgressConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 80)]

    def test_progress_concurrent(self):
        t = Tournament.objects.create(name="T", slug="t", draw_size=32)
        for i in range(32):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
            )
        generate_draw(t)
        for m in Match.objects.filter(tournament=t, round="R32"):
            m.winner = m.player1
            m.save()

        def run():
            close_old_connections()
            try:
                progress_bracket(t)
            except OperationalError:
                pass

        th1 = threading.Thread(target=run)
        th2 = threading.Thread(target=run)
        th1.start()
        th2.start()
        th1.join()
        th2.join()
        self.assertEqual(Match.objects.filter(tournament=t, round="R16").count(), 8)
        progress_bracket(t)
        self.assertEqual(Match.objects.filter(tournament=t, round="R16").count(), 8)
