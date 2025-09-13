import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_active_date_from_session_woorld_string():
    c = Client()
    s = c.session
    s["woorld_today"] = "01.05.2024"
    s.save()
    r = c.get("/msa/tournaments", follow=True)
    assert r.status_code in (200, 302)


def test_active_date_from_cookie_woorld_string():
    c = Client()
    c.cookies["woorld_date"] = "2024.05.01"
    r = c.get("/msa/calendar", follow=True)
    assert r.status_code in (200, 302)


def test_active_date_from_session_woorld_dict_like():
    c = Client()
    s = c.session
    s["woorld_today"] = {"year": 2024, "month": 5, "day": 1}
    s.save()
    r = c.get("/msa/tournaments", follow=True)
    assert r.status_code in (200, 302)
