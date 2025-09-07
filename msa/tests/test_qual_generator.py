import pytest

from msa.services.qual_generator import generate_qualification_mapping, seeds_per_bracket


def test_seeds_per_bracket_formula():
    assert seeds_per_bracket(1) == 0
    assert seeds_per_bracket(2) == 1
    assert seeds_per_bracket(3) == 2
    assert seeds_per_bracket(4) == 4


def test_R3_K2_tiers_top_bottom():
    K, R = 2, 3  # 8 hráčů na větev, 2 seedy/ větev => 4 seedy celkem
    seeds = ["S1", "S2", "S3", "S4"]  # globální pořadí
    # 2 větve → 2*8 = 16 slotů, z nich 4 seedové → 12 nenasazených
    U = [f"U{i}" for i in range(1, 13)]

    brackets = generate_qualification_mapping(K, R, seeds, U, rng_seed=42)
    # Tier1 (TOP): S1→branch0 slot1, S2→branch1 slot1
    assert brackets[0][1] == "S1"
    assert brackets[1][1] == "S2"
    # Tier2 (BOTTOM): S3→branch0 slot8, S4→branch1 slot8
    assert brackets[0][8] == "S3"
    assert brackets[1][8] == "S4"


def test_R4_K3_four_tiers():
    K, R = 3, 4  # 16 na větev, 4 seedy/ větev => 12 seedů celkem
    seeds = [f"S{i}" for i in range(1, 13)]
    U = [f"U{i}" for i in range(1, 3 * 16 - 12 + 1)]  # doplnit zbytek

    br = generate_qualification_mapping(K, R, seeds, U, rng_seed=7)
    # Tier1 TOP → slot 1
    assert [br[i][1] for i in range(K)] == ["S1", "S2", "S3"]
    # Tier2 BOTTOM → slot 16
    assert [br[i][16] for i in range(K)] == ["S4", "S5", "S6"]
    # Tier3 MIDDLE_A → slot 9
    assert [br[i][9] for i in range(K)] == ["S7", "S8", "S9"]
    # Tier4 MIDDLE_B → slot 8
    assert [br[i][8] for i in range(K)] == ["S10", "S11", "S12"]


def test_unseeded_determinism_changes_with_rng():
    K, R = 2, 3
    seeds = ["S1", "S2", "S3", "S4"]
    need = K * (2**R) - len(seeds)
    U = [f"U{i}" for i in range(1, need + 1)]

    b1 = generate_qualification_mapping(K, R, seeds, U, rng_seed=1)
    b2 = generate_qualification_mapping(K, R, seeds, U, rng_seed=2)
    # najdi aspoň jeden rozdíl v nenasazených
    assert any(
        b1[i][s] != b2[i][s] for i in range(K) for s in range(1, 2**R + 1) if s not in (1, 8)
    )


def test_size_checks():
    K, R = 2, 3
    seeds = ["S1", "S2", "S3", "S4"]
    # málo nenasazených → chyba
    need = K * (2**R) - len(seeds)
    with pytest.raises(ValueError):
        generate_qualification_mapping(K, R, seeds, ["U1"] * (need - 1), rng_seed=0)
    # špatný počet seedů → chyba
    with pytest.raises(ValueError):
        generate_qualification_mapping(K, R, seeds[:-1], ["U1"] * need, rng_seed=0)
