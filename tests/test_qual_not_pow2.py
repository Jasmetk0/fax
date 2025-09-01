from django.test import TestCase

from msa.models import Match, Player, Tournament, TournamentEntry
from msa.services.qual import generate_qualifying, progress_qualifying


class QualNotPow2Tests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 20)]

    def test_generate_with_byes(self):
        t = Tournament.objects.create(
            name="T", slug="t", draw_size=32, qualifiers_count=4
        )
        for i in range(10):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.Q,
            )
        self.assertTrue(generate_qualifying(t))
        self.assertEqual(Match.objects.filter(tournament=t, round="Q8").count(), 4)
        matches = Match.objects.filter(tournament=t, round="Q8")
        played_ids = {m.player1_id for m in matches} | {m.player2_id for m in matches}
        autopost = TournamentEntry.objects.filter(
            tournament=t,
            entry_type=TournamentEntry.EntryType.Q,
        ).exclude(player_id__in=played_ids)
        self.assertEqual(autopost.count(), 2)
        for m in matches:
            m.winner = m.player1
            m.save()
        self.assertTrue(progress_qualifying(t))
        next_players = {
            pid
            for pair in Match.objects.filter(tournament=t, round="Q4").values_list(
                "player1_id", "player2_id"
            )
            for pid in pair
            if pid
        }
        self.assertTrue(
            set(autopost.values_list("player_id", flat=True)).issubset(next_players)
        )
        self.assertFalse(generate_qualifying(t))
