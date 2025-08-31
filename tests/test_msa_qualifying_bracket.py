from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from msa.models import Player, Tournament, TournamentEntry
from msa.services.qual import generate_qualifying, progress_qualifying
from msa.services.match_results import record_match_result


class QualifyingBracketTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 60)]
        User = get_user_model()
        self.staff = User.objects.create_user("admin", password="x", is_staff=True)
        self.client.force_login(self.staff)
        session = self.client.session
        session["admin_mode"] = True
        session.save()

    def _create_qual_entries(self, tournament, n):
        for i in range(n):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i], entry_type="Q"
            )

    def test_qualifying_bracket_columns_render(self):
        t = Tournament.objects.create(name="TQ", slug="tq", draw_size=32)
        self._create_qual_entries(t, 8)
        generate_qualifying(t)
        for m in t.matches.filter(round="Q8"):
            m.winner = m.player1
            m.save(update_fields=["winner"])
        progress_qualifying(t)
        resp = self.client.get(reverse("msa:tournament-qualifying", args=[t.slug]))
        self.assertContains(resp, "Q8")
        self.assertContains(resp, "Q4")
        self.assertContains(resp, self.players[0].name)

    def test_print_mode_no_forms_qualifying(self):
        t = Tournament.objects.create(name="TQP", slug="tqp", draw_size=32)
        self._create_qual_entries(t, 8)
        generate_qualifying(t)
        resp = self.client.get(
            reverse("msa:tournament-qualifying", args=[t.slug]) + "?print=1"
        )
        self.assertContains(resp, t.name)
        self.assertNotContains(resp, "<form")

    def test_generate_then_progress_qualifying(self):
        t = Tournament.objects.create(name="TQG", slug="tqg", draw_size=32)
        self._create_qual_entries(t, 8)
        url = reverse("msa:tournament-qualifying", args=[t.slug])
        self.client.post(url, {"action": "qual_generate"})
        self.assertEqual(t.matches.filter(round__startswith="Q").count(), 4)
        for m in t.matches.filter(round="Q8"):
            record_match_result(m, result_type="NORMAL", scoreline_str="11-9 11-9 11-9")
        self.client.post(url, {"action": "qual_progress"})
        self.assertTrue(t.matches.filter(round="Q4").exists())
