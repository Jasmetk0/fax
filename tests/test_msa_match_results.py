import json

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from msa.models import Match, Player, Season, Tournament, TournamentEntry
from msa.services.draw import generate_draw


class MatchResultsTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 60)]
        User = get_user_model()
        self.staff = User.objects.create_user("admin", password="x", is_staff=True)
        self.client.force_login(self.staff)
        session = self.client.session
        session["admin_mode"] = True
        session.save()

    def _setup_tournament(self, *, season=False):
        t = Tournament.objects.create(name="T", slug="t", draw_size=32, seeds_count=8)
        if season:
            t.season = Season.objects.create(name="S")
            t.save()
        for i in range(32):
            seed = i + 1 if i < 8 else None
            TournamentEntry.objects.create(
                tournament=t, player=self.players[i], seed=seed
            )
        generate_draw(t)
        return t

    def test_normal_result_parsing_and_winner(self):
        t = self._setup_tournament()
        m = t.matches.order_by("id").first()
        url = reverse("msa:tournament-results", args=[t.slug])
        self.client.post(
            url,
            {
                "action": "match_result",
                "match_id": m.id,
                "result_type": "NORMAL",
                "scoreline": "11-8 7-11 11-9 11-6",
            },
        )
        m.refresh_from_db()
        self.assertEqual(m.winner, m.player1)
        self.assertEqual(m.scoreline, "11-8 7-11 11-9 11-6")
        meta = json.loads(m.section)["result_meta"]
        self.assertEqual(meta["type"], "NORMAL")

    def test_invalid_scoreline_rejected(self):
        t = self._setup_tournament()
        m = t.matches.order_by("id").first()
        url = reverse("msa:tournament-results", args=[t.slug])
        resp = self.client.post(
            url,
            {
                "action": "match_result",
                "match_id": m.id,
                "result_type": "NORMAL",
                "scoreline": "11-8 7-11",
            },
            follow=True,
        )
        m.refresh_from_db()
        self.assertIsNone(m.winner)
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertTrue(any("invalid" in msg.lower() for msg in msgs))

    def test_walkover_sets_winner_and_meta(self):
        t = self._setup_tournament()
        m = t.matches.order_by("id").first()
        url = reverse("msa:tournament-results", args=[t.slug])
        self.client.post(
            url,
            {"action": "match_result", "match_id": m.id, "result_type": "WO"},
        )
        m.refresh_from_db()
        self.assertEqual(m.winner, m.player2)
        meta = json.loads(m.section)["result_meta"]
        self.assertEqual(meta["type"], "WO")
        t.refresh_from_db()
        self.assertEqual(t.state, Tournament.State.LIVE)

    def test_retirement_requires_player_and_sets_meta(self):
        t = self._setup_tournament(season=True)
        matches = list(t.matches.order_by("id"))
        m1, m2 = matches[0], matches[1]
        for m in matches[1:]:
            m.winner = m.player1
            m.save()
        url = reverse("msa:tournament-results", args=[t.slug])
        self.client.post(
            url,
            {
                "action": "match_result",
                "match_id": m1.id,
                "result_type": "RET",
                "retired_player_id": m1.player1_id,
                "scoreline": "11-9 5-11 3-1",
            },
        )
        m1.refresh_from_db()
        self.assertEqual(m1.winner, m1.player2)
        meta = json.loads(m1.section)["result_meta"]
        self.assertEqual(meta["type"], "RET")
        self.assertEqual(meta["retired_player_id"], m1.player1_id)
        r16 = Match.objects.filter(
            tournament=t, round="R16", player1=m1.player2, player2=m2.player1
        ).first()
        self.assertIsNotNone(r16)
        m1.player2.refresh_from_db()
        self.assertGreater(m1.player2.rtf_current_points, 0)

    def test_idempotent_save_same_result(self):
        t = self._setup_tournament()
        matches = list(t.matches.order_by("id"))
        m = matches[0]
        for other in matches[1:]:
            other.winner = other.player1
            other.save()
        url = reverse("msa:tournament-results", args=[t.slug])
        payload = {
            "action": "match_result",
            "match_id": m.id,
            "result_type": "NORMAL",
            "scoreline": "6-0 6-0 6-0",
        }
        self.client.post(url, payload)
        self.client.post(url, payload)
        m.refresh_from_db()
        self.assertEqual(m.winner, m.player1)
        self.assertEqual(m.scoreline, "6-0 6-0 6-0")
        r16_count = Match.objects.filter(tournament=t, round="R16").count()
        self.assertEqual(r16_count, 8)
