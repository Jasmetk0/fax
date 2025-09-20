import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

pytestmark = pytest.mark.django_db

pytest_plugins = ["msa.tests.test_readonly_pages"]


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


def test_tournament_overview_has_section_controls(client, sample_tournament):
    user_model = get_user_model()
    staff = user_model.objects.create_user("overview-staff", "overview@example.com", "x")
    staff.is_staff = True
    staff.save()
    client.force_login(staff)
    _set_admin_mode(client, True)

    url = reverse("msa:tournament_info", args=[sample_tournament.id])
    response = client.get(url)
    assert response.status_code == 200

    html = response.content.decode()
    assert 'data-admin-section="info-summary"' in html
    assert 'data-admin-action="edit-scoring"' in html
    assert 'data-admin-mode="true"' in html


@override_settings(MSA_ADMIN_READONLY=True)
def test_admin_controls_remain_disabled_in_readonly_mode(client, sample_tournament):
    user_model = get_user_model()
    staff = user_model.objects.create_user("readonly-staff", "readonly@example.com", "x")
    staff.is_staff = True
    staff.save()
    client.force_login(staff)
    _set_admin_mode(client, True)

    urls = [
        reverse("msa:tournament_info", args=[sample_tournament.id]),
        reverse("msa:tournament_players", args=[sample_tournament.id]),
        reverse("msa:tournament_draws", args=[sample_tournament.id]),
    ]

    for url in urls:
        response = client.get(url)
        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-admin-readonly="true"' in html
        assert 'data-admin-enhance="fetch"' not in html
        assert 'aria-disabled="true"' in html


def test_admin_action_endpoint_guards(client):
    url = reverse("msa:admin_action")

    response = client.post(url, {"action": "noop"})
    assert response.status_code == 403
    assert response.json()["ok"] is False

    User = get_user_model()
    user = User.objects.create_user("guard", "guard@example.com", "x")
    client.force_login(user)

    response = client.post(url, {"action": "noop"})
    assert response.status_code == 403

    user.is_staff = True
    user.save()
    response = client.post(url, {"action": "noop"})
    assert response.status_code == 403

    _set_admin_mode(client, True)
    with override_settings(MSA_ADMIN_READONLY=True):
        response = client.post(url, {"action": "noop"})
    assert response.status_code == 403
    data = response.json()
    assert data["ok"] is False
    assert "error" in data


@override_settings(MSA_ADMIN_READONLY=False)
def test_admin_action_accepts_post_when_enabled(client, sample_tournament):
    user_model = get_user_model()
    staff = user_model.objects.create_user("action-staff", "action@example.com", "x")
    staff.is_staff = True
    staff.save()
    client.force_login(staff)
    _set_admin_mode(client, True)

    url = reverse("msa:admin_action")
    response = client.post(url, {"action": "reseed", "tournament_id": sample_tournament.id})
    assert response.status_code == 202
    data = response.json()
    assert data["ok"] is True
    assert data["action"] == "reseed"
    assert data["context"].get("tournament_id") == str(sample_tournament.id)
    assert "accepted" in data["message"]
    assert "csrfmiddlewaretoken" not in data["context"]
