import logging
from math import ceil, log2
from typing import Dict, List, Optional

from django.conf import settings
from django.db import connection, transaction, IntegrityError

from ..models import Match, RankingSnapshot, TournamentEntry
from .rounds import code_to_size, next_power_of_two


logger = logging.getLogger(__name__)


def _for_update(qs):
    return (
        qs.select_for_update()
        if getattr(connection.features, "supports_select_for_update", False)
        else qs
    )


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


DEFAULT_SEEDS = {32: 8, 48: 16, 56: 16, 64: 16, 96: 32, 128: 32}


def pair_first_round_slots(bracket_size: int) -> list[tuple[int, int]]:
    """Return slot pairs for the first round."""

    return [(i, i + 1) for i in range(1, bracket_size + 1, 2)]


def _sort_entries(entries: List, tournament) -> List:
    method = tournament.seeding_method
    if method == "ranking_snapshot":
        snapshot = None
        if tournament.seeding_rank_date:
            snapshot = (
                RankingSnapshot.objects.filter(as_of__lte=tournament.seeding_rank_date)
                .order_by("-as_of")
                .first()
            )
        else:
            snapshot = RankingSnapshot.objects.order_by("-as_of").first()
        if snapshot:
            ranks = {e.player_id: e.rank for e in snapshot.entries.all()}
            entries.sort(
                key=lambda e: (
                    ranks.get(e.player_id) is None,
                    ranks.get(e.player_id, 0),
                    e.player.id,
                    e.player.name,
                )
            )
            return entries
        # Fallback to manual ordering when no snapshot found
    if method in {"manual", "ranking_snapshot"}:
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
    if draw_size in {48, 56}:
        mapping_64 = SEED_POSITIONS[64]
        slots = list(range(1, 65))
        seed_map = {s: mapping_64[s] for s in range(1, seeds_count + 1)}
        byes = {(p + 1) if p % 2 else (p - 1) for p in seed_map.values()}
        playable = [p for p in slots if p not in byes and p not in seed_map.values()]
        return seed_map, slots, playable
    slots = list(range(1, draw_size + 1))
    mapping = SEED_POSITIONS.get(draw_size, {})
    seed_map = {s: mapping[s] for s in range(1, seeds_count + 1) if s in mapping}
    playable = [p for p in slots if p not in seed_map.values()]
    return seed_map, slots, playable


def _generate_draw_v1(tournament, force: bool = False, user=None):
    qs = (
        tournament.entries.filter(status="active")
        .exclude(
            entry_type__in=[
                TournamentEntry.EntryType.Q,
                TournamentEntry.EntryType.LL,
                TournamentEntry.EntryType.ALT,
            ]
        )
        .select_related("player")
    )
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
        entries = _sort_entries(entries, tournament)
        seeds_count = min(seeds_count, len(entries))
        seed_map, _, playable = _seed_map_for_draw(draw_size, seeds_count)

        used = set()
        for idx, entry in enumerate(entries[:seeds_count], start=1):
            pos = seed_map.get(idx)
            if pos is None:
                break
            entry.position = pos
            if user:
                entry.updated_by = user
                entry.save(update_fields=["position", "updated_by"])
            else:
                entry.save(update_fields=["position"])
            used.add(pos)

        available = [p for p in playable if p not in used]
        for entry, pos in zip(entries[seeds_count:], available):
            entry.position = pos
            if user:
                entry.updated_by = user
                entry.save(update_fields=["position", "updated_by"])
            else:
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
    user=None,
) -> bool:
    """
    Bezpečně (souběh-safe) nahradí držitele `slot` alternativou (ALT/LL).
    Funguje i když je slot prázdný. Atomické, idempotentní, vendor-aware.
    Pokud je 1. kolo už completed a `allow_over_completed` je False, nic nemění.
    Vrací True, pokud ALT/LL skončí v daném slotu.
    """
    with transaction.atomic():
        occupant = _for_update(
            TournamentEntry.objects.filter(tournament=tournament, position=slot)
        ).first()
        try:
            alt = (
                _for_update(
                    TournamentEntry.objects.filter(
                        pk=replacement_entry_id, tournament=tournament
                    )
                )
                .select_related("player")
                .get()
            )
        except TournamentEntry.DoesNotExist:
            return False

        if alt.position == slot:
            return False
        if alt.position is not None:
            return False

        match = None
        mate_slot = slot + 1 if (slot % 2) else slot - 1
        if occupant:
            mate = (
                TournamentEntry.objects.filter(
                    tournament=tournament, position=mate_slot, status="active"
                )
                .select_related("player")
                .first()
            )
            if mate:
                match_qs = tournament.matches.all()
                match_qs = _for_update(match_qs)
                match = match_qs.filter(
                    player1__in=[occupant.player, mate.player],
                    player2__in=[occupant.player, mate.player],
                    round=f"R{tournament.draw_size}",
                ).first()
                if match and match.winner_id and not allow_over_completed:
                    return False

        if occupant and occupant.pk != alt.pk:
            updates = {"position": None}
            status_enum = getattr(TournamentEntry, "Status", None)
            replaced = getattr(status_enum, "REPLACED", None) if status_enum else None
            if replaced is not None and getattr(occupant, "status", None) != replaced:
                updates["status"] = replaced
            TournamentEntry.objects.filter(pk=occupant.pk).update(**updates)

        assigned = False
        try:
            TournamentEntry.objects.filter(pk=alt.pk).update(
                position=slot, status=TournamentEntry.Status.ACTIVE
            )
        except IntegrityError:
            pass

        alt = TournamentEntry.objects.filter(pk=alt.pk).first()
        if alt and alt.position == slot:
            assigned = True
        else:
            again = TournamentEntry.objects.filter(
                tournament=tournament, position=slot
            ).first()
            if again is None:
                try:
                    TournamentEntry.objects.filter(pk=alt.pk).update(
                        position=slot, status=TournamentEntry.Status.ACTIVE
                    )
                except IntegrityError:
                    pass
                alt = TournamentEntry.objects.filter(pk=alt.pk).first()
                assigned = bool(alt and alt.position == slot)
            else:
                assigned = again.pk == alt.pk

        if match and not match.winner_id and assigned:
            low, high = sorted([slot, mate_slot])
            e_low = (
                TournamentEntry.objects.filter(tournament=tournament, position=low)
                .select_related("player")
                .first()
            )
            e_high = (
                TournamentEntry.objects.filter(tournament=tournament, position=high)
                .select_related("player")
                .first()
            )
            if e_low and e_high:
                match.player1 = e_low.player
                match.player2 = e_high.player
                match.save(update_fields=["player1", "player2"])

        return assigned


