"""
Scorecard and judging helpers for the MMA engine.

The goal of this module is to eventually encapsulate all 10-9 scoring logic and
decision typing (UD/SD/MD/Draw). For now it only contains simple placeholders.
"""

from __future__ import annotations

import random
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


def build_scorecards(
    round_stats: Iterable[RoundStats], *, rng: random.Random | None = None
) -> list[JudgeScorecard]:
    """
    Build three judge scorecards with a small amount of per-judge variance.

    The scoring heuristic is intentionally simple:
    - 10-9 to the fighter with more damage in a round
    - 10-8 if the winner's damage is more than 2.5x the opponent
    - Very small random noise is applied per judge to allow for split decisions
    """

    if rng is None:
        rng = random.Random()

    scorecards: list[JudgeScorecard] = []
    for judge_index in range(3):
        scores_per_round: list[tuple[int, int]] = []
        noise = rng.normalvariate(0, 0.05)

        for r in round_stats:
            red_damage = r.red_damage_score * (1 + noise)
            blue_damage = r.blue_damage_score * (1 - noise)

            if red_damage == blue_damage:
                scores_per_round.append((10, 10))
                continue

            if red_damage > blue_damage:
                diff = red_damage / max(blue_damage, 1e-6)
                red_score = 10
                blue_score = 8 if diff > 2.5 else 9
            else:
                diff = blue_damage / max(red_damage, 1e-6)
                blue_score = 10
                red_score = 8 if diff > 2.5 else 9

            scores_per_round.append((red_score, blue_score))

        scorecards.append(
            JudgeScorecard(judge_name=f"Judge {judge_index + 1}", scores_per_round=scores_per_round)
        )

    return scorecards
