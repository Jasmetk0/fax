"""
Utility functions for probability and random draws used by the MMA engine.

At this stage this module only provides very small helpers; the idea is to keep
all probability-related tuning in a single place so the simulation is easier to
reason about and adjust.
"""

from __future__ import annotations


def normalize_pair(a: float, b: float) -> tuple[float, float]:
    """Normalize two non-negative values into probabilities that sum to 1."""
    total = max(a + b, 1e-9)
    return a / total, b / total
