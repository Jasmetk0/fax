from django.apps import apps
from django.http import HttpResponse
from django.shortcuts import render

from msa.utils.dates import find_season_for_date, get_active_date


def home(request):
    return render(request, "msa/home/index.html")


def seasons_list(request):
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    seasons = Season.objects.all().order_by("id") if Season else []
    return render(request, "msa/seasons/list.html", {"seasons": seasons})


def tournaments_list(request):
    d = get_active_date(request)
    season = find_season_for_date(d)
    if not season:
        return seasons_list(request)

    Tournament = apps.get_model("msa", "Tournament") if apps.is_installed("msa") else None
    tournaments = []
    if Tournament:
        qs = Tournament.objects.all()
        fields = {f.name for f in Tournament._meta.get_fields()}
        if "season" in fields:
            tournaments = qs.filter(season=season)
        elif {"start_date", "end_date"}.issubset(fields):
            start = getattr(season, "start_date", None)
            end = getattr(season, "end_date", None)
            if start and end:
                tournaments = qs.filter(start_date__lte=end, end_date__gte=start)
        elif "start_date" in fields:
            start = getattr(season, "start_date", None)
            end = getattr(season, "end_date", None)
            if start and end:
                tournaments = qs.filter(start_date__range=(start, end))
        elif "date" in fields:
            start = getattr(season, "start_date", None)
            end = getattr(season, "end_date", None)
            if start and end:
                tournaments = qs.filter(date__range=(start, end))

    context = {
        "tournaments": tournaments,
        "active_season": season,
        "active_date": d,
    }
    return render(request, "msa/tournaments/list.html", context)


def rankings_list(request):
    return render(request, "msa/rankings/list.html")


def players_list(request):
    return render(request, "msa/players/list.html")


def calendar(request):
    d = get_active_date(request)
    season = find_season_for_date(d)
    if not season:
        return seasons_list(request)

    context = {"active_season": season, "active_date": d, "season": season}
    return render(request, "msa/calendar/index.html", context)


def media(request):
    return render(request, "msa/media/index.html")


def docs(request):
    return render(request, "msa/docs/index.html")


def search(request):
    return render(request, "msa/search/page.html")


def nav_live_badge(request):
    count = 0  # TODO: reálná logika později
    if count > 0:
        return HttpResponse(
            '<span id="live-badge" class="ml-1 inline-flex items-center justify-center '
            "rounded-md border border-slate-200 px-1.5 text-[11px] leading-5 text-slate-700 "
            f'bg-white align-middle">{count}</span>'
        )
    return HttpResponse('<span id="live-badge" class="ml-1 hidden"></span>')
