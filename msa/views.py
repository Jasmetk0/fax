<<<<<<< HEAD
from django.shortcuts import get_object_or_404, render

from msa.models import Season
=======
from django.core.exceptions import FieldError
from django.http import HttpResponse
from django.shortcuts import render
>>>>>>> 17c27c8 (MSA FE: Tournaments → Seasons list (dynamic), robust Season lookup, debug header [fmt])

from msa.models import Season


def home(request):
    return render(request, "msa/home/index.html")


def tournaments_list(request):
<<<<<<< HEAD
    seasons = Season.objects.order_by("-id")
=======
    qs = Season.objects.all()
    try:
        seasons = qs.order_by("-year")  # preferujeme nejnovější nahoře
    except FieldError:
        seasons = qs.order_by("-id")  # fallback, když model nemá 'year'
>>>>>>> 17c27c8 (MSA FE: Tournaments → Seasons list (dynamic), robust Season lookup, debug header [fmt])
    return render(request, "msa/tournaments/seasons.html", {"seasons": seasons})


def rankings_list(request):
    return render(request, "msa/rankings/list.html")


def players_list(request):
    return render(request, "msa/players/list.html")


def calendar(request):
    season_id = request.GET.get("season")
    season = get_object_or_404(Season, pk=season_id) if season_id else None
    return render(request, "msa/calendar/index.html", {"season": season})


def media(request):
    return render(request, "msa/media/index.html")


def docs(request):
    return render(request, "msa/docs/index.html")


def search(request):
<<<<<<< HEAD
    return render(request, "msa/search/page.html")


# Vysvětlení: aktivní stav v menu čteme v šabloně z request.path; proto je vhodné mít
# 'django.template.context_processors.request' aktivní (většinou default v settings).
=======
    q = (request.GET.get("q") or "").strip()
    return render(request, "msa/search/page.html", {"q": q})


def nav_live_badge(request):
    """HTMX badge pro Tournaments v topbaru — zatím placeholder."""
    count = 0  # TODO: napoj později na reálná „živá“ data
    if count > 0:
        html = (
            '<span id="live-badge" class="ml-1 inline-flex items-center justify-center '
            "rounded-md border border-slate-200 px-1.5 text-[11px] leading-5 text-slate-700 "
            f'bg-white align-middle">{count}</span>'
        )
    else:
        html = '<span id="live-badge" class="ml-1 hidden"></span>'
    return HttpResponse(html)
>>>>>>> 17c27c8 (MSA FE: Tournaments → Seasons list (dynamic), robust Season lookup, debug header [fmt])
