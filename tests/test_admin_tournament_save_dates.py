from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from msa.models import Tournament


class AdminTournamentSaveDatesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="admin", email="a@example.com", password="pass"
        )
        self.client.force_login(self.admin)
        self.tournament = Tournament.objects.create(name="T", slug="t")
        self.url = reverse("admin:msa_tournament_change", args=[self.tournament.pk])

    def _post_data(self, start_date):
        return {
            "name": "T",
            "slug": "t",
            "season": "",
            "category": "",
            "season_category": "",
            "start_date": start_date,
            "end_date": "",
            "city": "",
            "country": "",
            "venue": "",
            "prize_money": "",
            "status": "",
            "draw_size": "0",
            "seeds_count": "0",
            "qualifiers_count": "0",
            "lucky_losers": "0",
            "seeding_method": "manual",
            "seeding_rank_date": "",
            "entry_deadline": "",
            "allow_manual_bracket_edits": "on",
            "flex_mode": "",
            "draw_policy": "single_elim",
            "state": Tournament.State.DRAFT,
            "world_ranking_mode": Tournament.WorldRankingMode.AUTO,
            "world_ranking_snapshot": "",
            "_save": "Save",
        }

    def test_change_page_get(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_post_valid_iso(self):
        resp = self.client.post(self.url, self._post_data("2025-09-01"))
        self.assertEqual(resp.status_code, 302)
        self.tournament.refresh_from_db()
        self.assertEqual(self.tournament.start_date, "2025-09-01")

    def test_post_valid_dd_mm_yyyy(self):
        resp = self.client.post(self.url, self._post_data("01-09-2025"))
        self.assertEqual(resp.status_code, 302)
        self.tournament.refresh_from_db()
        self.assertEqual(self.tournament.start_date, "2025-09-01")

    def test_post_invalid(self):
        resp = self.client.post(self.url, self._post_data("32-13-2025"))
        self.assertEqual(resp.status_code, 200)
        form = resp.context["adminform"].form
        self.assertFormError(
            form,
            "start_date",
            "Datum musí být ve formátu DD-MM-YYYY nebo YYYY-MM-DD",
        )

    def test_post_empty(self):
        resp = self.client.post(self.url, self._post_data(""))
        self.assertEqual(resp.status_code, 302)
        self.tournament.refresh_from_db()
        self.assertIsNone(self.tournament.start_date)
