from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from wiki.models_data import DataCategory, DataPoint, DataSeries
from wiki.utils_data import replace_data_shortcodes


@pytest.mark.django_db
def test_category_api_and_table_shortcode(client):
    cache.clear()
    cat = DataCategory.objects.create(slug="country-population")
    francica = DataSeries.objects.create(
        slug="country-population/francica", title="Francica", unit="people"
    )
    italora = DataSeries.objects.create(
        slug="country-population/italora", title="Italora", unit="people"
    )
    francica.categories.add(cat)
    italora.categories.add(cat)
    DataPoint.objects.create(series=francica, key="2020", value=Decimal("5"))
    DataPoint.objects.create(series=italora, key="2020", value=Decimal("10"))

    resp = client.get(
        "/api/dataseries/category/country-population/?year=2020&ordering=-value_for_year&limit=1"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["slug"] == "country-population/italora"
    assert data["by_slug"]["country-population/italora"] == "10.0000"

    html = replace_data_shortcodes(
        "{{table:country-population|year=2020|sort=value|desc=1}}"
    )
    assert "<table" in html
    assert html.index("Italora") < html.index("Francica")

    html_map = replace_data_shortcodes("{{map:country-population|year=2020}}")
    assert '<div class="ds-map"' in html_map


@pytest.mark.django_db
def test_data_shortcode_backward_compatibility():
    series = DataSeries.objects.create(slug="francica-population", unit="people")
    DataPoint.objects.create(series=series, key="2020", value=Decimal("7"))
    html = replace_data_shortcodes("{{data:francica-population|2020}}")
    assert "7 people" in html


@pytest.mark.django_db
def test_dataseries_crud_views(client):
    User = get_user_model()
    staff = User.objects.create_user("admin", password="x", is_staff=True)
    client.force_login(staff)
    session = client.session
    session["admin_mode"] = True
    session.save()

    cat = DataCategory.objects.create(slug="country-population")

    resp = client.post(
        "/wiki/dataseries/create/",
        {
            "slug": "francica-population",
            "title": "Francica",
            "unit": "people",
            "description": "",
            "categories": [str(cat.id)],
            "points-TOTAL_FORMS": "1",
            "points-INITIAL_FORMS": "0",
            "points-MIN_NUM_FORMS": "0",
            "points-MAX_NUM_FORMS": "1000",
            "points-0-key": "2020",
            "points-0-value": "5",
            "points-0-note": "",
        },
    )
    assert resp.status_code == 302
    ds = DataSeries.objects.get(slug="francica-population")
    assert ds.points.filter(key="2020").exists()
    assert ds.categories.filter(slug="country-population").exists()

    resp = client.post(
        f"/wiki/dataseries/{ds.slug}/edit/",
        {
            "slug": ds.slug,
            "title": "Francica",
            "unit": "people",
            "description": "",
            "categories": [str(cat.id)],
            "points-TOTAL_FORMS": "1",
            "points-INITIAL_FORMS": "1",
            "points-MIN_NUM_FORMS": "0",
            "points-MAX_NUM_FORMS": "1000",
            "points-0-id": str(ds.points.get(key="2020").id),
            "points-0-key": "2020",
            "points-0-value": "6",
            "points-0-note": "",
        },
    )
    assert resp.status_code == 302
    ds.refresh_from_db()
    assert ds.points.get(key="2020").value == Decimal("6")

    resp = client.post(f"/wiki/dataseries/{ds.slug}/delete/")
    assert resp.status_code == 302
    assert not DataSeries.objects.filter(slug=ds.slug).exists()


@pytest.mark.django_db
def test_category_visible_on_pages(client):
    cat = DataCategory.objects.create(slug="country-population")
    ds = DataSeries.objects.create(slug="country-population/francica", title="Francica")
    ds.categories.add(cat)
    resp = client.get("/wiki/dataseries/")
    html = resp.content.decode()
    assert "categories: country-population" in html
    resp = client.get(f"/wiki/dataseries/{ds.slug}/")
    detail_html = resp.content.decode()
    assert "Categories:" in detail_html
    assert "country-population" in detail_html
