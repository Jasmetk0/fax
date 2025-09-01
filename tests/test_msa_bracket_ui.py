from django.test import TestCase
from django.urls import reverse

from msa.models import Match, Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw


class TestBracketUI(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 200)]

    def _create_entries(self, tournament, total, seeds=0, extra=None):
        idx = 0
        for s in range(seeds):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[idx], seed=s + 1
            )
            idx += 1
        if extra:
            for spec in extra:
                TournamentEntry.objects.create(
                    tournament=tournament, player=self.players[idx], **spec
                )
                idx += 1
        while idx < total:
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[idx]
            )
            idx += 1

    def test_bracket_contains_round_columns(self):
        t = Tournament.objects.create(
            name="T32", slug="t32", draw_size=32, seeds_count=8
        )
        self._create_entries(t, total=32, seeds=8)
        generate_draw(t)
        resp = self.client.get(reverse("msa:tournament-draw", args=[t.slug]))
        self.assertContains(resp, "<h3>Round of 32</h3>", html=True)
        self.assertNotContains(resp, "<h3>Round of 16</h3>", html=True)
        self.assertNotContains(resp, "<h3>Quarter Final</h3>", html=True)

    def test_seed_badges_and_chips_rendered(self):
        t = Tournament.objects.create(
            name="T32s", slug="t32s", draw_size=32, seeds_count=8
        )
        origin_match = Match.objects.create(
            tournament=t,
            round="Q1",
            player1=self.players[150],
            player2=self.players[151],
        )
        extra = [
            {"entry_type": "Q", "origin_note": "Q1", "origin_match": origin_match},
            {"entry_type": "LL", "origin_note": "LL1", "origin_match": origin_match},
        ]
        self._create_entries(t, total=32, seeds=8, extra=extra)
        generate_draw(t)
        resp = self.client.get(reverse("msa:tournament-draw", args=[t.slug]))
        html = resp.content.decode()
        self.assertIn("seed-badge", html)
        self.assertIn('entry-chip">Q', html)
        self.assertIn('entry-chip">LL', html)
        self.assertIn("origin-link", html)

    def test_print_mode_hides_forms(self):
        t = Tournament.objects.create(
            name="T32p", slug="t32p", draw_size=32, seeds_count=8
        )
        self._create_entries(t, total=32, seeds=8)
        generate_draw(t)
        resp = self.client.get(
            reverse("msa:tournament-draw", args=[t.slug]) + "?print=1"
        )
        self.assertContains(resp, t.name)
        self.assertNotContains(resp, "<form")

    def test_r96_bye_visualization(self):
        t = Tournament.objects.create(
            name="T96", slug="t96", draw_size=96, seeds_count=32
        )
        self._create_entries(t, total=96, seeds=32)
        generate_draw(t)
        resp = self.client.get(reverse("msa:tournament-draw", args=[t.slug]))
        self.assertContains(resp, "BYE")
