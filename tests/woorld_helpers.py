from fax_calendar.core import month_lengths


def woorld_last_day(year: int, month: int) -> int:
    return month_lengths(year)[month - 1]


def woorld_date(year: int, month: int, day: int | None = None, *, storage: bool = True) -> str:
    """Vrátí YYYY-MM-DD (výchozí) nebo DD-MM-YYYY (storage=False)."""
    if day is None:
        day = woorld_last_day(year, month)
    if storage:
        return f"{year:04d}-{month:02d}-{day:02d}"
    return f"{day:02d}-{month:02d}-{year:04d}"
