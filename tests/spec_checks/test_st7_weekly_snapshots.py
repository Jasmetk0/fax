from datetime import date

from msa.services.standings import weekly_snapshot_dates


def test_weekly_snapshot_dates_mondays_and_edges():
    start = date(2024, 1, 1)  # Monday
    end = date(2024, 1, 15)  # Monday
    days = weekly_snapshot_dates(start, end)
    assert days == [date(2024, 1, 1), date(2024, 1, 8), date(2024, 1, 15)]
    assert all(d.weekday() == 0 for d in days)


def test_weekly_snapshot_dates_empty_when_inverted():
    assert weekly_snapshot_dates(date(2024, 1, 15), date(2024, 1, 1)) == []
