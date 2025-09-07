from datetime import date

import pytest

from . import core
from .fields import WoorldDateFormField
from .utils import (
    format_woorld_date,
    from_storage,
    parse_woorld_date,
    to_storage,
)


def test_year_297_month1_has_48():
    lengths = core.month_lengths(297)
    assert lengths[0] == 48
    assert core.year_length(297) == 428 + (48 - 29)


def test_triple_P_after_v2():
    assert core.leap_base(302)
    assert core.leap_base(303)
    assert core.leap_base(304)


def test_weekday_pivots():
    assert core.weekday(1, 1, 1) == 0
    assert core.weekday(400, 1, 1) == 1
    assert core.weekday(2000, 1, 1) == 6


def test_proto_v3_years_add_one():
    for y in {689, 1067, 1433, 1657}:
        base = 30 if y % 2 == 0 else 29
        assert core.month1_length(y) == base + 1


def test_anchors_and_seasons():
    y = 304
    a = core.anchors(y)
    assert a["solstice_w"] == core.year_length(y)
    assert core.season_of(y, a["vernal"] - 1) == "Winter I"
    assert core.season_of(y, a["vernal"]) == "Spring"
    assert core.season_of(y, a["solstice_s"]) == "Summer"
    assert core.season_of(y, a["autumnal"]) == "Autumn"
    assert core.season_of(y, a["solstice_w"]) == "Winter II"


def test_parse_and_format():
    y, m, d = parse_woorld_date("05-02-2030")
    assert (y, m, d) == (2030, 2, 5)
    assert parse_woorld_date("05.02.2030") == (2030, 2, 5)
    stored = to_storage(y, m, d)
    assert stored == "2030-02-05"
    assert from_storage(stored) == (2030, 2, 5)
    assert from_storage(stored + "w") == (2030, 2, 5)
    assert format_woorld_date(y, m, d) == "05-02-2030"


def test_formfield_clean_and_prepare():
    field = WoorldDateFormField()
    stored = field.clean("07-01-2035")
    assert stored == date(2035, 1, 7)
    assert field.prepare_value("2035-01-07w") == "07-01-2035"


def test_invalid_day():
    field = WoorldDateFormField()
    with pytest.raises(Exception):
        field.clean("29-02-2000")


def test_month_lengths_sums_to_year_length():
    for y in list(range(296, 305)) + list(range(688, 691)):
        assert sum(core.month_lengths(y)) == core.year_length(y)
