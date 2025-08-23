"""Woorld calendar helper utilities."""

from __future__ import annotations

import re


MONTH_LENGTHS = {i: 29 if i % 2 == 1 else 28 for i in range(1, 16)}


def days_in_month(month: int) -> int:
    """Return number of days in given Woorld month."""
    if month not in MONTH_LENGTHS:
        raise ValueError("Měsíc musí být 1–15")
    return MONTH_LENGTHS[month]


def parse_woorld_ddmmyyyy(value: str) -> tuple[int, int, int]:
    """Parse DD/MM/YYYY string and return (year, month, day)."""
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{1,4})", value or "")
    if not match:
        raise ValueError("Datum musí být ve formátu DD/MM/YYYY")
    day, month, year = map(int, match.groups())
    if year <= 0:
        raise ValueError("Rok musí být větší než 0")
    if not 1 <= month <= 15:
        raise ValueError("Měsíc musí být 1–15")
    max_day = days_in_month(month)
    if not 1 <= day <= max_day:
        raise ValueError(f"Den pro měsíc {month} musí být 1–{max_day}")
    return year, month, day


def format_woorld_ddmmyyyy(year: int, month: int, day: int) -> str:
    """Return DD/MM/YYYY string from components."""
    days_in_month(month)  # validation
    return f"{day:02d}/{month:02d}/{year:04d}"


def to_storage(year: int, month: int, day: int) -> str:
    """Format components to storage format YYYY-MM-DDw."""
    days_in_month(month)
    return f"{year:04d}-{month:02d}-{day:02d}w"


def from_storage(value: str) -> tuple[int, int, int]:
    """Parse storage format YYYY-MM-DDw into components."""
    if not value:
        raise ValueError("Prázdná hodnota")
    if not value.endswith("w"):
        raise ValueError("Neplatný formát Woorld datum")
    try:
        year_s, month_s, day_s = value[:-1].split("-")
        return int(year_s), int(month_s), int(day_s)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError("Neplatný formát Woorld datum") from exc
