"""Validators for Woorld calendar."""

from django.core.exceptions import ValidationError

from .utils import days_in_month


def validate_woorld_date_parts(year: int, month: int, day: int) -> None:
    """Validate numeric parts of Woorld date."""
    if year <= 0:
        raise ValidationError("Rok musí být větší než 0")
    if not 1 <= month <= 15:
        raise ValidationError("Měsíc musí být 1–15")
    max_day = days_in_month(year, month)
    if not 1 <= day <= max_day:
        raise ValidationError(f"Month {month} has {max_day} days in year {year}")
