from __future__ import annotations

import re

from django import forms

from fax_calendar import core

try:
    from fax_calendar.validators import validate_woorld_date_parts as _validate_parts
except Exception:  # pragma: no cover - fallback if validators missing
    _validate_parts = None

_WDM_RE1 = re.compile(r"^\s*(\d{1,2})-(\d{1,2})-(\d{1,4})\s*$")  # DD-MM-YYYY
_WDM_RE2 = re.compile(r"^\s*(\d{1,4})-(\d{1,2})-(\d{1,2})\s*$")  # YYYY-MM-DD


def _days_in_month(y: int, m: int) -> int:
    if _validate_parts is not None:
        try:
            _validate_parts(y, m, 1)
        except forms.ValidationError:
            raise
    else:
        if not (1 <= m <= 15):
            raise forms.ValidationError("Měsíc musí být 1–15.")
    return core.month_lengths(y)[m - 1]


def parse_woorld_date(s: str) -> tuple[int, int, int]:
    if not s:
        raise forms.ValidationError("Vyplňte datum.")
    m = _WDM_RE1.match(s) or None
    if m:
        d, mo, y = map(int, m.groups())
    else:
        m = _WDM_RE2.match(s) or None
        if not m:
            raise forms.ValidationError("Čekám DD-MM-YYYY nebo YYYY-MM-DD (Woorld).")
        y, mo, d = map(int, m.groups())
    dim = _days_in_month(y, mo)
    if not (1 <= mo <= 15):
        raise forms.ValidationError("Měsíc musí být 1–15.")
    if not (1 <= d <= dim):
        raise forms.ValidationError(f"Den musí být 1–{dim} pro {mo}. měsíc roku {y}.")
    if _validate_parts is not None:
        try:
            _validate_parts(y, mo, d)
        except forms.ValidationError as exc:
            raise forms.ValidationError(f"Den musí být 1–{dim} pro {mo}. měsíc roku {y}.") from exc
    return y, mo, d


def format_woorld_date(y: int, m: int, d: int) -> str:
    return f"{y:04d}-{m:02d}-{d:02d}"


class WoorldDateFormField(forms.Field):
    """\
    Čistě textové pole pro Woorld datum (15 měsíců).
    clean() vrací normalizovaný string YYYY-MM-DD (s m=1..15).
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", forms.TextInput(attrs={"placeholder": "DD-MM-YYYY"}))
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in (None, ""):
            return ""
        if isinstance(value, str):
            y, m, d = parse_woorld_date(value)
            return format_woorld_date(y, m, d)
        return str(value)

    def clean(self, value):
        v = super().clean(value)
        if v in ("", None):
            return ""
        return v
