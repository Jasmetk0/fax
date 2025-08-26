import datetime

from django.utils import timezone

from mma.models import Event, NewsItem, Organization, Venue


def create_event(slug: str, days: int) -> Event:
    org = Organization.objects.create(slug=f"org-{slug}", name="Org", short_name="ORG")
    venue = Venue.objects.create(name="Arena", city="Prague", country="CZ")
    return Event.objects.create(
        slug=slug,
        organization=org,
        name=f"Event {slug}",
        date_start=timezone.now() + datetime.timedelta(days=days),
        venue=venue,
    )


def test_event_list_filters(client, db):
    create_event("past", days=-1)
    create_event("future", days=1)

    resp = client.get("/api/mma/events/?upcoming=1")
    slugs = {e["slug"] for e in resp.json()}
    assert "future" in slugs and "past" not in slugs

    resp = client.get("/api/mma/events/?limit=1")
    assert len(resp.json()) == 1


def test_event_detail(client, db):
    event = create_event("detail", days=2)
    resp = client.get(f"/api/mma/events/{event.slug}/")
    data = resp.json()
    assert data["slug"] == event.slug
    assert "organization" in data


def test_news_endpoints(client, db):
    NewsItem.objects.create(
        slug="n1", title="News 1", summary="s", content="c", published_at=timezone.now()
    )
    NewsItem.objects.create(
        slug="n2", title="News 2", summary="s", content="c", published_at=timezone.now()
    )
    resp = client.get("/api/mma/news/?limit=1")
    assert len(resp.json()) == 1
    detail = client.get("/api/mma/news/n1/")
    assert detail.json()["slug"] == "n1"
