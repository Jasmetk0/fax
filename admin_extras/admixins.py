from django import forms
from django.db import models

FAX_DATE_FORMAT = "%d-%m-%Y"
FAX_INPUT_FORMATS = [FAX_DATE_FORMAT, "%Y-%m-%d"]


def _resolve_date_widget():
    """Return a text based DateInput widget with DD-MM-YYYY format."""
    for mod, name in [
        ("fax_calendar.widgets", "WoorldAdminDateWidget"),
        ("fax_calendar.widgets", "WorldAdminDateWidget"),
        ("fax_calendar.widgets", "WorldDateInput"),
        ("fax_calendar.widgets", "FaxAdminDateWidget"),
        ("fax_calendar.widgets", "FaxDateInput"),
    ]:
        try:
            Widget = getattr(__import__(mod, fromlist=[name]), name)
            try:
                return Widget(format=FAX_DATE_FORMAT)
            except TypeError:
                try:
                    w = Widget()
                    if hasattr(w, "format"):
                        w.format = FAX_DATE_FORMAT
                    return w
                except Exception:
                    pass
        except Exception:
            continue
    return forms.DateInput(format=FAX_DATE_FORMAT)


class WorldDateAdminMixin:
    formfield_overrides = {
        models.DateField: {"widget": _resolve_date_widget()},
    }

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if isinstance(db_field, models.DateField) and field:
            field.input_formats = FAX_INPUT_FORMATS
            w = field.widget
            if hasattr(w, "format"):
                try:
                    w.format = FAX_DATE_FORMAT
                except Exception:
                    pass
            for k in ("min", "max"):
                try:
                    if k in w.attrs:
                        w.attrs.pop(k, None)
                except Exception:
                    pass
            w.attrs.setdefault("placeholder", "DD-MM-YYYY")
        return field
