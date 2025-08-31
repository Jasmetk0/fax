from django.test import TestCase

from msa.models import Match, Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw
from msa.services.qual import (
    generate_qualifying,
    progress_qualifying,
    promote_qualifiers,
)


class QualifyingFlowTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 60)]

    def test_main_draw_ignores_q_entries(self):
        t = Tournament.objects.create(name="T", slug="t", draw_size=32)
        for i in range(4):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.DA,
            )
        for i in range(4, 6):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.Q,
            )
        generate_draw(t)
        da_positions = TournamentEntry.objects.filter(
            tournament=t, entry_type=TournamentEntry.EntryType.DA
        ).values_list("position", flat=True)
        q_positions = TournamentEntry.objects.filter(
            tournament=t, entry_type=TournamentEntry.EntryType.Q
        ).values_list("position", flat=True)
        self.assertTrue(all(p is not None for p in da_positions))
        self.assertTrue(all(p is None for p in q_positions))

    def test_generate_and_progress_qualifying(self):
        t = Tournament.objects.create(
            name="Q", slug="q", draw_size=32, qualifiers_count=4
        )
        for i in range(8):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.Q,
            )
        generate_qualifying(t)
        self.assertEqual(Match.objects.filter(tournament=t, round="Q8").count(), 4)
        for m in Match.objects.filter(tournament=t, round="Q8"):
            m.winner = m.player1
            m.save()
        self.assertTrue(progress_qualifying(t))
        self.assertEqual(Match.objects.filter(tournament=t, round="Q4").count(), 2)
        for m in Match.objects.filter(tournament=t, round="Q4"):
            m.winner = m.player1
            m.save()
        self.assertTrue(progress_qualifying(t))
        self.assertEqual(Match.objects.filter(tournament=t, round="Q2").count(), 1)
        self.assertFalse(progress_qualifying(t))

    def test_promote_qualifiers_into_main(self):
        t = Tournament.objects.create(
            name="P", slug="p", draw_size=32, qualifiers_count=2, seeds_count=0
        )
        for i in range(4):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.DA,
            )
        generate_draw(t)
        da_positions_before = list(
            TournamentEntry.objects.filter(
                tournament=t, entry_type=TournamentEntry.EntryType.DA
            ).values_list("position", flat=True)
        )
        for i in range(4, 8):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.Q,
            )
        generate_qualifying(t)
        final_matches = list(Match.objects.filter(tournament=t, round="Q4"))
        for m in final_matches:
            m.winner = m.player1
            m.save()
        promote_qualifiers(t)
        winners = [m.player1 for m in final_matches]
        entries = TournamentEntry.objects.filter(
            tournament=t, entry_type=TournamentEntry.EntryType.Q, player__in=winners
        )
        self.assertTrue(all(e.position is not None for e in entries))
        self.assertTrue(all(e.origin_note == "Q" for e in entries))
        for e in entries:
            self.assertIn(e.origin_match, final_matches)
        da_positions_after = list(
            TournamentEntry.objects.filter(
                tournament=t, entry_type=TournamentEntry.EntryType.DA
            ).values_list("position", flat=True)
        )
        self.assertEqual(da_positions_after, da_positions_before)

    def test_promote_fails_if_not_enough_free_slots(self):
        t = Tournament.objects.create(
            name="F", slug="f", draw_size=32, qualifiers_count=2, seeds_count=0
        )
        for i in range(31):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.DA,
            )
        generate_draw(t)
        for i in range(31, 35):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.Q,
            )
        generate_qualifying(t)
        for m in Match.objects.filter(tournament=t, round="Q4"):
            m.winner = m.player1
            m.save()
        self.assertFalse(promote_qualifiers(t))
        self.assertTrue(
            all(
                e.position is None
                for e in TournamentEntry.objects.filter(
                    tournament=t, entry_type=TournamentEntry.EntryType.Q
                )
            )
        )

    def test_qual_regenerate_idempotent(self):
        t = Tournament.objects.create(
            name="R", slug="r", draw_size=32, qualifiers_count=2
        )
        for i in range(4):
            TournamentEntry.objects.create(
                tournament=t,
                player=self.players[i],
                entry_type=TournamentEntry.EntryType.Q,
            )
        generate_qualifying(t)
        pairs_first = {
            (m.player1_id, m.player2_id)
            for m in Match.objects.filter(tournament=t, round="Q4")
        }
        generate_qualifying(t, force=True)
        pairs_second = {
            (m.player1_id, m.player2_id)
            for m in Match.objects.filter(tournament=t, round="Q4")
        }
        self.assertEqual(pairs_first, pairs_second)
        generate_qualifying(t, force=True)
        pairs_third = {
            (m.player1_id, m.player2_id)
            for m in Match.objects.filter(tournament=t, round="Q4")
        }
        self.assertEqual(pairs_second, pairs_third)
