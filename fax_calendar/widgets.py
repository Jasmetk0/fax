"""Form widgets for Woorld calendar."""

from django.forms.widgets import TextInput
from django.utils.safestring import mark_safe


class WoorldDateWidget(TextInput):
    """Simple text input widget for ``DD-MM-YYYY`` Woorld dates."""

    input_type = "text"

    def __init__(self, attrs=None):
        attrs = {"placeholder": "DD-MM-YYYY", **(attrs or {})}
        css = attrs.get("class", "")
        attrs["class"] = f"{css} woorld-date-input".strip()
        super().__init__(attrs)

    class Media:
        css = {"all": ["fax_calendar/datepicker.css"]}
        js = [
            "fax_calendar/core.js",
            "fax_calendar/astro.js",
            "fax_calendar/datepicker.js",
        ]


class WoorldAdminDateWidget(TextInput):
    """Admin text input enhanced by Woorld calendar popup."""

    input_type = "text"

    def __init__(self, attrs=None):
        attrs = {"placeholder": "DD-MM-YYYY", **(attrs or {})}
        css = attrs.get("class", "")
        attrs["class"] = f"{css} woorld-date-input".strip()
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        button = '<button type="button" class="woorld-calendar-btn">&#x1F4C5;</button>'
        return mark_safe(f"{html}{button}")

    class Media:
        css = {"all": ["fax_calendar/datepicker.css"]}
        js = [
            "admin/js/core.js",
            "fax_calendar/core.js",
            "fax_calendar/astro.js",
            "fax_calendar/datepicker.js",
        ]
