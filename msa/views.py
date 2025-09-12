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


# Vysvětlení: aktivní stav v menu čteme v šabloně z request.path; proto je vhodné mít
# 'django.template.context_processors.request' aktivní (většinou default v settings).
