"""Django model fields for Woorld calendar."""

from __future__ import annotations

from datetime import date, datetime

from django.db import models

from .forms import WoorldDateFormField, format_woorld_date, parse_woorld_date


class WoorldDateField(models.CharField):
    """Store Woorld calendar dates as normalized ``YYYY-MM-DD`` strings.

    All parsing and validation delegates to :mod:`fax_calendar.forms` which in
    turn relies on :mod:`fax_calendar.core` for month lengths and leap rules.
    """

    description = "Woorld calendar date"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 16)
        super().__init__(*args, **kwargs)

    # ------------------------------------------------------------------
    # Normalization helpers
    # ------------------------------------------------------------------
    def _normalize(self, value: str | None) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, date | datetime):
            return value.strftime("%Y-%m-%d")
        y, m, d = parse_woorld_date(str(value))
        return format_woorld_date(y, m, d)

    # Django hooks ------------------------------------------------------
    def to_python(self, value):
        return self._normalize(value)

    def get_prep_value(self, value):
        v = self._normalize(value)
        return v or None if self.null else v

    def from_db_value(self, value, expression, connection):  # pragma: no cover - Django API
        return self._normalize(value)

    def formfield(self, **kwargs):
        defaults = {"form_class": WoorldDateFormField}
        defaults.update(kwargs)
        return models.Field.formfield(self, **defaults)


__all__ = ["WoorldDateField"]
