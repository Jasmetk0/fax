import logging
from typing import Dict, List, Tuple

from django.db import IntegrityError, transaction
from django.db.models import Q
from ..models import Player, Tournament, TournamentEntry


logger = logging.getLogger(__name__)


MAIN_TYPES = {
    TournamentEntry.EntryType.DA,
    TournamentEntry.EntryType.WC,
    TournamentEntry.EntryType.Q,
}


def compute_capacity(tournament: Tournament) -> Dict[str, int]:
    """Compute capacity counters for a tournament.

    Must be called inside a transaction; locks all entries for update to
    guarantee consistent counts under concurrent modifications.
    """

    entries = tournament.entries.select_for_update()
    active_main = entries.filter(
        status=TournamentEntry.Status.ACTIVE, entry_type__in=MAIN_TYPES
    ).count()
    alt = entries.filter(
        status=TournamentEntry.Status.ACTIVE,
        entry_type=TournamentEntry.EntryType.ALT,
    ).count()
    withdrawn = entries.filter(status=TournamentEntry.Status.WITHDRAWN).count()
    return {
        "active_main": active_main,
        "alt": alt,
        "withdrawn": withdrawn,
        "draw_size": tournament.draw_size or 0,
    }


def add_entry(
    tournament: Tournament, player: Player, entry_type: str, user
) -> Tuple[bool, str]:
    """Add a player entry to the tournament."""

    with transaction.atomic():
        if tournament.state not in {
            Tournament.State.DRAFT,
            Tournament.State.ENTRY_OPEN,
        }:
            msg = "Entries locked"
            logger.info(
                "entries.action",
                user_id=user.id,
                tournament_id=tournament.id,
                action="add",
                params={"player_id": player.id, "entry_type": entry_type},
                result="blocked",
            )
            return False, msg
        entry_type = entry_type.upper()
        cap = compute_capacity(tournament)
        if tournament.entries.filter(player=player).exists():
            msg = "Player already entered"
            logger.info(
                "entries.action",
                user_id=user.id,
                tournament_id=tournament.id,
                action="add",
                params={"player_id": player.id, "entry_type": entry_type},
                result="duplicate",
            )
            return False, msg
        final_type = entry_type
        message = "Entry added"
        if entry_type in MAIN_TYPES and cap["active_main"] >= cap["draw_size"]:
            final_type = TournamentEntry.EntryType.ALT
            message = "Draw full; entry set as ALT"
        try:
            TournamentEntry.objects.create(
                tournament=tournament,
                player=player,
                entry_type=final_type,
                created_by=user,
                updated_by=user,
            )
        except IntegrityError:
            msg = "Player already entered"
            logger.info(
                "entries.action",
                user_id=user.id,
                tournament_id=tournament.id,
                action="add",
                params={"player_id": player.id, "entry_type": entry_type},
                result="duplicate",
            )
            return False, msg
        logger.info(
            "entries.action",
            user_id=user.id,
            tournament_id=tournament.id,
            action="add",
            params={"player_id": player.id, "entry_type": entry_type},
            result=message,
        )
        return True, message


def bulk_add_entries(tournament: Tournament, csv_text: str, user) -> Dict[str, object]:
    """Bulk import entries from CSV text."""

    added = skipped = errors = 0
    messages: List[str] = []
    for line in csv_text.splitlines():
        row = line.strip()
        if not row or row.startswith("#"):
            continue
        parts = [p.strip() for p in row.split(",")]
        try:
            player_id = int(parts[0])
        except ValueError:
            errors += 1
            messages.append(f"Invalid player id: {parts[0] if parts else row}")
            continue
        player = Player.objects.filter(pk=player_id).first()
        if not player:
            errors += 1
            messages.append(f"Player {player_id} not found")
            continue
        entry_type = parts[1].upper() if len(parts) > 1 else "DA"
        if entry_type not in TournamentEntry.EntryType.values:
            errors += 1
            messages.append(f"Unknown type '{entry_type}' for player {player_id}")
            continue
        ok, msg = add_entry(tournament, player, entry_type, user)
        if ok:
            added += 1
        else:
            skipped += 1
        messages.append(msg)
    summary = {
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "messages": messages,
    }
    logger.info(
        "entries.action",
        user_id=user.id,
        tournament_id=tournament.id,
        action="bulk_add",
        params={"rows": len(csv_text.splitlines())},
        result=summary,
    )
    return summary


