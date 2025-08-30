"""Canonical Woorld calendar implementation.

This module provides the single source of truth for the Woorld
calendar used across the project.  It implements the historical
variations V1/V2 and proto-V3 as described in the specification.

The calendar starts on Monday (weekday 0) on 1/1/1.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

TROPICAL_YEAR: float = 428.5646875
PROMOTED_START: int = 303
PROTO_V3_YEARS: set[int] = {689, 1067, 1433, 1657}
WEEKDAY_NAMES: List[str] = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def promoted(y: int) -> bool:
    """Return True if year ``y`` is a promoted leap year (V2).

    Promotion starts in year 303 and repeats every 16 years thereafter.
    """

    return y >= PROMOTED_START and (y - PROMOTED_START) % 16 == 0


def leap_base(y: int) -> bool:
    """Return True if ``y`` is a leap year under V1/V2 rules.

    V1: even years have one extra day in month 1.
    V2: in addition to the V1 rule, every promoted year (see ``promoted``)
        is also treated as leap, regardless of parity.  The special
        historical year 297 is *not* a leap year here; it is handled via
        ``E`` with a +19 day micro-adjustment.
    """

    return (y % 2 == 0) or promoted(y)


def micro(y: int) -> int:
    """Return micro adjustments for proto-V3 irregular years."""

    return 1 if y in PROTO_V3_YEARS else 0


def E(y: int) -> int:
    """Return total extra days added to year ``y``.

    ``E`` combines the base leap rules, proto-V3 micro adjustments and the
    special +19 days of year 297.
    """

    extra = 0
    if leap_base(y):
        extra += 1
    extra += micro(y)
    if y == 297:
        extra += 19
    return extra


def year_length(y: int) -> int:
    """Return the number of days in year ``y``."""

    return 428 + E(y)


def month1_length(y: int) -> int:
    """Length of the first month in year ``y``."""

    return 29 + E(y)


def month_lengths(y: int) -> List[int]:
    """Return a list of month lengths for year ``y``.

    The calendar has 15 months alternating 29/28 days starting with 29.
    Month 1 is extended by ``E(y)`` days.
    """

    e = E(y)
    lengths: List[int] = []
    for m in range(1, 16):
        if m == 1:
            lengths.append(29 + e)
        elif m % 2 == 1:
            lengths.append(29)
        else:
            lengths.append(28)
    return lengths


def anchors(y: int) -> Dict[str, int]:
    """Return seasonal anchor day-of-year positions for year ``y``."""

    e = E(y)
    return {
        "vernal": 107 + e,
        "solstice_s": 214 + e,
        "autumnal": 321 + e,
        "solstice_w": 428 + e,
    }


def season_of(y: int, doy: int) -> str:
    """Return season name for day-of-year ``doy`` in year ``y``."""

    if not 1 <= doy <= year_length(y):
        raise ValueError("day-of-year out of range")
    a = anchors(y)
    if doy < a["vernal"]:
        return "Winter I"
    if doy < a["solstice_s"]:
        return "Spring"
    if doy < a["autumnal"]:
        return "Summer"
    if doy < a["solstice_w"]:
        return "Autumn"
    return "Winter II"


def to_ordinal(y: int, m: int, d: int) -> int:
    """Convert Y-M-D to day-of-year (1-based)."""

    lengths = month_lengths(y)
    if not 1 <= m <= 15:
        raise ValueError("month out of range")
    if not 1 <= d <= lengths[m - 1]:
        raise ValueError("day out of range")
    return sum(lengths[: m - 1]) + d


def from_ordinal(y: int, doy: int) -> Tuple[int, int, int]:
    """Return (y, m, d) for given day-of-year ``doy``."""

    if not 1 <= doy <= year_length(y):
        raise ValueError("day-of-year out of range")
    lengths = month_lengths(y)
    m = 1
    remaining = doy
    for length in lengths:
        if remaining <= length:
            return y, m, remaining
        remaining -= length
        m += 1
    raise ValueError("day-of-year out of range")  # pragma: no cover


def weekday(y: int, m: int, d: int) -> int:
    """Return weekday index (0=Mon .. 6=Sun)."""

    total = 0
    for year in range(1, y):
        total += year_length(year)
    total += to_ordinal(y, m, d) - 1
    return total % 7
