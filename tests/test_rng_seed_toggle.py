from types import SimpleNamespace

from msa.services.md_generator import generate_main_draw_mapping
from msa.services.qual_generator import generate_qualification_mapping


def test_md_unseeded_changes_when_rng_seed_changes():
    draw = 16
    seeds = [f"S{i}" for i in range(1, 5)]
    unseeded = [f"U{i}" for i in range(1, 13)]

    t = SimpleNamespace(rng_seed_active=123)
    m1 = generate_main_draw_mapping(draw, seeds, unseeded, rng_seed=t.rng_seed_active)
    order1 = [m1[i] for i in range(1, draw + 1) if m1[i] not in seeds]
    seed_pos1 = {p: s for s, p in m1.items() if p in seeds}

    t.rng_seed_active = 456
    m2 = generate_main_draw_mapping(draw, seeds, unseeded, rng_seed=t.rng_seed_active)
    order2 = [m2[i] for i in range(1, draw + 1) if m2[i] not in seeds]
    seed_pos2 = {p: s for s, p in m2.items() if p in seeds}

    assert order1 != order2
    assert seed_pos1 == seed_pos2


def test_qual_unseeded_changes_when_rng_seed_changes():
    K, R = 2, 3
    seeds = ["S1", "S2", "S3", "S4"]
    need = K * (2**R) - len(seeds)
    unseeded = [f"U{i}" for i in range(1, need + 1)]

    t = SimpleNamespace(rng_seed_active=111)
    b1 = generate_qualification_mapping(K, R, seeds, unseeded, rng_seed=t.rng_seed_active)

    def unseeded_order(brackets):
        out = []
        for b in range(K):
            for s in range(1, 2**R + 1):
                player = brackets[b][s]
                if player not in seeds:
                    out.append(player)
        return out

    order1 = unseeded_order(b1)
    seed_slots1 = [(b1[b][1], b1[b][8]) for b in range(K)]

    t.rng_seed_active = 222
    b2 = generate_qualification_mapping(K, R, seeds, unseeded, rng_seed=t.rng_seed_active)
    order2 = unseeded_order(b2)
    seed_slots2 = [(b2[b][1], b2[b][8]) for b in range(K)]

    assert order1 != order2
    assert seed_slots1 == seed_slots2
