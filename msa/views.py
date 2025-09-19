import re
from collections import OrderedDict, defaultdict
from typing import Any

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import OperationalError
from django.db.models import Q
from django.db.models.fields.related import ForeignKey
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from msa.services.md_embed import effective_template_size_for_md, md_anchor_map
from msa.services.qual_generator import (
    bracket_anchor_tiers,
    generate_qualification_mapping,
    seeds_per_bracket,
)
from msa.utils.dates import find_season_for_date, get_active_date

from .utils import enumerate_fax_months


def _to_iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


DEFAULT_BADGE = "bg-slate-600/10 text-slate-800 border-slate-300"

CATEGORY_BADGES = {
    "Diamond": "bg-indigo-600/10 text-indigo-700 border-indigo-200",
    "Emerald": "bg-emerald-600/10 text-emerald-700 border-emerald-200",
    "Platinum": "bg-slate-700/10 text-slate-800 border-slate-300",
    "Gold": "bg-amber-500/10 text-amber-700 border-amber-200",
    "Silver": "bg-gray-500/10 text-gray-700 border-gray-300",
    "Bronze": "bg-orange-500/10 text-orange-700 border-orange-200",
}

TOUR_BADGES = {
    "World Tour": "bg-blue-600/10 text-blue-700 border-blue-200",
    "Elite Tour": "bg-purple-600/10 text-purple-700 border-purple-200",
    "Challenger Tour": "bg-teal-600/10 text-teal-700 border-teal-200",
    "Development Tour": "bg-lime-600/10 text-lime-700 border-lime-200",
}

STATUS_BADGES = {
    "planned": ("Plánován", "bg-sky-500/10 text-sky-700 border-sky-200"),
    "running": ("Probíhá", "bg-emerald-500/10 text-emerald-700 border-emerald-200"),
    "completed": ("Dokončeno", "bg-slate-500/10 text-slate-700 border-slate-300"),
}


def _badge_class(value: str | None, mapping: dict[str, str]) -> str:
    if not value:
        return DEFAULT_BADGE
    return mapping.get(str(value), DEFAULT_BADGE)


def _parse_fax_iso(value: str | None):
    if not value:
        return None
    parts = str(value).split("-")
    if len(parts) < 3:
        return None
    try:
        return tuple(int(p) for p in parts[:3])
    except (TypeError, ValueError):
        return None


def _normalize_woorld_value(value) -> str | None:
    if value in (None, "", "None"):
        return None
    if isinstance(value, dict):
        y = value.get("year") or value.get("y")
        m = value.get("month") or value.get("m")
        d = value.get("day") or value.get("d")
        try:
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        except (TypeError, ValueError):
            return None
    try:
        from fax_calendar.utils import parse_woorld_date, to_storage
    except Exception:
        parse_woorld_date = None
        to_storage = None

    if parse_woorld_date and to_storage:
        try:
            y, m, d = parse_woorld_date(value)
        except Exception:
            y = m = d = None
        if None not in (y, m, d):
            try:
                return to_storage(int(y), int(m), int(d))
            except Exception:
                return None

    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            parts = cleaned.split("-")
            if len(parts) >= 3:
                try:
                    y, m, d = (int(parts[0]), int(parts[1]), int(parts[2]))
                except ValueError:
                    return None
                return f"{y:04d}-{m:02d}-{d:02d}"
    return None


def _current_fax_iso(request) -> str:
    candidates = [
        getattr(request, "session", {}).get("woorld_today"),
        getattr(request, "session", {}).get("woorld_date"),
        request.COOKIES.get("woorld_today"),
        request.COOKIES.get("woorld_date"),
    ]
    for value in candidates:
        iso = _normalize_woorld_value(value)
        if iso:
            return iso
    today = timezone.now().date()
    return f"{today.year:04d}-{today.month:02d}-{today.day:02d}"


def _resolve_tournament_status(request, start_iso: str | None, end_iso: str | None):
    now_iso = _current_fax_iso(request)
    now_tuple = _parse_fax_iso(now_iso)
    start_tuple = _parse_fax_iso(start_iso)
    end_tuple = _parse_fax_iso(end_iso)

    status_key = "planned"
    if now_tuple and start_tuple and now_tuple < start_tuple:
        status_key = "planned"
    elif now_tuple and start_tuple and end_tuple and start_tuple <= now_tuple <= end_tuple:
        status_key = "running"
    elif now_tuple and end_tuple and now_tuple > end_tuple:
        status_key = "completed"

    label, css_class = STATUS_BADGES.get(status_key, STATUS_BADGES["planned"])
    return {"label": label, "class": css_class, "key": status_key, "now": now_iso}


def _get_tournament_model():
    return apps.get_model("msa", "Tournament") if apps.is_installed("msa") else None


def _get_tournament_or_404(tournament_id: int):
    Tournament = _get_tournament_model()
    if not Tournament:
        raise Http404("Tournament model unavailable")
    try:
        qs = Tournament.objects.all()
        qs = qs.select_related("season", "category", "category__tour")
        return qs.get(pk=tournament_id)
    except (Tournament.DoesNotExist, OperationalError) as err:
        raise Http404("Tournament not found") from err


def _tournament_base_context(request, tournament):
    season = getattr(tournament, "season", None)
    category_obj = getattr(tournament, "category", None)
    tour_obj = getattr(category_obj, "tour", None)

    start_iso = getattr(tournament, "start_date", "") or ""
    end_iso = getattr(tournament, "end_date", "") or ""

    category_label = None
    if category_obj:
        category_label = getattr(category_obj, "name", None) or str(category_obj)
    elif getattr(tournament, "category", None):
        category_label = str(getattr(tournament, "category", ""))

    tour_label = None
    if tour_obj:
        tour_label = getattr(tour_obj, "name", None) or str(tour_obj)

    status_meta = _resolve_tournament_status(request, start_iso, end_iso)

    return {
        "tournament": tournament,
        "season": season,
        "fax_range_start": start_iso or "",
        "fax_range_end": end_iso or "",
        "category_label": category_label,
        "category_badge_class": _badge_class(category_label, CATEGORY_BADGES),
        "tour_label": tour_label,
        "tour_badge_class": _badge_class(tour_label, TOUR_BADGES),
        "status": status_meta,
    }


def _has_model_field(model, field_name: str) -> bool:
    if not model:
        return False
    try:
        model._meta.get_field(field_name)
        return True
    except (FieldDoesNotExist, AttributeError, LookupError):
        return False


def _normalize_entry_type(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).upper()


def _player_display(player) -> str:
    if not player:
        return "Unknown player"
    for attr in ("full_name", "name", "last_name"):
        text = getattr(player, attr, None)
        if text:
            return str(text)
    if getattr(player, "id", None):
        return f"Player #{player.id}"
    return "Unknown player"


def _player_country(player) -> str | None:
    if not player:
        return None
    country = getattr(player, "country", None)
    if not country:
        return None
    for attr in ("iso3", "iso2", "name"):
        value = getattr(country, attr, None)
        if value:
            return str(value)
    return None


def _entry_tag(row: dict[str, Any]) -> str:
    if row.get("is_placeholder"):
        return "PLACEHOLDER"
    entry_type = _normalize_entry_type(row.get("entry_type"))
    if row.get("is_wc") or entry_type == "WC":
        return "WC"
    if row.get("is_qwc") or entry_type == "QWC":
        return "QWC"
    if entry_type == "Q":
        return "Q"
    if entry_type == "LL":
        return "LL"
    if entry_type == "ALT":
        return "ALT"
    return "DA"


