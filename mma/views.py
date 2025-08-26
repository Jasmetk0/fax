"""Views for the MMA app."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, UpdateView

from .models import (
    Bout,
    Event,
    Fighter,
    NewsItem,
    Organization,
    Ranking,
    WeightClass,
)
from .forms import (
    BoutForm,
    EventForm,
    FighterForm,
    NewsItemForm,
    OrganizationForm,
    RankingForm,
)


def _is_admin(request):
    return request.user.is_staff and request.session.get("admin_mode")


def dashboard(request):
    """Render the MMA dashboard with basic sections."""
    now = timezone.now()
    upcoming_events = (
        Event.objects.filter(date_start__gte=now)
        .select_related("organization", "venue")
        .order_by("date_start")[:3]
    )
    recent_results = (
        Event.objects.filter(date_start__lt=now, is_completed=True)
        .select_related("organization", "venue")
        .order_by("-date_start")[:3]
    )
    rankings = Ranking.objects.select_related(
        "organization", "weight_class", "fighter"
    ).order_by("position")[:5]
    fighters = Fighter.objects.order_by("last_name")[:5]
    news_items = NewsItem.objects.order_by("-published_at")[:5]
    admin = _is_admin(request)

    return render(
        request,
        "mma/dashboard.html",
        {
            "upcoming_events": upcoming_events,
            "recent_results": recent_results,
            "rankings": rankings,
            "fighters": fighters,
            "news_items": news_items,
            "admin": admin,
        },
    )


def organization_list(request):
    organizations = Organization.objects.order_by("name")
    return render(
        request,
        "mma/organizations.html",
        {"organizations": organizations, "admin": _is_admin(request)},
    )


def organization_detail(request, slug):
    organization = get_object_or_404(Organization, slug=slug)
    events = organization.events.order_by("-date_start")
    return render(
        request,
        "mma/organization_detail.html",
        {
            "organization": organization,
            "events": events,
            "admin": _is_admin(request),
        },
    )


def event_list(request):
    events = Event.objects.select_related("organization").order_by("-date_start")
    return render(
        request,
        "mma/events.html",
        {"events": events, "admin": _is_admin(request)},
    )


def event_detail(request, slug):
    event = get_object_or_404(
        Event.objects.select_related("organization", "venue"), slug=slug
    )
    bouts = event.bouts.select_related("fighter_red", "fighter_blue").order_by("id")
    return render(
        request,
        "mma/event_detail.html",
        {"event": event, "bouts": bouts, "admin": _is_admin(request)},
    )


def fighter_list(request):
    query = request.GET.get("query", "")
    fighters = Fighter.objects.all()
    if query:
        fighters = fighters.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
    fighters = fighters.order_by("last_name")
    return render(
        request,
        "mma/fighters.html",
        {"fighters": fighters, "admin": _is_admin(request)},
    )


def fighter_detail(request, slug):
    fighter = get_object_or_404(Fighter, slug=slug)
    bouts = (
        Bout.objects.filter(Q(fighter_red=fighter) | Q(fighter_blue=fighter))
        .select_related("event", "fighter_red", "fighter_blue")
        .order_by("-event__date_start")
    )
    return render(
        request,
        "mma/fighter_detail.html",
        {"fighter": fighter, "bouts": bouts, "admin": _is_admin(request)},
    )


def ranking_list(request):
    ranking_groups = (
        Ranking.objects.select_related("organization", "weight_class")
        .values(
            "organization",
            "organization__short_name",
            "organization__slug",
            "weight_class",
            "weight_class__name",
            "weight_class__slug",
        )
        .distinct()
    )
    ranking_groups = [
        {
            "organization": Organization(
                id=r["organization"],
                short_name=r["organization__short_name"],
                slug=r["organization__slug"],
            ),
            "weight_class": WeightClass(
                id=r["weight_class"],
                name=r["weight_class__name"],
                slug=r["weight_class__slug"],
            ),
        }
        for r in ranking_groups
    ]
    return render(
        request,
        "mma/rankings.html",
        {"ranking_groups": ranking_groups, "admin": _is_admin(request)},
    )


def ranking_detail(request, org_slug, weight_slug):
    organization = get_object_or_404(Organization, slug=org_slug)
    weight_class = get_object_or_404(WeightClass, slug=weight_slug)
    rankings = (
        Ranking.objects.filter(organization=organization, weight_class=weight_class)
        .select_related("fighter")
        .order_by("position")
    )
    return render(
        request,
        "mma/ranking_detail.html",
        {
            "organization": organization,
            "weight_class": weight_class,
            "rankings": rankings,
            "admin": _is_admin(request),
        },
    )


class AdminModeRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin ensuring the user is staff and has admin mode enabled."""

    def test_func(self):
        return _is_admin(self.request)


# Organization CRUD -----------------------------------------------------


