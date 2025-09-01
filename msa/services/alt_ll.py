import logging
from typing import List, Tuple, Dict

from django.db import transaction, connection, IntegrityError
from django.db.models import Q

from ..models import (
    Match,
    RankingSnapshot,
    Tournament,
    TournamentEntry,
)
from .draw import replace_slot

logger = logging.getLogger(__name__)


def _get_snapshot(tournament: Tournament):
    snap = None
    if tournament.seeding_rank_date:
        snap = (
            RankingSnapshot.objects.filter(as_of__lte=tournament.seeding_rank_date)
            .order_by("-as_of")
            .first()
        )
    if not snap:
        snap = RankingSnapshot.objects.order_by("-as_of").first()
    return snap


@transaction.atomic
def auto_fill_with_alternates(tournament: Tournament, *, limit=None, user=None) -> Dict:
    entries = tournament.entries.select_for_update().select_related("player")
    occupied = set(
        entries.filter(position__isnull=False, status="active").values_list(
            "position", flat=True
        )
    )
    draw_size = tournament.draw_size or 0
    free = sorted(p for p in range(1, draw_size + 1) if p not in occupied)
    alts = [
        e
        for e in entries
        if e.entry_type == TournamentEntry.EntryType.ALT
        and e.status == TournamentEntry.Status.ACTIVE
        and e.position is None
    ]
    if not free or not alts:
        logger.info(
            "alt.autofill tournament=%s user=%s added=0",
            tournament.id,
            getattr(user, "id", None),
        )
        return {"filled": 0}
    snap = _get_snapshot(tournament)
    rank_map = {}
    if snap:
        rank_map = {re.player_id: re.rank for re in snap.entries.all()}
    alts.sort(
        key=lambda e: (
            rank_map.get(e.player_id, 10**9),
            e.seed if e.seed is not None else 10**9,
            e.player.name,
        )
    )
    filled = 0
    for slot, entry in zip(free, alts):
        if limit is not None and filled >= limit:
            break
        entry.position = slot
        if user:
            entry.updated_by = user
            entry.save(update_fields=["position", "updated_by"])
        else:
            entry.save(update_fields=["position"])
        filled += 1
    logger.info(
        "alt.autofill tournament=%s user=%s added=%s",
        tournament.id,
        getattr(user, "id", None),
        filled,
    )
    return {"filled": filled}


def _rank_key(entry: TournamentEntry, rank_map):
    return (
        rank_map.get(entry.player_id, 10**9),
        entry.seed if entry.seed is not None else 10**9,
        entry.player.name,
    )


def select_ll_candidates(
    tournament: Tournament, count: int
) -> List[Tuple[TournamentEntry, Match]]:
    qs = tournament.matches.filter(round__startswith="Q").select_related(
        "winner", "player1", "player2"
    )
    if not qs.exists():
        return []
    last = min(int(m.round[1:]) for m in qs)
    finals = qs.filter(round=f"Q{last}", winner__isnull=False)
    entries_q = {
        e.player_id: e
        for e in tournament.entries.filter(
            entry_type=TournamentEntry.EntryType.Q, status="active"
        ).select_related("player")
    }
    candidates: List[Tuple[TournamentEntry, Match]] = []
    for m in finals:
        loser = m.player1 if m.winner_id == m.player2_id else m.player2
        entry = entries_q.get(loser.id)
        if not entry:
            continue
        if tournament.entries.filter(
            player=loser, status="active", position__isnull=False
        ).exists():
            continue
        candidates.append((entry, m))
    if not candidates:
        return []
    snap = _get_snapshot(tournament)
    rank_map = {}
    if snap:
        rank_map = {re.player_id: re.rank for re in snap.entries.all()}
    candidates.sort(key=lambda item: _rank_key(item[0], rank_map))
    return candidates[:count]


