from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db.models import Q

from msa.models import (
    Match,
    Player,
    RankingEntry,
    RankingSnapshot,
    Tournament,
    TournamentEntry,
)
from msa.services.draw import generate_draw
from msa.services.qual import (
    generate_qualifying,
    progress_qualifying,
    promote_qualifiers,
)
from msa.services.alt_ll import select_ll_candidates


class LLAltFlowTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 80)]
        self.snapshot = RankingSnapshot.objects.create(as_of="2024-01-01")
        for i, p in enumerate(self.players, start=1):
            RankingEntry.objects.create(
                snapshot=self.snapshot, player=p, rank=i, points=1000 - i
            )
        User = get_user_model()
        self.staff = User.objects.create_user("admin", password="x", is_staff=True)
        self.client.force_login(self.staff)
        session = self.client.session
        session["admin_mode"] = True
        session.save()

    def test_alt_autofill_fills_empty_slots_pre_draw(self):
        t = Tournament.objects.create(
            name="T", slug="t", draw_size=32, seeding_rank_date=self.snapshot.as_of
        )
        # 28 direct acceptances
        for i in range(28):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.DA,
            )
        generate_draw(t)
        # three alternates
        for i in range(28, 31):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.ALT,
            )
        url = reverse("msa:tournament-draw", args=[t.slug])
        resp = self.client.post(url, {"action": "alt_autofill"})
        self.assertEqual(resp.status_code, 302)
        alts = TournamentEntry.objects.filter(
            tournament=t, entry_type=TournamentEntry.EntryType.ALT
        )
        self.assertTrue(all(e.position is not None for e in alts))

    def _setup_with_qualifying(self):
        t = Tournament.objects.create(
            name="Q",
            slug="q",
            draw_size=32,
            qualifiers_count=2,
            seeding_rank_date=self.snapshot.as_of,
        )
        for i in range(30):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.DA,
            )
        generate_draw(t)
        for i in range(30, 38):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.Q,
            )
        generate_qualifying(t)
        # Q8 -> Q4
        for m in Match.objects.filter(tournament=t, round="Q8"):
            m.winner = m.player1
            m.save()
        progress_qualifying(t)
        finals = list(Match.objects.filter(tournament=t, round="Q4"))
        for m in finals:
            m.winner = m.player1
            m.save()
        promote_qualifiers(t)
        return t, finals

    def test_ll_promotion_after_withdraw(self):
        t, finals = self._setup_with_qualifying()
        url = reverse("msa:tournament-draw", args=[t.slug])
        resp = self.client.post(url, {"action": "withdraw_slot_ll", "slot": 1})
        self.assertEqual(resp.status_code, 302)
        entry = TournamentEntry.objects.get(tournament=t, position=1)
        self.assertEqual(entry.entry_type, TournamentEntry.EntryType.LL)
        self.assertEqual(entry.origin_note, "LL")
        self.assertIn(entry.origin_match, finals)
        match_exists = (
            Match.objects.filter(
                tournament=t,
                round="R32",
            )
            .filter(Q(player1=entry.player) | Q(player2=entry.player))
            .exists()
        )
        self.assertTrue(match_exists)

    def test_ll_respects_completed_block(self):
        t, _ = self._setup_with_qualifying()
        # complete first-round match on slots 1-2
        match = Match.objects.filter(tournament=t, round="R32").first()
        match.winner = match.player1
        match.save()
        url = reverse("msa:tournament-draw", args=[t.slug])
        resp = self.client.post(url, {"action": "withdraw_slot_ll", "slot": 1})
        self.assertEqual(resp.status_code, 302)
        entry = TournamentEntry.objects.filter(tournament=t, position=1).first()
        self.assertNotEqual(entry.entry_type, TournamentEntry.EntryType.LL)

    def test_ll_ordering_by_snapshot(self):
        t, _ = self._setup_with_qualifying()
        losers = select_ll_candidates(t, 2)
        self.assertEqual(len(losers), 2)
        e1, _ = losers[0]
        e2, _ = losers[1]
        self.assertLess(
            RankingEntry.objects.get(snapshot=self.snapshot, player=e1.player).rank,
            RankingEntry.objects.get(snapshot=self.snapshot, player=e2.player).rank,
        )
