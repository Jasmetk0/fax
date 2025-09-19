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

    _set_admin_mode(client, False)
    r = client.get(url)
    assert r.status_code == 200
    assert b"data-admin-controls" not in r.content

    _set_admin_mode(client, True)
    r = client.get(url)
    assert r.status_code == 200
    assert b'id="msa-topbar"' in r.content
    assert b'data-admin-controls="true"' in r.content


def test_admin_toolbar_actions_render_for_tournaments_list(client):
    url = reverse("msa:tournaments_list")

    User = get_user_model()
    user = User.objects.create_user("staff2", "staff2@example.com", "x")
    user.is_staff = True
    user.save()
    client.force_login(user)
    _set_admin_mode(client, True)

    response = client.get(url)
    assert response.status_code == 200

    html = response.content.decode()
    assert 'data-admin-controls="true"' in html
    for action in ("new-tournament", "bulk-ops", "export-calendar"):
        assert f'data-admin-action="{action}"' in html
