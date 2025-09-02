import json
import logging
from datetime import datetime
from collections import defaultdict

from django.db import connection, transaction

from ..models import Match

logger = logging.getLogger(__name__)

SESSION_MAP = {
    "M": "MORNING",
    "MORNING": "MORNING",
    "D": "DAY",
    "DAY": "DAY",
    "E": "EVENING",
    "EVENING": "EVENING",
}

ALLOWED_SESSIONS = set(SESSION_MAP.values())


def _for_update(qs):
    return (
        qs.select_for_update()
        if getattr(connection.features, "supports_select_for_update", False)
        else qs
    )


def _normalize_session(value: str) -> str:
    key = value.strip().upper()
    session = SESSION_MAP.get(key)
    if not session:
        raise ValueError("invalid session")
    return session


def load_section_dict(match) -> dict | None:
    if not match.section:
        return None
    try:
        data = json.loads(match.section)
    except json.JSONDecodeError:
        return None
    return data


def save_section_dict(match, data: dict, *, user=None):
    match.section = json.dumps(data)
    if user:
        match.updated_by = user
        match.save(update_fields=["section", "updated_by"])
    else:
        match.save(update_fields=["section"])


def put_schedule(match, schedule: dict, *, user=None, preserve_legacy: bool = True):
    data = load_section_dict(match)
    if data is None:
        if match.section and preserve_legacy:
            data = {"legacy_section": match.section}
        else:
            data = {}
    data["schedule"] = schedule
    save_section_dict(match, data, user=user)


