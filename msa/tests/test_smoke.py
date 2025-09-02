import datetime

from django.test import Client, TestCase

from fax_calendar.widgets import WoorldAdminDateWidget

from msa.forms import TournamentForm
from msa.models import Tournament


class TournamentAdminFormTests(TestCase):
    def test_uses_fax_calendar_widgets(self):
        form = TournamentForm()
        assert isinstance(form.fields["start_date"].widget, WoorldAdminDateWidget)
        assert isinstance(form.fields["end_date"].widget, WoorldAdminDateWidget)


class TournamentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tournament = Tournament.objects.create(
            name="Open", slug="open", start_date=datetime.date(2024, 1, 2)
        )

    def test_list_view(self):
        resp = self.client.get("/msasquashtour/tournaments/")
        assert resp.status_code == 200
        assert "Open" in resp.content.decode()
        assert "2024-01-02" in resp.content.decode()

    def test_detail_view(self):
        resp = self.client.get(f"/msasquashtour/tournaments/{self.tournament.slug}/")
        assert resp.status_code == 200
        assert "Open" in resp.content.decode()
        assert "2024-01-02" in resp.content.decode()
