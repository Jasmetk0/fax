from django.test import TestCase

from msa.models import Match, Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw


class TestDrawMatches(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 300)]

    def _create_entries(self, tournament, seeds, total):
        for i in range(seeds):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i], seed=i + 1
            )
        for i in range(seeds, total):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i]
            )

    def test_32_draw_matches(self):
        tournament = Tournament.objects.create(
            name="T32m", slug="t32m", draw_size=32, seeds_count=8
        )
        self._create_entries(tournament, seeds=8, total=32)
        generate_draw(tournament)
        matches = list(
            Match.objects.filter(tournament=tournament).select_related(
                "player1", "player2"
            )
        )
        self.assertEqual(len(matches), 16)
        self.assertTrue(all(m.round == "R32" for m in matches))
        pairs = {(m.player1_id, m.player2_id) for m in matches}
        self.assertEqual(len(pairs), 16)
        players = {m.player1_id for m in matches} | {m.player2_id for m in matches}
        self.assertEqual(len(players), 32)

    def test_96_draw_matches(self):
        tournament = Tournament.objects.create(
            name="T96m", slug="t96m", draw_size=96, seeds_count=32
        )
        self._create_entries(tournament, seeds=32, total=96)
        generate_draw(tournament)
        matches = list(
            Match.objects.filter(tournament=tournament).select_related(
                "player1", "player2"
            )
        )
        self.assertEqual(len(matches), 32)
        self.assertTrue(all(m.round == "R96" for m in matches))
        seed_players = {self.players[i].id for i in range(32)}
        for m in matches:
            self.assertNotIn(m.player1_id, seed_players)
            self.assertNotIn(m.player2_id, seed_players)

    def test_idempotent_generation(self):
        tournament = Tournament.objects.create(
            name="Tidemp", slug="tidemp", draw_size=32, seeds_count=8
        )
        self._create_entries(tournament, seeds=8, total=32)
        generate_draw(tournament)
        first_positions = list(
            tournament.entries.order_by("player__name").values_list(
                "position", flat=True
            )
        )
        first_match_ids = list(tournament.matches.values_list("id", flat=True))
        generate_draw(tournament)
        second_positions = list(
            tournament.entries.order_by("player__name").values_list(
                "position", flat=True
            )
        )
        second_match_ids = list(tournament.matches.values_list("id", flat=True))
        self.assertEqual(first_positions, second_positions)
        self.assertEqual(first_match_ids, second_match_ids)

    def test_regenerate_block_and_force(self):
        tournament = Tournament.objects.create(
            name="Tregm", slug="tregm", draw_size=32, seeds_count=8
        )
        self._create_entries(tournament, seeds=8, total=32)
        generate_draw(tournament)
        original_positions = list(
            tournament.entries.order_by("player__name").values_list(
                "position", flat=True
            )
        )
        original_match_ids = list(tournament.matches.values_list("id", flat=True))
        match = tournament.matches.first()
        match.winner = match.player1
        match.save()
        generate_draw(tournament, force=True)
        self.assertEqual(
            original_positions,
            list(
                tournament.entries.order_by("player__name").values_list(
                    "position", flat=True
                )
            ),
        )
        self.assertEqual(
            original_match_ids, list(tournament.matches.values_list("id", flat=True))
        )
        tournament.flex_mode = True
        tournament.save()
        e1 = TournamentEntry.objects.get(tournament=tournament, seed=1)
        e8 = TournamentEntry.objects.get(tournament=tournament, seed=8)
        e1.seed, e8.seed = e8.seed, e1.seed
        e1.save()
        e8.save()
        generate_draw(tournament, force=True)
        new_positions = list(
            tournament.entries.order_by("player__name").values_list(
                "position", flat=True
            )
        )
        new_match_ids = list(tournament.matches.values_list("id", flat=True))
        self.assertNotEqual(original_positions, new_positions)
        self.assertNotEqual(set(original_match_ids), set(new_match_ids))
        self.assertEqual(tournament.matches.count(), 16)
