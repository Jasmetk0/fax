import datetime

from django.utils import timezone

from mma.models import (
    Bout,
    Event,
    Fighter,
    Organization,
    Ranking,
    Venue,
    WeightClass,
)


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


def test_section_pages_render(client, db):
    org = Organization.objects.create(slug="org", name="Org", short_name="ORG")
    weight = WeightClass.objects.create(slug="lw", name="Lightweight", limit_kg=70)
    venue = Venue.objects.create(name="Arena", city="Prague", country="CZ")
    event = Event.objects.create(
        slug="e1",
        organization=org,
        name="Event 1",
        date_start=timezone.now(),
        venue=venue,
    )
    f1 = Fighter.objects.create(
        slug="f1", first_name="John", last_name="Doe", country="USA"
    )
    f2 = Fighter.objects.create(
        slug="f2", first_name="Max", last_name="Must", country="DE"
    )
    Bout.objects.create(
        event=event,
        weight_class=weight,
        fighter_red=f1,
        fighter_blue=f2,
    )
    Ranking.objects.create(
        organization=org,
        weight_class=weight,
        position=1,
        fighter=f1,
        date_effective=timezone.now().date(),
    )

    assert client.get("/mma/organizations/").status_code == 200
    assert client.get(f"/mma/organizations/{org.slug}/").status_code == 200
    assert client.get("/mma/events/").status_code == 200
    assert client.get(f"/mma/events/{event.slug}/").status_code == 200
    assert client.get("/mma/fighters/").status_code == 200
    assert client.get(f"/mma/fighters/{f1.slug}/").status_code == 200
    assert client.get("/mma/rankings/").status_code == 200
    assert client.get(f"/mma/rankings/{org.slug}/{weight.slug}/").status_code == 200


def test_admin_buttons_show(client, db, django_user_model):
    user = django_user_model.objects.create_user("admin", password="pw", is_staff=True)
    client.force_login(user)
    session = client.session
    session["admin_mode"] = True
    session.save()

    Organization.objects.create(slug="org", name="Org", short_name="ORG")

    resp = client.get("/mma/organizations/")
    content = resp.content.decode()
    assert "Add Organization" in content


def test_organization_add_form_renders(client, db, django_user_model):
    user = django_user_model.objects.create_user("admin", password="pw", is_staff=True)
    client.force_login(user)
    session = client.session
    session["admin_mode"] = True
    session.save()

    resp = client.get("/mma/organizations/add/")
    assert resp.status_code == 200
    assert "Add Organization" in resp.content.decode()