def _entry_payload(row: dict[str, Any]) -> dict[str, Any] | None:
    if not row:
        return None
    payload = {
        "entry_id": row.get("entry_id"),
        "player_id": row.get("player_id"),
        "name": row.get("name"),
        "country": row.get("country"),
        "wr": row.get("wr"),
        "seed": row.get("seed"),
        "entry_type": row.get("entry_type"),
        "tag": _entry_tag(row),
        "placeholder": bool(row.get("is_placeholder")),
    }
    return payload


def _parse_sets(score_payload: Any) -> tuple[list[dict[str, Any]], bool]:
    sets: list[dict[str, Any]] = []
    has_partial = False
    raw_sets = []
    if isinstance(score_payload, dict):
        raw_sets = score_payload.get("sets") or []
    for item in raw_sets:
        if isinstance(item, dict):
            raw_a = item.get("a", item.get("top"))
            raw_b = item.get("b", item.get("bottom"))
            status_raw = item.get("status")
            if raw_a in (None, "", "-") or raw_b in (None, "", "-"):
                has_partial = True
            try:
                a_val = int(raw_a)
                b_val = int(raw_b)
            except (TypeError, ValueError):
                if raw_a is not None or raw_b is not None:
                    has_partial = True
                continue
            if status_raw:
                status_norm = str(status_raw).strip().lower()
                if status_norm and status_norm not in {"finished", "done", "completed"}:
                    has_partial = True
            sets.append({"a": a_val, "b": b_val, "status": status_raw})
        elif isinstance(item, list | tuple) and len(item) >= 2:
            raw_a, raw_b = item[0], item[1]
            try:
                a_val = int(raw_a)
                b_val = int(raw_b)
            except (TypeError, ValueError):
                if raw_a is not None or raw_b is not None:
                    has_partial = True
                continue
            sets.append({"a": a_val, "b": b_val, "status": None})
    if isinstance(score_payload, dict) and len(sets) < len(raw_sets):
        has_partial = True
    return sets, has_partial


def _match_status_and_sets(match) -> tuple[str, list[dict[str, Any]]]:
    score_payload = getattr(match, "score", None) or {}
    sets, has_partial = _parse_sets(score_payload)
    meta_status = ""
    if isinstance(score_payload, dict):
        meta = score_payload.get("meta")
        if isinstance(meta, dict):
            meta_status = (meta.get("status") or "").strip().lower()

    state_value = (getattr(match, "state", None) or "").upper()
    base_status = {
        "DONE": "finished",
        "SCHEDULED": "scheduled",
        "PENDING": "scheduled",
        "LIVE": "live",
    }.get(state_value, state_value.lower() or "scheduled")

    if state_value == "DONE":
        base_status = "finished"

    if base_status != "finished":
        in_progress_flag = bool(getattr(match, "in_progress", False))
        has_recorded_sets = bool(sets)
        if meta_status == "live":
            base_status = "live"
        elif base_status == "live" or in_progress_flag:
            base_status = "live"
        elif has_partial and (base_status != "scheduled" or has_recorded_sets):
            base_status = "live"

    return base_status, sets


def _entry_rows_for_tournament(tournament) -> dict[str, Any]:
    TournamentEntry = apps.get_model("msa", "TournamentEntry") if apps.is_installed("msa") else None
    PlayerLicense = apps.get_model("msa", "PlayerLicense") if apps.is_installed("msa") else None

    rows: list[dict[str, Any]] = []
    entries_by_id: dict[int, dict[str, Any]] = {}
    if not TournamentEntry:
        summary = {
            "seeds": 0,
            "draw_size": getattr(tournament, "draw_size", None),
            "qualifiers": getattr(tournament, "qualifiers_count_effective", 0),
            "direct_acceptances": None,
            "qual_draw_size": 0,
            "wc": {"used": 0, "limit": 0},
            "qwc": {"used": 0, "limit": 0},
        }
        return {
            "rows": rows,
            "blocks": {"seeds": [], "da": [], "q": [], "reserve": []},
            "summary": summary,
            "entries_by_id": entries_by_id,
            "da_cut_index": 0,
        }

    try:
        qs = TournamentEntry.objects.filter(tournament=tournament)
        if _has_model_field(TournamentEntry, "status"):
            active_value = None
            status_enum = getattr(TournamentEntry, "Status", None)
            if status_enum and hasattr(status_enum, "ACTIVE"):
                active_value = status_enum.ACTIVE
            entry_status = getattr(TournamentEntry, "EntryStatus", None)
            if entry_status and hasattr(entry_status, "ACTIVE"):
                active_value = entry_status.ACTIVE
            if active_value is not None:
                qs = qs.filter(status=active_value)
            else:
                qs = qs.filter(status="ACTIVE")
        else:
            qs = qs.filter(status="ACTIVE")
        qs = qs.select_related("player", "player__country")
        entries = list(qs)
    except OperationalError:
        entries = []

    player_ids = [e.player_id for e in entries if getattr(e, "player_id", None)]
    licensed_ids: set[int] = set()
    season_id = getattr(tournament, "season_id", None)
    if PlayerLicense and season_id and player_ids:
        try:
            licensed_ids = set(
                PlayerLicense.objects.filter(
                    season_id=season_id, player_id__in=player_ids
                ).values_list("player_id", flat=True)
            )
        except OperationalError:
            licensed_ids = set()

    for entry in entries:
        player = getattr(entry, "player", None)
        row = {
            "entry_id": entry.id,
            "player_id": getattr(entry, "player_id", None),
            "name": _player_display(player),
            "raw_name": getattr(player, "name", None),
            "country": _player_country(player),
            "wr": getattr(entry, "wr_snapshot", None),
            "seed": getattr(entry, "seed", None),
            "entry_type": _normalize_entry_type(getattr(entry, "entry_type", None)),
            "position": getattr(entry, "position", None),
            "license_ok": (not season_id)
            or not getattr(entry, "player_id", None)
            or getattr(entry, "player_id", None) in licensed_ids,
            "is_wc": bool(
                getattr(entry, "is_wc", False)
                or _normalize_entry_type(getattr(entry, "entry_type", None)) == "WC"
            ),
            "is_qwc": bool(
                getattr(entry, "is_qwc", False)
                or _normalize_entry_type(getattr(entry, "entry_type", None)) == "QWC"
            ),
            "is_placeholder": bool(
                getattr(player, "name", "") and str(player.name).upper().startswith("WINNER K#")
            ),
        }
        rows.append(row)
        entries_by_id[entry.id] = row

    seeds = [row for row in rows if row.get("seed") not in (None, "")]
    seeds.sort(
        key=lambda item: (
            int(item.get("seed") or 0),
            1 if item.get("wr") is None else 0,
            item.get("wr") or 10**6,
            item.get("name") or "",
        )
    )

    def _sort_key_for(row: dict[str, Any]):
        return (
            row.get("position") if row.get("position") is not None else 10**6,
            1 if row.get("wr") is None else 0,
            row.get("wr") or 10**6,
            row.get("name") or "",
        )

    da_block: list[dict[str, Any]] = []
    q_block: list[dict[str, Any]] = []
    reserve_block: list[dict[str, Any]] = []
    for row in rows:
        if row in seeds:
            continue
        entry_type = _normalize_entry_type(row.get("entry_type"))
        if entry_type in {"DA", "", None} or row.get("is_wc"):
            da_block.append(row)
        elif entry_type in {"Q", "QWC"}:
            q_block.append(row)
        elif entry_type in {"ALT", "LL"}:
            reserve_block.append(row)
        else:
            reserve_block.append(row)

    da_block.sort(key=_sort_key_for)
    q_block.sort(key=_sort_key_for)
    reserve_block.sort(key=_sort_key_for)

    qualifiers = int(getattr(tournament, "qualifiers_count_effective", 0) or 0)
    draw_size = getattr(tournament, "draw_size", None)
    if draw_size is None:
        cs = getattr(tournament, "category_season", None)
        draw_size = getattr(cs, "draw_size", None)
    draw_size_int = int(draw_size) if draw_size else None
    direct_acceptances = None
    if draw_size_int is not None:
        direct_acceptances = max(draw_size_int - qualifiers, 0)

    cs = getattr(tournament, "category_season", None)
    qual_rounds = int(getattr(cs, "qual_rounds", 0) or 0)
    qual_draw_size = int(qualifiers * (2 ** max(qual_rounds, 0))) if qualifiers else 0

    wc_limit = getattr(tournament, "wc_slots", None)
    if wc_limit in (None, "") and cs:
        wc_limit = getattr(cs, "wc_slots_default", None)
    qwc_limit = getattr(tournament, "q_wc_slots", None)
    if qwc_limit in (None, "") and cs:
        qwc_limit = getattr(cs, "q_wc_slots_default", None)

    wc_used = len([row for row in rows if row.get("is_wc")])
    qwc_used = len([row for row in rows if row.get("is_qwc")])

    da_cut_index = 0
    if direct_acceptances is not None:
        da_cut_index = max(direct_acceptances - len(seeds), 0)

    summary = {
        "seeds": len(seeds),
        "draw_size": draw_size_int,
        "qualifiers": qualifiers,
        "qual_rounds": qual_rounds,
        "direct_acceptances": direct_acceptances,
        "qual_draw_size": qual_draw_size,
        "wc": {"used": wc_used, "limit": int(wc_limit or 0)},
        "qwc": {"used": qwc_used, "limit": int(qwc_limit or 0)},
        "total": len(rows),
    }

    return {
        "rows": rows,
        "blocks": {"seeds": seeds, "da": da_block, "q": q_block, "reserve": reserve_block},
        "summary": summary,
        "entries_by_id": entries_by_id,
        "da_cut_index": da_cut_index,
    }


