from __future__ import annotations

_MD_ROUNDS = [128, 64, 32, 16, 8, 4, 2]
_MD_NAMES = {128: "R128", 64: "R64", 32: "R32", 16: "R16", 8: "QF", 4: "SF", 2: "F"}


def _next_power_of_two(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


def build_md_skeleton(draw_size: int) -> dict[str, int]:
    template = _next_power_of_two(draw_size)
    rounds = [name for size in _MD_ROUNDS if template >= size for name in [_MD_NAMES[size]]]
    return {r: 0 for r in rounds}


def build_qual_skeleton(qual_rounds: int) -> dict[str, int]:
    return {f"Q-R{i}": 0 for i in range(1, qual_rounds + 1)}
