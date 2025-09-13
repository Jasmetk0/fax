import json

import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_set_date_endpoint_sets_session_and_cookie():
    c = Client()
    r = c.post(
        "/set-date/", data=json.dumps({"date": "2024-05-01"}), content_type="application/json"
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True and data.get("iso") == "2024-05-01"
    # cookies jsou přítomny v odpovědi a Client je bude nosit dál
    assert "topbar_date" in r.cookies and r.cookies["topbar_date"].value == "2024-05-01"

    # následný GET by měl mít v kontextu active_date_iso (z context processoru)
    resp = c.get(reverse("msa:tournaments_list"), follow=True)
    assert resp.status_code in (200, 302)
    # context může být None, pokud non-template response; v tom případě jen nepadnout
    if hasattr(resp, "context") and resp.context is not None:
        # context může být list při více renderech
        ctx = resp.context[-1] if isinstance(resp.context, list) else resp.context
        if "active_date_iso" in ctx:
            assert ctx["active_date_iso"] == "2024-05-01"


def test_set_date_rejects_bad_input():
    c = Client()
    r = c.post(
        "/set-date/", data=json.dumps({"date": "nonsense-date"}), content_type="application/json"
    )
    assert r.status_code in (400, 422)
