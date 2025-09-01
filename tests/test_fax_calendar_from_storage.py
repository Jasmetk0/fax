from fax_calendar.utils import from_storage


def test_from_storage_blank_none():
    assert from_storage(None) == (None, None, None)
    assert from_storage("") == (None, None, None)


def test_from_storage_string_and_tuple():
    assert from_storage("2025-09-01") == (2025, 9, 1)
    assert from_storage((2025, 9, 1)) == (2025, 9, 1)
