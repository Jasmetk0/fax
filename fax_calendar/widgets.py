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
        # marker for JS datepicker hookup
        attrs.setdefault("data-woorld-datepicker", "1")
        super().__init__(attrs)

    class Media:
        css = {"all": ["fax_calendar/woorld.css"]}
        js = ["fax_calendar/core.js", "fax_calendar/woorld.js"]


class WoorldAdminDateWidget(TextInput):
    """Admin text input enhanced by Woorld calendar popup."""

    input_type = "text"

    def __init__(self, attrs=None):
        attrs = {"placeholder": "DD-MM-YYYY", "data-woorld-date": "1", **(attrs or {})}
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        button = '<button type="button" class="woorld-calendar-btn">&#x1F4C5;</button>'
        return mark_safe(f"{html}{button}")

    class Media:
        css = {"all": ["fax_calendar/admin_calendar.css"]}
        js = [
            "fax_calendar/core.js",
            "fax_calendar/astro.js",
            "fax_calendar/admin_calendar.js",
        ]
