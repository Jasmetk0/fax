"""Admin integration for data series."""

from __future__ import annotations

import io

from django import forms
from django.contrib import admin, messages
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _

from .models_data import DataPoint, DataSeries
from .utils_data import import_csv_to_series


class DataPointInlineFormSet(BaseInlineFormSet):
    """Validate that keys are unique within a series."""

    def clean(self) -> None:  # type: ignore[override]
        super().clean()
        keys = []
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            key = form.cleaned_data.get("key")
            if key in keys:
                raise forms.ValidationError(
                    _("Duplicate key %(key)s"), params={"key": key}
                )
            keys.append(key)


class DataPointInline(admin.TabularInline):
    model = DataPoint
    formset = DataPointInlineFormSet
    extra = 0
    ordering = ("key",)


class CSVImportActionForm(admin.helpers.ActionForm):
    csv_file = forms.FileField(label=_("CSV file"), required=True)


@admin.register(DataSeries)
class DataSeriesAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "unit", "category", "sub_category")
    inlines = [DataPointInline]
    action_form = CSVImportActionForm
    actions = ["import_csv"]

    def import_csv(self, request, queryset):  # pragma: no cover - simple wrapper
        if queryset.count() != 1:
            self.message_user(
                request, _("Select exactly one series."), level=messages.ERROR
            )
            return
        file = request.FILES.get("csv_file")
        if not file:
            self.message_user(request, _("No file provided."), level=messages.ERROR)
            return
        series = queryset.first()
        created, updated = import_csv_to_series(
            series, io.TextIOWrapper(file, encoding="utf-8")
        )
        self.message_user(
            request,
            _(f"Imported: {created} created, {updated} updated."),
        )

    import_csv.short_description = _("Import CSV")