class OrganizationCreateView(AdminModeRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = "mma/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Add Organization"
        return ctx

    def get_success_url(self):
        return reverse("mma:organization_list")


class OrganizationUpdateView(AdminModeRequiredMixin, UpdateView):
    model = Organization
    form_class = OrganizationForm
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "mma/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Edit Organization"
        return ctx

    def get_success_url(self):
        return reverse("mma:organization_detail", args=[self.object.slug])


class OrganizationDeleteView(AdminModeRequiredMixin, DeleteView):
    model = Organization
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "mma/confirm_delete.html"
    success_url = reverse_lazy("mma:organization_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Delete Organization"
        ctx["cancel_url"] = reverse("mma:organization_detail", args=[self.object.slug])
        return ctx


# Event CRUD ------------------------------------------------------------


class EventCreateView(AdminModeRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "mma/form.html"

    def get_initial(self):
        initial = super().get_initial()
        org_slug = self.request.GET.get("organization")
        if org_slug:
            initial["organization"] = get_object_or_404(Organization, slug=org_slug)
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Add Event"
        return ctx

    def get_success_url(self):
        return reverse("mma:event_list")


class EventUpdateView(AdminModeRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "mma/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Edit Event"
        return ctx

    def get_success_url(self):
        return reverse("mma:event_detail", args=[self.object.slug])


class EventDeleteView(AdminModeRequiredMixin, DeleteView):
    model = Event
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "mma/confirm_delete.html"
    success_url = reverse_lazy("mma:event_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Delete Event"
        ctx["cancel_url"] = reverse("mma:event_detail", args=[self.object.slug])
        return ctx


# Fighter CRUD ----------------------------------------------------------


class FighterCreateView(AdminModeRequiredMixin, CreateView):
    model = Fighter
    form_class = FighterForm
    template_name = "mma/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Add Fighter"
        return ctx

    def get_success_url(self):
        return reverse("mma:fighter_list")


class FighterUpdateView(AdminModeRequiredMixin, UpdateView):
    model = Fighter
    form_class = FighterForm
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "mma/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Edit Fighter"
        return ctx

    def get_success_url(self):
        return reverse("mma:fighter_detail", args=[self.object.slug])


class FighterDeleteView(AdminModeRequiredMixin, DeleteView):
    model = Fighter
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "mma/confirm_delete.html"
    success_url = reverse_lazy("mma:fighter_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Delete Fighter"
        ctx["cancel_url"] = reverse("mma:fighter_detail", args=[self.object.slug])
        return ctx


# Bout CRUD -------------------------------------------------------------


class BoutCreateView(AdminModeRequiredMixin, CreateView):
    model = Bout
    form_class = BoutForm
    template_name = "mma/form.html"

    def get_initial(self):
        initial = super().get_initial()
        event_slug = self.kwargs.get("event_slug")
        if event_slug:
            initial["event"] = get_object_or_404(Event, slug=event_slug)
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Add Bout"
        return ctx

    def get_success_url(self):
        return reverse("mma:event_detail", args=[self.object.event.slug])


class BoutUpdateView(AdminModeRequiredMixin, UpdateView):
    model = Bout
    form_class = BoutForm
    template_name = "mma/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Edit Bout"
        return ctx

    def get_success_url(self):
        return reverse("mma:event_detail", args=[self.object.event.slug])


class BoutDeleteView(AdminModeRequiredMixin, DeleteView):
    model = Bout
    template_name = "mma/confirm_delete.html"

    def get_success_url(self):
        return reverse("mma:event_detail", args=[self.object.event.slug])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Delete Bout"
        ctx["cancel_url"] = reverse("mma:event_detail", args=[self.object.event.slug])
        return ctx


# Ranking CRUD ----------------------------------------------------------


class RankingCreateView(AdminModeRequiredMixin, CreateView):
    model = Ranking
    form_class = RankingForm
    template_name = "mma/form.html"

    def get_initial(self):
        initial = super().get_initial()
        org_slug = self.kwargs.get("org_slug") or self.request.GET.get("organization")
        weight_slug = self.kwargs.get("weight_slug") or self.request.GET.get(
            "weight_class"
        )
        if org_slug:
            initial["organization"] = get_object_or_404(Organization, slug=org_slug)
        if weight_slug:
            initial["weight_class"] = get_object_or_404(WeightClass, slug=weight_slug)
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Add Ranking Entry"
        return ctx

    def get_success_url(self):
        return reverse(
            "mma:ranking_detail",
            args=[self.object.organization.slug, self.object.weight_class.slug],
        )


class RankingUpdateView(AdminModeRequiredMixin, UpdateView):
    model = Ranking
    form_class = RankingForm
    template_name = "mma/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Edit Ranking Entry"
        return ctx

    def get_success_url(self):
        return reverse(
            "mma:ranking_detail",
            args=[self.object.organization.slug, self.object.weight_class.slug],
        )


class RankingDeleteView(AdminModeRequiredMixin, DeleteView):
    model = Ranking
    template_name = "mma/confirm_delete.html"

    def get_success_url(self):
        return reverse(
            "mma:ranking_detail",
            args=[self.object.organization.slug, self.object.weight_class.slug],
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Delete Ranking Entry"
        ctx["cancel_url"] = reverse(
            "mma:ranking_detail",
            args=[self.object.organization.slug, self.object.weight_class.slug],
        )
        return ctx


# NewsItem CRUD ---------------------------------------------------------


class NewsItemCreateView(AdminModeRequiredMixin, CreateView):
    model = NewsItem
    form_class = NewsItemForm
    template_name = "mma/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Add News Item"
        return ctx

    def get_success_url(self):
        return reverse("mma:dashboard")


class NewsItemUpdateView(AdminModeRequiredMixin, UpdateView):
    model = NewsItem
    form_class = NewsItemForm
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "mma/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Edit News Item"
        return ctx

    def get_success_url(self):
        return reverse("mma:dashboard")


class NewsItemDeleteView(AdminModeRequiredMixin, DeleteView):
    model = NewsItem
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "mma/confirm_delete.html"
    success_url = reverse_lazy("mma:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Delete News Item"
        ctx["cancel_url"] = reverse("mma:dashboard")
        return ctx
