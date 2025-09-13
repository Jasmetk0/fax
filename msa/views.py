from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from msa.models import Season


def home(request):
    return render(request, "msa/home/index.html")


def tournaments_list(request):
    seasons = Season.objects.order_by("-id")
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
