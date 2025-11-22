from __future__ import annotations

import random

from .config import DEFAULT_RANDOM_SEED
from .models import EngineFighter, FightResult, FightRules, JudgeScorecard, RoundStats


def simulate_bout(
    red: EngineFighter,
    blue: EngineFighter,
    *,
    rules: FightRules | None = None,
    seed: int | None = DEFAULT_RANDOM_SEED,
) -> FightResult:
    """
    Simulate a single MMA bout between two fighters under given rules.

    For now this is a very simple placeholder implementation that will be
    replaced with a more detailed engine in later steps. The goal of this file
    is to define a stable public interface that the rest of the project can
    call without caring about internal details.
    """
    if rules is None:
        rules = FightRules()

    rng = random.Random(seed) if seed is not None else random.Random()

    round_stats: list[RoundStats] = []
    for round_number in range(1, rules.rounds + 1):
        round_stats.append(_simulate_round(red, blue, round_number=round_number, rng=rng))

    # Very naive placeholder scoring: fighter with more total "damage" wins.
    red_damage = sum(r.red_damage_score for r in round_stats)
    blue_damage = sum(r.blue_damage_score for r in round_stats)

    # Build a trivial 3-judge scorecard where all judges agree.
    # This will be replaced by a proper scoring engine later.
    scores_per_round = []
    for r in round_stats:
        if r.red_damage_score >= r.blue_damage_score:
            scores_per_round.append((10, 9))
        else:
            scores_per_round.append((9, 10))

    scorecards = [
        JudgeScorecard(judge_name=f"Judge {i+1}", scores_per_round=scores_per_round)
        for i in range(3)
    ]

    if red_damage > blue_damage:
        winner = "red"
    elif blue_damage > red_damage:
        winner = "blue"
    else:
        winner = "draw"

    summary = _build_summary_text(winner, scorecards)

    return FightResult(
        winner=winner,
        method="decision",
        finish_round=None,
        finish_time_seconds=None,
        round_stats=round_stats,
        scorecards=scorecards,
        red_overall_stats={"total_damage": red_damage},
        blue_overall_stats={"total_damage": blue_damage},
        rules=rules,
        seed_used=seed,
        summary_text=summary,
    )


def _simulate_round(
    red: EngineFighter,
    blue: EngineFighter,
    *,
    round_number: int,
    rng: random.Random,
) -> RoundStats:
    """
    Very primitive placeholder round simulation.

    This will later be replaced by a more detailed exchange-based model, but for
    now we just generate a couple of synthetic stats based on the fighters'
    overall ratings so that the engine is testable end-to-end.
    """
    base_red = red.overall_rating
    base_blue = blue.overall_rating

    # Simple noise around base skill levels.
    red_damage = max(0.0, rng.gauss(base_red, 10.0))
    blue_damage = max(0.0, rng.gauss(base_blue, 10.0))

    return RoundStats(
        round_number=round_number,
        red_sig_strikes_landed=int(red_damage // 5),
        red_sig_strikes_attempted=int(red_damage // 3),
        red_damage_score=red_damage,
        blue_sig_strikes_landed=int(blue_damage // 5),
        blue_sig_strikes_attempted=int(blue_damage // 3),
        blue_damage_score=blue_damage,
    )


def _build_summary_text(
    winner: str,
    scorecards: list[JudgeScorecard],
) -> str:
    """Build a human-readable summary line from the scorecards."""
    if winner == "nc":
        return "No contest"
    if winner == "draw":
        return "Draw (decision)"

    decision_type = "unanimous decision"
    # In the future we can inspect the scorecards to decide UD/SD/MD.

    totals = [f"{sc.total_red}-{sc.total_blue}" for sc in scorecards]
    joined = ", ".join(totals)
    corner = "Red" if winner == "red" else "Blue"
    return f"{corner} wins by {decision_type} ({joined})"
