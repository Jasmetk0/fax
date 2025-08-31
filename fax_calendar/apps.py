from django.apps import AppConfig


class FaxCalendarConfig(AppConfig):
    name = "fax_calendar"

    def ready(self) -> None:  # pragma: no cover - import side effects
        from django.contrib.admin.options import ModelAdmin
        from .widgets import WoorldAdminDateWidget

        original_get_form = ModelAdmin.get_form

        def get_form(self, request, obj=None, **kwargs):
            form = original_get_form(self, request, obj, **kwargs)
            for name, field in form.base_fields.items():
                w = field.widget
                if (
                    name.endswith("_date")
                    or getattr(w, "input_type", "") == "date"
                    or getattr(w.attrs, "get", lambda x, y=None: None)("data-fax-date")
                ):
                    attrs = getattr(w, "attrs", {})
                    field.widget = WoorldAdminDateWidget(attrs=attrs)
            return form

        ModelAdmin.get_form = get_form
