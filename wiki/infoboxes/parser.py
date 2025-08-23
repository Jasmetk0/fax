import hashlib
import json
import logging
import os
import re
from typing import Dict, List

import bleach
from django.conf import settings
from django.core.cache import cache
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

INFOBOX_RE = re.compile(r"\{\{Infobox\s+([A-Za-z0-9._-]+)(.*?)\}\}", re.DOTALL)
SCHEMA_CACHE: Dict[str, List[Dict[str, str]] | None] = {}


def _normalize_key(key: str) -> str:
    return re.sub(r"\s+", "_", key.strip().lower())


def parse_params(raw: str) -> Dict[str, str]:
    params: Dict[str, str] = {}
    key: List[str] | None = None
    val: List[str] = []
    quote: str | None = None
    i = 0
    while i < len(raw):
        ch = raw[i]
        if key is None:
            if ch == "|":
                key = []
                val = []
            i += 1
            continue
        if quote:
            if ch == quote:
                quote = None
            else:
                val.append(ch)
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            i += 1
            continue
        if ch == "=" and not val:
            key_str = _normalize_key("".join(key))
            key = key_str  # type: ignore[assignment]
            i += 1
            continue
        if ch == "|":
            if isinstance(key, str):
                params[key] = "".join(val).strip()
            key = []
            val = []
            i += 1
            continue
        if isinstance(key, list):
            key.append(ch)
        else:
            val.append(ch)
        i += 1
    if isinstance(key, str):
        params[key] = "".join(val).strip()
    return params


def load_schema(ibox_type: str) -> List[Dict[str, str]] | None:
    if ibox_type not in SCHEMA_CACHE:
        path = os.path.join(settings.BASE_DIR, "infoboxes", f"{ibox_type}.schema.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                SCHEMA_CACHE[ibox_type] = json.load(fh)
        except FileNotFoundError:
            logger.debug("Schema not found for %s", ibox_type)
            SCHEMA_CACHE[ibox_type] = None
    return SCHEMA_CACHE[ibox_type]


ALLOWED_TAGS = [
    "div",
    "h2",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "img",
    "a",
    "caption",
]
ALLOWED_ATTRS = {
    "img": ["src", "alt", "title", "loading", "width", "height"],
    "a": ["href", "title", "rel", "target"],
    "div": ["class"],
    "table": ["class"],
    "th": ["class"],
    "td": ["class"],
}


def _sanitize_params(params: Dict[str, str]) -> Dict[str, str]:
    return {
        k: bleach.clean(v, tags=[], attributes={}, strip=True)
        for k, v in params.items()
    }


def _validate_params(
    params: Dict[str, str], schema: List[Dict[str, str]] | None
) -> List[str]:
    if not schema:
        return []
    schema_map = {item["name"]: item for item in schema}
    warnings: List[str] = []
    for key, value in params.items():
        if key not in schema_map:
            warnings.append(f"Unknown parameter: {key}")
            continue
        expected = schema_map[key].get("type")
        if expected == "number":
            try:
                float(value)
            except ValueError:
                warnings.append(f"Parameter {key} expects number")
    return warnings


def render_infobox(
    ibox_type: str,
    params: Dict[str, str],
    schema: List[Dict[str, str]] | None,
    page_title: str,
) -> str:
    template = f"infoboxes/{ibox_type}.html"
    cache_key = (
        "infobox:"
        + hashlib.md5(
            (template + json.dumps(params, sort_keys=True)).encode()
        ).hexdigest()
    )
    cached = cache.get(cache_key)
    if cached:
        return cached
    context = {
        **params,
        "page_title": page_title,
        "schema": schema or [],
    }
    if schema:
        rows = [
            {
                "title": item["title"],
                "value": params.get(item["name"], ""),
            }
            for item in schema
            if item["name"]
            not in {"name", "flag", "coat_of_arms", "map", "image", "caption"}
        ]
        context["rows"] = rows
    try:
        html = render_to_string(template, context)
    except TemplateDoesNotExist:
        if settings.DEBUG:
            return f'<div class="infobox infobox--missing">Missing template: {ibox_type}</div>'
        return ""
    html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
    cache.set(cache_key, html)
    return html


def process(text: str, page_title: str) -> str:
    def repl(match: re.Match) -> str:
        ibox_type = match.group(1)
        body = match.group(2)
        params = parse_params(body)
        schema = load_schema(ibox_type)
        if not params and schema:
            params = {item["name"]: "" for item in schema}
        warnings = _validate_params(params, schema)
        params = _sanitize_params(params)
        html = render_infobox(ibox_type, params, schema, page_title)
        if warnings and settings.DEBUG:
            warn_html = (
                '<div class="infobox-warning">'
                + "<br>".join(bleach.clean(w, tags=[], attributes={}) for w in warnings)
                + "</div>"
            )
            html += warn_html
        return html

    return INFOBOX_RE.sub(repl, text)
