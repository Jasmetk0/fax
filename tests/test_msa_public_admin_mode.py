import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


def _set_admin_mode(client, on=True):
    session = client.session
    session["admin_mode"] = bool(on)
    session.save()


def test_players_public(client):
    url = reverse("msa:players_list")
    r = client.get(url)
    assert r.status_code in (200, 302)


def test_admin_controls_visible_only_in_admin_mode(client):
    url = reverse("msa:players_list")
    r = client.get(url)
    assert r.status_code == 200
    assert b'id="msa-topbar"' in r.content
    assert b"data-admin-controls" not in r.content

    User = get_user_model()
    u = User.objects.create_user("staff", "s@example.com", "x")
    u.is_staff = True
    u.save()
    client.force_login(u)
    _set_admin_mode(client, True)
    r = client.get(url)
    assert r.status_code == 200
    assert b'id="msa-topbar"' in r.content
    assert b"data-admin-controls" not in r.content
