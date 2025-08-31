from datetime import date

from django.test import TestCase

from msa.models import Match, Player, Season, Tournament
from msa.services.points import (
    compute_tournament_points,
    load_points_table,
    rebuild_season_live_points,
)
from msa.services.snapshot import create_ranking_snapshot


class PointsAndSnapshotsTests(TestCase):
    def test_compute_tournament_points_basic(self):
        season = Season.objects.create(name="S")
        t = Tournament.objects.create(name="T", slug="t", season=season, draw_size=4)
        players = [Player.objects.create(name=f"P{i}") for i in range(4)]
        Match.objects.create(
            tournament=t,
            round="SF",
            player1=players[0],
            player2=players[1],
            winner=players[0],
        )
        Match.objects.create(
            tournament=t,
            round="SF",
            player1=players[2],
            player2=players[3],
            winner=players[2],
        )
        Match.objects.create(
            tournament=t,
            round="F",
            player1=players[0],
            player2=players[2],
            winner=players[0],
        )
        pts = compute_tournament_points(t)
        table = load_points_table(None)
        self.assertEqual(len(pts), 4)
        self.assertGreater(pts[players[0].id], pts[players[2].id])
        self.assertEqual(pts[players[1].id], table["SF"])
        self.assertEqual(pts[players[3].id], table["SF"])

    def test_rebuild_season_live_points_updates_players(self):
        season = Season.objects.create(name="S")
        t1 = Tournament.objects.create(name="T1", slug="t1", season=season, draw_size=2)
        t2 = Tournament.objects.create(name="T2", slug="t2", season=season, draw_size=2)
        p1 = Player.objects.create(name="A")
        p2 = Player.objects.create(name="B")
        Match.objects.create(
            tournament=t1, round="F", player1=p1, player2=p2, winner=p1
        )
        Match.objects.create(
            tournament=t2, round="F", player1=p1, player2=p2, winner=p2
        )
        rebuild_season_live_points(season)
        table = load_points_table(None)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.rtf_current_points, table["W"] + table["F"])
        self.assertEqual(p2.rtf_current_points, table["W"] + table["F"])

    def test_create_ranking_snapshot_freezes_current_live_points(self):
        p1 = Player.objects.create(name="A", rtf_current_points=300)
        p2 = Player.objects.create(name="B", rtf_current_points=100)
        snap = create_ranking_snapshot(date.today())
        entries = list(snap.entries.order_by("rank"))
        self.assertEqual(entries[0].player, p1)
        self.assertEqual(entries[0].points, 300)
        self.assertEqual(entries[1].player, p2)
        self.assertEqual(entries[1].points, 100)
        p1.rtf_current_points = 50
        p1.save()
        entries = list(snap.entries.order_by("rank"))
        self.assertEqual(entries[0].points, 300)
