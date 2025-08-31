from django.test import TestCase
from django.urls import reverse

from msa.models import (
    Match,
    Player,
    RankingEntry,
    RankingSnapshot,
    Tournament,
    TournamentEntry,
)
from msa.services.draw import generate_draw, progress_bracket, _seed_map_for_draw


class OriginProgressTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 150)]

    def test_origin_render_players_and_draw(self):
        tournament = Tournament.objects.create(name="T", slug="t", draw_size=32)
        TournamentEntry.objects.create(
            tournament=tournament,
            player=self.players[0],
            entry_type=TournamentEntry.EntryType.Q,
            origin_note="Q3",
        )
        qual_match = Match.objects.create(
            tournament=tournament,
            player1=self.players[1],
            player2=self.players[2],
            round="Q",
            section="",
            best_of=5,
        )
        TournamentEntry.objects.create(
            tournament=tournament,
            player=self.players[3],
            entry_type=TournamentEntry.EntryType.LL,
            origin_note="LL2",
            origin_match=qual_match,
        )
        TournamentEntry.objects.create(tournament=tournament, player=self.players[4])
        generate_draw(tournament)

        url_players = reverse("msa:tournament-players", args=[tournament.slug])
        response = self.client.get(url_players)
        match_url = reverse("msa:match-edit", args=[qual_match.pk])
        self.assertContains(response, "Q3")
        self.assertContains(response, "LL2")
        self.assertContains(response, match_url)

        url_draw = reverse("msa:tournament-draw", args=[tournament.slug])
        response = self.client.get(url_draw)
        self.assertContains(response, "Q3")
        self.assertContains(response, "LL2")
        self.assertContains(response, match_url)

    def test_progress_bracket_r32_to_r16(self):
        tournament = Tournament.objects.create(name="T32", slug="t32", draw_size=32)
        for i in range(32):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i]
            )
        generate_draw(tournament)
        for m in Match.objects.filter(tournament=tournament, round="R32"):
            m.winner = m.player1
            m.save()
        progress_bracket(tournament)
        self.assertEqual(
            Match.objects.filter(tournament=tournament, round="R16").count(), 8
        )
        progress_bracket(tournament)
        self.assertEqual(
            Match.objects.filter(tournament=tournament, round="R16").count(), 8
        )

    def test_progress_bracket_r96_to_r64(self):
        tournament = Tournament.objects.create(
            name="T96", slug="t96", draw_size=96, seeds_count=32
        )
        for i in range(32):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i], seed=i + 1
            )
        for i in range(32, 96):
            TournamentEntry.objects.create(
                tournament=tournament, player=self.players[i]
            )
        generate_draw(tournament)
        for m in Match.objects.filter(tournament=tournament, round="R96"):
            m.winner = m.player1
            m.save()
        progress_bracket(tournament)
        r64 = Match.objects.filter(tournament=tournament, round="R64")
        self.assertEqual(r64.count(), 32)
        for m in r64:
            e1 = TournamentEntry.objects.get(tournament=tournament, player=m.player1)
            e2 = TournamentEntry.objects.get(tournament=tournament, player=m.player2)
            self.assertNotEqual(bool(e1.seed), bool(e2.seed))
        progress_bracket(tournament)
        self.assertEqual(
            Match.objects.filter(tournament=tournament, round="R64").count(), 32
        )

    def test_seeding_snapshot_fallback(self):
        snapshot = RankingSnapshot.objects.create(as_of="2024-01-01")
        ranks = [5, 1, 3, 2, 4, 6]
        for player, rank in zip(self.players[:6], ranks):
            RankingEntry.objects.create(
                snapshot=snapshot, player=player, rank=rank, points=0
            )
        t_snap = Tournament.objects.create(
            name="Tsnap",
            slug="tsnap",
            draw_size=32,
            seeds_count=4,
            seeding_method="ranking_snapshot",
            seeding_rank_date="2024-02-01",
        )
        for i in range(6):
            TournamentEntry.objects.create(tournament=t_snap, player=self.players[i])
        generate_draw(t_snap)
        seed_map, _, _ = _seed_map_for_draw(32, 4)
        ordered_players = [self.players[ranks.index(i + 1)] for i in range(4)]
        for idx in range(1, 5):
            pos = seed_map[idx]
            entry = TournamentEntry.objects.get(tournament=t_snap, position=pos)
            self.assertEqual(entry.player, ordered_players[idx - 1])

        t_manual = Tournament.objects.create(
            name="Tman",
            slug="tman",
            draw_size=32,
            seeds_count=4,
            seeding_method="manual",
        )
        t_fb = Tournament.objects.create(
            name="Tfb",
            slug="tfb",
            draw_size=32,
            seeds_count=4,
            seeding_method="ranking_snapshot",
            seeding_rank_date="2023-12-01",
        )
        for i in range(4):
            TournamentEntry.objects.create(
                tournament=t_manual, player=self.players[i], seed=i + 1
            )
            TournamentEntry.objects.create(
                tournament=t_fb, player=self.players[i], seed=i + 1
            )
        generate_draw(t_manual)
        generate_draw(t_fb)
        positions_manual = list(
            TournamentEntry.objects.filter(tournament=t_manual)
            .order_by("player_id")
            .values_list("position", flat=True)
        )
        positions_fb = list(
            TournamentEntry.objects.filter(tournament=t_fb)
            .order_by("player_id")
            .values_list("position", flat=True)
        )
        self.assertEqual(positions_manual, positions_fb)
