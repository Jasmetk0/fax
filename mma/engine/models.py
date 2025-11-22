from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class FightRules:
    """Definition of the ruleset for a fight (rounds, duration, etc.)."""

    rounds: int = 3
    round_duration_seconds: int = 5 * 60
    allow_draws: bool = True
    # placeholder for future flags, e.g. grounded knee rules, etc.


@dataclass
class EngineFighter:
    """
    Snapshot of fighter attributes as seen by the simulation engine.

    This is intentionally decoupled from the Django Fighter model so that
    we can evolve the engine independently of the database schema.
    """

    id: int | None = None
    name: str = ""

    weight_class_slug: str | None = None

    # Core MMA attributes – these are intentionally normalized to a 0–100 scale.
    striking_offense: float = 50.0
    striking_defense: float = 50.0
    power: float = 50.0
    chin: float = 50.0
    wrestling_offense: float = 50.0
    wrestling_defense: float = 50.0
    grappling_offense: float = 50.0
    grappling_defense: float = 50.0
    clinch: float = 50.0
    cardio: float = 50.0
    pace: float = 50.0
    fight_iq: float = 50.0
    toughness: float = 50.0
    aggression: float = 50.0

    style: Literal["striker", "grappler", "wrestler", "brawler", "balanced"] | None = None

    # Optional overall rating as a convenience.
    overall_rating: float = 50.0


@dataclass
class RoundStats:
    """Aggregated stats for a single round of a simulated fight."""

    round_number: int

    red_sig_strikes_landed: int = 0
    red_sig_strikes_attempted: int = 0
    red_knockdowns: int = 0
    red_takedowns: int = 0
    red_sub_attempts: int = 0
    red_control_seconds: int = 0
    red_damage_score: float = 0.0

    blue_sig_strikes_landed: int = 0
    blue_sig_strikes_attempted: int = 0
    blue_knockdowns: int = 0
    blue_takedowns: int = 0
    blue_sub_attempts: int = 0
    blue_control_seconds: int = 0
    blue_damage_score: float = 0.0


@dataclass
class JudgeScorecard:
    """Scores given by a single judge over the whole fight."""

    judge_name: str | None = None
    # list of (red_points, blue_points) per round, in order
    scores_per_round: list[tuple[int, int]] = field(default_factory=list)

    @property
    def total_red(self) -> int:
        return sum(r for r, _ in self.scores_per_round)

    @property
    def total_blue(self) -> int:
        return sum(b for _, b in self.scores_per_round)


@dataclass
class FightResult:
    """High-level container for the result of a simulated fight."""

    winner: Literal["red", "blue", "draw", "nc"]
    method: str
    finish_round: int | None
    finish_time_seconds: int | None

    round_stats: list[RoundStats] = field(default_factory=list)
    scorecards: list[JudgeScorecard] = field(default_factory=list)

    red_overall_stats: dict = field(default_factory=dict)
    blue_overall_stats: dict = field(default_factory=dict)

    rules: FightRules = field(default_factory=FightRules)
    seed_used: int | None = None

    summary_text: str = ""
