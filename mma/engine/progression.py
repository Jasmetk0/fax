"""
Attribute progression and degradation helpers for the MMA engine.

These functions are intentionally very conservative no-ops at this stage.
They are meant as extension points for modelling training improvements,
age-related decline, wear and tear, etc.
"""

from __future__ import annotations

from dataclasses import replace

from .models import EngineFighter


def apply_age_curve(fighter: EngineFighter, *, age_years: float) -> EngineFighter:
    """
    Return a modified copy of `fighter` with age-related adjustments applied.

    The curve favours a prime window in the late twenties, eases into a slow
    decline in the early thirties, and accelerates degradation in the late
    thirties. Attributes that typically age faster (cardio, pace, aggression)
    are dampened a little more, while power holds up slightly better. Fight IQ
    gains a small boost up to the mid-thirties before stabilising.
    """
    clone = replace(fighter)

    base_multiplier = _base_age_multiplier(age_years)
    fast_decline = _fast_decline_multiplier(age_years)

    clone.striking_offense = _clamp(clone.striking_offense * base_multiplier)
    clone.striking_defense = _clamp(clone.striking_defense * base_multiplier)

    power_multiplier = base_multiplier if age_years < 36 else max(base_multiplier, 0.96)
    clone.power = _clamp(clone.power * power_multiplier)

    clone.chin = _clamp(clone.chin * base_multiplier)

    wrestling_multiplier = base_multiplier
    clone.wrestling_offense = _clamp(clone.wrestling_offense * wrestling_multiplier)
    clone.wrestling_defense = _clamp(clone.wrestling_defense * wrestling_multiplier)

    grappling_multiplier = base_multiplier
    clone.grappling_offense = _clamp(clone.grappling_offense * grappling_multiplier)
    clone.grappling_defense = _clamp(clone.grappling_defense * grappling_multiplier)

    clone.clinch = _clamp(clone.clinch * base_multiplier)

    cardio_multiplier = base_multiplier * fast_decline
    clone.cardio = _clamp(clone.cardio * cardio_multiplier)
    clone.pace = _clamp(clone.pace * cardio_multiplier)
    clone.aggression = _clamp(clone.aggression * cardio_multiplier)

    iq_multiplier = base_multiplier
    if age_years <= 34:
        iq_multiplier = min(base_multiplier * 1.02, base_multiplier + 0.02)
    clone.fight_iq = _clamp(clone.fight_iq * iq_multiplier)

    clone.toughness = _clamp(clone.toughness * base_multiplier)

    clone.overall_rating = _clamp(clone.overall_rating * base_multiplier)

    return clone


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
    clone = replace(fighter)

    if focus == "striking":
        clone.striking_offense = _clamp(clone.striking_offense + 2)
        clone.power = _clamp(clone.power + 2)
        clone.wrestling_offense = _clamp(clone.wrestling_offense - 1)
    elif focus == "wrestling":
        clone.wrestling_offense = _clamp(clone.wrestling_offense + 2)
        clone.wrestling_defense = _clamp(clone.wrestling_defense + 2)
        clone.striking_offense = _clamp(clone.striking_offense - 1)
    elif focus == "grappling":
        clone.grappling_offense = _clamp(clone.grappling_offense + 2)
        clone.grappling_defense = _clamp(clone.grappling_defense + 2)
    elif focus == "cardio":
        clone.cardio = _clamp(clone.cardio + 3)
        clone.pace = _clamp(clone.pace + 1)
        clone.toughness = _clamp(clone.toughness + 1)

    return clone


def apply_wear_and_tear(
    fighter: EngineFighter,
) -> EngineFighter:
    """
    Apply long-term wear-and-tear adjustments based on previous wars,
    knockouts, and accumulated damage.

    Currently a no-op; this will be implemented once we have a way to feed
    past fight results and damage into the engine.
    """
    clone = replace(fighter)
    clone.chin = _clamp(clone.chin - 1)
    clone.cardio = _clamp(clone.cardio - 1)
    clone.pace = _clamp(clone.pace - 1)
    return clone


def _base_age_multiplier(age_years: float) -> float:
    if age_years < 18:
        return 0.90
    if age_years < 22:
        return 0.93 + (age_years - 18) * 0.01
    if age_years < 27:
        return 0.98 + (age_years - 22) * 0.004
    if age_years <= 30:
        return 1.02
    if age_years < 32:
        return 1.0 - (age_years - 30) * 0.01
    if age_years <= 35:
        return 0.98
    if age_years <= 40:
        return 0.95
    return 0.93


def _fast_decline_multiplier(age_years: float) -> float:
    if age_years >= 36:
        return 0.94
    if age_years >= 32:
        return 0.97
    return 1.0


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))
