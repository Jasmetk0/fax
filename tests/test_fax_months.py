import pytest

from msa.utils import enumerate_fax_months, parse_fax_month


def test_enumerate_fax_months_wrap_inclusive():
    seq = enumerate_fax_months("2000-11-03", "2001-11-01")
    assert seq == [11, 12, 13, 14, 15, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]


def test_parse_fax_month_invalid():
    with pytest.raises(ValueError, match="FAX month must be 1..15"):
        parse_fax_month("2000-16-01")