@transaction.atomic
def promote_lucky_losers_to_slot(
    tournament: Tournament, slot: int, *, user=None
) -> bool:
    entries = tournament.entries.select_for_update().select_related("player")
    current = (
        entries.filter(position=slot, status="active").select_related("player").first()
    )
    candidates = select_ll_candidates(tournament, 1)
    if not candidates:
        logger.info(
            "ll.promote tournament=%s user=%s slot=%s ok=%s",
            tournament.id,
            getattr(user, "id", None),
            slot,
            False,
        )
        return False
    entry, origin_match = candidates[0]
    if (
        current
        and current.player_id == entry.player_id
        and current.entry_type == TournamentEntry.EntryType.LL
    ):
        return True
    mate_slot = slot + 1 if slot % 2 else slot - 1
    mate = (
        entries.filter(position=mate_slot, status="active")
        .select_related("player")
        .first()
    )
    match = None
    if current or mate:
        match_qs = tournament.matches.select_for_update().filter(
            round=f"R{tournament.draw_size}"
        )
        if current:
            match_qs = match_qs.filter(
                Q(player1=current.player) | Q(player2=current.player)
            )
        if mate:
            match_qs = match_qs.filter(Q(player1=mate.player) | Q(player2=mate.player))
        match = match_qs.first()
        if match and match.winner_id and not tournament.flex_mode:
            logger.info(
                "ll.promote tournament=%s user=%s slot=%s ok=%s",
                tournament.id,
                getattr(user, "id", None),
                slot,
                False,
            )
            return False
    entry.entry_type = TournamentEntry.EntryType.LL
    entry.origin_note = "LL"
    entry.origin_match = origin_match
    if current:
        ok = replace_slot(
            tournament,
            slot,
            entry.pk,
            allow_over_completed=tournament.flex_mode,
            user=user,
        )
        if not ok:
            logger.info(
                "ll.promote tournament=%s user=%s slot=%s ok=%s",
                tournament.id,
                getattr(user, "id", None),
                slot,
                False,
            )
            return False
        if user:
            entry.updated_by = user
            entry.save(
                update_fields=[
                    "entry_type",
                    "origin_note",
                    "origin_match",
                    "updated_by",
                ]
            )
        else:
            entry.save(update_fields=["entry_type", "origin_note", "origin_match"])
    else:
        if mate and match and not match.winner_id:
            if slot < mate_slot:
                match.player1 = entry.player
                match.player2 = mate.player
            else:
                match.player1 = mate.player
                match.player2 = entry.player
            match.save(update_fields=["player1", "player2"])
        entry.status = TournamentEntry.Status.ACTIVE
        entry.position = slot
        if user:
            entry.updated_by = user
            entry.save(
                update_fields=[
                    "entry_type",
                    "status",
                    "position",
                    "origin_note",
                    "origin_match",
                    "updated_by",
                ]
            )
        else:
            entry.save(
                update_fields=[
                    "entry_type",
                    "status",
                    "position",
                    "origin_note",
                    "origin_match",
                ]
            )
    logger.info(
        "ll.promote tournament=%s user=%s slot=%s ok=%s",
        tournament.id,
        getattr(user, "id", None),
        slot,
        True,
    )
    return True


@transaction.atomic
def withdraw_slot_and_fill_ll(tournament: Tournament, slot: int, *, user=None) -> bool:
    entries = tournament.entries.select_for_update().select_related("player")
    current = (
        entries.filter(position=slot, status="active").select_related("player").first()
    )
    if current:
        mate_slot = slot + 1 if slot % 2 else slot - 1
        mate = (
            entries.filter(position=mate_slot, status="active")
            .select_related("player")
            .first()
        )
        match = None
        if mate:
            match = (
                tournament.matches.select_for_update()
                .filter(
                    player1__in=[current.player, mate.player],
                    player2__in=[current.player, mate.player],
                    round=f"R{tournament.draw_size}",
                )
                .first()
            )
            if match and match.winner_id and not tournament.flex_mode:
                return False
        current.status = TournamentEntry.Status.WITHDRAWN
        current.position = None
        if user:
            current.updated_by = user
            current.save(update_fields=["status", "position", "updated_by"])
        else:
            current.save(update_fields=["status", "position"])
    return promote_lucky_losers_to_slot(tournament, slot, user=user)
