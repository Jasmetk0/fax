from django.test import Client, TestCase
from django.urls import reverse


class MSAViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_index(self):
        response = self.client.get(reverse("msa:index"))
        assert response.status_code == 200

    def test_h2h(self):
        response = self.client.get(reverse("msa:h2h"))
        assert response.status_code == 200

    def test_players(self):
        response = self.client.get(reverse("msa:players"))
        assert response.status_code == 200

    def test_squash_tv(self):
        response = self.client.get(reverse("msa:squash-tv"))
        assert response.status_code == 200
