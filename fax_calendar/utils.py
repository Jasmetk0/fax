"""Woorld calendar helper utilities."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Iterable, Tuple, Union

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


def from_storage(
    value: Union[str, bytes, date, datetime, Iterable[int]],
) -> Tuple[int | None, int | None, int | None]:
    """Parse storage format ``YYYY-MM-DD``.

    Gracefully handles ``None`` and various input types. Returns a
    ``(year, month, day)`` tuple or ``(None, None, None)`` when parsing fails.
    """

    # Empty / nullish values -------------------------------------------------
    if value is None or value in ("", b"", "None"):
        return (None, None, None)

    # ``date`` / ``datetime`` instances --------------------------------------
    if isinstance(value, (date, datetime)):
        return value.year, value.month, value.day

    # Raw tuple/list of components -------------------------------------------
    if isinstance(value, (list, tuple)) and len(value) == 3:
        try:
            y, m, d = [int(v) for v in value]
            days_in_month(y, m)
            if 1 <= d <= days_in_month(y, m):
                return y, m, d
        except Exception:  # pragma: no cover - fail soft
            return (None, None, None)
        return (None, None, None)

    # Bytes -> decode to str --------------------------------------------------
    if isinstance(value, bytes):
        try:
            value = value.decode()
        except Exception:  # pragma: no cover - fail soft
            return (None, None, None)

    # String in storage format -----------------------------------------------
    if isinstance(value, str):
        if value.endswith("w"):
            value = value[:-1]
        try:
            year_s, month_s, day_s = value.split("-")
            y, m, d = int(year_s), int(month_s), int(day_s)
            days_in_month(y, m)
            if 1 <= d <= days_in_month(y, m):
                return y, m, d
        except Exception:  # pragma: no cover - fail soft
            return (None, None, None)
        return (None, None, None)

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
