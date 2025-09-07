from unittest.mock import patch

from django.template.loader import render_to_string as django_render_to_string
from django.test import override_settings

from wiki.infoboxes import parser


def render(md: str) -> str:
    return parser.process(md, page_title="Page")


def test_parse_quotes_and_pipes():
    raw = "| name = 'New | York' | note=\"multi\nline\""
    params = parser.parse_params(raw)
    assert params["name"] == "New | York"
    assert params["note"] == "multi\nline"


def test_normalize_keys():
    raw = "| Native Name = Praha"
    params = parser.parse_params(raw)
    assert "native_name" in params


@override_settings(DEBUG=True)
def test_unknown_param_warning():
    html = render("{{Infobox city | unknown=val }}")
    assert "Unknown parameter" in html


def test_stub_renders():
    html = render("{{Infobox country}}")
    assert "infobox--country" in html


def test_empty_values_hidden():
    html = render("{{Infobox city | name=Test | population= }}")
    assert "Population" not in html


def test_sanitization():
    html = render("{{Infobox city | name=<script>alert(1)</script> }}")
    assert "<script>" not in html and "alert(1)" in html


def test_cache_usage():
    md = "{{Infobox city | name=Prague }}"
    with patch("wiki.infoboxes.parser.render_to_string", wraps=django_render_to_string) as r:
        render(md)
        render(md)
        assert r.call_count == 1
