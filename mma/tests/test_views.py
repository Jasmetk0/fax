import datetime

from django.utils import timezone

from mma.models import Event, Organization, Venue


def test_dashboard_renders(client, db):
    org = Organization.objects.create(slug="org", name="Org", short_name="ORG")
    venue = Venue.objects.create(name="Arena", city="Prague", country="CZ")
    Event.objects.create(
        slug="e1",
        organization=org,
        name="Event 1",
        date_start=timezone.now() + datetime.timedelta(days=1),
        venue=venue,
    )

    resp = client.get("/mma/")
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Upcoming Events" in content
    assert "Event 1" in content
