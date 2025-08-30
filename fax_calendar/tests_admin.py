import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model

from msa.models import Season


@pytest.fixture
def admin_client(db):
    User = get_user_model()
    user = User.objects.create_superuser("admin", "admin@example.com", "pass")
    client = Client()
    client.force_login(user)
    return client


def test_admin_widget_and_validation(admin_client):
    url = reverse("admin:msa_season_add")
    resp = admin_client.get(url)
    html = resp.content.decode()
    assert "fax_calendar/admin_calendar.js" in html
    assert 'data-woorld-date="1"' in html
    assert "woorld-calendar-btn" in html

    invalid = {
        "name": "S1",
        "code": "s1",
        "start_date": "49-01-0297",
        "end_date": "49-01-0297",
        "_save": "Save",
    }
    resp_bad = admin_client.post(url, invalid)
    assert "Month 1 has 48 days in year 297" in resp_bad.content.decode()
    assert Season.objects.count() == 0

    valid = {**invalid, "start_date": "48-01-0297", "end_date": "48-01-0297"}
    admin_client.post(url, valid)
    assert Season.objects.count() == 1
