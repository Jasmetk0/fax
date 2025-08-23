import pytest

from .utils import parse_woorld_ddmmyyyy, format_woorld_ddmmyyyy
from .fields import WoorldDateFormField


def test_parse_and_format_roundtrip():
    y, m, d = parse_woorld_ddmmyyyy("05/02/2030")
    assert (y, m, d) == (2030, 2, 5)
    assert format_woorld_ddmmyyyy(y, m, d) == "05/02/2030"


def test_formfield_clean_and_prepare():
    field = WoorldDateFormField()
    stored = field.clean("07/01/2035")
    assert stored == "2035-01-07w"
    assert field.prepare_value(stored) == "07/01/2035"


def test_invalid_day():
    field = WoorldDateFormField()
    with pytest.raises(Exception):
        field.clean("29/02/2000")
