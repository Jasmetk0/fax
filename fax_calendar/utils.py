"""Woorld calendar helper utilities."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Any

from django.core.exceptions import ValidationError

from . import core


def days_in_month(year: int, month: int) -> int:
    """Return number of days in ``month`` for ``year``."""

    lengths = core.month_lengths(year)
    if not 1 <= month <= 15:
        raise ValueError("Měsíc musí být 1–15")
    return lengths[month - 1]


def parse_woorld_date(value: Any) -> tuple[int | None, int | None, int | None]:
    """Tolerant parser for Woorld calendar dates.

    Accepts multiple input types:

    * ``None``/``""``/``b""`` → ``(None, None, None)``
    * ``date``/``datetime`` → components
    * ``tuple``/``list`` of three items → components (strings allowed)
    * ``bytes`` → decoded as UTF-8
    * ``str`` in formats ``DD-MM-YYYY`` or ``YYYY-MM-DD``

    Raises :class:`django.core.exceptions.ValidationError` on invalid input.
    """

    err_msg = "Datum musí být ve formátu DD-MM-YYYY nebo YYYY-MM-DD"

    # Empty values ------------------------------------------------------
    if value in (None, "", b""):
        return (None, None, None)

    # ``date`` / ``datetime`` instances --------------------------------
    if isinstance(value, date | datetime):
        return value.year, value.month, value.day

    # Tuple/list of components -----------------------------------------
    if isinstance(value, list | tuple) and len(value) == 3:
        if all(v in (None, "", b"") for v in value):
            return (None, None, None)
        try:
            y, m, d = [int(v) for v in value]
            max_day = days_in_month(y, m)
            if not 1 <= d <= max_day:
                raise ValidationError(err_msg)
            return y, m, d
        except Exception as exc:  # pragma: no cover - defensive
            raise ValidationError(err_msg) from exc

    # Bytes -------------------------------------------------------------
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except Exception as exc:  # pragma: no cover - defensive
            raise ValidationError(err_msg) from exc

    # Strings -----------------------------------------------------------
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return (None, None, None)

        iso = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", value)
        if iso:
            y, m, d = map(int, iso.groups())
        else:
            dmy = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{4})", value)
            if not dmy:
                raise ValidationError(err_msg)
            d, m, y = map(int, dmy.groups())

        try:
            max_day = days_in_month(y, m)
            if not 1 <= d <= max_day:
                raise ValidationError(err_msg)
        except Exception as exc:
            raise ValidationError(err_msg) from exc
        return y, m, d

    # Fallback ----------------------------------------------------------
    raise ValidationError(err_msg)


def format_woorld_date(year: int, month: int, day: int) -> str:
    """Return ``DD-MM-YYYY`` string from components."""

    days_in_month(year, month)  # validation
    return f"{day:02d}-{month:02d}-{year:04d}"


def to_storage(year: int, month: int, day: int) -> str:
    """Format components to storage format ``YYYY-MM-DD``."""

    days_in_month(year, month)
    return f"{year:04d}-{month:02d}-{day:02d}"


def from_storage(
    value: str | bytes | date | datetime | Iterable[int],
) -> tuple[int | None, int | None, int | None]:
    """Parse storage format ``YYYY-MM-DD``.

    Gracefully handles ``None`` and various input types. Returns a
    ``(year, month, day)`` tuple or ``(None, None, None)`` when parsing fails.
    """

    # Empty / nullish values -------------------------------------------------
    if value is None or value in ("", b"", "None"):
        return (None, None, None)

    # ``date`` / ``datetime`` instances --------------------------------------
    if isinstance(value, date | datetime):
        return value.year, value.month, value.day

    # Raw tuple/list of components -------------------------------------------
    if isinstance(value, list | tuple) and len(value) == 3:
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


def parse_woorld_ddmmyyyy(value: str) -> tuple[int, int, int]:
    """Deprecated DD/MM/YYYY parser."""

    return parse_woorld_date(value)


def format_woorld_ddmmyyyy(year: int, month: int, day: int) -> str:
    """Deprecated formatter returning ``DD/MM/YYYY``."""

    return format_woorld_date(year, month, day).replace("-", "/")


# ---------------------------------------------------------------------------
# Monday/normalize helpers (experimental)
# ---------------------------------------------------------------------------


def monday_of(d: date) -> date:
    """Return Monday of the week for given date."""
    return d - timedelta(days=d.weekday())


def normalize(d: date) -> date:
    """Placeholder for future normalization logic."""
    return d
