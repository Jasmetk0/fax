from django.db.models import Q
from django.shortcuts import render

from wiki.models import Article

try:  # optional apps
    from maps.models import Place
except Exception:  # ImportError or attribute
    Place = None

try:
    from sports.models import Event
except Exception:
    Event = None


def search(request):
    q = (request.GET.get("q") or "").strip()
    results: list[dict] = []
    if q:
        wiki = Article.objects.filter(
            Q(title__icontains=q) | Q(content_md__icontains=q)
        )[:20]

        def pack(items, typ, get_url, get_title, get_snippet):
            for it in items:
                results.append(
                    {
                        "type": typ,
                        "url": get_url(it),
                        "title": get_title(it),
                        "snippet": (get_snippet(it) or "")[:180],
                    }
                )

        pack(
            wiki,
            "Wiki",
            lambda a: f"/wiki/{a.slug}/",
            lambda a: a.title,
            lambda a: getattr(a, "summary", None) or a.content_md,
        )
        if Place is not None:
            places = Place.objects.filter(
                Q(name__icontains=q) | Q(description__icontains=q)
            )[:20]
            pack(
                places,
                "Map",
                lambda p: f"/maps/place/{p.slug}/",
                lambda p: p.name,
                lambda p: getattr(p, "description", ""),
            )
        if Event is not None:
            events = Event.objects.filter(
                Q(name__icontains=q) | Q(summary__icontains=q)
            )[:20]
            pack(
                events,
                "LiveSport",
                lambda e: f"/livesport/event/{e.slug}/",
                lambda e: getattr(e, "summary", None) or e.name,
                lambda e: getattr(e, "summary", ""),
            )
    return render(request, "search/results.html", {"q": q, "results": results})
