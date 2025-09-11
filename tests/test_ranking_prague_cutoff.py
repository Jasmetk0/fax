from datetime import date, datetime
from zoneinfo import ZoneInfo

from msa.services.standings_snapshot import activation_monday, official_monday


def test_official_monday_is_calendar_monday_date():
    d = datetime(2024, 1, 10, 12, tzinfo=ZoneInfo("Europe/Prague"))
    assert official_monday(d) == date(2024, 1, 8)


def test_activation_monday_across_dst_changes():
    dt = datetime(2024, 3, 31, 12, tzinfo=ZoneInfo("Europe/Prague"))
    assert activation_monday(dt) == date(2024, 4, 1)
