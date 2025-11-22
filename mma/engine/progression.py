"""
Attribute progression and degradation helpers for the MMA engine.

These functions are intentionally very conservative no-ops at this stage.
They are meant as extension points for modelling training improvements,
age-related decline, wear and tear, etc.
"""

from __future__ import annotations

from .models import EngineFighter


def apply_age_curve(fighter: EngineFighter, *, age_years: float) -> EngineFighter:
    """
    Return a modified copy of `fighter` with age-related adjustments applied.

    At this stage this is a no-op and simply returns the fighter unchanged.
    """
    return fighter


def apply_training_block(
    fighter: EngineFighter,
    *,
    focus: str,
) -> EngineFighter:
    """
    Apply a theoretical 'training block' to the fighter attributes.

    The 'focus' parameter is a free-form string for now (e.g. 'striking',
    'wrestling', 'cardio') and has no effect in this placeholder implementation.
    """
    return fighter


def apply_wear_and_tear(
    fighter: EngineFighter,
) -> EngineFighter:
    """
    Apply long-term wear-and-tear adjustments based on previous wars,
    knockouts, and accumulated damage.

    Currently a no-op; this will be implemented once we have a way to feed
    past fight results and damage into the engine.
    """
    return fighter
