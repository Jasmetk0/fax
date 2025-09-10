from msa.services.calendar_sync import is_enabled


def test_calendar_sync_import_smoke():
    assert isinstance(is_enabled(None), bool)
