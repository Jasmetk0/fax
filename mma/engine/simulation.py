from __future__ import annotations

import random

from .config import DEFAULT_RANDOM_SEED
from .models import EngineFighter, FightResult, FightRules, JudgeScorecard, RoundStats
from .probability import normalize_pair
from .scorecards import build_scorecards


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
        round_stats.append(
            _simulate_round(
                red,
                blue,
                round_number=round_number,
                rng=rng,
                rules=rules,
            )
        )

    scorecards = build_scorecards(round_stats, rng=rng)

    red_judges = sum(1 for sc in scorecards if sc.total_red > sc.total_blue)
    blue_judges = sum(1 for sc in scorecards if sc.total_blue > sc.total_red)

    if red_judges > blue_judges:
        winner = "red"
    elif blue_judges > red_judges:
        winner = "blue"
    else:
        winner = "draw"

    if winner == "draw":
        decision_type = "draw"
    elif max(red_judges, blue_judges) == 3:
        decision_type = "UD"
    else:
        decision_type = "SD"

    red_damage = sum(r.red_damage_score for r in round_stats)
    blue_damage = sum(r.blue_damage_score for r in round_stats)

    summary = _build_summary_text(winner, decision_type, scorecards)

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
    rules: FightRules,
) -> RoundStats:
    """Simulate a single round using basic activity and probability models."""

    red_activity = _round_activity(red, round_number=round_number, rng=rng)
    blue_activity = _round_activity(blue, round_number=round_number, rng=rng)

    red_attempts = max(1, int(red_activity * 3))
    blue_attempts = max(1, int(blue_activity * 3))

    red_p_hit = normalize_pair(red.striking_offense, blue.striking_defense)[0]
    blue_p_hit = normalize_pair(blue.striking_offense, red.striking_defense)[0]

    red_landed = _sample_successes(red_attempts, red_p_hit, rng)
    blue_landed = _sample_successes(blue_attempts, blue_p_hit, rng)

    red_kd = _sample_knockdowns(
        landed=red_landed, power=red.power, opponent_chin=blue.chin, rng=rng
    )
    blue_kd = _sample_knockdowns(
        landed=blue_landed, power=blue.power, opponent_chin=red.chin, rng=rng
    )

    red_td_attempts = max(0, int(red_activity * 0.3))
    blue_td_attempts = max(0, int(blue_activity * 0.3))

    red_td = _sample_successes(
        red_td_attempts,
        normalize_pair(red.wrestling_offense, blue.wrestling_defense)[0],
        rng,
    )
    blue_td = _sample_successes(
        blue_td_attempts,
        normalize_pair(blue.wrestling_offense, red.wrestling_defense)[0],
        rng,
    )

    red_sub_attempts = _sample_submissions(
        attempts=max(1, red_td),
        offense=red.grappling_offense,
        defense=blue.grappling_defense,
        aggression=red.aggression,
        rng=rng,
    )
    blue_sub_attempts = _sample_submissions(
        attempts=max(1, blue_td),
        offense=blue.grappling_offense,
        defense=red.grappling_defense,
        aggression=blue.aggression,
        rng=rng,
    )

    red_damage = _damage_score(
        strikes=red_landed,
        knockdowns=red_kd,
        takedowns=red_td,
        submissions=red_sub_attempts,
    )
    blue_damage = _damage_score(
        strikes=blue_landed,
        knockdowns=blue_kd,
        takedowns=blue_td,
        submissions=blue_sub_attempts,
    )

    return RoundStats(
        round_number=round_number,
        red_sig_strikes_landed=red_landed,
        red_sig_strikes_attempted=red_attempts,
        red_knockdowns=red_kd,
        red_takedowns=red_td,
        red_sub_attempts=red_sub_attempts,
        red_control_seconds=int(red_td * rules.round_duration_seconds * 0.05),
        red_damage_score=red_damage,
        blue_sig_strikes_landed=blue_landed,
        blue_sig_strikes_attempted=blue_attempts,
        blue_knockdowns=blue_kd,
        blue_takedowns=blue_td,
        blue_sub_attempts=blue_sub_attempts,
        blue_control_seconds=int(blue_td * rules.round_duration_seconds * 0.05),
        blue_damage_score=blue_damage,
    )


def _build_summary_text(
    winner: str,
    decision_type: str,
    scorecards: list[JudgeScorecard],
) -> str:
    """Build a human-readable summary line from the scorecards."""
    if winner == "nc":
        return "No contest"
    if winner == "draw":
        totals = [f"{sc.total_red}-{sc.total_blue}" for sc in scorecards]
        joined = ", ".join(totals)
        return f"Draw (decision: {joined})"

    totals = [f"{sc.total_red}-{sc.total_blue}" for sc in scorecards]
    joined = ", ".join(totals)
    corner = "Red" if winner == "red" else "Blue"
    return f"{corner} wins by {decision_type} ({joined})"


def _round_activity(fighter: EngineFighter, *, round_number: int, rng: random.Random) -> float:
    """Compute a simple activity measure for the round."""

    cardio_decline = 0.05 * (round_number - 1)
    cardio_factor = max(0.5, (fighter.cardio / 100) * (1 - cardio_decline))
    return (fighter.pace / 10) * cardio_factor * rng.uniform(0.7, 1.3)


def _sample_successes(attempts: int, probability: float, rng: random.Random) -> int:
    probability = max(0.0, min(1.0, probability))
    successes = 0
    for _ in range(attempts):
        if rng.random() < probability:
            successes += 1
    return successes


def _sample_knockdowns(
    *,
    landed: int,
    power: float,
    opponent_chin: float,
    rng: random.Random,
) -> int:
    if landed <= 0:
        return 0

    base_prob = normalize_pair(power, opponent_chin)[0] * 0.1
    knockdowns = 0
    for _ in range(landed):
        if rng.random() < base_prob:
            knockdowns += 1
    return knockdowns


def _sample_submissions(
    *,
    attempts: int,
    offense: float,
    defense: float,
    aggression: float,
    rng: random.Random,
) -> int:
    base_chance = normalize_pair(offense + aggression * 0.3, defense)[0] * 0.5
    submissions = 0
    for _ in range(attempts):
        if rng.random() < base_chance:
            submissions += 1
    return submissions


def _damage_score(*, strikes: int, knockdowns: int, takedowns: int, submissions: int) -> float:
    return strikes * 1.0 + knockdowns * 8.0 + takedowns * 2.0 + submissions * 3.0