def update_entry_type(entry: TournamentEntry, new_type: str, user) -> Tuple[bool, str]:
    """Update entry type for a tournament entry."""

    with transaction.atomic():
        entry = TournamentEntry.objects.select_for_update().get(pk=entry.pk)
        tournament = entry.tournament
        if tournament.state not in {
            Tournament.State.DRAFT,
            Tournament.State.ENTRY_OPEN,
        }:
            msg = "Entries locked"
            logger.info(
                "entries.action",
                user_id=user.id,
                tournament_id=tournament.id,
                action="update_type",
                params={"entry_id": entry.id, "entry_type": new_type},
                result="blocked",
            )
            return False, msg
        new_type = new_type.upper()
        cap = compute_capacity(tournament)
        final_type = new_type
        message = "Entry type updated"
        if new_type in MAIN_TYPES and cap["active_main"] >= cap["draw_size"]:
            final_type = TournamentEntry.EntryType.ALT
            message = "Draw full; entry set as ALT"
        entry.entry_type = final_type
        entry.updated_by = user
        entry.save(update_fields=["entry_type", "updated_by"])
        logger.info(
            "entries.action",
            user_id=user.id,
            tournament_id=tournament.id,
            action="update_type",
            params={"entry_id": entry.id, "entry_type": new_type},
            result=message,
        )
        return True, message


def set_entry_status(entry: TournamentEntry, status: str, user) -> Tuple[bool, str]:
    """Set status for a tournament entry."""

    with transaction.atomic():
        entry = TournamentEntry.objects.select_for_update().get(pk=entry.pk)
        tournament = entry.tournament
        desired = status
        if desired == TournamentEntry.Status.WITHDRAWN:
            entry.status = TournamentEntry.Status.WITHDRAWN
            entry.updated_by = user
            entry.save(update_fields=["status", "updated_by"])
            message = "Entry withdrawn"
            logger.info(
                "entries.action",
                user_id=user.id,
                tournament_id=tournament.id,
                action="set_status",
                params={"entry_id": entry.id, "status": desired},
                result=message,
            )
            return True, message
        if tournament.state not in {
            Tournament.State.DRAFT,
            Tournament.State.ENTRY_OPEN,
        }:
            msg = "Entries locked"
            logger.info(
                "entries.action",
                user_id=user.id,
                tournament_id=tournament.id,
                action="set_status",
                params={"entry_id": entry.id, "status": desired},
                result="blocked",
            )
            return False, msg
        cap = compute_capacity(tournament)
        message = "Entry reactivated"
        final_type = entry.entry_type
        if entry.entry_type in MAIN_TYPES and cap["active_main"] >= cap["draw_size"]:
            final_type = TournamentEntry.EntryType.ALT
            message = "Draw full; entry set as ALT"
        entry.status = TournamentEntry.Status.ACTIVE
        entry.entry_type = final_type
        entry.updated_by = user
        entry.save(update_fields=["status", "entry_type", "updated_by"])
        logger.info(
            "entries.action",
            user_id=user.id,
            tournament_id=tournament.id,
            action="set_status",
            params={"entry_id": entry.id, "status": desired},
            result=message,
        )
        return True, message


