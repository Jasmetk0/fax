"""Custom fields for Woorld calendar."""

from django import forms
from django.db import models
from datetime import date as date_cls

from .widgets import WoorldDateWidget
from .utils import (
    parse_woorld_date,
    format_woorld_date,
    from_storage,
)


class WoorldDateFormField(forms.CharField):
    """Form field handling ``DD-MM-YYYY`` input and storage formatting."""

    widget = WoorldDateWidget

    def to_python(self, value):
        if value in self.empty_values:
            return None
        year, month, day = parse_woorld_date(value)
        if (year, month, day) == (None, None, None):
            return None
        return date_cls(year, month, day)

    def prepare_value(self, value):
        if isinstance(value, str):
            try:
                year, month, day = from_storage(value)
                if None in (year, month, day):
                    return (None, None, None)
                return format_woorld_date(year, month, day)
            except Exception:  # pragma: no cover - defensive
                return (None, None, None)
        return super().prepare_value(value)


class WoorldDateField(models.CharField):
    """Model field storing Woorld date as ``YYYY-MM-DD`` string."""

    description = "Woorld calendar date"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 16)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {"form_class": WoorldDateFormField, "max_length": None}
        defaults.update(kwargs)
        return super().formfield(**defaults)
