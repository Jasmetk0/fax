"""Form widgets for Woorld calendar."""

from django.forms.widgets import TextInput


class WoorldDateWidget(TextInput):
    """Simple text input widget for DD/MM/YYYY Woorld dates."""

    input_type = "text"

    def __init__(self, attrs=None):
        attrs = {"placeholder": "DD/MM/YYYY", **(attrs or {})}
        css = attrs.get("class", "")
        attrs["class"] = f"{css} woorld-date-input".strip()
        super().__init__(attrs)

    class Media:
        css = {"all": ["fax_calendar/widget.css"]}
        js = ["fax_calendar/widget.js"]
