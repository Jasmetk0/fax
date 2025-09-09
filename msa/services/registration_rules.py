from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

Section = Literal["SEEDS", "DA", "Q", "RESERVE"]


@dataclass(frozen=True)
class EntryView:
    id: int
    section: Section  # "SEEDS" | "DA" | "Q" | "RESERVE"
    wr_snapshot: int | None  # None for NR in RESERVE
    is_seed: bool = False


@dataclass(frozen=True)
class Move:
    entry_id: int
    new_index: int  # index within its section list


def _bucket_bounds(entries: list[EntryView]) -> dict[int, tuple[int, int]]:
    """Return map position -> (lo, hi) bounds for its WR-tie bucket."""
    by_wr: dict[int, list[int]] = {}
    for idx, e in enumerate(entries):
        key = int(e.wr_snapshot) if e.wr_snapshot is not None else 10**9
        by_wr.setdefault(key, []).append(idx)
    bounds: dict[int, tuple[int, int]] = {}
    for _, positions in by_wr.items():
        lo, hi = min(positions), max(positions)
        for p in positions:
            bounds[p] = (lo, hi)
    return bounds


def validate_reorder(section: Section, entries: list[EntryView], moves: Iterable[Move]) -> None:
    """
    Raises ValueError if any move violates rules.

    Rules:
      - SEEDS/DA/Q: only inside same wr_snapshot tie bucket.
      - RESERVE: any reordering inside RESERVE allowed.
      - Moves must reference only entries of this section.
      - new_index must be within 0..len(entries)-1.
    """
    if not entries and not list(moves):
        return
    ids = {e.id for e in entries}
    for m in moves:
        if m.entry_id not in ids:
            raise ValueError("move.cross_section")
        if not (0 <= m.new_index < len(entries)):
            raise ValueError("move.index_oob")
    if section == "RESERVE":
        return  # free block within Reserve

    pos_map = {e.id: i for i, e in enumerate(entries)}
    bounds = _bucket_bounds(entries)
    for m in moves:
        src_pos = pos_map[m.entry_id]
        lo, hi = bounds[src_pos]
        if not (lo <= m.new_index <= hi):
            raise ValueError("move.cross_bucket")


__all__ = ["EntryView", "Move", "validate_reorder"]
