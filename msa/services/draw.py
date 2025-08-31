import logging
from math import ceil, log2
from typing import Dict, List

from django.conf import settings
from django.db import transaction
from ..models import Match, TournamentEntry


logger = logging.getLogger(__name__)


def _generate_draw_legacy(tournament, force: bool = False):
    """Placeholder for legacy draw generation."""
    return None


def _build_seed_positions(size: int) -> List[int]:
    """Return list mapping seed index -> slot for power-of-two size."""

    if size == 1:
        return [1]
    prev = _build_seed_positions(size // 2)
    result: List[int] = []
    for p in prev:
        result.append(p)
        result.append(size + 1 - p)
    return result


# Pre-computed seeding maps for standard draw sizes
SEED_POSITIONS: Dict[int, Dict[int, int]] = {
    n: {i + 1: pos for i, pos in enumerate(_build_seed_positions(n))}
    for n in (32, 64, 128)
}


DEFAULT_SEEDS = {32: 8, 64: 16, 96: 32, 128: 32}


def pair_first_round_slots(bracket_size: int) -> list[tuple[int, int]]:
    """Return slot pairs for the first round."""

    return [(i, i + 1) for i in range(1, bracket_size + 1, 2)]


def _sort_entries(entries: List, method: str) -> List:
    if method in {"manual", "ranking_snapshot"}:
        # ranking_snapshot fallback behaves like manual for now
        entries.sort(
            key=lambda e: (e.seed is None, e.seed or 0, e.player.id, e.player.name)
        )
        return entries
    if method in {"random", "local_rating"}:
        raise NotImplementedError("Seeding method not implemented")
    return entries


def _next_pow2(n: int) -> int:
    return 1 << ceil(log2(n))


def _seed_map_for_draw(
    draw_size: int, seeds_count: int
) -> (Dict[int, int], List[int], List[int]):
    """Return mapping of seed -> slot, all slots, and playable slots."""

    if draw_size == 96:
        mapping_128 = SEED_POSITIONS[128]
        slots = list(range(1, 129))
        seed_map = {s: mapping_128[s] for s in range(1, seeds_count + 1)}
        byes = {(p + 1) if p % 2 else (p - 1) for p in seed_map.values()}
        playable = [p for p in slots if p not in byes and p not in seed_map.values()]
        return seed_map, slots, playable
    slots = list(range(1, draw_size + 1))
    mapping = SEED_POSITIONS.get(draw_size, {})
    seed_map = {s: mapping[s] for s in range(1, seeds_count + 1) if s in mapping}
    playable = [p for p in slots if p not in seed_map.values()]
    return seed_map, slots, playable


def _generate_draw_v1(tournament, force: bool = False):
    qs = tournament.entries.filter(status="active").select_related("player")
    if not qs.exists():
        return None

    draw_size = tournament.draw_size or 32
    if draw_size not in {32, 64, 96, 128}:
        logger.warning("Unsupported draw size %s", draw_size)
        return None

    seeds_default = DEFAULT_SEEDS.get(draw_size, 0)
    seeds_count = min(tournament.seeds_count or seeds_default, seeds_default)

    with transaction.atomic():
        if force:
            if has_completed_main_matches(tournament) and not tournament.flex_mode:
                return None
            tournament.matches.all().delete()
            qs.update(position=None)
        else:
            if tournament.matches.exists():
                return None

        entries = list(qs)
        entries = _sort_entries(entries, tournament.seeding_method)
        seeds_count = min(seeds_count, len(entries))
        seed_map, _, playable = _seed_map_for_draw(draw_size, seeds_count)

        used = set()
        for idx, entry in enumerate(entries[:seeds_count], start=1):
            pos = seed_map.get(idx)
            if pos is None:
                break
            entry.position = pos
            entry.save(update_fields=["position"])
            used.add(pos)

        available = [p for p in playable if p not in used]
        for entry, pos in zip(entries[seeds_count:], available):
            entry.position = pos
            entry.save(update_fields=["position"])

        bracket = 1 << (draw_size - 1).bit_length()
        by_pos = {e.position: e for e in entries if e.position}
        for a, b in pair_first_round_slots(bracket):
            ea = by_pos.get(a)
            eb = by_pos.get(b)
            if ea and eb:
                Match.objects.create(
                    tournament=tournament,
                    player1=ea.player,
                    player2=eb.player,
                    round=f"R{draw_size}",
                    section="",
                    best_of=5,
                )

        if tournament.state != tournament.State.DRAWN:
            tournament.state = tournament.State.DRAWN
            tournament.save(update_fields=["state"])
    return None


def replace_slot(
    tournament,
    slot: int,
    replacement_entry_id: int,
    *,
    allow_over_completed: bool = False,
) -> bool:
    """
    Vrátí True při úspěchu. Najde current entry v `position=slot` (ACTIVE),
    označí ho `replaced`, replacement (ALT/LL) nastaví `ACTIVE` + `position=slot`.
    Pokud existuje ne-completed zápas 1. kola pro tento slot, přepiš p1/p2.
    Pokud je zápas completed a `allow_over_completed` False → return False.
    """

    with transaction.atomic():
        entries = tournament.entries.select_for_update()
        current = (
            entries.filter(position=slot, status="active")
            .select_related("player")
            .first()
        )
        if not current:
            return False
        try:
            replacement = entries.get(pk=replacement_entry_id)
        except TournamentEntry.DoesNotExist:
            return False
        if replacement.position is not None:
            return False
        if replacement.status not in {
            "active",
            "withdrawn",
        } or replacement.entry_type not in {
            "ALT",
            "LL",
        }:
            return False
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
            if match and match.winner_id and not allow_over_completed:
                return False
        current.status = TournamentEntry.Status.REPLACED
        current.position = None
        current.save(update_fields=["status", "position"])
        replacement.status = TournamentEntry.Status.ACTIVE
        replacement.position = slot
        replacement.save(update_fields=["status", "position"])
        if match and not match.winner_id:
            entries_by_pos = {slot: replacement}
            if mate:
                entries_by_pos[mate_slot] = mate
            low, high = sorted([slot, mate_slot])
            e_low = entries_by_pos.get(low)
            e_high = entries_by_pos.get(high)
            if e_low and e_high:
                match.player1 = e_low.player
                match.player2 = e_high.player
                match.save(update_fields=["player1", "player2"])
        return True


def has_completed_main_matches(tournament) -> bool:
    return tournament.matches.filter(winner__isnull=False).exists()


def generate_draw(tournament, force: bool = False):
    """Generate tournament draw using configured engine."""
    engine = getattr(settings, "MSA_DRAW_ENGINE", "v1")
    if engine == "legacy":
        return _generate_draw_legacy(tournament, force=force)
    if engine == "v1":
        return _generate_draw_v1(tournament, force=force)
    raise ValueError(f"Unknown draw engine: {engine}")
