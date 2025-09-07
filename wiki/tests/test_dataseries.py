from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.urls import reverse

from wiki.models_data import DataPoint, DataSeries
from wiki.utils_data import replace_data_shortcodes


@pytest.mark.django_db
def test_datapoint_unique_and_ordering():
    series = DataSeries.objects.create(slug="s1")
    DataPoint.objects.create(series=series, key="2020", value=1)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DataPoint.objects.create(series=series, key="2020", value=2)
    DataPoint.objects.create(series=series, key="2019", value=3)
    assert list(series.points.values_list("key", flat=True)) == ["2019", "2020"]


@pytest.mark.django_db
def test_api_endpoints(client):
    series = DataSeries.objects.create(slug="pop", title="Population", unit="people")
    DataPoint.objects.create(series=series, key="1990", value=1)
    DataPoint.objects.create(series=series, key="1991", value=2)

    resp = client.get("/api/dataseries/")
    assert resp.status_code == 200
    assert resp.json()[0]["slug"] == "pop"

    resp = client.get("/api/dataseries/pop/")
    assert resp.status_code == 200
    assert len(resp.json()["points"]) == 2

    resp = client.get("/api/dataseries/pop/point/1990/")
    assert resp.status_code == 200
    assert resp.json()["value"] == "1.0000"

    resp = client.get("/api/dataseries/missing/")
    assert resp.status_code == 404

    resp = client.post("/api/dataseries/", {"slug": "x"})
    assert resp.status_code == 403

    User = get_user_model()
    staff = User.objects.create_user("admin", password="x", is_staff=True)
    client.force_login(staff)
    resp = client.post("/api/dataseries/", {"slug": "x"}, content_type="application/json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_replace_data_shortcodes_formats_and_cache():
    cache.clear()
    series = DataSeries.objects.create(slug="pop", unit="people")
    DataPoint.objects.create(series=series, key="1990", value=Decimal("1234"))
    DataPoint.objects.create(series=series, key="1991", value=Decimal("1234000"))

    html = replace_data_shortcodes("{{data:pop|1990}}")
    assert "1234 people" in html

    html = replace_data_shortcodes("{{data:pop|1992|default=—}}")
    assert "—" in html

    cache.clear()
    html = replace_data_shortcodes("{{data:pop|1990|fmt=comma}}")
    assert "1 234" in html

    html = replace_data_shortcodes("{{data:pop|1991|fmt=si}}")
    assert "1.23M" in html

    html = replace_data_shortcodes("{{data:pop|agg=latest}}")
    assert "1234000" in html

    DataPoint.objects.create(series=series, key="1992", value=3)
    cache.clear()
    html = replace_data_shortcodes("{{data:pop|agg=latest}}")
    assert "3 people" in html

    html = replace_data_shortcodes("{{data:pop|agg=min:1990-1992}}")
    assert html.startswith("3")

    html = replace_data_shortcodes("{{data:pop|agg=max:1990-1992}}")
    assert html.startswith("1234000")

    html = replace_data_shortcodes("{{data:pop|agg=sum:1990-1992}}")
    assert html.startswith("1235237")

    cache.clear()
    html1 = replace_data_shortcodes("{{data:pop|1990}}")
    series.points.filter(key="1990").delete()
    html2 = replace_data_shortcodes("{{data:pop|1990}}")
    assert html1 == html2


@pytest.mark.django_db
def test_management_command(tmp_path):
    csv_content = "key;value\n1990;1\n1991;2\n"
    file_path = tmp_path / "data.csv"
    file_path.write_text(csv_content, encoding="utf-8")
    call_command(
        "import_dataseries",
        slug="pop",
        unit="people",
        title="Population",
        file=file_path,
    )
    series = DataSeries.objects.get(slug="pop")
    assert series.points.count() == 2
    call_command(
        "import_dataseries",
        slug="pop",
        unit="people",
        title="Population",
        file=file_path,
    )
    assert series.points.count() == 2


@pytest.mark.django_db
def test_dataseries_list_and_detail_access(client, django_user_model):
    series = DataSeries.objects.create(slug="pop", title="Population")
    DataPoint.objects.create(series=series, key="2020", value=Decimal("1"))
    list_url = reverse("wiki:dataseries-list")
    detail_url = reverse("wiki:dataseries-detail", args=["pop"])

    # Anonymous user can view list and detail but not see admin controls
    resp = client.get(list_url)
    assert resp.status_code == 200
    assert "Population" in resp.text
    assert "Create series" not in resp.text
    resp = client.get(detail_url)
    assert resp.status_code == 200
    assert "2020" in resp.text
    assert "Edit" not in resp.text

    # Staff with admin mode sees controls
    User = django_user_model
    staff = User.objects.create_user("admin", password="pw", is_staff=True)
    client.force_login(staff)
    session = client.session
    session["admin_mode"] = True
    session.save()

    resp = client.get(list_url)
    assert "Create series" in resp.text
    resp = client.get(detail_url)
    assert reverse("wiki:dataseries-edit", args=["pop"]) in resp.text


@pytest.mark.django_db
def test_dataseries_create_requires_admin_mode(client, django_user_model):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    client.force_login(user)
    url = reverse("wiki:dataseries-create")
    resp = client.get(url)
    assert resp.status_code == 302
    session = client.session
    session["admin_mode"] = True
    session.save()
    assert client.get(url).status_code == 200
