"""Backwards-compatible aliases for Woorld calendar fields."""

from .forms import WoorldDateFormField
from .model_fields import WoorldDateField

__all__ = ["WoorldDateField", "WoorldDateFormField"]
