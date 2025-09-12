from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    return render(request, "msa/home/index.html")


def tournaments_list(request):
    return render(request, "msa/tournaments/list.html")


def rankings_list(request):
    return render(request, "msa/rankings/list.html")


def players_list(request):
    return render(request, "msa/players/list.html")


def calendar(request):
    return render(request, "msa/calendar/index.html")


def media(request):
    return render(request, "msa/media/index.html")


def docs(request):
    return render(request, "msa/docs/index.html")


def search(request):
    q = request.GET.get("q", "")
    return render(request, "msa/search/page.html", {"q": q})


def nav_live_badge(request):
    """Return small badge with count of live tournaments for nav."""
    # TODO: sem dej reálné počítání live turnajů. Zatím 0 → vracíme skrytý badge.
    count = 0
    if count > 0:
        html = (
            '<span id="live-badge" class="ml-1 inline-flex items-center justify-center '
            "rounded-md border border-slate-200 px-1.5 text-[11px] leading-5 text-slate-700 "
            f'bg-white align-middle">{count}</span>'
        )
    else:
        html = '<span id="live-badge" class="ml-1 hidden"></span>'
    return HttpResponse(html)


# Vysvětlení: aktivní stav v menu čteme v šabloně z request.path; proto je vhodné mít
# 'django.template.context_processors.request' aktivní (většinou default v settings).
