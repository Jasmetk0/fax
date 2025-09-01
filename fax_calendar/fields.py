"""Custom fields for Woorld calendar."""

from django import forms
from django.db import models
from .widgets import WoorldDateWidget
from .utils import (
    parse_woorld_date,
    format_woorld_date,
    to_storage,
    from_storage,
)
from .validators import validate_woorld_date_parts


class WoorldDateFormField(forms.CharField):
    """Form field handling ``DD-MM-YYYY`` input and storage formatting."""

    widget = WoorldDateWidget

    def to_python(self, value):
        if not value:
            return ""
        year, month, day = parse_woorld_date(value)
        validate_woorld_date_parts(year, month, day)
        return to_storage(year, month, day)

    def prepare_value(self, value):
        try:
            year, month, day = from_storage(value)
        except Exception:
            return (None, None, None)
        if None in (year, month, day):
            return (None, None, None)
        return format_woorld_date(year, month, day)


class WoorldDateField(models.CharField):
    """Model field storing Woorld date as ``YYYY-MM-DD`` string."""

    description = "Woorld calendar date"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 16)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {"form_class": WoorldDateFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)
