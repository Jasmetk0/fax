from django.test import TestCase

from msa.models import Match, Player, Tournament, TournamentEntry
from msa.services.draw import progress_bracket


class BestOfPolicyTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 33)]

    def _seed32(self, t):
        # 32 aktivních hráčů usazených do pozic 1..32
        for i, p in enumerate(self.players, start=1):
            TournamentEntry.objects.create(
                tournament=t, player=p, position=i, status=TournamentEntry.Status.ACTIVE
            )
        # hotové kolo R32 s vítězi na lichých pozicích
        for i in range(1, 17):
            Match.objects.create(
                tournament=t, round="R32", position=i, winner=self.players[2 * i - 1]
            )

    def test_next_round_uses_md_best_of(self):
        t = Tournament.objects.create(name="T", slug="t", draw_size=32, md_best_of=3)
        self._seed32(t)
        created = progress_bracket(t)
        self.assertTrue(created)
        for m in Match.objects.filter(tournament=t, round="R16"):
            self.assertEqual(m.best_of, 3)
