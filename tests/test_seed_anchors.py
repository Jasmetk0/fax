from msa.services.seed_anchors import band_sequence_for_S, md_anchor_map


def _expand_band(band: str) -> list[int]:
    start, _, end = band.partition("-")
    start_i = int(start)
    end_i = int(end) if end else start_i
    return list(range(start_i, end_i + 1))


def _seed_slots(draw_size: int) -> dict[int, int]:
    m = md_anchor_map(draw_size)
    seeds: list[int] = []
    slots: list[int] = []
    for band, band_slots in m.items():
        seeds.extend(_expand_band(band))
        slots.extend(band_slots)
    return dict(zip(seeds, slots, strict=False))


def test_band_sequence_is_permutation_and_stable():
    draw_size = 16
    for S in (8, 16):
        seq1 = band_sequence_for_S(draw_size, S)
        seq2 = band_sequence_for_S(draw_size, S)
        assert seq1 == seq2
        seeds: list[int] = []
        for band in seq1:
            seeds.extend(_expand_band(band))
        assert seeds == list(range(1, S + 1))
        assert len(seeds) == len(set(seeds))


def test_top_seeds_land_in_distinct_quarters():
    S = 16
    mapping = _seed_slots(S)
    quarters = {((pos - 1) * 4) // S for pos in [mapping[i] for i in range(1, 5)]}
    assert len(quarters) == 4


def test_md_anchor_map_has_unique_slots_and_correct_bounds():
    S = 16
    mapping = _seed_slots(S)
    assert sorted(mapping.keys()) == list(range(1, S + 1))
    slots = list(mapping.values())
    assert len(slots) == len(set(slots))
    assert all(1 <= slot <= S for slot in slots)


def test_seed_1_and_2_anchor_opposite_halves():
    S = 16
    mapping = _seed_slots(S)
    assert mapping[1] <= S // 2 < mapping[2]