def lock_entries(tournament: Tournament, user) -> Tuple[bool, str]:
    with transaction.atomic():
        t = Tournament.objects.select_for_update().get(pk=tournament.pk)
        if t.state not in {Tournament.State.DRAFT, Tournament.State.ENTRY_OPEN}:
            msg = "Cannot lock entries"
            logger.info(
                "entries.action",
                user_id=user.id,
                tournament_id=t.id,
                action="lock",
                params={},
                result="blocked",
            )
            return False, msg
        t.state = Tournament.State.ENTRY_LOCKED
        t.updated_by = user
        t.save(update_fields=["state", "updated_by"])
    logger.info(
        "entries.action",
        user_id=user.id,
        tournament_id=tournament.id,
        action="lock",
        params={},
        result="locked",
    )
    return True, "Entries locked"


def unlock_entries(tournament: Tournament, user) -> Tuple[bool, str]:
    with transaction.atomic():
        t = Tournament.objects.select_for_update().get(pk=tournament.pk)
        if (
            t.state
            in {
                Tournament.State.DRAWN,
                Tournament.State.LIVE,
                Tournament.State.COMPLETE,
            }
            or t.state != Tournament.State.ENTRY_LOCKED
        ):
            msg = "Cannot unlock entries"
            logger.info(
                "entries.action",
                user_id=user.id,
                tournament_id=t.id,
                action="unlock",
                params={},
                result="blocked",
            )
            return False, msg
        t.state = Tournament.State.ENTRY_OPEN
        t.updated_by = user
        t.save(update_fields=["state", "updated_by"])
    logger.info(
        "entries.action",
        user_id=user.id,
        tournament_id=tournament.id,
        action="unlock",
        params={},
        result="unlocked",
    )
    return True, "Entries unlocked"


