"""Builders for default scoring skeletons."""

from __future__ import annotations

from msa.utils.rounds import build_default_points_map


def build_md_skeleton(draw_size: int, *, third_place: bool = False) -> dict[str, int]:
    """Return the default main-draw points map for ``draw_size``.

    The map contains ordered round labels ending with ``"W"`` for the champion. When
    ``third_place`` is ``True``, the semifinal label is replaced by ``"4th"`` and
    ``"3rd"``.
    """
    return build_default_points_map(draw_size, third_place=third_place)


def build_qual_skeleton(qual_rounds: int, *, include_winner: bool = True) -> dict[str, int]:
    """Return a default qualification points map with ``qual_rounds`` rounds.

    When ``include_winner`` is ``True`` and ``qual_rounds > 0``, an additional
    ``"Q-W"`` key is appended for the qualification champion.
    """
    base = {f"Q-R{i}": 0 for i in range(1, qual_rounds + 1)}
    if include_winner and qual_rounds > 0:
        base["Q-W"] = 0
    return base
