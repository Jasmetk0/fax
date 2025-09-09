from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from django.conf import settings

from msa.models import Match, Tournament


class _MatchLike(Protocol):
    id: int
    round_name: str | None
    slot_top: int | None
    slot_bottom: int | None


def day_order_description(matches: Iterable[_MatchLike]) -> str:
    lines = []
    for i, m in enumerate(matches, start=1):
        rn = m.round_name or "R?"
        st = m.slot_top if m.slot_top is not None else "-"
        sb = m.slot_bottom if m.slot_bottom is not None else "-"
        lines.append(f"{i}. {rn} [{st} vs {sb}]")
    return "\n".join(lines)


def is_enabled() -> bool:
    return bool(getattr(settings, "MSA_CALENDAR_SYNC_ENABLED", False))


def escape_ics(text: str) -> str:
    r"""Escape pro ICS (\, \;, \, a \n → \n)."""

    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_dayorder_vevent(tournament: Tournament, play_date: str) -> str:
    """Build one VEVENT block for the given tournament day."""

    matches = Match.objects.filter(tournament=tournament, schedule__play_date=play_date).order_by(
        "schedule__order"
    )
    description = escape_ics(day_order_description(matches))
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    dtstart = play_date.replace("-", "")
    summary = escape_ics(f"{tournament.name} – Day Order ({play_date})")
    lines = [
        "BEGIN:VEVENT",
        f"UID:msa-{tournament.id}-{play_date}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;VALUE=DATE:{dtstart}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        "END:VEVENT",
    ]
    return "\n".join(lines)


def build_ics_for_days(tournament: Tournament, days: list[str]) -> str:
    """Return full VCALENDAR string with VEVENTs for all provided days."""

    if not is_enabled():
        return ""
    events = [build_dayorder_vevent(tournament, d) for d in days]
    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//MSA//Day Order//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        *events,
        "END:VCALENDAR",
    ]
    return "\n".join(lines)


__all__ = [
    "day_order_description",
    "is_enabled",
    "escape_ics",
    "build_dayorder_vevent",
    "build_ics_for_days",
]
