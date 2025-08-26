"""Views for the MMA app."""

from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import (
    Bout,
    Event,
    Fighter,
    NewsItem,
    Organization,
    Ranking,
    WeightClass,
)


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

    return render(
        request,
        "mma/dashboard.html",
        {
            "upcoming_events": upcoming_events,
            "recent_results": recent_results,
            "rankings": rankings,
            "fighters": fighters,
            "news_items": news_items,
        },
    )


def organization_list(request):
    organizations = Organization.objects.order_by("name")
    return render(request, "mma/organizations.html", {"organizations": organizations})


def organization_detail(request, slug):
    organization = get_object_or_404(Organization, slug=slug)
    events = organization.events.order_by("-date_start")
    return render(
        request,
        "mma/organization_detail.html",
        {"organization": organization, "events": events},
    )


def event_list(request):
    events = Event.objects.select_related("organization").order_by("-date_start")
    return render(request, "mma/events.html", {"events": events})


def event_detail(request, slug):
    event = get_object_or_404(
        Event.objects.select_related("organization", "venue"), slug=slug
    )
    bouts = event.bouts.select_related("fighter_red", "fighter_blue").order_by("id")
    return render(
        request,
        "mma/event_detail.html",
        {"event": event, "bouts": bouts},
    )


def fighter_list(request):
    query = request.GET.get("query", "")
    fighters = Fighter.objects.all()
    if query:
        fighters = fighters.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
    fighters = fighters.order_by("last_name")
    return render(request, "mma/fighters.html", {"fighters": fighters})


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
        {"fighter": fighter, "bouts": bouts},
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
    return render(request, "mma/rankings.html", {"ranking_groups": ranking_groups})


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
        },
    )
