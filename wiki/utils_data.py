"""Utilities for working with wiki data series."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from django.core.cache import cache
from django.db.models import Sum

from .models_data import DataPoint, DataSeries

CACHE_TTL = 30  # seconds


@dataclass
class ShortcodeParams:
    fmt: Optional[str] = None
    unit: Optional[str] = None
    default: str = ""
    agg: Optional[str] = None


def format_number(value: Decimal, fmt: Optional[str]) -> str:
    """Format numeric value according to ``fmt`` parameter."""

    if fmt == "comma":
        formatted = f"{value:,}"
        return formatted.replace(",", "\xa0")
    if fmt == "si":
        num = float(value)
        for factor, suffix in [
            (1_000_000_000_000, "T"),
            (1_000_000_000, "G"),
            (1_000_000, "M"),
            (1_000, "k"),
        ]:
            if abs(num) >= factor:
                return f"{num / factor:.2f}{suffix}".rstrip("0").rstrip(".")
        return f"{num}"
    return str(value).rstrip("0").rstrip(".")


def _parse_params(parts: Iterable[str]) -> Tuple[Optional[str], ShortcodeParams]:
    key = None
    params: Dict[str, str] = {}
    for part in parts:
        if "=" in part:
            k, v = part.split("=", 1)
            params[k] = v
        elif key is None:
            key = part
    sp = ShortcodeParams(
        fmt=params.get("fmt"),
        unit=params.get("unit"),
        default=params.get("default", ""),
        agg=params.get("agg"),
    )
    return key, sp


def _agg_query(series: DataSeries, agg: str) -> Optional[Decimal]:
    """Aggregate values based on ``agg`` expression."""

    range_part = None
    if ":" in agg:
        agg, range_part = agg.split(":", 1)
    qs = series.points.all()
    if range_part:
        start, end = range_part.split("-")
        qs = qs.filter(key__gte=start, key__lte=end)
    if agg == "latest":
        point = qs.order_by("-key").first()
        return point.value if point else None
    if agg == "min":
        point = qs.order_by("value").first()
        return point.value if point else None
    if agg == "max":
        point = qs.order_by("-value").first()
        return point.value if point else None
    if agg == "sum":
        return qs.aggregate(Sum("value"))["value__sum"]
    return None


def parse_series_slug(slug: str) -> Tuple[str, str, str]:
    """Split slug into ``(category, sub_category, entity)``."""

    parts = slug.split("/")
    category = parts[0] if parts else ""
    sub = parts[1] if len(parts) > 1 else ""
    entity = "/".join(parts[2:]) if len(parts) > 2 else ""
    return category, sub, entity


def get_series_by_category(category: str, sub_category: Optional[str] = None):
    """Return a queryset of series in ``category`` and optional ``sub_category``."""

    qs = DataSeries.objects.filter(category=category)
    if sub_category is not None:
        qs = qs.filter(sub_category=sub_category)
    return qs


def get_value_for_year(series: DataSeries, year: str) -> Optional[Decimal]:
    """Return value for ``year`` or ``None``."""

    try:
        return series.points.get(key=year).value
    except DataPoint.DoesNotExist:
        return None


def replace_data_shortcodes(html: str) -> str:
    """Replace data-related shortcodes in HTML.

    Supports ``{{data:...}}``, ``{{chart:...}}``, ``{{table:...}}`` and
    ``{{map:...}}``.
    """

    def repl(match: re.Match[str]) -> str:
        slug = match.group("slug")
        rest = match.group("rest") or ""
        parts = [p for p in rest.split("|") if p]
        key, params = _parse_params(parts)
        cache_key = f"ds:{slug}:{key}:{params.agg}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            series = DataSeries.objects.get(slug=slug)
        except DataSeries.DoesNotExist:
            cache.set(cache_key, params.default, CACHE_TTL)
            return params.default
        value: Optional[Decimal]
        if params.agg:
            value = _agg_query(series, params.agg)
        else:
            if key is None:
                cache.set(cache_key, params.default, CACHE_TTL)
                return params.default
            try:
                point = series.points.get(key=key)
                value = point.value
            except DataPoint.DoesNotExist:
                value = None
        if value is None:
            cache.set(cache_key, params.default, CACHE_TTL)
            return params.default
        formatted = format_number(value, params.fmt)
        unit = params.unit or series.unit
        text = f"{formatted} {unit}".strip()
        cache.set(cache_key, text, CACHE_TTL)
        return text

    data_pattern = re.compile(r"\{\{data:(?P<slug>[^|}]+)(?:\|(?P<rest>[^}]+))?\}\}")
    html = data_pattern.sub(repl, html)

    def repl_chart(match: re.Match[str]) -> str:
        slug = match.group("slug")
        rest = match.group("rest") or ""
        params = dict(part.split("=", 1) for part in rest.split("|") if "=" in part)
        chart_type = params.get("type", "line")
        data_from = params.get("from", "")
        data_to = params.get("to", "")
        height = params.get("height", "200")
        return (
            f'<div class="ds-chart" data-series="{slug}" data-type="{chart_type}" '
            f'data-from="{data_from}" data-to="{data_to}" '
            f'data-height="{height}"></div>'
        )

    chart_pattern = re.compile(r"\{\{chart:(?P<slug>[^|}]+)(?:\|(?P<rest>[^}]+))?\}\}")
    html = chart_pattern.sub(repl_chart, html)

    def repl_table(match: re.Match[str]) -> str:
        cat_slug = match.group("slug")
        rest = match.group("rest") or ""
        params = dict(part.split("=", 1) for part in rest.split("|") if "=" in part)
        year = params.get("year")
        if not year:
            return ""
        sort = params.get("sort", "value")
        desc = params.get("desc", "0") == "1"
        limit = int(params.get("limit", "0") or 0) or None
        fmt = params.get("fmt")
        unit = params.get("unit") == "1"
        empty = params.get("empty", "—")
        category, sub, _ = parse_series_slug(cat_slug)
        cache_key = f"ds-table:{category}:{sub}:{year}:{sort}:{desc}:{limit}:{fmt}:{unit}:{empty}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        rows: List[Dict[str, object]] = []
        for series in get_series_by_category(category, sub or None):
            value = get_value_for_year(series, year)
            if value is None:
                display = empty
                value_sort: Optional[Decimal] = None
            else:
                display = format_number(value, fmt)
                if unit and series.unit:
                    display = f"{display} {series.unit}"
                value_sort = value
            rows.append(
                {
                    "title": series.title or series.slug,
                    "slug": series.slug,
                    "display": display,
                    "value_sort": value_sort,
                }
            )
        if sort == "title":
            rows.sort(key=lambda r: str(r["title"]))
        elif sort == "slug":
            rows.sort(key=lambda r: str(r["slug"]))
        else:
            rows.sort(key=lambda r: (r["value_sort"] is None, r["value_sort"]))
        if desc:
            rows.reverse()
        if limit:
            rows = rows[:limit]
        body = "".join(
            f"<tr><td>{r['title']}</td><td>{r['display']}</td></tr>" for r in rows
        )
        html_table = (
            f'<table class="ds-table"><thead><tr><th>Název</th>'
            f"<th>Hodnota ({year})</th></tr></thead>"
            f"<tbody>{body}</tbody></table>"
        )
        cache.set(cache_key, html_table, CACHE_TTL)
        return html_table

    table_pattern = re.compile(r"\{\{table:(?P<slug>[^|}]+)(?:\|(?P<rest>[^}]+))?\}\}")
    html = table_pattern.sub(repl_table, html)

    def repl_map(match: re.Match[str]) -> str:
        category = match.group("slug")
        rest = match.group("rest") or ""
        params = dict(part.split("=", 1) for part in rest.split("|") if "=" in part)
        year = params.get("year", "")
        palette = params.get("palette", "Blues")
        legend = params.get("legend", "0")
        height = params.get("height", "360")
        return (
            f'<div class="ds-map" data-category="{category}" data-year="{year}" '
            f'data-palette="{palette}" data-legend="{legend}" '
            f'style="height:{height}px"></div>'
        )

    map_pattern = re.compile(r"\{\{map:(?P<slug>[^|}]+)(?:\|(?P<rest>[^}]+))?\}\}")
    return map_pattern.sub(repl_map, html)


def import_csv_to_series(
    series: DataSeries, file_obj: io.TextIOBase
) -> Tuple[int, int]:
    """Import CSV data into ``series``.

    Returns a tuple ``(created, updated)``.
    """

    reader = csv.reader(file_obj, delimiter=";")
    created = updated = 0
    for row in reader:
        if not row or row[0].startswith("#"):
            continue
        if row[0].lower() == "key":  # header
            continue
        key, value = row[0], row[1]
        dp, was_created = DataPoint.objects.update_or_create(
            series=series, key=key, defaults={"value": Decimal(value)}
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated
