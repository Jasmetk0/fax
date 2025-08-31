import json
import logging
from datetime import datetime
from collections import defaultdict

from django.db import transaction

from ..models import Match

logger = logging.getLogger(__name__)


def parse_bulk_schedule_slots(csv_text: str) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(csv_text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) not in (4, 5):
            raise ValueError(f"Line {line_no}: expected 4 or 5 columns")
        match_id_str, date_str, session, slot_str = parts[:4]
        court = parts[4] if len(parts) == 5 else None
        try:
            match_id = int(match_id_str)
        except ValueError:
            raise ValueError(f"Line {line_no}: invalid match_id")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Line {line_no}: invalid date")
        if not session:
            raise ValueError(f"Line {line_no}: session required")
        try:
            slot = int(slot_str)
        except ValueError:
            raise ValueError(f"Line {line_no}: invalid slot")
        row = {
            "match_id": match_id,
            "date": dt.isoformat(),
            "session": session,
            "slot": slot,
        }
        if court:
            row["court"] = court
        rows.append(row)
    return rows


def apply_bulk_schedule_slots(tournament, rows, *, user=None) -> dict:
    ids = [r["match_id"] for r in rows]
    with transaction.atomic():
        matches = {
            m.id: m for m in Match.objects.select_for_update().filter(id__in=ids)
        }
        updated = 0
        not_found = []
        foreign = []
        for row in rows:
            match = matches.get(row["match_id"])
            if not match:
                not_found.append(row["match_id"])
                continue
            if match.tournament_id != tournament.id:
                foreign.append(row["match_id"])
                continue
            schedule = {
                "date": row["date"],
                "session": row["session"],
                "slot": row["slot"],
            }
            if "court" in row:
                schedule["court"] = row["court"]
            match.section = json.dumps({"schedule": schedule})
            if user:
                match.updated_by = user
                match.save(update_fields=["section", "updated_by"])
            else:
                match.save(update_fields=["section"])
            updated += 1
        logger.info(
            "schedule.bulk_slots user=%s tournament=%s updated=%s not_found=%s foreign=%s",
            getattr(user, "id", None),
            tournament.id,
            updated,
            not_found,
            foreign,
        )
    return {"updated": updated, "not_found": not_found, "foreign": foreign}


def _extract_schedule(match):
    if not match.section:
        return None
    try:
        data = json.loads(match.section)
    except json.JSONDecodeError:
        return None
    return data.get("schedule")


def find_conflicts_slots(tournament) -> dict:
    player_matches: dict[int, list] = defaultdict(list)
    scheduled_matches = 0
    for m in tournament.matches.select_related("player1", "player2"):
        sched = _extract_schedule(m)
        if not sched:
            continue
        scheduled_matches += 1
        for player in (m.player1, m.player2):
            player_matches[player.id].append(
                (m.id, sched["date"], sched["session"], int(sched["slot"]))
            )
    hard = []
    b2b = []
    for pid, entries in player_matches.items():
        seen = defaultdict(list)
        for item in entries:
            key = (item[1], item[2], item[3])
            seen[key].append(item)
        for items in seen.values():
            if len(items) > 1:
                hard.append({"player_id": pid, "matches": items})
        sorted_entries = sorted(entries, key=lambda x: (x[1], x[2], x[3]))
        for i in range(1, len(sorted_entries)):
            prev = sorted_entries[i - 1]
            curr = sorted_entries[i]
            if prev[1] == curr[1] and prev[2] == curr[2]:
                delta = curr[3] - prev[3]
                if delta < 2:
                    b2b.append(
                        {
                            "player_id": pid,
                            "prev_id": prev[0],
                            "next_id": curr[0],
                            "delta_slots": delta,
                        }
                    )
    return {
        "hard": hard,
        "b2b": b2b,
        "stats": {
            "scheduled": scheduled_matches,
            "unique_players": len(player_matches),
        },
    }


def generate_tournament_ics_date_only(tournament) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//fax//EN"]
    for m in tournament.matches.select_related("player1", "player2"):
        sched = _extract_schedule(m)
        if not sched:
            continue
        date_str = sched["date"].replace("-", "")
        session = sched["session"]
        slot = sched["slot"]
        court = sched.get("court")
        summary = f"{m.player1.name} vs {m.player2.name} — {tournament.name}"
        desc_parts = [f"Round={m.round}", f"Session={session}", f"Slot={slot}"]
        if court:
            desc_parts.append(f"Court={court}")
        if m.scoreline:
            desc_parts.append(f"Score={m.scoreline}")
        description = "; ".join(desc_parts)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:match-{m.id}@fax",
                f"DTSTART;VALUE=DATE:{date_str}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                f"X-WOORLD-SESSION:{session}",
                f"X-WOORLD-SLOT:{slot}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
