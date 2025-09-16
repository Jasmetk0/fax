from __future__ import annotations

FAX_MONTHS_IN_YEAR = 15


def parse_fax_month(date_str: str) -> int:
    parts = str(date_str).split("-")
    if len(parts) < 2:
        raise ValueError(f"Invalid FAX date string: {date_str!r}")
    month = int(parts[1])
    if not 1 <= month <= FAX_MONTHS_IN_YEAR:
        raise ValueError("FAX month must be 1..15")
    return month


def enumerate_fax_months(
    start_date: str, end_date: str, months_in_year: int = FAX_MONTHS_IN_YEAR
) -> list[int]:
    s = parse_fax_month(start_date)
    e = parse_fax_month(end_date)
    out = [s]
    while True:
        s = (s % months_in_year) + 1
        out.append(s)
        if s == e:
            break
    return out
