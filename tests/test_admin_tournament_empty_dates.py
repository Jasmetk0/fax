from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from msa.models import Tournament


class AdminTournamentEmptyDatesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="admin", email="a@example.com", password="pass"
        )

    def test_change_page_with_empty_dates(self):
        t = Tournament.objects.create(name="T", slug="t")
        self.client.force_login(self.admin)
        url = reverse("admin:msa_tournament_change", args=[t.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
