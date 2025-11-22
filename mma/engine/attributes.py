from __future__ import annotations

from typing import TYPE_CHECKING

from .models import EngineFighter

if TYPE_CHECKING:
    from mma.models import Fighter  # pragma: no cover


def engine_fighter_from_model(
    fighter: Fighter,
    *,
    overall_rating: float | None = None,
) -> EngineFighter:
    """
    Build an EngineFighter snapshot from a Django Fighter instance.

    For now this uses very simple default values and an optional overall_rating
    override. The plan is to extend this once we have a proper attribute model
    (skill ratings, cardio, etc.) in the database.
    """
    full_name = f"{fighter.first_name} {fighter.last_name}".strip()

    ef = EngineFighter(
        id=fighter.id,
        name=full_name or fighter.slug,
        weight_class_slug=None,
    )

    if overall_rating is not None:
        ef.overall_rating = float(overall_rating)

    return ef
