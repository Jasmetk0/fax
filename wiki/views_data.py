"""Views for managing data series via the web interface."""

from __future__ import annotations

from django.forms import inlineformset_factory
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .models_data import DataPoint, DataSeries
from .views import AdminModeRequiredMixin

DataPointFormSet = inlineformset_factory(
    DataSeries, DataPoint, fields=["key", "value", "note"], extra=1, can_delete=True
)


class DataSeriesListView(ListView):
    """List all data series; editing controls are shown separately."""

    model = DataSeries
    template_name = "wiki/dataseries_list.html"
    context_object_name = "series_list"

    def get_queryset(self):
        return DataSeries.objects.prefetch_related("categories").order_by("slug")


class DataSeriesDetailView(DetailView):
    """Display a data series with its points."""

    model = DataSeries
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "wiki/dataseries_detail.html"
    queryset = DataSeries.objects.prefetch_related("categories", "points")


class DataSeriesFormMixin(AdminModeRequiredMixin):
    model = DataSeries
    fields = ["slug", "title", "unit", "description", "categories"]
    template_name = "wiki/dataseries_form.html"
    success_url = reverse_lazy("wiki:dataseries-list")

    def get_formset(self):
        if self.request.method == "POST":
            return DataPointFormSet(
                self.request.POST,
                instance=getattr(self, "object", None),
                prefix="points",
            )
        return DataPointFormSet(instance=getattr(self, "object", None), prefix="points")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["points_formset"] = self.get_formset()
        return context

    def form_valid(self, form):
        formset = self.get_formset()
        if not formset.is_valid():
            return self.form_invalid(form)
        self.object = form.save()
        formset.instance = self.object
        formset.save()
        return redirect(self.get_success_url())


class DataSeriesCreateView(DataSeriesFormMixin, CreateView):
    pass


class DataSeriesUpdateView(DataSeriesFormMixin, UpdateView):
    slug_field = "slug"
    slug_url_kwarg = "slug"


class DataSeriesDeleteView(AdminModeRequiredMixin, DeleteView):
    model = DataSeries
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "wiki/dataseries_confirm_delete.html"
    success_url = reverse_lazy("wiki:dataseries-list")
