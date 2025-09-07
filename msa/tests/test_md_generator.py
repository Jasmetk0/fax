import pytest
from msa.services.md_generator import generate_main_draw_mapping


def test_md32_s8_seed_positions_deterministic():
    draw = 32
    seeds = [f"S{i}" for i in range(1, 9)]
    unseeded = [f"U{i}" for i in range(1, 25)]

    m = generate_main_draw_mapping(draw, seeds, unseeded, rng_seed=12345)
    assert m[1] == "S1"
    assert m[32] == "S2"
    assert m[17] == "S3"
    assert m[16] == "S4"
    assert set([m[8], m[9], m[24], m[25]]) == set(["S5", "S6", "S7", "S8"])

    m2 = generate_main_draw_mapping(draw, seeds, unseeded, rng_seed=12345)
    assert m == m2


def test_md16_s4_and_randomness_changes():
    draw = 16
    seeds = [f"S{i}" for i in range(1, 5)]
    unseeded = [f"U{i}" for i in range(1, 13)]
    m1 = generate_main_draw_mapping(draw, seeds, unseeded, rng_seed=1)
    m2 = generate_main_draw_mapping(draw, seeds, unseeded, rng_seed=2)
    assert any(m1[k] != m2[k] for k in m1.keys())


def test_not_enough_unseeded_raises():
    draw = 16
    seeds = [f"S{i}" for i in range(1, 9)]
    unseeded = [f"U{i}" for i in range(1, 7)]
    with pytest.raises(ValueError):
        generate_main_draw_mapping(draw, seeds, unseeded, rng_seed=7)