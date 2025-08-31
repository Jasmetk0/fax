import json

from django.test import TestCase
from django.urls import reverse

from msa.models import Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw
from msa.services.qual import generate_qualifying


class BracketJsonTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 80)]

    def _create_entries(self, tournament, total, seeds=0, qual=0):
        idx = 0
        for s in range(seeds):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[idx], seed=s + 1
            )
            idx += 1
        for _ in range(qual):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[idx], entry_type="Q"
            )
            idx += 1
        while idx < total:
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[idx]
            )
            idx += 1

    def test_draw_json_shape(self):
        t = Tournament.objects.create(name="TD", slug="td", draw_size=32, seeds_count=8)
        self._create_entries(t, total=32, seeds=8)
        generate_draw(t)
        resp = self.client.get(reverse("msa:tournament-draw-json", args=[t.slug]))
        data = json.loads(resp.content)
        self.assertEqual(data["tournament"]["slug"], t.slug)
        self.assertEqual(data["tournament"]["draw_size"], 32)
        self.assertTrue(data["rounds"])
        first_round = data["rounds"][0]
        self.assertEqual(first_round["code"], "R32")
        self.assertIn("p1", first_round["matches"][0])
        seeds = [m["p1"]["seed"] or m["p2"]["seed"] for m in first_round["matches"]]
        self.assertIn(1, seeds)

    def test_qualifying_json_shape(self):
        t = Tournament.objects.create(name="TQJ", slug="tqj", draw_size=32)
        self._create_entries(t, total=8, qual=8)
        generate_qualifying(t)
        resp = self.client.get(reverse("msa:tournament-qualifying-json", args=[t.slug]))
        data = json.loads(resp.content)
        self.assertEqual(data["tournament"]["slug"], t.slug)
        self.assertTrue(data["rounds"])
        self.assertEqual(data["rounds"][0]["code"], "Q8")
        self.assertEqual(len(data["rounds"][0]["matches"]), 4)
