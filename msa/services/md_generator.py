from typing import List, Dict, Any
import random
from msa.services.seed_anchors import md_anchor_map, band_sequence_for_S


def generate_main_draw_mapping(
    draw_size: int,
    seeds_in_order: List[Any],   # [p1..pS] v seeding pořadí
    unseeded_players: List[Any], # DA/WC/Q/LL v libovolném pořadí
    rng_seed: int,
) -> Dict[int, Any]:
    """
    Mapping {slot -> player} pro MD (16/32/64):
      - seedy na kanonických kotvách po bandech ve správném pořadí,
      - nenasazení deterministicky zamícháni a dosazeni na zbývající sloty vzestupně.
    """
    anchors = md_anchor_map(draw_size)
    S = len(seeds_in_order)
    used_bands = band_sequence_for_S(draw_size, S)

    slot_to_player: Dict[int, Any] = {}
    seed_idx = 0
    for band in used_bands:
        for slot in anchors[band]:
            if seed_idx >= S:
                break
            slot_to_player[slot] = seeds_in_order[seed_idx]
            seed_idx += 1

    remaining_slots = [i for i in range(1, draw_size + 1) if i not in slot_to_player]

    if len(unseeded_players) < len(remaining_slots):
        raise ValueError("Nedostatek nenasazených hráčů pro vyplnění zbytku MD.")
    if len(unseeded_players) > len(remaining_slots):
        unseeded_players = unseeded_players[: len(remaining_slots)]

    rnd = random.Random(rng_seed)
    shuffled = unseeded_players[:]
    rnd.shuffle(shuffled)

    for slot, player in zip(remaining_slots, shuffled):
        slot_to_player[slot] = player

    assert len(slot_to_player) == draw_size
    assert len(set(slot_to_player.keys())) == draw_size
    assert len(set(slot_to_player.values())) == draw_size
    return slot_to_player