def validate_pre_draw(tournament: Tournament) -> Dict[str, List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    with transaction.atomic():
        entries = list(tournament.entries.select_for_update().select_related("player"))
        cap = compute_capacity(tournament)
    if cap["active_main"] > cap["draw_size"]:
        errors.append("Main draw capacity exceeded")
    elif cap["active_main"] < cap["draw_size"]:
        warnings.append("Main draw not full")
    seeds_total = tournament.seeds_count or 0
    all_seeds = [e.seed for e in entries if e.seed]
    if any(s < 1 or s > seeds_total for s in all_seeds):
        errors.append("Seed out of range")
    active_seeds = [
        e.seed for e in entries if e.status == TournamentEntry.Status.ACTIVE and e.seed
    ]
    if len(active_seeds) != len(set(active_seeds)):
        errors.append("Duplicate seeds")
    if len(set(active_seeds)) < seeds_total:
        warnings.append("Missing seeds")
    if len(set(active_seeds)) > seeds_total:
        errors.append("Too many seeds")
    if tournament.entries.filter(
        ~Q(status=TournamentEntry.Status.ACTIVE), seed__isnull=False
    ).exists():
        errors.append("Seeded entry not active")
    if tournament.seeding_method != "manual":
        warnings.append("Seeding method not manual; seeds may be ignored")
    return {"errors": errors, "warnings": warnings}


def set_seed(entry: TournamentEntry, seed, user) -> Tuple[bool, str]:
    with transaction.atomic():
        entry = TournamentEntry.objects.select_for_update().get(pk=entry.pk)
        tournament = entry.tournament
        if not (tournament.seeding_method == "manual" or tournament.flex_mode):
            msg = "Seeding not editable"
            logger.info(
                "entries.action",
                user_id=user.id,
                tournament_id=tournament.id,
                action="set_seed",
                params={"entry_id": entry.id, "seed": seed},
                result="blocked",
            )
            return False, msg
        if entry.status != TournamentEntry.Status.ACTIVE:
            msg = "Entry not active"
            logger.info(
                "entries.action",
                user_id=user.id,
                tournament_id=tournament.id,
                action="set_seed",
                params={"entry_id": entry.id, "seed": seed},
                result="inactive",
            )
            return False, msg
        if seed is not None:
            if seed < 1 or seed > tournament.seeds_count:
                msg = "Seed out of range"
                logger.info(
                    "entries.action",
                    user_id=user.id,
                    tournament_id=tournament.id,
                    action="set_seed",
                    params={"entry_id": entry.id, "seed": seed},
                    result="range",
                )
                return False, msg
            conflict = (
                tournament.entries.select_for_update()
                .filter(seed=seed)
                .exclude(pk=entry.pk)
                .exists()
            )
            if conflict:
                msg = "Seed already taken"
                logger.info(
                    "entries.action",
                    user_id=user.id,
                    tournament_id=tournament.id,
                    action="set_seed",
                    params={"entry_id": entry.id, "seed": seed},
                    result="duplicate",
                )
                return False, msg
        entry.seed = seed
        entry.updated_by = user
        entry.save(update_fields=["seed", "updated_by"])
    result_msg = "Seed updated"
    if tournament.seeding_method != "manual" and tournament.flex_mode:
        result_msg += "; warning: seeding method not manual"
    logger.info(
        "entries.action",
        user_id=user.id,
        tournament_id=entry.tournament_id,
        action="set_seed",
        params={"entry_id": entry.id, "seed": seed},
        result=result_msg,
    )
    return True, result_msg


def bulk_set_seeds(
    tournament: Tournament, mapping: Dict[int, int], user
) -> Dict[str, object]:
    updated = 0
    errors: Dict[int, str] = {}
    with transaction.atomic():
        entries_qs = tournament.entries.select_for_update()
        if not (tournament.seeding_method == "manual" or tournament.flex_mode):
            for eid in mapping.keys():
                errors[eid] = "Seeding not editable"
            logger.info(
                "entries.action",
                user_id=user.id,
                tournament_id=tournament.id,
                action="bulk_set_seeds",
                params={"count": len(mapping)},
                result={"updated": 0, "errors": errors},
            )
            return {"updated": 0, "errors": errors}
        used = set(
            entries_qs.exclude(pk__in=mapping.keys())
            .filter(seed__isnull=False)
            .values_list("seed", flat=True)
        )
        for eid, seed in mapping.items():
            entry = entries_qs.filter(pk=eid).first()
            if not entry:
                errors[eid] = "Entry not found"
                continue
            if entry.status != TournamentEntry.Status.ACTIVE:
                errors[eid] = "Entry not active"
                continue
            if seed is not None and (seed < 1 or seed > tournament.seeds_count):
                errors[eid] = "Seed out of range"
                continue
            if seed in used:
                errors[eid] = "Seed already taken"
                continue
            entry.seed = seed
            entry.updated_by = user
            entry.save(update_fields=["seed", "updated_by"])
            updated += 1
            if seed is not None:
                used.add(seed)
    result = {"updated": updated, "errors": errors}
    logger.info(
        "entries.action",
        user_id=user.id,
        tournament_id=tournament.id,
        action="bulk_set_seeds",
        params={"count": len(mapping)},
        result=result,
    )
    return result


def export_entries_csv(tournament: Tournament) -> str:
    import csv
    from io import StringIO
    from django.db.models import Case, IntegerField, When

    order = [
        Case(
            When(status=TournamentEntry.Status.ACTIVE, then=0),
            When(status=TournamentEntry.Status.WITHDRAWN, then=1),
            When(status=TournamentEntry.Status.REPLACED, then=2),
            output_field=IntegerField(),
        ),
        "entry_type",
        "seed",
        "player__name",
    ]
    entries = tournament.entries.select_related("player").order_by(*order)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "player_id",
            "player_name",
            "entry_type",
            "status",
            "seed",
            "position",
            "origin_note",
        ]
    )
    for e in entries:
        writer.writerow(
            [
                e.player_id,
                e.player.name,
                e.entry_type,
                e.status,
                e.seed or "",
                e.position or "",
                e.origin_note or "",
            ]
        )
    return output.getvalue()
