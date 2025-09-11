from django import forms
from django.db import models

# Dynamický import kanonického widgetu (nezlom aplikaci, když není)
_DateWidget = None
try:
    from fax_calendar.widgets import WoorldAdminDateWidget as _DateWidget  # pokud existuje
except Exception:
    try:
        from fax_calendar.widgets import WorldDateInput as _DateWidget
    except Exception:
        try:
            from fax_calendar.widgets import FaxDateInput as _DateWidget
        except Exception:
            pass

if _DateWidget is None:
    # Fallback – HTML5 datepicker, klikací v moderních prohlížečích
    class _DateWidget(forms.DateInput):
        input_type = "date"


class WorldDateAdminMixin:
    # sjednotí widgety pro všechny DateField v adminu
    formfield_overrides = {
        models.DateField: {"widget": _DateWidget},
    }
