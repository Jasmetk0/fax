from django.core.management.base import BaseCommand
from django.utils import timezone

from msa.models import (
    Match,
    MediaItem,
    NewsPost,
    Player,
    RankingEntry,
    RankingSnapshot,
    Tournament,
)


class Command(BaseCommand):
    help = "Load demo data for MSA Squash Tour"

    def handle(self, *args, **options):
        if Player.objects.exists():
            self.stdout.write("Demo data already loaded")
            return

        countries = ["USA", "UK", "CZE", "FRA", "GER", "ESP", "EGY", "AUS"]
        players = []
        for i in range(1, 13):
            p = Player.objects.create(
                name=f"Player {i}",
                slug=f"player-{i}",
                country=countries[i % len(countries)],
            )
            players.append(p)

        today = timezone.now().date()
        t1 = Tournament.objects.create(
            name="Ongoing Open",
            slug="ongoing-open",
            category="Diamond",
            start_date=today,
            end_date=today,
            city="CityA",
            country="USA",
            status="ongoing",
        )
        t2 = Tournament.objects.create(
            name="Future Cup",
            slug="future-cup",
            category="Emerald",
            start_date=today + timezone.timedelta(days=30),
            end_date=today + timezone.timedelta(days=37),
            city="CityB",
            country="UK",
            status="upcoming",
        )

        Match.objects.create(
            tournament=t1,
            round="Final",
            best_of=5,
            player1=players[0],
            player2=players[1],
            winner=players[0],
            scoreline="3-1",
            live_status="finished",
        )
        Match.objects.create(
            tournament=t1,
            round="Semi",
            best_of=5,
            player1=players[2],
            player2=players[3],
            winner=players[2],
            scoreline="3-0",
            live_status="finished",
        )
        Match.objects.create(
            tournament=t2,
            round="Round 1",
            best_of=5,
            player1=players[4],
            player2=players[5],
            live_status="live",
            live_p1_points=1,
            live_p2_points=0,
            live_game_no=1,
        )

        snapshot = RankingSnapshot.objects.create(as_of=today)
        for idx, p in enumerate(players, start=1):
            RankingEntry.objects.create(
                snapshot=snapshot, player=p, rank=idx, points=1000 - idx * 10
            )

        for i in range(1, 4):
            NewsPost.objects.create(
                title=f"News {i}",
                slug=f"news-{i}",
                published_at=timezone.now(),
                author="Admin",
                excerpt="Demo news",
                body="Demo body",
            )

        for i in range(1, 4):
            MediaItem.objects.create(
                title=f"Video {i}",
                slug=f"video-{i}",
                published_at=timezone.now(),
                video_url="https://youtu.be/dQw4w9WgXcQ",
            )

        self.stdout.write("Demo data loaded")
