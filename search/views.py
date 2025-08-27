from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.text import slugify


from wiki.models import Article

try:  # optional apps
    from maps.models import Place
except Exception:  # ImportError or attribute
    Place = None

try:
    from sports.models import Event
except Exception:
    Event = None

try:
    from mma.models import (
        Fighter as MmaFighter,
        Event as MmaEvent,
        Organization as MmaOrg,
    )
except Exception:
    MmaFighter = MmaEvent = MmaOrg = None

try:
    from msa.models import (
        Player as MsaPlayer,
        Tournament as MsaTournament,
        NewsPost as MsaNews,
    )
except Exception:
    MsaPlayer = MsaTournament = MsaNews = None


def _has_field(model, name: str) -> bool:
    try:
        return any(f.name == name for f in model._meta.get_fields())
    except Exception:
        return False


def search(request):
    q = (request.GET.get("q") or "").strip()
    slug_q = slugify(q)
    results: list[dict] = []
    if q:
        wiki = Article.objects.filter(
            Q(title__icontains=q)
            | Q(slug__icontains=slug_q)
            | Q(content_md__icontains=q)
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
            if _has_field(Place, "slug"):
                places = Place.objects.filter(
                    Q(name__icontains=q)
                    | Q(description__icontains=q)
                    | Q(slug__icontains=slug_q)
                )[:20]
            else:
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
            if _has_field(Event, "slug"):
                events = Event.objects.filter(
                    Q(name__icontains=q)
                    | Q(summary__icontains=q)
                    | Q(slug__icontains=slug_q)
                )[:20]
            else:
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


def suggest(request):
    """
    GET /search/suggest?q=...
    Vrací JSON: {"results": [{"title":"...", "url":"/cesta/"}]}
    - podporuje prefix 'wiki/' → hledá jen ve wiki podle zbytku dotazu
    - nabízí i deep stránky (wiki, mma, msa)
    - doplňuje statické hlavní stránky (/, /wiki/, /maps/, /livesport/, /mma/, /msasquashtour/, /openfaxmap/)
    """
    q = (request.GET.get("q") or "").strip()
    q_norm = q.lower()
    slug_q = slugify(q)

    results = []  # dočasně se "score", nakonec odřízneme na {title,url}

    # --- statické hlavní stránky (fallback a prefix match) ---
    static_pages = [
        ("Domů", "/"),
        ("Wiki", "/wiki/"),
        ("Mapy", "/maps/"),
        ("LiveSport", "/livesport/"),
        ("MMA", "/mma/"),
        ("MSA Squash", "/msasquashtour/"),
        ("OpenFaxMap", "/openfaxmap/"),
    ]

    def add_static():
        if not q_norm:
            # prázdný dotaz → krátký seznam top stránek
            for title, url in static_pages[:5]:
                results.append({"title": title, "url": url, "score": 10})
        else:
            path_like = slug_q.lstrip("/")
            for title, url in static_pages:
                # match na title prefix nebo na začátek cesty (bez počáteční '/')
                if title.lower().startswith(q_norm) or url.lstrip("/").startswith(
                    path_like
                ):
                    results.append({"title": title, "url": url, "score": 30})

    # --- wiki provider (Article) ---
    def add_wiki(term: str):
        slug_term = slugify(term)
        qs = Article.objects.filter(is_deleted=False).filter(
            Q(title__icontains=term) | Q(slug__icontains=slug_term)
        )[:30]

        t = term.lower()
        for a in qs:
            title_l = (a.title or "").lower()
            slug_l = (a.slug or "").lower()
            # skórování: slug prefix > title prefix > contains
            if slug_l.startswith(slug_term):
                sc = 120
            elif title_l.startswith(t):
                sc = 110
            else:
                sc = 80
            url = reverse("wiki:article-detail", kwargs={"slug": a.slug})
            results.append({"title": a.title, "url": url, "score": sc})

    # --- MMA provider (fighters, events, orgs) ---
    def add_mma(term: str):
        if not (MmaFighter or MmaEvent or MmaOrg):
            return
        t = term.lower()
        slug_t = slugify(term)
        # Fighters
        if MmaFighter:
            qs = MmaFighter.objects.filter(
                Q(first_name__icontains=t)
                | Q(last_name__icontains=t)
                | Q(nickname__icontains=t)
                | Q(slug__icontains=slug_t)
            )[:20]
            for f in qs:
                name = f"{f.first_name} {f.last_name}".strip()
                slug_l = (f.slug or "").lower()
                name_l = name.lower()
                sc = 120 if slug_l.startswith(slug_t) or name_l.startswith(t) else 80
                results.append(
                    {
                        "title": name or f.slug,
                        "url": f"/mma/fighters/{f.slug}/",
                        "score": sc,
                    }
                )
        # Events
        if MmaEvent:
            qs = MmaEvent.objects.filter(
                Q(name__icontains=t) | Q(slug__icontains=slug_t)
            )[:20]
            for e in qs:
                name_l = (e.name or "").lower()
                slug_l = (e.slug or "").lower()
                sc = 120 if slug_l.startswith(slug_t) or name_l.startswith(t) else 80
                results.append(
                    {
                        "title": e.name or e.slug,
                        "url": f"/mma/events/{e.slug}/",
                        "score": sc,
                    }
                )
        # Orgs
        if MmaOrg:
            qs = MmaOrg.objects.filter(
                Q(name__icontains=t)
                | Q(short_name__icontains=t)
                | Q(slug__icontains=slug_t)
            )[:20]
            for o in qs:
                label = o.name or o.short_name or o.slug
                label_l = (label or "").lower()
                slug_l = (o.slug or "").lower()
                sc = 120 if slug_l.startswith(slug_t) or label_l.startswith(t) else 70
                results.append(
                    {
                        "title": label,
                        "url": f"/mma/organizations/{o.slug}/",
                        "score": sc,
                    }
                )

    # --- MSA provider (players, tournaments, news) ---
    def add_msa(term: str):
        if not (MsaPlayer or MsaTournament or MsaNews):
            return
        t = term.lower()
        slug_t = slugify(term)
        if MsaPlayer:
            qs = MsaPlayer.objects.filter(
                Q(name__icontains=t) | Q(slug__icontains=slug_t)
            )[:20]
            for p in qs:
                name_l = (p.name or "").lower()
                slug_l = (p.slug or "").lower()
                sc = 120 if slug_l.startswith(slug_t) or name_l.startswith(t) else 80
                results.append(
                    {
                        "title": p.name or p.slug,
                        "url": f"/msasquashtour/players/{p.slug}/",
                        "score": sc,
                    }
                )
        if MsaTournament:
            qs = MsaTournament.objects.filter(
                Q(name__icontains=t) | Q(slug__icontains=slug_t)
            )[:20]
            for tmt in qs:
                name_l = (tmt.name or "").lower()
                slug_l = (tmt.slug or "").lower()
                sc = 120 if slug_l.startswith(slug_t) or name_l.startswith(t) else 80
                results.append(
                    {
                        "title": tmt.name or tmt.slug,
                        "url": f"/msasquashtour/tournaments/{tmt.slug}/",
                        "score": sc,
                    }
                )
        if MsaNews:
            qs = MsaNews.objects.filter(
                Q(title__icontains=t) | Q(slug__icontains=slug_t)
            )[:20]
            for n in qs:
                title_l = (n.title or "").lower()
                slug_l = (n.slug or "").lower()
                sc = 110 if title_l.startswith(t) or slug_l.startswith(slug_t) else 75
                results.append(
                    {
                        "title": n.title or n.slug,
                        "url": f"/msasquashtour/news/{n.slug}/",
                        "score": sc,
                    }
                )

    # --- řízení providerů podle dotazu ---
    if q_norm.startswith("wiki/"):
        # explicitní wiki/… → hledej jen ve wiki
        term = q_norm.split("/", 1)[1]
        slug_term = slugify(term)
        if slug_term:
            add_wiki(term)
    else:
        if q_norm:
            add_wiki(q_norm)
            add_mma(q_norm)
            add_msa(q_norm)

    # vždy doplň statické stránky (prefix match)
    add_static()

    # deduplikace + seřazení + limit 10
    seen = set()
    uniq = []
    for r in results:
        url = r.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        uniq.append(r)

    uniq.sort(key=lambda r: r.get("score", 0), reverse=True)
    payload = [{"title": r["title"], "url": r["url"]} for r in uniq[:10]]
    return JsonResponse({"results": payload})