def has_completed_main_matches(tournament) -> bool:
    return tournament.matches.filter(winner__isnull=False).exists()


def generate_draw(tournament, force: bool = False, user=None):
    """Generate tournament draw using configured engine."""
    engine = getattr(settings, "MSA_DRAW_ENGINE", "v1")
    if engine == "legacy":
        return _generate_draw_legacy(tournament, force=force)
    if engine == "v1":
        return _generate_draw_v1(tournament, force=force, user=user)
    raise ValueError(f"Unknown draw engine: {engine}")


def _rounds_numeric(code: str) -> int:
    return code_to_size(code)


_BRACKET_ORDER = [
    "R128",
    "R96",
    "R64",
    "R56",
    "R48",
    "R32",
    "R16",
    "QF",
    "SF",
    "F",
]


def _next_round_code(code: str) -> Optional[str]:
    try:
        idx = _BRACKET_ORDER.index(code)
    except ValueError:
        return None
    if idx + 1 >= len(_BRACKET_ORDER):
        return None
    return _BRACKET_ORDER[idx + 1]


def _find_highest_complete_round_code(tournament) -> Optional[str]:
    codes = (
        Match.objects.filter(tournament=tournament)
        .values_list("round", flat=True)
        .distinct()
    )
    ordered = sorted(codes, key=_rounds_numeric, reverse=True)
    for code in ordered:
        qs = Match.objects.filter(tournament=tournament, round=code)
        if qs.exists() and not qs.filter(winner__isnull=True).exists():
            return code
    return None


@transaction.atomic
def progress_bracket(tournament) -> bool:
    current_code = _find_highest_complete_round_code(tournament)
    if not current_code:
        return False
    next_code = _next_round_code(current_code)
    if not next_code:
        return False

    if Match.objects.filter(tournament=tournament, round=next_code).exists():
        return False

    cur_qs = _for_update(
        Match.objects.filter(tournament=tournament, round=current_code).order_by("id")
    )

    if Match.objects.filter(tournament=tournament, round=next_code).exists():
        return False

    if cur_qs.filter(winner__isnull=True).exists():
        return False

    bracket = next_power_of_two(tournament.draw_size or 0)
    entries_qs = _for_update(
        tournament.entries.filter(
            position__isnull=False, status="active"
        ).select_related("player")
    )
    by_pos = {e.position: e for e in entries_qs}

    winners: List[Optional[TournamentEntry]] = []
    for a, b in pair_first_round_slots(bracket):
        ea = by_pos.get(a)
        eb = by_pos.get(b)
        winner_entry = None
        if ea and eb:
            match = cur_qs.filter(
                player1__in=[ea.player, eb.player],
                player2__in=[ea.player, eb.player],
            ).first()
            if match and match.winner_id is not None:
                winner_entry = ea if match.winner_id == ea.player_id else eb
            else:
                winners.append(None)
                continue
        elif ea or eb:
            winner_entry = ea or eb
        winners.append(winner_entry)

    created_any = False
    for i in range(0, len(winners), 2):
        w1 = winners[i]
        w2 = winners[i + 1] if i + 1 < len(winners) else None
        if not w1 or not w2:
            continue
        match, created = Match.objects.get_or_create(
            tournament=tournament,
            round=next_code,
            section=str(i // 2),
            defaults={
                "player1": w1.player,
                "player2": w2.player,
                "best_of": 5,
            },
        )
        if not created and (
            match.player1_id != w1.player_id or match.player2_id != w2.player_id
        ):
            match.player1 = w1.player
            match.player2 = w2.player
            match.save(update_fields=["player1", "player2"])
        created_any = created_any or created

    return created_any
