"""Utilities for working with wiki data series."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, Optional, Tuple

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


def _format_value(value: Decimal, fmt: Optional[str]) -> str:
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


def replace_data_shortcodes(html: str) -> str:
    """Replace ``{{data:...}}`` and ``{{chart:...}}`` shortcodes in HTML."""

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
        formatted = _format_value(value, params.fmt)
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
    return chart_pattern.sub(repl_chart, html)


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
