import pytest
from django.core.exceptions import ValidationError

from fax_calendar.utils import parse_woorld_date


def test_parse_none():
    assert parse_woorld_date(None) == (None, None, None)


def test_parse_empty_string():
    assert parse_woorld_date("") == (None, None, None)


def test_parse_iso_format():
    assert parse_woorld_date("2025-09-01") == (2025, 9, 1)


def test_parse_dd_mm_yyyy():
    assert parse_woorld_date("01-09-2025") == (2025, 9, 1)


def test_parse_with_dots_rejected():
    with pytest.raises(ValidationError):
        parse_woorld_date("01.09.2025")


def test_parse_bytes():
    assert parse_woorld_date(b"2025-09-01") == (2025, 9, 1)


def test_invalid_input_raises_validation_error():
    with pytest.raises(ValidationError) as excinfo:
        parse_woorld_date("32-13-2025")
    assert "Datum musí být ve formátu DD-MM-YYYY nebo YYYY-MM-DD" in str(excinfo.value)