def _qualification_structure(tournament, entry_data: dict[str, Any]) -> dict[str, Any]:
    qualifiers = int(getattr(tournament, "qualifiers_count_effective", 0) or 0)
    cs = getattr(tournament, "category_season", None)
    qual_rounds = int(getattr(cs, "qual_rounds", 0) or 0)
    result = {"K": qualifiers, "R": qual_rounds, "brackets": []}
    if qualifiers <= 0 or qual_rounds <= 0:
        return result

    size = 2**qual_rounds
    seeds_per_branch = seeds_per_bracket(qual_rounds)
    expected_total = qualifiers * size

    qual_entries = [
        row
        for row in entry_data["rows"]
        if _normalize_entry_type(row.get("entry_type")) in {"Q", "QWC"}
    ]
    if not qual_entries:
        return result

    sorted_for_seeding = sorted(
        qual_entries,
        key=lambda item: (
            1 if item.get("wr") is None else 0,
            item.get("wr") or 10**6,
            item.get("entry_id") or 10**6,
        ),
    )

    q_seed_ids = [
        row.get("entry_id") for row in sorted_for_seeding[: qualifiers * seeds_per_branch]
    ]
    unseeded_ids = [
        row.get("entry_id") for row in sorted_for_seeding[qualifiers * seeds_per_branch :]
    ]

    mapping: list[dict[int, int | None]] = []
    try:
        if len(sorted_for_seeding) >= expected_total:
            mapping = generate_qualification_mapping(
                K=qualifiers,
                R=qual_rounds,
                q_seeds_in_order=[eid for eid in q_seed_ids if eid is not None],
                unseeded_players=[eid for eid in unseeded_ids if eid is not None],
                rng_seed=int(getattr(tournament, "rng_seed_active", 0) or 0),
            )
    except Exception:
        mapping = []

    if not mapping:
        pool = [row.get("entry_id") for row in sorted_for_seeding]
        while len(pool) < expected_total:
            pool.append(None)
        for branch_index in range(qualifiers):
            branch: dict[int, int | None] = {}
            for local_slot in range(1, size + 1):
                idx = branch_index * size + (local_slot - 1)
                branch[local_slot] = pool[idx] if idx < len(pool) else None
            mapping.append(branch)

    tiers_template = bracket_anchor_tiers(qual_rounds)
    brackets: list[dict[str, Any]] = []
    for branch_index in range(qualifiers):
        branch_map = mapping[branch_index] if branch_index < len(mapping) else {}
        tiers_payload: dict[str, list[dict[str, Any]]] = {}
        tier_names = list(tiers_template.keys())
        for idx, tier_name in enumerate(tier_names):
            tiers_payload[tier_name] = []
            seed_block_start = idx * qualifiers
            seed_block_end = seed_block_start + qualifiers
            block = sorted_for_seeding[seed_block_start:seed_block_end]
            if branch_index < len(block):
                tiers_payload[tier_name].append(_entry_payload(block[branch_index]))

        rounds: list[dict[str, Any]] = []
        round_size = size
        round_index = 1
        while round_size >= 2:
            label = f"Q{round_size}"
            pairs: list[dict[str, Any]] = []
            for top_local in range(1, round_size // 2 + 1):
                bottom_local = round_size + 1 - top_local
                slot_top = branch_map.get(top_local)
                slot_bottom = branch_map.get(bottom_local)
                player_top = entry_data["entries_by_id"].get(slot_top)
                player_bottom = entry_data["entries_by_id"].get(slot_bottom)
                pairs.append(
                    {
                        "slot_top": top_local,
                        "slot_bottom": bottom_local,
                        "player_top": _entry_payload(player_top),
                        "player_bottom": _entry_payload(player_bottom),
                        "status": "scheduled" if player_top or player_bottom else "pending",
                        "best_of": getattr(tournament, "q_best_of", None) or 3,
                        "score": None,
                    }
                )
            rounds.append({"round": round_index, "label": label, "pairs": pairs})
            round_size //= 2
            round_index += 1

        brackets.append(
            {
                "index": branch_index + 1,
                "tiers": tiers_payload,
                "rounds": rounds,
            }
        )

    result["brackets"] = brackets
    return result


def _main_draw_structure(tournament, entry_data: dict[str, Any]) -> dict[str, Any]:
    template_size = None
    try:
        template_size = effective_template_size_for_md(tournament)
    except ValidationError:
        draw_size = getattr(tournament, "draw_size", None)
        if draw_size:
            template_size = 1
            while template_size < int(draw_size):
                template_size *= 2
    except Exception:
        template_size = None

    if not template_size:
        return {
            "template_size": None,
            "seed_bands": {},
            "slots": [],
            "placeholders": {"qual_winner_map": {}},
        }

    try:
        anchors = md_anchor_map(template_size)
    except ValueError:
        anchors = OrderedDict()

    seed_bands = {label: slots for label, slots in anchors.items()}

    position_map: dict[int, dict[str, Any]] = {}
    for row in entry_data["rows"]:
        pos = row.get("position")
        if pos is not None:
            position_map[int(pos)] = row

    slots: list[dict[str, Any]] = []
    for position in range(1, template_size + 1):
        row = position_map.get(position)
        slots.append(
            {
                "pos": position,
                "seed": row.get("seed") if row else None,
                "player": _entry_payload(row) if row else None,
            }
        )

    placeholder_map: dict[str, int] = {}
    for row in entry_data["rows"]:
        if not row.get("is_placeholder"):
            continue
        pos = row.get("position")
        raw_name = str(row.get("raw_name") or row.get("name") or "").upper()
        match = re.search(r"K#(\d+)", raw_name)
        if pos and match:
            key = f"K{match.group(1)}"
            placeholder_map[key] = int(pos)

    return {
        "template_size": template_size,
        "seed_bands": seed_bands,
        "slots": slots,
        "placeholders": {"qual_winner_map": placeholder_map},
    }


def _tournament_detail_url(tournament) -> str:
    identifier = getattr(tournament, "id", None)
    if identifier is None:
        return "#"
    try:
        return reverse("msa:tournament_info", args=[identifier])
    except NoReverseMatch:
        return f"/msa/tournament/{identifier}/"


def _tournament_location(tournament) -> str | None:
    parts: list[str] = []
    for attr in ("city", "city_name", "location"):
        value = getattr(tournament, attr, None)
        if value:
            parts.append(str(value))
            break
    country = getattr(tournament, "country", None)
    if country:
        if isinstance(country, str):
            parts.append(country)
        else:
            for attr in ("name", "iso3", "iso2"):
                value = getattr(country, attr, None)
                if value:
                    parts.append(str(value))
                    break
    return ", ".join(parts) if parts else None


def _tournament_card(request, tournament) -> dict[str, Any]:
    base = _tournament_base_context(request, tournament)
    cs = getattr(tournament, "category_season", None)
    draw_size = getattr(tournament, "draw_size", None)
    if draw_size is None and cs:
        draw_size = getattr(cs, "draw_size", None)
    qualifiers = int(getattr(tournament, "qualifiers_count_effective", 0) or 0)
    qual_rounds = int(getattr(cs, "qual_rounds", 0) or 0)
    qual_round_size = 2**qual_rounds if qual_rounds else 0
    status_meta = base.get("status", {})
    chips: list[dict[str, Any]] = []
    if getattr(tournament, "md_best_of", None):
        chips.append({"label": f"MD BO{tournament.md_best_of}", "tone": "primary"})
    if getattr(tournament, "q_best_of", None):
        chips.append({"label": f"Q BO{tournament.q_best_of}", "tone": "secondary"})
    if getattr(tournament, "calendar_sync_enabled", False):
        chips.append({"label": "Calendar sync", "tone": "accent"})
    if getattr(tournament, "third_place_enabled", False):
        chips.append({"label": "Third place", "tone": "muted"})

    return {
        "id": getattr(tournament, "id", None),
        "name": getattr(tournament, "name", None)
        or getattr(tournament, "slug", None)
        or "Tournament",
        "category_label": base.get("category_label"),
        "category_badge_class": base.get("category_badge_class", DEFAULT_BADGE),
        "tour_label": base.get("tour_label"),
        "tour_badge_class": base.get("tour_badge_class", DEFAULT_BADGE),
        "status": status_meta,
        "draw_size": int(draw_size) if draw_size else None,
        "qualifiers": qualifiers,
        "qual_rounds": qual_rounds,
        "qual_round_size": qual_round_size,
        "start_date": base.get("fax_range_start"),
        "end_date": base.get("fax_range_end"),
        "location": _tournament_location(tournament),
        "md_best_of": getattr(tournament, "md_best_of", None),
        "q_best_of": getattr(tournament, "q_best_of", None),
        "calendar_sync_enabled": bool(getattr(tournament, "calendar_sync_enabled", False)),
        "detail_url": _tournament_detail_url(tournament),
        "season_label": str(base.get("season")) if base.get("season") else None,
        "chips": chips,
    }


def _scoring_items(scoring_data: Any) -> list[tuple[str, Any]]:
    if isinstance(scoring_data, dict):
        return [(str(key), scoring_data[key]) for key in scoring_data]
    return []


def home(request):
    return render(request, "msa/home/index.html")


def seasons_list(request):
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    seasons = []
    if Season:
        try:
            seasons = list(Season.objects.all().order_by("id"))
        except OperationalError:
            seasons = []
    return render(request, "msa/seasons/list.html", {"seasons": seasons})


def tournaments_list(request):
    d = get_active_date(request)
    season = find_season_for_date(d)
    if not season:
        return seasons_list(request)

    Tournament = apps.get_model("msa", "Tournament") if apps.is_installed("msa") else None
    tournaments = []
    if Tournament:
        qs = Tournament.objects.all()
        fields = {f.name for f in Tournament._meta.get_fields()}
        if "season" in fields:
            tournaments = qs.filter(season=season)
        elif {"start_date", "end_date"}.issubset(fields):
            start = getattr(season, "start_date", None)
            end = getattr(season, "end_date", None)
            if start and end:
                tournaments = qs.filter(start_date__lte=end, end_date__gte=start)
        elif "start_date" in fields:
            start = getattr(season, "start_date", None)
            end = getattr(season, "end_date", None)
            if start and end:
                tournaments = qs.filter(start_date__range=(start, end))
        elif "date" in fields:
            start = getattr(season, "start_date", None)
            end = getattr(season, "end_date", None)
            if start and end:
                tournaments = qs.filter(date__range=(start, end))

    context = {
        "tournaments": tournaments,
        "active_season": season,
        "active_date": d,
    }
    return render(request, "msa/tournaments/list.html", context)


def tournaments_seasons(request):
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    Category = apps.get_model("msa", "Category") if apps.is_installed("msa") else None
    Tournament = _get_tournament_model()

    seasons: list[Any] = []
    if Season:
        try:
            model_fields = {f.name for f in Season._meta.get_fields()}
            order_fields = (
                ["-start_date", "-end_date", "-id"]
                if {"start_date", "end_date"} <= model_fields
                else ["-id"]
            )
            seasons = list(Season.objects.all().order_by(*order_fields))
        except OperationalError:
            seasons = []

    categories: list[Any] = []
    if Category:
        try:
            categories = list(
                Category.objects.select_related("tour").all().order_by("tour__rank", "rank", "name")
            )
        except OperationalError:
            categories = []

    selected_season = (request.GET.get("season") or "").strip()
    selected_category = (request.GET.get("category") or "").strip()
    status_filter = (request.GET.get("status") or "").strip().lower()
    search_query = (request.GET.get("q") or "").strip()

    tournaments_raw: list[Any] = []
    if Tournament:
        try:
            qs = Tournament.objects.all()
            if selected_season:
                if _has_model_field(Tournament, "season"):
                    qs = qs.filter(season_id=selected_season)
                elif (
                    Season
                    and _has_model_field(Tournament, "start_date")
                    and _has_model_field(Tournament, "end_date")
                ):
                    try:
                        season_obj = Season.objects.get(pk=selected_season)
                    except (Season.DoesNotExist, OperationalError):
                        season_obj = None
                    if (
                        season_obj
                        and getattr(season_obj, "start_date", None)
                        and getattr(season_obj, "end_date", None)
                    ):
                        qs = qs.filter(
                            start_date__lte=season_obj.end_date,
                            end_date__gte=season_obj.start_date,
                        )
            if selected_category and _has_model_field(Tournament, "category"):
                qs = qs.filter(category_id=selected_category)
            if search_query and _has_model_field(Tournament, "name"):
                qs = qs.filter(name__icontains=search_query)
            try:
                qs = qs.select_related("season", "category", "category__tour", "category_season")
            except Exception:
                qs = qs
            order_fields = []
            if _has_model_field(Tournament, "start_date"):
                order_fields.append("start_date")
            if _has_model_field(Tournament, "name"):
                order_fields.append("name")
            order_fields.append("id")
            qs = qs.order_by(*order_fields)
            tournaments_raw = list(qs)
        except OperationalError:
            tournaments_raw = []

    cards = [_tournament_card(request, tournament) for tournament in tournaments_raw]

    valid_status = {"planned", "running", "completed"}
    if status_filter in valid_status:
        cards = [card for card in cards if card.get("status", {}).get("key") == status_filter]

    stats = {
        "total": len(cards),
        "upcoming": sum(1 for card in cards if card.get("status", {}).get("key") == "planned"),
        "running": sum(1 for card in cards if card.get("status", {}).get("key") == "running"),
        "completed": sum(1 for card in cards if card.get("status", {}).get("key") == "completed"),
    }

    paginator = Paginator(cards, 12)
    page_number = request.GET.get("page") or 1
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    status_choices = [
        {"value": "", "label": "Vše"},
        {"value": "planned", "label": "Upcoming"},
        {"value": "running", "label": "Running"},
        {"value": "completed", "label": "Completed"},
    ]

    active_season = None
    if selected_season:
        active_season = next(
            (s for s in seasons if str(getattr(s, "id", "")) == selected_season),
            None,
        )

    context = {
        "seasons": seasons,
        "categories": categories,
        "selected_season": selected_season,
        "selected_category": selected_category,
        "selected_status": status_filter,
        "search_query": search_query,
        "status_choices": status_choices,
        "page_obj": page_obj,
        "paginator": paginator,
        "cards": page_obj.object_list,
        "stats": stats,
        "active_season": active_season,
    }
    query_params = request.GET.copy()
    if "page" in query_params:
        query_params.pop("page")
    context["query_string"] = query_params.urlencode()
    return render(request, "msa/tournaments/list.html", context)


def _get_season_by_query_param(request):
    """
    Pokud je v URL ?season=<id>, vrať konkrétní Season; jinak None.
    """
    season_id = request.GET.get("season")
    if not season_id:
        return None
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    if not Season:
        return None
    try:
        return Season.objects.get(pk=season_id)
    except Season.DoesNotExist as err:
        raise Http404("Season not found") from err
    except OperationalError as err:
        raise Http404("Season not found") from err


def rankings_list(request):
    return render(request, "msa/rankings/list.html")


def players_list(request):
    return render(request, "msa/players/list.html")


def calendar(request):
    """
    Kalendář – respektuje ?season=<id>, jinak vybere sezónu dle aktivního data.
    """
    d = get_active_date(request)

    try:
        season = _get_season_by_query_param(request)
    except OperationalError:
        season = None

    if not season:
        try:
            season = find_season_for_date(d)
        except OperationalError:
            season = None

    if not season:
        return seasons_list(request)

    season_id = request.GET.get("season")
    if not season_id:
        season_id = getattr(season, "id", "")
    season_id = str(season_id) if season_id not in {None, ""} else ""

    tournaments: list[Any] = []
    Tournament = _get_tournament_model()
    if Tournament and season:
        try:
            qs = Tournament.objects.all()
            if _has_model_field(Tournament, "season"):
                qs = qs.filter(season=season)
            elif _has_model_field(Tournament, "start_date") and _has_model_field(
                Tournament, "end_date"
            ):
                if getattr(season, "start_date", None) and getattr(season, "end_date", None):
                    qs = qs.filter(
                        start_date__lte=season.end_date,
                        end_date__gte=season.start_date,
                    )
            try:
                qs = qs.select_related("category", "category__tour", "category_season")
            except Exception:
                qs = qs
            order_fields = []
            if _has_model_field(Tournament, "start_date"):
                order_fields.append("start_date")
            if _has_model_field(Tournament, "name"):
                order_fields.append("name")
            order_fields.append("id")
            tournaments = list(qs.order_by(*order_fields))
        except OperationalError:
            tournaments = []

    cards = [_tournament_card(request, tournament) for tournament in tournaments]

    month_sequence: list[int] = []
    start_iso = getattr(season, "start_date", None)
    end_iso = getattr(season, "end_date", None)
    if start_iso and end_iso:
        try:
            month_sequence = [
                int(value) for value in enumerate_fax_months(str(start_iso), str(end_iso))
            ]
        except Exception:
            month_sequence = []

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in cards:
        start_value = card.get("start_date")
        month_key = "Unknown"
        if start_value:
            parts = str(start_value).split("-")
            if len(parts) >= 2:
                try:
                    month_num = int(parts[1])
                except ValueError:
                    month_num = None
                if month_num:
                    month_key = str(month_num)
        groups[month_key].append(card)

    ordered_keys: list[str] = []
    if month_sequence:
        ordered_keys = [str(value) for value in month_sequence if str(value) in groups]
    remaining_keys = [key for key in groups.keys() if key not in ordered_keys and key != "Unknown"]
    ordered_keys.extend(sorted(remaining_keys, key=lambda x: int(x) if x.isdigit() else x))
    if "Unknown" in groups:
        ordered_keys.append("Unknown")

    month_groups: list[dict[str, Any]] = []
    for key in ordered_keys:
        items = groups.get(key, [])
        if key == "Unknown":
            label = "Neznámý měsíc"
        else:
            label = f"Měsíc {key}"
        month_groups.append(
            {
                "key": key,
                "label": label,
                "items": items,
                "count": len(items),
            }
        )

    context = {
        "active_season": season,
        "active_date": d,
        "season": season,
        "season_id": season_id,
        "month_groups": month_groups,
        "month_sequence": month_sequence,
        "cards": cards,
    }
    return render(request, "msa/calendar/index.html", context)


def media(request):
    return render(request, "msa/media/index.html")


def docs(request):
    return render(request, "msa/docs/index.html")


def search(request):
    return render(request, "msa/search/page.html")


def nav_live_badge(request):
    Match = apps.get_model("msa", "Match") if apps.is_installed("msa") else None
    live_count = 0
    if Match:
        try:
            qs = Match.objects.all()
            iterator = qs.iterator() if hasattr(qs, "iterator") else qs
            for match in iterator:
                try:
                    status, _ = _match_status_and_sets(match)
                except Exception:
                    continue
                if status == "live":
                    live_count += 1
        except OperationalError:
            live_count = 0
    if live_count > 0:
        badge = (
            '<span id="live-badge" aria-live="polite" '
            'class="ml-1 inline-flex items-center justify-center rounded-md border '
            'border-emerald-200 bg-emerald-50 px-2 text-xs font-medium text-emerald-700">'
            f"● {live_count}</span>"
        )
        return HttpResponse(badge)
    return HttpResponse('<span id="live-badge" class="ml-1 hidden" aria-hidden="true"></span>')


def tournament_info(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    entry_data = _entry_rows_for_tournament(tournament)
    context.update(
        {
            "active_tab": "info",
            "entry_summary": entry_data["summary"],
            "wc_usage": entry_data["summary"].get("wc", {}),
            "qwc_usage": entry_data["summary"].get("qwc", {}),
            "scoring_md_items": _scoring_items(getattr(tournament, "scoring_md", {})),
            "scoring_qual_items": _scoring_items(getattr(tournament, "scoring_qual_win", {})),
            "seeding_source": getattr(tournament, "seeding_source", None),
            "snapshot_label": getattr(tournament, "snapshot_label", None),
            "seeding_monday": _to_iso(getattr(tournament, "seeding_monday", None)),
            "rng_seed_active": getattr(tournament, "rng_seed_active", None),
        }
    )
    return render(request, "msa/tournament/info.html", context)


def tournament_program(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    context.update({"active_tab": "program"})

    matches_url = None
    courts_url = None
    if getattr(tournament, "id", None) is not None:
        try:
            matches_url = reverse("msa-tournament-matches-api", args=[tournament.id])
        except NoReverseMatch:
            matches_url = f"/api/msa/tournament/{tournament.id}/matches"
        try:
            courts_url = reverse("msa-tournament-courts-api", args=[tournament.id])
        except NoReverseMatch:
            courts_url = f"/api/msa/tournament/{tournament.id}/courts"

    context.update(
        {
            "matches_api_url": matches_url,
            "courts_api_url": courts_url,
        }
    )
    return render(request, "msa/tournament/program.html", context)


def tournament_draws(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    entry_data = _entry_rows_for_tournament(tournament)
    context.update(
        {
            "active_tab": "draws",
            "qualification_data": _qualification_structure(tournament, entry_data),
            "maindraw_data": _main_draw_structure(tournament, entry_data),
        }
    )
    return render(request, "msa/tournament/draws.html", context)


def tournament_players(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    entry_data = _entry_rows_for_tournament(tournament)
    context.update(
        {
            "active_tab": "players",
            "entry_summary": entry_data["summary"],
            "entry_blocks": entry_data["blocks"],
            "da_cut_index": entry_data["da_cut_index"],
        }
    )
    return render(request, "msa/tournament/players.html", context)


def tournament_scoring(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    entry_data = _entry_rows_for_tournament(tournament)
    context.update(
        {
            "active_tab": "scoring",
            "entry_summary": entry_data["summary"],
            "scoring_md_items": _scoring_items(getattr(tournament, "scoring_md", {})),
            "scoring_qual_items": _scoring_items(getattr(tournament, "scoring_qual_win", {})),
        }
    )
    return render(request, "msa/tournament/scoring.html", context)


def tournament_media(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    context.update({"active_tab": "media"})
    return render(request, "msa/tournament/media.html", context)


def season_api(request):
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    season_id = request.GET.get("id") or request.GET.get("season")
    data = {}

    if Season and season_id:
        season = Season.objects.filter(pk=season_id).first()
        if season:
            start = getattr(season, "start_date", None)
            end = getattr(season, "end_date", None)
            start_iso = _to_iso(start)
            end_iso = _to_iso(end)
            months = enumerate_fax_months(start_iso, end_iso) if start_iso and end_iso else []
            data = {
                "id": getattr(season, "id", None),
                "name": getattr(season, "name", None),
                "start_date": start_iso,
                "end_date": end_iso,
                "month_sequence": months,
            }

    return JsonResponse(data)


def tournaments_api(request):
    """
    JSON seznam turnajů. Preferuje sezonní filtr ?season=<id>.
    Robustně čte typické sloupce Tournament modelu; když nejsou, vrátí základ.
    """
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    Tournament = apps.get_model("msa", "Tournament") if apps.is_installed("msa") else None
    season_id = request.GET.get("season")

    items = []
    if Tournament:
        try:
            qs = Tournament.objects.all()
            fields = {f.name for f in Tournament._meta.get_fields()}
            # filtr podle sezony, pokud existuje FK season
            if season_id and "season" in fields:
                qs = qs.filter(season_id=season_id)
            # fallback: pokud nejsou sezony, ale jsou start/end a máme season interval
            elif (
                season_id
                and Season
                and {"start_date", "end_date"} <= {f.name for f in Season._meta.get_fields()}
                and {"start_date", "end_date"} <= fields
            ):
                try:
                    s = Season.objects.get(pk=season_id)
                    if getattr(s, "start_date", None) and getattr(s, "end_date", None):
                        qs = qs.filter(start_date__lte=s.end_date, end_date__gte=s.start_date)
                except (Season.DoesNotExist, OperationalError):
                    pass
            rels = []
            for fname in ("season", "category"):
                try:
                    field = Tournament._meta.get_field(fname)
                except (FieldDoesNotExist, AttributeError, LookupError):
                    continue
                if getattr(field, "is_relation", False) and isinstance(field, ForeignKey):
                    rels.append(fname)
            if rels:
                qs = qs.select_related(*rels)

            orderable = [fname for fname in ("start_date", "name") if fname in fields]
            if orderable:
                qs = qs.order_by(*orderable)

            def resolve_category(tournament):
                display = getattr(tournament, "get_category_display", None)
                if callable(display):
                    value = display()
                    if value not in (None, ""):
                        return str(value)

                category_attr = getattr(tournament, "category", None)
                if getattr(category_attr, "name", None):
                    return str(category_attr.name)
                if category_attr not in (None, ""):
                    return str(category_attr)

                tier_value = getattr(tournament, "tier", None)
                return "" if tier_value in (None, "") else str(tier_value)

            def resolve_tour(tournament, category_value: str) -> str:
                display = getattr(tournament, "get_tour_display", None)
                if callable(display):
                    value = display()
                    if value not in (None, ""):
                        return str(value)

                tour_attr = getattr(tournament, "tour", None)
                if getattr(tour_attr, "name", None):
                    return str(tour_attr.name)
                if tour_attr not in (None, ""):
                    return str(tour_attr)

                cat = (category_value or "").lower()
                world = {"diamond", "emerald", "platinum", "gold", "silver", "bronze"}
                elite = {"copper", "cobalt", "iron", "nickel", "tin", "zinc"}
                if any(x in cat for x in world):
                    return "World Tour"
                if any(x in cat for x in elite):
                    return "Elite Tour"
                if "challenger" in cat:
                    return "Challenger Tour"
                if "future" in cat or "isd" in cat:
                    return "Development Tour"
                return ""

            def build_url(tournament):
                get_absolute = getattr(tournament, "get_absolute_url", None)
                if callable(get_absolute):
                    try:
                        url_value = get_absolute()
                    except (TypeError, ValueError):
                        url_value = None
                    else:
                        if url_value:
                            return url_value

                if getattr(tournament, "id", None) is not None:
                    try:
                        return reverse("msa:tournament_detail", args=[tournament.id])
                    except NoReverseMatch:
                        return None
                return None

            for t in qs:
                start_attr = getattr(t, "start_date", None) or getattr(t, "start", None)
                end_attr = getattr(t, "end_date", None) or getattr(t, "end", None)
                category_value = resolve_category(t)
                row = {
                    "id": getattr(t, "id", None),
                    "name": getattr(t, "name", None) or getattr(t, "title", None),
                    "city": getattr(t, "city", None),
                    "country": getattr(t, "country", None),
                    "category": category_value,
                    "tour": resolve_tour(t, category_value),
                    "start_date": _to_iso(start_attr),
                    "end_date": _to_iso(end_attr),
                    "url": build_url(t),
                }
                items.append(row)
        except OperationalError:
            items = []
    return JsonResponse({"tournaments": items})


def ranking_api(request):
    """Return ranking entries for the frontend table."""
    return JsonResponse({"entries": []})


def tournament_matches_api(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    Match = apps.get_model("msa", "Match") if apps.is_installed("msa") else None
    Schedule = apps.get_model("msa", "Schedule") if apps.is_installed("msa") else None

    try:
        limit = min(max(int(request.GET.get("limit", 100)), 1), 500)
    except (TypeError, ValueError):
        limit = 100
    try:
        offset = max(int(request.GET.get("offset", 0)), 0)
    except (TypeError, ValueError):
        offset = 0

    def _base_response(matches: list[dict] | None = None) -> JsonResponse:
        return JsonResponse(
            {
                "matches": matches or [],
                "count": len(matches or []),
                "limit": limit,
                "offset": offset,
                "next_offset": None,
            }
        )

    if not Match:
        return _base_response([])

    def _model_has_field(model, field_name: str) -> bool:
        if not model:
            return False
        try:
            model._meta.get_field(field_name)
            return True
        except FieldDoesNotExist:
            return False

    def _combine_or(filters: list[Q]) -> Q | None:
        if not filters:
            return None
        combined = filters[0]
        for item in filters[1:]:
            combined |= item
        return combined

    def _serialize_court(candidate):
        if not candidate:
            return None
        if isinstance(candidate, dict):
            cid = candidate.get("id") or candidate.get("pk")
            name = (
                candidate.get("name")
                or candidate.get("label")
                or candidate.get("title")
                or candidate.get("court")
            )
            if cid is None and name is None and candidate:
                name = str(candidate)
            if cid is None and name is None:
                return None
            return {"id": cid, "name": name}
        if isinstance(candidate, str):
            cleaned = candidate.strip()
            if not cleaned:
                return None
            return {"id": None, "name": cleaned}
        cid = getattr(candidate, "id", None)
        name = getattr(candidate, "name", None)
        if name:
            return {"id": cid, "name": name}
        text = str(candidate)
        if text:
            return {"id": cid, "name": text}
        return None

    def _resolve_court(match, schedule):
        for obj in (schedule, match):
            if not obj:
                continue
            for attr in ("court", "court_name"):
                resolved = _serialize_court(getattr(obj, attr, None))
                if resolved:
                    return resolved
        score = getattr(match, "score", None)
        if isinstance(score, dict):
            for key in ("court", "court_name"):
                resolved = _serialize_court(score.get(key))
                if resolved:
                    return resolved
            meta = score.get("meta")
            if isinstance(meta, dict):
                for key in ("court", "court_name"):
                    resolved = _serialize_court(meta.get(key))
                    if resolved:
                        return resolved
        return None

    try:
        qs = Match.objects.filter(tournament=tournament)
        qs = qs.select_related(
            "schedule",
            "player1__country",
            "player2__country",
            "player_top__country",
            "player_bottom__country",
            "winner",
        )
    except OperationalError:
        qs = Match.objects.none()

    phase = request.GET.get("phase", "")
    if phase:
        phase_normalized = phase.strip().lower()
        if phase_normalized in {"md", "main", "main_draw"}:
            qs = qs.filter(phase__iexact="MD")
        elif phase_normalized in {"qual", "qualification", "q"}:
            qs = qs.filter(phase__iexact="QUAL")

    status_param = (request.GET.get("status", "") or "").strip().lower()
    status_filter = status_param if status_param not in {"", "all"} else None
    explicit_live_state = False
    try:
        state_field = Match._meta.get_field("state")
        explicit_live_state = any(
            str(choice[0]).upper() == "LIVE" for choice in getattr(state_field, "choices", [])
        )
    except FieldDoesNotExist:
        state_field = None

    if status_filter == "live":
        live_states = ["LIVE"] if explicit_live_state else ["SCHEDULED", "PENDING"]
        if state_field:
            qs = qs.filter(state__in=live_states)
    elif status_filter == "finished":
        if state_field:
            qs = qs.filter(state__in=["DONE"])
    elif status_filter == "scheduled":
        if state_field:
            qs = qs.filter(state__in=["SCHEDULED", "PENDING"])
    elif status_filter == "pending":
        if state_field:
            qs = qs.filter(state__in=["PENDING"])

    best_of_param = request.GET.get("best_of")
    if best_of_param and best_of_param not in {"default", ""}:
        if str(best_of_param).lower() == "win_only":
            # TODO: implement dedicated filter once "win only" matches are modeled explicitly.
            pass
        else:
            try:
                qs = qs.filter(best_of=int(best_of_param))
            except (TypeError, ValueError):
                pass

    fax_day_param = (request.GET.get("fax_day") or "").strip()
    if fax_day_param:
        day_filters = []
        if _model_has_field(Schedule, "play_date"):
            day_filters.append(Q(schedule__play_date=fax_day_param))
        if _model_has_field(Match, "play_date"):
            day_filters.append(Q(play_date=fax_day_param))
        combined = _combine_or(day_filters)
        if combined is not None:
            qs = qs.filter(combined)

    fax_month_param = request.GET.get("fax_month")
    if fax_month_param:
        try:
            month_int = int(fax_month_param)
        except (TypeError, ValueError):
            month_int = None
        if month_int and 1 <= month_int <= 15:
            mm = f"{month_int:02d}"
            month_re = rf"^\d{{4}}-{mm}-"
            month_filters = []
            if _model_has_field(Schedule, "play_date"):
                month_filters.append(Q(schedule__play_date__regex=month_re))
            if _model_has_field(Match, "play_date"):
                month_filters.append(Q(play_date__regex=month_re))
            combined = _combine_or(month_filters)
            if combined is not None:
                qs = qs.filter(combined)

    court_param = (request.GET.get("court") or "").strip()
    if court_param:
        court_filters = []
        if _model_has_field(Schedule, "court"):
            court_filters.extend(
                [
                    Q(schedule__court__id__iexact=court_param),
                    Q(schedule__court__name__icontains=court_param),
                    Q(schedule__court__iexact=court_param),
                ]
            )
        if _model_has_field(Schedule, "court_name"):
            court_filters.append(Q(schedule__court_name__icontains=court_param))
        if _model_has_field(Match, "court"):
            court_filters.extend(
                [
                    Q(court__id__iexact=court_param),
                    Q(court__name__icontains=court_param),
                    Q(court__iexact=court_param),
                ]
            )
        if _model_has_field(Match, "court_name"):
            court_filters.append(Q(court_name__icontains=court_param))
        # Fallback for court information stored in JSON score payloads.
        court_filters.extend(
            [
                Q(score__court__id__iexact=court_param),
                Q(score__court__name__icontains=court_param),
                Q(score__court__icontains=court_param),
                Q(score__meta__court__id__iexact=court_param),
                Q(score__meta__court__name__icontains=court_param),
            ]
        )
        combined = _combine_or(court_filters)
        if combined is not None:
            qs = qs.filter(combined)

    search_param = (request.GET.get("q") or "").strip()
    if search_param:
        search_filters = [
            Q(player1__full_name__icontains=search_param),
            Q(player1__name__icontains=search_param),
            Q(player2__full_name__icontains=search_param),
            Q(player2__name__icontains=search_param),
            Q(player_top__full_name__icontains=search_param),
            Q(player_top__name__icontains=search_param),
            Q(player_bottom__full_name__icontains=search_param),
            Q(player_bottom__name__icontains=search_param),
            Q(round_name__icontains=search_param),
            Q(round__icontains=search_param),
        ]
        if _model_has_field(Match, "notes"):
            search_filters.append(Q(notes__icontains=search_param))
        combined = _combine_or(search_filters)
        if combined is not None:
            qs = qs.filter(combined)

    ordering_fields = []
    if _model_has_field(Schedule, "play_date"):
        ordering_fields.append("schedule__play_date")
    if _model_has_field(Match, "play_date"):
        ordering_fields.append("play_date")
    if _model_has_field(Schedule, "court"):
        ordering_fields.append("schedule__court__name")
    if _model_has_field(Schedule, "court_name"):
        ordering_fields.append("schedule__court_name")
    if _model_has_field(Match, "court"):
        ordering_fields.append("court__name")
    if _model_has_field(Match, "court_name"):
        ordering_fields.append("court_name")
    if _model_has_field(Schedule, "order"):
        ordering_fields.append("schedule__order")
    if _model_has_field(Match, "position"):
        ordering_fields.append("position")
    ordering_fields.append("id")

    seen = []
    final_ordering = []
    for field in ordering_fields:
        if field not in seen:
            seen.append(field)
            final_ordering.append(field)
    qs = qs.order_by(*final_ordering) if final_ordering else qs.order_by("id")

    matches = []
    raw_matches = list(qs)

    for match in raw_matches:
        schedule = getattr(match, "schedule", None)
        fax_day_raw = getattr(schedule, "play_date", None) or getattr(match, "play_date", None)
        if isinstance(fax_day_raw, str):
            fax_day_raw = fax_day_raw.strip() or None
        fax_day = _to_iso(fax_day_raw) if fax_day_raw else None
        order_value = getattr(schedule, "order", None)
        if order_value is None:
            order_value = getattr(match, "position", None)

        player_candidates = [
            getattr(match, "player1", None) or getattr(match, "player_top", None),
            getattr(match, "player2", None) or getattr(match, "player_bottom", None),
        ]

        players = []
        for player in player_candidates:
            if not player:
                continue
            name = (
                getattr(player, "full_name", None) or getattr(player, "name", None) or str(player)
            )
            country = getattr(getattr(player, "country", None), "iso3", None) or getattr(
                getattr(player, "country", None), "name", None
            )
            players.append({"id": getattr(player, "id", None), "name": name, "country": country})

        state_value = (getattr(match, "state", None) or "").upper()
        base_status, sets = _match_status_and_sets(match)

        phase_value = (getattr(match, "phase", None) or "").lower()
        if phase_value in {"qual", "qualification"}:
            phase_value = "qual"
        elif phase_value in {"md", "main", "main_draw"}:
            phase_value = "md"

        if status_filter == "live" and base_status != "live":
            continue
        if status_filter == "finished" and base_status != "finished":
            continue
        if status_filter == "scheduled" and base_status != "scheduled":
            continue
        if status_filter == "pending" and state_value != "PENDING":
            continue

        court_value = _resolve_court(match, schedule)

        matches.append(
            {
                "id": getattr(match, "id", None),
                "phase": phase_value,
                "round_label": getattr(match, "round_name", None) or getattr(match, "round", None),
                "court": court_value,
                "fax_day": fax_day,
                "order": order_value,
                "players": players,
                "best_of": getattr(match, "best_of", None),
                "sets": sets,
                "winner_id": getattr(match, "winner_id", None),
                "status": base_status,
                "needs_review": bool(getattr(match, "needs_review", False)),
            }
        )

    def _sort_key(item):
        fax_day_val = str(item.get("fax_day") or "")
        court_val = item.get("court")
        if isinstance(court_val, dict):
            court_key = court_val.get("name") or court_val.get("id") or ""
        else:
            court_key = court_val or ""
        order_val = item.get("order")
        try:
            order_key = int(order_val)
        except (TypeError, ValueError):
            order_key = 10**6
        return (fax_day_val, str(court_key), order_key, item.get("id") or 0)

    matches.sort(key=_sort_key)

    total = len(matches)
    paginated = matches[offset : offset + limit]
    next_offset = offset + limit if offset + limit < total else None

    return JsonResponse(
        {
            "matches": paginated,
            "count": total,
            "limit": limit,
            "offset": offset,
            "next_offset": next_offset,
        }
    )


def tournament_courts_api(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    Match = apps.get_model("msa", "Match") if apps.is_installed("msa") else None
    if not Match:
        return JsonResponse({"courts": []})

    try:
        qs = Match.objects.filter(tournament=tournament).select_related("schedule")
    except OperationalError:
        return JsonResponse({"courts": []})

    seen = set()
    courts = []

    def _append_court(candidate):
        if not candidate:
            return
        if isinstance(candidate, dict):
            cid = candidate.get("id")
            name = candidate.get("name")
        else:
            cid = getattr(candidate, "id", None)
            name = getattr(candidate, "name", None) or (str(candidate) if candidate else None)
        name_value = name or ""
        key = (cid, name_value)
        if (cid is None and not name_value) or key in seen:
            return
        seen.add(key)
        courts.append({"id": cid, "name": name})

    for match in qs:
        for attr in ("court", "court_name"):
            _append_court(getattr(match, attr, None))
        score_payload = getattr(match, "score", None)
        if isinstance(score_payload, dict):
            for key in ("court", "court_name"):
                _append_court(score_payload.get(key))
            meta = score_payload.get("meta")
            if isinstance(meta, dict):
                for key in ("court", "court_name"):
                    _append_court(meta.get(key))
        schedule = getattr(match, "schedule", None)
        if schedule:
            for attr in ("court", "court_name"):
                _append_court(getattr(schedule, attr, None))

    def _sort_key(court):
        if not isinstance(court, dict):
            return ("", "")
        raw_name = court.get("name")
        if isinstance(raw_name, str):
            cleaned_name = raw_name.strip()
        elif raw_name is None:
            cleaned_name = ""
        else:
            cleaned_name = str(raw_name).strip()
        name_key = cleaned_name.casefold()
        raw_id = court.get("id")
        id_key = "" if raw_id in (None, "") else str(raw_id)
        return (name_key, id_key)

    courts.sort(key=_sort_key)

    return JsonResponse({"courts": courts})


def tournament_entries_api(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    entry_data = _entry_rows_for_tournament(tournament)
    summary = entry_data["summary"]

    def serialize(
        rows: list[dict[str, Any]], extra: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for row in rows:
            payload = _entry_payload(row) or {}
            payload.update(
                {
                    "wr": row.get("wr"),
                    "license_ok": row.get("license_ok"),
                    "position": row.get("position"),
                }
            )
            if extra:
                for key, func in extra.items():
                    payload[key] = func(row)
            payloads.append(payload)
        return payloads

    response = {
        "summary": {
            "S": summary.get("seeds", 0),
            "D": summary.get("direct_acceptances") or 0,
            "Q_draw_size": summary.get("qual_draw_size", 0),
            "wc": {
                "used": int(summary.get("wc", {}).get("used", 0)),
                "limit": int(summary.get("wc", {}).get("limit", 0)),
            },
            "qwc": {
                "used": int(summary.get("qwc", {}).get("used", 0)),
                "limit": int(summary.get("qwc", {}).get("limit", 0)),
            },
        },
        "blocks": {
            "seeds": serialize(entry_data["blocks"].get("seeds", [])),
            "da": serialize(
                entry_data["blocks"].get("da", []),
                extra={"wc_label": lambda row: bool(row.get("is_wc"))},
            ),
            "q": serialize(
                entry_data["blocks"].get("q", []),
                extra={"qwc_label": lambda row: bool(row.get("is_qwc"))},
            ),
            "reserve": serialize(entry_data["blocks"].get("reserve", [])),
        },
        "meta": {
            "total": summary.get("total", 0),
            "da_cut_index": entry_data.get("da_cut_index", 0),
        },
    }
    return JsonResponse(response)


def tournament_qualification_api(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    entry_data = _entry_rows_for_tournament(tournament)
    data = _qualification_structure(tournament, entry_data)
    return JsonResponse(data)


def tournament_maindraw_api(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    entry_data = _entry_rows_for_tournament(tournament)
    data = _main_draw_structure(tournament, entry_data)
    data["summary"] = entry_data["summary"]
    return JsonResponse(data)


def tournament_history_api(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    Snapshot = apps.get_model("msa", "Snapshot") if apps.is_installed("msa") else None
    snapshots: list[dict[str, Any]] = []
    if Snapshot:
        try:
            qs = Snapshot.objects.filter(tournament=tournament).order_by("-created_at")
            for snap in qs:
                payload = snap.payload if isinstance(snap.payload, dict) else {}
                rng_seed = payload.get("rng_seed")
                created_at = getattr(snap, "created_at", None)
                snapshots.append(
                    {
                        "id": getattr(snap, "id", None),
                        "type": getattr(snap, "type", None),
                        "rng_seed": rng_seed if rng_seed not in {"", None} else None,
                        "ts": created_at.isoformat() if created_at else None,
                    }
                )
        except OperationalError:
            snapshots = []

    return JsonResponse({"snapshots": snapshots})
