from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from msa.models import Match, Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw, replace_slot


class SwapReplaceTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 60)]
        User = get_user_model()
        self.staff = User.objects.create_user("admin", password="x", is_staff=True)
        self.client.force_login(self.staff)
        session = self.client.session
        session["admin_mode"] = True
        session.save()

    def _create_tournament(self):
        tournament = Tournament.objects.create(
            name="T", slug="t", draw_size=32, seeds_count=8
        )
        for i in range(8):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i], seed=i + 1
            )
        for i in range(8, 32):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i]
            )
        generate_draw(tournament)
        return tournament

    def test_swap_updates_match(self):
        t = self._create_tournament()
        url = reverse("msa:tournament-draw", args=[t.slug])
        e7 = TournamentEntry.objects.get(tournament=t, position=7)
        e8 = TournamentEntry.objects.get(tournament=t, position=8)
        match = Match.objects.filter(
            player1__in=[e7.player, e8.player],
            player2__in=[e7.player, e8.player],
        ).first()
        self.client.post(url, {"action": "swap", "slot_a": 7, "slot_b": 8})
        e7.refresh_from_db()
        e8.refresh_from_db()
        match.refresh_from_db()
        self.assertEqual(e7.position, 8)
        self.assertEqual(e8.position, 7)
        self.assertEqual(match.player1, e8.player)
        self.assertEqual(match.player2, e7.player)

    def test_swap_completed_match_block(self):
        t = self._create_tournament()
        url = reverse("msa:tournament-draw", args=[t.slug])
        e7 = TournamentEntry.objects.get(tournament=t, position=7)
        e8 = TournamentEntry.objects.get(tournament=t, position=8)
        match = Match.objects.filter(
            player1__in=[e7.player, e8.player],
            player2__in=[e7.player, e8.player],
        ).first()
        match.winner = e7.player
        match.save()
        self.client.post(url, {"action": "swap", "slot_a": 7, "slot_b": 8})
        e7.refresh_from_db()
        e8.refresh_from_db()
        match.refresh_from_db()
        self.assertEqual(e7.position, 7)
        self.assertEqual(e8.position, 8)
        self.assertEqual(match.player1, e7.player)
        self.assertEqual(match.player2, e8.player)
        t.flex_mode = True
        t.save()
        self.client.post(url, {"action": "swap", "slot_a": 7, "slot_b": 8})
        e7.refresh_from_db()
        e8.refresh_from_db()
        match.refresh_from_db()
        self.assertEqual(e7.position, 8)
        self.assertEqual(e8.position, 7)
        self.assertEqual(match.player1, e7.player)
        self.assertEqual(match.player2, e8.player)

    def test_replace_updates_match(self):
        t = self._create_tournament()
        slot = 5
        current = TournamentEntry.objects.get(tournament=t, position=slot)
        alt = TournamentEntry.objects.create(
            tournament=t,
            player=self.players[40],
            entry_type=TournamentEntry.EntryType.ALT,
            status=TournamentEntry.Status.ACTIVE,
        )
        ok = replace_slot(t, slot, alt.pk)
        self.assertTrue(ok)
        current.refresh_from_db()
        alt.refresh_from_db()
        self.assertEqual(current.status, TournamentEntry.Status.REPLACED)
        self.assertIsNone(current.position)
        self.assertEqual(alt.status, TournamentEntry.Status.ACTIVE)
        self.assertEqual(alt.position, slot)
        mate = slot + 1 if slot % 2 else slot - 1
        partner = TournamentEntry.objects.get(tournament=t, position=mate)
        match = Match.objects.filter(
            player1__in=[alt.player, partner.player],
            player2__in=[alt.player, partner.player],
        ).first()
        low, high = sorted([slot, mate])
        self.assertEqual(match.player1, alt.player if low == slot else partner.player)
        self.assertEqual(match.player2, partner.player if low == slot else alt.player)

    def test_replace_completed_match_block(self):
        t = self._create_tournament()
        slot = 5
        current = TournamentEntry.objects.get(tournament=t, position=slot)
        mate = slot + 1 if slot % 2 else slot - 1
        partner = TournamentEntry.objects.get(tournament=t, position=mate)
        match = Match.objects.filter(
            player1__in=[current.player, partner.player],
            player2__in=[current.player, partner.player],
        ).first()
        match.winner = current.player
        match.save()
        alt = TournamentEntry.objects.create(
            tournament=t,
            player=self.players[41],
            entry_type=TournamentEntry.EntryType.ALT,
            status=TournamentEntry.Status.ACTIVE,
        )
        ok = replace_slot(t, slot, alt.pk)
        self.assertFalse(ok)
        current.refresh_from_db()
        alt.refresh_from_db()
        self.assertEqual(current.status, TournamentEntry.Status.ACTIVE)
        self.assertEqual(current.position, slot)
        self.assertIsNone(alt.position)
        t.flex_mode = True
        t.save()
        ok = replace_slot(t, slot, alt.pk, allow_over_completed=True)
        self.assertTrue(ok)
        current.refresh_from_db()
        alt.refresh_from_db()
        match.refresh_from_db()
        self.assertEqual(current.status, TournamentEntry.Status.REPLACED)
        self.assertEqual(alt.position, slot)
        self.assertEqual(match.player1, current.player)
        self.assertEqual(match.player2, partner.player)
