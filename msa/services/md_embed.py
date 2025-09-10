# msa/services/md_embed.py
from __future__ import annotations

from types import SimpleNamespace

from django.core.exceptions import ValidationError

from msa.models import Tournament
from msa.services.randoms import rng_for, seeded_shuffle
from msa.services.seed_anchors import band_sequence_for_S, md_anchor_map


def next_power_of_two(n: int) -> int:
    if n <= 0:
        raise ValidationError("draw_size musí být > 0.")
    p = 1
    while p < n:
        p <<= 1
    return p


def effective_template_size_for_md(t: Tournament) -> int:
    if not t.category_season or not t.category_season.draw_size:
        raise ValidationError("Tournament nemá nastavený CategorySeason.draw_size.")
    return next_power_of_two(int(t.category_season.draw_size))


def r1_name_for_md(t: Tournament) -> str:
    """Round name R{template} — i pro embed (např. draw 24 → R32)."""
    return f"R{effective_template_size_for_md(t)}"


def _seed_anchor_slots_in_order(template_size: int, S: int) -> list[int]:
    """Vrátí seznam kotev (slotů) pro seedy 1..S v přesném pořadí (1,2,3,4,5,6,7,8,...)."""
    if S <= 0:
        return []
    anchors = md_anchor_map(template_size)  # dict: band -> [slots...]
    bands = band_sequence_for_S(template_size, S)  # např. ["1","2","3-4","5-8",...]
    out: list[int] = []
    left = S
    for band in bands:
        for s in anchors[band]:
            out.append(s)
            left -= 1
            if left == 0:
                return out
    return out


def _opponent_slot(template_size: int, slot: int) -> int:
    return template_size + 1 - slot


def generate_md_mapping_with_byes(
    *,
    template_size: int,  # např. 32/64
    seeds_in_order: list[int],  # TournamentEntry.id v pořadí seeda 1..S
    unseeded_players: list[int],  # TournamentEntry.id nenasazených (pool)
    bye_count: int,  # kolik BYE párů v R1 (např. 32-24 = 8)
    rng_seed: int,
) -> dict[int, int]:
    """
    Vytvoří mapping {slot -> entry_id} pro šablonu template_size tak, že
    - umístí seedy na jejich kotvy,
    - vybere `bye_count` R1 protislots (oponenty) TOP seedů 1..bye_count a nechá je PRÁZDNÉ,
    - zbylé unseeded sloty zaplní deterministicky zamíchaným poolem.
    """
    S = len(seeds_in_order)
    seed_slots = _seed_anchor_slots_in_order(template_size, S)
    if len(seed_slots) != S:
        raise ValidationError("Nepodařilo se spočítat kotvy pro všechny seedy.")

    # 1) umísti seedy
    mapping: dict[int, int] = {}
    for slot, eid in zip(seed_slots, seeds_in_order, strict=False):
        mapping[int(slot)] = int(eid)

    # 2) připrav BYE sloty pro top seedy (opponent slots)
    bye_opponent_slots = set()
    bye_for_seeds = min(max(0, bye_count), S)
    for slot in seed_slots[:bye_for_seeds]:
        bye_opponent_slots.add(_opponent_slot(template_size, slot))

    remaining_byes = max(0, bye_count - bye_for_seeds)

    # 3) připrav dostupné unseeded sloty: všechny kromě seed_slots a bye_opponent_slots
    all_slots = list(range(1, template_size + 1))
    blocked = set(seed_slots) | set(bye_opponent_slots)
    available_set = {s for s in all_slots if s not in blocked}

    # 4) pokud zbývají BYE sloty, přidej je jako protislots k dalším hráčům
    if remaining_byes:
        for slot in sorted(available_set):
            if remaining_byes == 0:
                break
            opp = _opponent_slot(template_size, slot)
            if opp in available_set:
                available_set.remove(opp)
                bye_opponent_slots.add(opp)
                remaining_byes -= 1
        if remaining_byes != 0:
            raise ValidationError("Příliš mnoho BYE slotů pro dostupné pozice.")

    available_unseeded_slots = sorted(available_set)

    if len(unseeded_players) > len(available_unseeded_slots):
        raise ValidationError("Příliš mnoho nenasazených pro dostupné sloty (BYE konfigurace).")

    # 5) deterministicky promíchej a naplň
    rng = rng_for(SimpleNamespace(rng_seed_active=rng_seed))
    pool = seeded_shuffle(unseeded_players, rng)
    for slot, eid in zip(available_unseeded_slots, pool, strict=False):
        mapping[int(slot)] = int(eid)

    return mapping


def pairings_round1(template_size: int) -> list[tuple[int, int]]:
    """Zrcadlové páry pro danou šablonu (1..template_size)."""
    return [(i, template_size + 1 - i) for i in range(1, template_size // 2 + 1)]
