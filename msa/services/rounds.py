from __future__ import annotations

from typing import Optional


ROUND_LABELS = {
    128: "Round of 128",
    96: "Round of 96",
    64: "Round of 64",
    56: "Round of 56",
    48: "Round of 48",
    32: "Round of 32",
    16: "Round of 16",
    8: "Quarter Final",
    4: "Semi Final",
    2: "Final",
    1: "Winner",
}


def next_power_of_two(n: int) -> int:
    """Return the next power of two greater than or equal to n."""
    if n < 1:
        return 1
    return 1 << (n - 1).bit_length()


def round_label(
    total_slots: int, *, entrants: Optional[int] = None, mode: str = "slots"
) -> str:
    """Return human label for a round.

    Args:
        total_slots: bracket slots including BYEs.
        entrants: actual number of entrants (used when ``mode='entrants'``).
        mode: ``"slots"`` uses ``total_slots``; ``"entrants"`` uses ``entrants``.
    """

    size = total_slots
    if mode == "entrants" and entrants is not None:
        size = entrants
    if size in ROUND_LABELS:
        return ROUND_LABELS[size]
    if size > 8:
        return f"Round of {size}"
    return ROUND_LABELS.get(size, f"R{size}")
