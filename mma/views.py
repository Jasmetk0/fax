"""Views for the MMA app."""

from django.shortcuts import render
from django.utils import timezone

from .models import Event, Fighter, NewsItem, Ranking


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
