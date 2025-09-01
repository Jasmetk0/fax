import json

from django.test import TestCase
from django.urls import reverse

from msa.models import Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw
from msa.services.qual import generate_qualifying


class DrawJsonLabelTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 60)]

    def test_draw_json_has_labels(self):
        t = Tournament.objects.create(name="T", slug="t", draw_size=32, seeds_count=8)
        for i in range(32):
            TournamentEntry.objects.create(tournament=t, player=self.players[i])
        generate_draw(t)
        resp = self.client.get(reverse("msa:tournament-draw-json", args=[t.slug]))
        data = json.loads(resp.content)
        first = data["rounds"][0]
        self.assertEqual(first["code"], "R32")
        self.assertEqual(first["round_label"], "Round of 32")

    def test_qual_json_has_labels(self):
        t = Tournament.objects.create(name="TQ", slug="tq", draw_size=32)
        for i in range(8):
            TournamentEntry.objects.create(
                tournament=t, player=self.players[i], entry_type="Q"
            )
        generate_qualifying(t)
        resp = self.client.get(reverse("msa:tournament-qualifying-json", args=[t.slug]))
        data = json.loads(resp.content)
        first = data["rounds"][0]
        self.assertEqual(first["code"], "Q8")
        self.assertEqual(first["round_label"], "Quarter Final")
