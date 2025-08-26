import datetime

from django.utils import timezone

from mma import models
from decimal import Decimal


def test_create_event_and_bout(db):
    org = models.Organization.objects.create(slug="org", name="Org", short_name="ORG")
    wc = models.WeightClass.objects.create(
        slug="lw", name="Lightweight", limit_kg=Decimal("70.50")
    )
    venue = models.Venue.objects.create(name="Arena", city="Prague", country="CZ")
    event = models.Event.objects.create(
        slug="event1",
        organization=org,
        name="Event 1",
        date_start=timezone.now(),
        venue=venue,
    )
    fighter_red = models.Fighter.objects.create(
        slug="red",
        first_name="Red",
        last_name="Fighter",
        country="CZ",
    )
    fighter_blue = models.Fighter.objects.create(
        slug="blue",
        first_name="Blue",
        last_name="Fighter",
        country="US",
    )
    bout = models.Bout.objects.create(
        event=event,
        weight_class=wc,
        fighter_red=fighter_red,
        fighter_blue=fighter_blue,
    )
    assert bout.result == models.Bout.Result.PENDING


def test_ranking_and_news(db):
    org = models.Organization.objects.create(slug="org2", name="Org2", short_name="O2")
    wc = models.WeightClass.objects.create(
        slug="hw", name="Heavyweight", limit_kg=Decimal("120.00")
    )
    fighter = models.Fighter.objects.create(
        slug="champ",
        first_name="Champ",
        last_name="McGee",
        country="US",
    )
    ranking = models.Ranking.objects.create(
        organization=org,
        weight_class=wc,
        position=1,
        fighter=fighter,
        date_effective=datetime.date.today(),
    )
    assert ranking.position == 1
    news = models.NewsItem.objects.create(
        slug="news-1",
        title="News",
        summary="Summary",
        content="Content",
        published_at=timezone.now(),
    )
    assert "News" in str(news)