def parse_bulk_schedule_slots(csv_text: str) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(csv_text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if line_no == 1 and parts and parts[0].lower() == "match_id":
            # header row from export
            continue
        if len(parts) < 4:
            raise ValueError(f"Line {line_no}: expected at least 4 columns")
        match_id_str, date_str, session_raw, slot_str = parts[:4]
        court = parts[4] if len(parts) > 4 and parts[4] else None
        try:
            match_id = int(match_id_str)
        except ValueError:
            raise ValueError(f"Line {line_no}: invalid match_id")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Line {line_no}: invalid date")
        if not session_raw:
            raise ValueError(f"Line {line_no}: session required")
        try:
            session = _normalize_session(session_raw)
        except ValueError:
            raise ValueError(f"Line {line_no}: invalid session")
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
        not_found = []
        foreign = []
        for row in rows:
            match = matches.get(row["match_id"])
            if not match:
                not_found.append(row["match_id"])
            elif match.tournament_id != tournament.id:
                foreign.append(row["match_id"])
        if not_found or foreign:
            raise ValueError(f"Not found: {not_found}; foreign: {foreign}".strip())
        updated = 0
        for row in rows:
            match = matches[row["match_id"]]
            schedule = {
                "date": row["date"],
                "session": row["session"],
                "slot": row["slot"],
            }
            if "court" in row and row["court"]:
                schedule["court"] = row["court"]
            put_schedule(match, schedule, user=user)
            updated += 1
    conflicts = find_conflicts_slots(tournament)
    for c in conflicts.get("court_double_booked", []):
        logger.warning(
            "schedule.double_booked user=%s tournament=%s date=%s session=%s slot=%s court=%s matches=%s",
            getattr(user, "id", None),
            tournament.id,
            c["date"],
            c["session"],
            c["slot"],
            c["court"],
            c["match_ids"],
        )
    logger.info(
        "schedule.bulk_slots user=%s tournament=%s updated=%s",
        getattr(user, "id", None),
        tournament.id,
        updated,
    )
    return {"updated": updated}


def _extract_schedule(match):
    data = load_section_dict(match)
    if not data:
        return None
    return data.get("schedule")


def find_conflicts_slots(tournament) -> dict:
    player_matches: dict[int, list] = defaultdict(list)
    scheduled_matches = 0
    court_map: dict[tuple, list] = defaultdict(list)
    for m in tournament.matches.select_related("player1", "player2"):
        sched = _extract_schedule(m)
        if not sched:
            continue
        scheduled_matches += 1
        key = (
            sched["date"],
            sched["session"],
            int(sched["slot"]),
            sched.get("court"),
        )
        court_map[key].append(m.id)
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
    court_double_booked = []
    for key, ids in court_map.items():
        if key[3] and len(ids) > 1:
            court_double_booked.append(
                {
                    "date": key[0],
                    "session": key[1],
                    "slot": key[2],
                    "court": key[3],
                    "match_ids": ids,
                }
            )
    return {
        "hard": hard,
        "b2b": b2b,
        "court_double_booked": court_double_booked,
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


def swap_scheduled_matches(tournament, match_id_a, match_id_b, *, user=None) -> bool:
    ids = sorted([match_id_a, match_id_b])
    with transaction.atomic():
        matches = list(_for_update(Match.objects.filter(id__in=ids).order_by("id")))
        if len(matches) != 2:
            return False
        m_map = {m.id: m for m in matches}
        a = m_map.get(match_id_a)
        b = m_map.get(match_id_b)
        if (
            not a
            or not b
            or a.tournament_id != tournament.id
            or b.tournament_id != tournament.id
        ):
            return False
        sched_a = _extract_schedule(a)
        sched_b = _extract_schedule(b)
        if not sched_a or not sched_b:
            return False
        if sched_a == sched_b:
            return False
        put_schedule(a, sched_b, user=user)
        put_schedule(b, sched_a, user=user)
    logger.info(
        "schedule.swap user=%s tournament=%s a=%s b=%s",
        getattr(user, "id", None),
        tournament.id,
        match_id_a,
        match_id_b,
    )
    return True


def move_scheduled_match(
    tournament, match_id, new_schedule: dict, *, user=None
) -> bool:
    try:
        session = _normalize_session(new_schedule["session"])
    except ValueError:
        return False
    target = {
        "date": new_schedule["date"],
        "session": session,
        "slot": new_schedule["slot"],
    }
    if new_schedule.get("court"):
        target["court"] = new_schedule["court"]

    section_payload = json.dumps({"schedule": target})

    with transaction.atomic():
        occ_id = (
            Match.objects.filter(tournament=tournament, section=section_payload)
            .exclude(pk=match_id)
            .values_list("pk", flat=True)
            .first()
        )
        ids = [match_id]
        if occ_id:
            ids.append(occ_id)
        ids.sort()
        matches = list(_for_update(Match.objects.filter(pk__in=ids).order_by("pk")))
        m_map = {m.pk: m for m in matches}
        m = m_map.get(match_id)
        if not m:
            return False
        occ = m_map.get(occ_id) if occ_id else None
        cur = _extract_schedule(m)
        if cur == target:
            return False
        if occ and _extract_schedule(occ) != target:
            occ = None

        if occ:
            s_m = cur
            s_o = _extract_schedule(occ)
            put_schedule(m, s_o, user=user)
            put_schedule(occ, s_m, user=user)
        else:
            put_schedule(m, target, user=user)

    conflicts = find_conflicts_slots(tournament)
    for c in conflicts.get("court_double_booked", []):
        if match_id in c.get("match_ids", []):
            logger.warning(
                "schedule.double_booked user=%s tournament=%s date=%s session=%s slot=%s court=%s matches=%s",
                getattr(user, "id", None),
                tournament.id,
                c["date"],
                c["session"],
                c["slot"],
                c["court"],
                c["match_ids"],
            )
            break
    logger.info(
        "schedule.move user=%s tournament=%s match=%s",
        getattr(user, "id", None),
        tournament.id,
        match_id,
    )
    return True


def export_schedule_csv(tournament) -> str:
    lines = ["match_id,date,session,slot,court,round,player1,player2"]
    for m in tournament.matches.select_related("player1", "player2"):
        sched = _extract_schedule(m)
        if not sched:
            continue
        line = ",".join(
            [
                str(m.id),
                sched["date"],
                sched["session"],
                str(sched["slot"]),
                sched.get("court", ""),
                m.round,
                m.player1.name,
                m.player2.name,
            ]
        )
        lines.append(line)
    return "\n".join(lines)
