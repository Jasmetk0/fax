"""
Scorecard and judging helpers for the MMA engine.

The goal of this module is to eventually encapsulate all 10-9 scoring logic and
decision typing (UD/SD/MD/Draw). For now it only contains simple placeholders.
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import JudgeScorecard, RoundStats


def build_unanimous_10_9_scorecards(
    round_stats: Iterable[RoundStats],
) -> list[JudgeScorecard]:
    """
    Build a very simple set of 3 unanimous 10-9 scorecards based purely on
    damage score per round.

    This is a convenience helper and will likely be replaced by a richer model.
    """
    scores_per_round: list[tuple[int, int]] = []
    for r in round_stats:
        if r.red_damage_score >= r.blue_damage_score:
            scores_per_round.append((10, 9))
        else:
            scores_per_round.append((9, 10))

    return [
        JudgeScorecard(judge_name=f"Judge {i+1}", scores_per_round=scores_per_round)
        for i in range(3)
    ]
