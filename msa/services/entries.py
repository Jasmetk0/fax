import logging
from typing import Dict, List, Tuple

from django.db import IntegrityError, transaction
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
