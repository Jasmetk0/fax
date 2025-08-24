from __future__ import annotations

from decimal import Decimal

import pytest
from django.apps import apps as global_apps
from django.core.cache import cache
from django.db import connection

from wiki.models_data import DataPoint, DataSeries
from wiki.utils_data import replace_data_shortcodes

import importlib

migration = importlib.import_module("wiki.migrations.0005_dataseries_category")
populate_categories = migration.populate_categories


@pytest.mark.django_db
def test_migration_populates_category_subcategory():
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO wiki_dataseries(slug, title, unit, description, category, sub_category, created_at) "
            "VALUES (%s, '', '', '', '', '', CURRENT_TIMESTAMP)",
            ["country-population/francica"],
        )
    populate_categories(global_apps, None)
    ds = DataSeries.objects.get(slug="country-population/francica")
    assert ds.category == "country-population"
    assert ds.sub_category == "francica"


@pytest.mark.django_db
def test_category_api_and_table_shortcode(client):
    cache.clear()
    francica = DataSeries.objects.create(
        slug="country-population/francica", title="Francica", unit="people"
    )
    italora = DataSeries.objects.create(
        slug="country-population/italora", title="Italora", unit="people"
    )
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
def test_category_sub_api(client):
    country = DataSeries.objects.create(
        slug="city-population/francica/parisca", title="Parisca", unit="people"
    )
    DataPoint.objects.create(series=country, key="2020", value=Decimal("3"))
    resp = client.get("/api/dataseries/category/city-population/francica/")
    assert resp.status_code == 200
    assert resp.json()["results"][0]["slug"] == "city-population/francica/parisca"


@pytest.mark.django_db
def test_data_shortcode_backward_compatibility():
    series = DataSeries.objects.create(slug="francica-population", unit="people")
    DataPoint.objects.create(series=series, key="2020", value=Decimal("7"))
    html = replace_data_shortcodes("{{data:francica-population|2020}}")
    assert "7 people" in html
