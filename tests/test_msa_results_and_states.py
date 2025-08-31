from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from msa.models import Match, Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw


class ResultsAndStateTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 50)]
        User = get_user_model()
        self.staff = User.objects.create_user("admin", password="x", is_staff=True)
        self.client.force_login(self.staff)
        session = self.client.session
        session["admin_mode"] = True
        session.save()

    def _setup_tournament(self):
        t = Tournament.objects.create(name="T", slug="t", draw_size=32, seeds_count=8)
        for i in range(32):
            seed = i + 1 if i < 8 else None
            TournamentEntry.objects.create(
                tournament=t, player=self.players[i], seed=seed
            )
        generate_draw(t)
        return t

    def test_match_result_sets_winner_and_progresses(self):
        t = self._setup_tournament()
        matches = list(t.matches.order_by("id"))
        m1 = matches[0]
        m2 = matches[1]
        for m in matches[1:]:
            m.winner = m.player1
            m.save()
        url = reverse("msa:tournament-results", args=[t.slug])
        self.client.post(
            url,
            {
                "action": "match_result",
                "match_id": m1.id,
                "winner": "p1",
                "scoreline": "6-0 6-0",
            },
        )
        m1.refresh_from_db()
        self.assertEqual(m1.winner, m1.player1)
        self.assertEqual(m1.scoreline, "6-0 6-0")
        r16_matches = Match.objects.filter(tournament=t, round="R16")
        self.assertEqual(r16_matches.count(), 8)
        r16 = r16_matches.filter(
            player1__in=[m1.player1, m2.player1],
            player2__in=[m1.player1, m2.player1],
        ).first()
        self.assertIsNotNone(r16)
        # idempotent
        self.client.post(
            url,
            {
                "action": "match_result",
                "match_id": m1.id,
                "winner": "p1",
                "scoreline": "6-0 6-0",
            },
        )
        self.assertEqual(Match.objects.filter(tournament=t, round="R16").count(), 8)

    def test_state_transitions_live_and_complete(self):
        t = Tournament.objects.create(name="Ts", slug="ts", draw_size=32, seeds_count=0)
        p1, p2, p3, p4 = self.players[:4]
        TournamentEntry.objects.create(tournament=t, player=p1, position=1)
        TournamentEntry.objects.create(tournament=t, player=p2, position=2)
        TournamentEntry.objects.create(tournament=t, player=p3, position=3)
        TournamentEntry.objects.create(tournament=t, player=p4, position=4)
        m1 = Match.objects.create(tournament=t, player1=p1, player2=p2, round="R32")
        m2 = Match.objects.create(tournament=t, player1=p3, player2=p4, round="R32")
        url = reverse("msa:tournament-results", args=[t.slug])
        self.client.post(
            url, {"action": "match_result", "match_id": m1.id, "winner": "p1"}
        )
        t.refresh_from_db()
        self.assertEqual(t.state, Tournament.State.LIVE)
        self.client.post(
            url, {"action": "match_result", "match_id": m2.id, "winner": "p1"}
        )
        t.refresh_from_db()
        self.assertEqual(t.state, Tournament.State.LIVE)
        final = Match.objects.get(tournament=t, round="R16")
        self.client.post(
            url, {"action": "match_result", "match_id": final.id, "winner": "p1"}
        )
        t.refresh_from_db()
        self.assertEqual(t.state, Tournament.State.COMPLETE)
