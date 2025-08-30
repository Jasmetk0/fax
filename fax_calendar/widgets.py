"""Form widgets for Woorld calendar."""

from django.forms.widgets import TextInput


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
