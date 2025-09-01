import datetime

from fax_calendar.utils import from_storage


def test_from_storage_various_inputs():
    assert from_storage(None) == (None, None, None)
    assert from_storage("") == (None, None, None)
    assert from_storage(b"") == (None, None, None)
    assert from_storage("None") == (None, None, None)

    assert from_storage(datetime.date(2024, 5, 3)) == (2024, 5, 3)
    assert from_storage(datetime.datetime(2024, 5, 3, 12, 0)) == (2024, 5, 3)
    assert from_storage([2024, 5, 3]) == (2024, 5, 3)
    assert from_storage((2024, 5, 3)) == (2024, 5, 3)
    assert from_storage("2024-05-03") == (2024, 5, 3)

    # invalid formats fall back to None triple
    assert from_storage("bad") == (None, None, None)
    assert from_storage("2024-13-40") == (None, None, None)
