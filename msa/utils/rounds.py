from __future__ import annotations

"""Utilities for dealing with tournament round labels."""

CHAMPION_KEY = "W"
FINAL_KEY = "F"
BRONZE_KEYS = ("3rd", "4th")


def has_third_place(labels: list[str]) -> bool:
    """Return ``True`` if the label sequence contains a third-place playoff."""
    return all(k in labels for k in BRONZE_KEYS)


def round_labels_from_md_size(md_size: int, *, third_place: bool = False) -> list[str]:
    """Build ordered main-draw round labels from ``md_size`` down to ``"W"``.

    ``third_place`` injects ``"4th"``/``"3rd"`` in lieu of the semifinal round when
    the draw is large enough to accommodate a bronze match.
    """

    labels: list[str] = []

    def numeric_to_label(n: int) -> str:
        return "QF" if n == 8 else "SF" if n == 4 else "F" if n == 2 else f"R{n}"

    n = int(md_size)
    is_power_of_two = n & (n - 1) == 0
    if not is_power_of_two and n > 8:
        labels.append(f"R{n}")
        n = 1 << (n.bit_length() - 1)

    while n >= 2:
        labels.append(numeric_to_label(n))
        if n == 2:
            break
        n //= 2

    if third_place and "SF" in labels and md_size >= 4:
        out: list[str] = []
        for lab in labels:
            if lab == "SF":
                out.extend(["4th", "3rd"])
            else:
                out.append(lab)
        labels = out

    labels.append(CHAMPION_KEY)
    return labels


def build_default_points_map(md_size: int, *, third_place: bool = False) -> dict[str, int]:
    """Return an insertion-ordered map of round labels to zero points."""
    return {label: 0 for label in round_labels_from_md_size(md_size, third_place=third_place)}
