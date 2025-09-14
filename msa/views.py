from django.apps import apps
from django.db import OperationalError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render

from msa.utils.dates import find_season_for_date, get_active_date


def home(request):
    return render(request, "msa/home/index.html")


def seasons_list(request):
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    seasons = []
    if Season:
        try:
            seasons = list(Season.objects.all().order_by("id"))
        except OperationalError:
            seasons = []
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


def tournaments_seasons(request):
    """
    Seznam sezón pro Tournaments landing page, seřazený od nejnovější po nejstarší.
    Preferuje řazení podle start_date/end_date, fallback na -id.
    """
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    seasons = []
    if Season:
        try:
            model_fields = {f.name for f in Season._meta.get_fields()}
            if {"start_date", "end_date"} <= model_fields:
                seasons = list(Season.objects.all().order_by("-start_date", "-end_date", "-id"))
            else:
                seasons = list(Season.objects.all().order_by("-id"))
        except OperationalError:
            seasons = []
    ctx = {"seasons": seasons}
    return render(request, "msa/tournaments/seasons.html", ctx)


def _get_season_by_query_param(request):
    """
    Pokud je v URL ?season=<id>, vrať konkrétní Season; jinak None.
    """
    season_id = request.GET.get("season")
    if not season_id:
        return None
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    if not Season:
        return None
    try:
        return Season.objects.get(pk=season_id)
    except Season.DoesNotExist as err:
        raise Http404("Season not found") from err
    except OperationalError as err:
        raise Http404("Season not found") from err


def rankings_list(request):
    return render(request, "msa/rankings/list.html")


def players_list(request):
    return render(request, "msa/players/list.html")


def calendar(request):
    """
    Kalendář – respektuje ?season=<id>, jinak vybere sezónu dle aktivního data.
    """
    d = get_active_date(request)
    try:
        season = _get_season_by_query_param(request) or find_season_for_date(d)
    except OperationalError:
        season = None
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


def tournaments_api(request):
    """
    JSON seznam turnajů. Preferuje sezonní filtr ?season=<id>.
    Robustně čte typické sloupce Tournament modelu; když nejsou, vrátí základ.
    """
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    Tournament = apps.get_model("msa", "Tournament") if apps.is_installed("msa") else None
    season_id = request.GET.get("season")

    items = []
    if Tournament:
        try:
            qs = Tournament.objects.all()
            fields = {f.name for f in Tournament._meta.get_fields()}
            # filtr podle sezony, pokud existuje FK season
            if season_id and "season" in fields:
                qs = qs.filter(season_id=season_id)
            # fallback: pokud nejsou sezony, ale jsou start/end a máme season interval
            elif (
                season_id
                and Season
                and {"start_date", "end_date"} <= {f.name for f in Season._meta.get_fields()}
                and {"start_date", "end_date"} <= fields
            ):
                try:
                    s = Season.objects.get(pk=season_id)
                    if getattr(s, "start_date", None) and getattr(s, "end_date", None):
                        qs = qs.filter(start_date__lte=s.end_date, end_date__gte=s.start_date)
                except Season.DoesNotExist:
                    pass
            # sestavení výstupu
            for t in qs:
                row = {
                    "id": getattr(t, "id", None),
                    "name": getattr(t, "name", None) or getattr(t, "title", None),
                    "city": getattr(t, "city", None),
                    "country": getattr(t, "country", None),
                    "category": getattr(t, "category", None) or getattr(t, "tier", None),
                    "start_date": getattr(t, "start_date", None) or getattr(t, "start", None),
                    "end_date": getattr(t, "end_date", None) or getattr(t, "end", None),
                }
                # volitelný detail URL, pokud existuje pojmenovaná route
                try:
                    from django.urls import reverse

                    if getattr(t, "id", None) is not None:
                        row["url"] = reverse("msa:tournament_detail", args=[t.id])
                except Exception:
                    row["url"] = None
                items.append(row)
        except OperationalError:
            items = []
    return JsonResponse({"tournaments": items})


def ranking_api(request):
    """Return ranking entries for the frontend table."""
    return JsonResponse({"entries": []})
