from django.test import Client, TestCase
from django.urls import reverse
from msa.models import Tournament, Player, Match, TournamentEntry


class TestTournamentPlayers(TestCase):
    def setUp(self):
        self.client = Client()
        self.tournament = Tournament.objects.create(name="T", slug="t")
        self.p1 = Player.objects.create(name="Alpha")
        self.p2 = Player.objects.create(name="Beta")

    def test_uses_entries_when_present(self):
        TournamentEntry.objects.create(tournament=self.tournament, player=self.p1)
        Match.objects.create(
            tournament=self.tournament,
            round="R1",
            section="",
            best_of=5,
            player1=self.p1,
            player2=self.p2,
        )
        resp = self.client.get(
            reverse("msa:tournament-players", args=[self.tournament.slug])
        )
        self.assertContains(resp, self.p1.name)
        self.assertNotContains(resp, self.p2.name)

    def test_fallback_to_matches_when_no_entries(self):
        Match.objects.create(
            tournament=self.tournament,
            round="R1",
            section="",
            best_of=5,
            player1=self.p1,
            player2=self.p2,
        )
        resp = self.client.get(
            reverse("msa:tournament-players", args=[self.tournament.slug])
        )
        self.assertContains(resp, self.p1.name)
        self.assertContains(resp, self.p2.name)
