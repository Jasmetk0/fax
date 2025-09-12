from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from django.conf import settings

from msa.models import Match, Schedule, Tournament


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


def is_enabled(tournament: "Tournament | None" = None) -> bool:  # noqa: UP037
    return bool(
        getattr(settings, "MSA_CALENDAR_SYNC_ENABLED", False)
        or (tournament and getattr(tournament, "calendar_sync_enabled", False))
    )


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

    if not is_enabled(tournament):
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


def build_match_vevent(match: Match, play_date: str) -> str:
    """
    VEVENT pro jeden zápas (all-day):
      - UID: f"msa-match-{match.id}"
      - DTSTAMP: UTC nyní (YYYYMMDDTHHMMSSZ)
      - DTSTART;VALUE=DATE:{YYYYMMDD}  # all-day (čas neřeš)
      - SUMMARY: "<round> – <Ptop> vs <Pbot>"  (P… = jméno nebo 'TBD')
      - DESCRIPTION: "Slot: [<slot_top> vs <slot_bottom>], Order: <order>"
    Všechny texty escapuj escape_ics().
    """

    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    dtstart = play_date.replace("-", "")

    ptop = match.player_top.name if match.player_top and match.player_top.name else "TBD"
    pbot = match.player_bottom.name if match.player_bottom and match.player_bottom.name else "TBD"
    summary = escape_ics(f"{match.round_name or 'R?'} – {ptop} vs {pbot}")

    st = match.slot_top if match.slot_top is not None else "-"
    sb = match.slot_bottom if match.slot_bottom is not None else "-"
    # Prefer attached schedule order; otherwise try to resolve by (match, play_date); fallback to "-"
    order = "-"
    try:
        sch = getattr(match, "schedule", None)
        if sch is not None and getattr(sch, "order", None) is not None:
            order = sch.order
        else:
            sch2 = Schedule.objects.filter(match=match, play_date=play_date).first()
            if sch2 and sch2.order is not None:
                order = sch2.order
    except Exception:
        order = "-"
    description = escape_ics(f"Slot: [{st} vs {sb}], Order: {order}")

    lines = [
        "BEGIN:VEVENT",
        f"UID:msa-match-{match.id}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;VALUE=DATE:{dtstart}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        "END:VEVENT",
    ]
    return "\n".join(lines)


def build_ics_for_matches(tournament: Tournament, days: list[str]) -> str:
    """
    Vrátí VCALENDAR s VEVENT pro všechny zápasy, které mají záznam v Schedule
    na některý z 'days'. Respektuj is_enabled() – pokud False, vrať "".
    """

    if not is_enabled(tournament):
        return ""

    matches = (
        Match.objects.filter(tournament=tournament, schedule__play_date__in=days)
        .select_related("player_top", "player_bottom", "schedule")
        .order_by("schedule__play_date", "schedule__order")
    )
    events = [build_match_vevent(m, m.schedule.play_date) for m in matches]
    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//MSA//Matches//EN",
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
    "build_match_vevent",
    "build_ics_for_matches",
]
