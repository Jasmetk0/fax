from django import forms
from django.db import models

# Dynamický import kanonického widgetu (nezlom aplikaci, když není)
_DateWidget = None
try:
    # 1) preferuj "Woorld…" (pokud v repu existuje s dvojitým 'o')
    from fax_calendar.widgets import WoorldAdminDateWidget as _DateWidget
except Exception:
    try:
        # 2) běžnější pravopis
        from fax_calendar.widgets import WorldAdminDateWidget as _DateWidget
    except Exception:
        try:
            # 3) input varianta
            from fax_calendar.widgets import WorldDateInput as _DateWidget
        except Exception:
            try:
                # 4) Fax admin
                from fax_calendar.widgets import FaxAdminDateWidget as _DateWidget
            except Exception:
                try:
                    # 5) Fax input
                    from fax_calendar.widgets import FaxDateInput as _DateWidget
                except Exception:
                    _DateWidget = None

if _DateWidget is None:
    # Fallback – HTML5 datepicker, klikací v moderních prohlížečích
    class _DateWidget(forms.DateInput):
        input_type = "date"


class WorldDateAdminMixin:
    # sjednotí widgety pro všechny DateField v adminu
    formfield_overrides = {
        models.DateField: {"widget": _DateWidget},
    }
