import random
from collections import OrderedDict
from typing import Any

# --- Anchor map pro JEDNU kvalifikační větev (bracket) o velikosti 2^R ---
# Tiers v přesném pořadí plnění globálními Q-seedy: TOP → BOTTOM → MIDDLE_A → MIDDLE_B → ...
# Podporujeme R ∈ {1,2,3,4}. Pro R>=5 by se dal použít MD-like kotvy (32/64), ale zatím není potřeba.


def bracket_anchor_tiers(R: int) -> OrderedDict:
    size = 2**R
    if R <= 0:
        raise ValueError("R must be >= 1")
    if size == 2:  # R=1 → bez seedů (2^(R-2) = 0)
        return OrderedDict()  # žádné kotvy, ale vracíme prázdno
    if size == 4:  # R=2 → 1 seed/bracket: TOP
        return OrderedDict(
            {
                "TOP": [1],
            }
        )
    if size == 8:  # R=3 → 2 seedy/bracket: TOP, BOTTOM
        return OrderedDict(
            {
                "TOP": [1],
                "BOTTOM": [8],
            }
        )
    if size == 16:  # R=4 → 4 seedy/bracket: TOP, BOTTOM, MIDDLE_A, MIDDLE_B
        return OrderedDict(
            {
                "TOP": [1],
                "BOTTOM": [16],
                "MIDDLE_A": [9],
                "MIDDLE_B": [8],
            }
        )
    raise ValueError(f"Unsupported bracket size 2^{R}. Supported R: 1..4")


def seeds_per_bracket(R: int) -> int:
    return 0 if R < 2 else 2 ** (R - 2)


def generate_qualification_mapping(
    K: int,  # počet kvalifikačních větví = počet kvalifikantů do MD
    R: int,  # počet kol v každé větvi (počet hráčů na větev = 2^R)
    q_seeds_in_order: list[Any],  # globální pořadí Q-seedů (SNAPSHOT/CURRENT), délka = K * 2^(R-2)
    unseeded_players: list[Any],  # ostatní hráči (Q + Reserve/QWC), libovolné pořadí
    rng_seed: int,
) -> list[dict[int, Any]]:
    """
    Vygeneruje K kvalifikačních větví. Každá větev je dict {local_slot(1..2^R) -> player}.

    Rozdělení seedů:
      - `q_seeds_in_order` rozděl na tiery po K kusech: Tier1→TOP, Tier2→BOTTOM, Tier3→MIDDLE_A, Tier4→MIDDLE_B...
      - Každý tier naplní odpovídající kotvu v každé větvi (ve stejné indexaci 0..K-1).
    Nenasazení:
      - Deterministicky zamícháme jedním RNG (`rng_seed`) a plníme zbývající sloty ve všech větvích
        v pořadí (větev 0..K-1) a uvnitř větve vzestupně podle local_slot.
    """
    if K <= 0:
        raise ValueError("K must be >= 1")
    if R < 1:
        raise ValueError("R must be >= 1")

    size = 2**R
    spb = seeds_per_bracket(R)
    anchors = bracket_anchor_tiers(R)  # OrderedDict tier-> [slots]

    expected_seeds = K * spb
    if len(q_seeds_in_order) != expected_seeds:
        raise ValueError(
            f"q_seeds_in_order must have length {expected_seeds} (got {len(q_seeds_in_order)}) for K={K}, R={R}"
        )

    total_slots = K * size
    # kolik slotů zbývá pro nenasazené
    remaining_needed = total_slots - expected_seeds
    if len(unseeded_players) < remaining_needed:
        raise ValueError("Nedostatek nenasazených hráčů pro vyplnění kvalifikace.")

    # Připrav prázdné větve
    brackets: list[dict[int, Any]] = [dict() for _ in range(K)]

    # 1) Rozdělení seedů do tierů po blocích K
    # Např. R=4 (spb=4): bloky [0:K] -> TOP, [K:2K] -> BOTTOM, [2K:3K] -> MIDDLE_A, [3K:4K] -> MIDDLE_B
    tiers = list(anchors.keys())  # pořadí tierů
    for i_tier, tier in enumerate(tiers[:spb]):
        start = i_tier * K
        end = start + K
        block = q_seeds_in_order[start:end]
        slots_for_tier = anchors[tier]
        assert len(slots_for_tier) == 1, "Každý tier má právě jednu kotvu ve větvi"
        local_slot = slots_for_tier[0]
        for b in range(K):
            brackets[b][local_slot] = block[b]

    # 2) Nenasazení – deterministicky zamíchat a vyplnit zbytek slotů
    rnd = random.Random(rng_seed)
    pool = unseeded_players[:remaining_needed]
    rnd.shuffle(pool)

    it = iter(pool)
    for b in range(K):
        for local_slot in range(1, size + 1):
            if local_slot in brackets[b]:
                continue
            try:
                brackets[b][local_slot] = next(it)
            except StopIteration as err:
                raise AssertionError("Internal fill error: unexpected pool exhaustion") from err

    # sanity
    for b in range(K):
        assert len(brackets[b]) == size
        assert len(set(brackets[b].keys())) == size
        assert len(set(brackets[b].values())) == size

    return brackets
