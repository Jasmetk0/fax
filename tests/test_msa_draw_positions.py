from django.test import TestCase

from msa.models import Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw, _seed_map_for_draw


class TestDrawGeneration(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 200)]

    def test_32_draw_idempotence(self):
        tournament = Tournament.objects.create(name="T32", slug="t32", draw_size=32)
        for i in range(8):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i], seed=i + 1
            )
        for i in range(8, 32):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i]
            )
        generate_draw(tournament)
        first = list(
            tournament.entries.order_by("player__name").values_list(
                "position", flat=True
            )
        )
        generate_draw(tournament)
        second = list(
            tournament.entries.order_by("player__name").values_list(
                "position", flat=True
            )
        )
        self.assertEqual(first, second)
        self.assertEqual(tournament.state, Tournament.State.DRAWN)

    def test_96_draw_byes(self):
        tournament = Tournament.objects.create(name="T96", slug="t96", draw_size=96)
        for i in range(32):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i], seed=i + 1
            )
        for i in range(32, 96):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i]
            )
        generate_draw(tournament)
        seed_map, slots, playable = _seed_map_for_draw(96, 32)
        for seed, pos in seed_map.items():
            entry = TournamentEntry.objects.get(tournament=tournament, seed=seed)
            self.assertEqual(entry.position, pos)
        self.assertEqual(tournament.entries.filter(position__isnull=False).count(), 96)
        self.assertEqual(tournament.state, Tournament.State.DRAWN)

    def test_regenerate(self):
        tournament = Tournament.objects.create(name="Treg", slug="treg", draw_size=32)
        for i in range(8):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i], seed=i + 1
            )
        generate_draw(tournament)
        original = list(
            tournament.entries.order_by("player__name").values_list(
                "position", flat=True
            )
        )
        e1 = TournamentEntry.objects.get(tournament=tournament, seed=1)
        e8 = TournamentEntry.objects.get(tournament=tournament, seed=8)
        e1.seed, e8.seed = e8.seed, e1.seed
        e1.save()
        e8.save()
        generate_draw(tournament, force=True)
        updated = list(
            tournament.entries.order_by("player__name").values_list(
                "position", flat=True
            )
        )
        self.assertNotEqual(original, updated)
        self.assertEqual(tournament.state, Tournament.State.DRAWN)
