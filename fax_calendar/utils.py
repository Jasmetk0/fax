"""Woorld calendar helper utilities."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Tuple, Union

from . import core


def days_in_month(year: int, month: int) -> int:
    """Return number of days in ``month`` for ``year``."""

    lengths = core.month_lengths(year)
    if not 1 <= month <= 15:
        raise ValueError("Měsíc musí být 1–15")
    return lengths[month - 1]


_SEP_RE = r"[-./]"


def parse_woorld_date(value: str) -> Tuple[int, int, int]:
    """Parse ``DD-MM-YYYY`` (also ``DD.MM.YYYY``) string.

    Separators ``-``, ``.`` and ``/`` are accepted for backwards
    compatibility.
    """

    match = re.fullmatch(
        rf"(\d{{1,2}}){_SEP_RE}(\d{{1,2}}){_SEP_RE}(\d{{1,4}})", value or ""
    )
    if not match:
        raise ValueError("Datum musí být ve formátu DD-MM-YYYY")
    day, month, year = map(int, match.groups())
    if year <= 0:
        raise ValueError("Rok musí být větší než 0")
    max_day = days_in_month(year, month)
    if not 1 <= day <= max_day:
        raise ValueError(f"Den pro měsíc {month} musí být 1–{max_day}")
    return year, month, day


def format_woorld_date(year: int, month: int, day: int) -> str:
    """Return ``DD-MM-YYYY`` string from components."""

    days_in_month(year, month)  # validation
    return f"{day:02d}-{month:02d}-{year:04d}"


def to_storage(year: int, month: int, day: int) -> str:
    """Format components to storage format ``YYYY-MM-DD``."""

    days_in_month(year, month)
    return f"{year:04d}-{month:02d}-{day:02d}"


def _normalize_part(part: Union[str, int, None]) -> Union[int, None]:
    if part in (None, "", b"", "None"):
        return None
    return int(part)


def from_storage(
    value: object,
) -> Tuple[Union[int, None], Union[int, None], Union[int, None]]:
    """Parse various representations of a Woorld date.

    Accepts ``YYYY-MM-DD`` strings (optionally suffixed with ``w``), ``date`` or
    ``datetime`` objects, ``(y, m, d)`` tuples/lists and tolerates empty values.
    Unknown formats fail softly by returning ``(None, None, None)``.
    """

    if value in (None, "", b"", "None"):
        return (None, None, None)

    try:
        if isinstance(value, (date, datetime)):
            y, m, d = value.year, value.month, value.day
        elif isinstance(value, (tuple, list)):
            y, m, d = (_normalize_part(p) for p in value[:3])
        else:
            if isinstance(value, (bytes, bytearray)):
                value = value.decode()
            if isinstance(value, str):
                value = value.strip()
                if not value or value.lower() == "none":
                    return (None, None, None)
                if value.endswith("w"):
                    value = value[:-1]
                y, m, d = (_normalize_part(part) for part in value.split("-"))
            else:
                return (None, None, None)

        if None in (y, m, d):
            return (y, m, d)
        days_in_month(y, m)
        if not 1 <= d <= days_in_month(y, m):
            return (None, None, None)
        return (int(y), int(m), int(d))
    except Exception:  # pragma: no cover - defensive
        return (None, None, None)


def season_name(year: int, month: int, day: int) -> str:
    """Return season name for given date."""

    doy = core.to_ordinal(year, month, day)
    return core.season_of(year, doy)


# ---------------------------------------------------------------------------
# Backwards compatibility wrappers
# ---------------------------------------------------------------------------


def parse_woorld_ddmmyyyy(value: str) -> Tuple[int, int, int]:
    """Deprecated DD/MM/YYYY parser."""

    return parse_woorld_date(value)


def format_woorld_ddmmyyyy(year: int, month: int, day: int) -> str:
    """Deprecated formatter returning ``DD/MM/YYYY``."""

    return format_woorld_date(year, month, day).replace("-", "/")
