from typing import Dict, List

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.text import slugify

from .utils import normalize
from wiki.models import Article

try:  # optional apps for suggestions
    from msa.models import (
        Player as MsaPlayer,
        Tournament as MsaTournament,
        NewsPost as MsaNews,
    )
except Exception:  # pragma: no cover - optional
    MsaPlayer = MsaTournament = MsaNews = None

try:
    from mma.models import Fighter as MmaFighter, Event as MmaEvent, NewsItem as MmaNews
except Exception:  # pragma: no cover - optional
    MmaFighter = MmaEvent = MmaNews = None


def _score_match(
    q_norm: str, slug_q: str, title: str, slug: str | None, content: str | None
) -> int:
    title_norm = normalize(title)
    slug_norm = slug or ""
    content_norm = normalize(content or "")
    score = 0
    if q_norm and (title_norm.startswith(q_norm) or slug_norm.startswith(slug_q)):
        score += 100
    if q_norm and q_norm in title_norm:
        score += 40
    if q_norm and q_norm in content_norm:
        score += 15
    return score


def search(request):
    q = (request.GET.get("q") or "").strip()
    q_norm = normalize(q)
    slug_q = slugify(q)
    results: List[Dict] = []

    if q:
        qs = (
            Article.objects.filter(is_deleted=False)
            .filter(
                Q(title__icontains=q)
                | Q(slug__icontains=slug_q)
                | Q(summary__icontains=q)
                | Q(content_md__icontains=q)
            )
            .order_by("-updated_at")[:600]
        )
        for a in qs:
            score = _score_match(
                q_norm, slug_q, a.title, a.slug, a.summary or a.content_md
            )
            if score:
                results.append(
                    {
                        "type": "Wiki",
                        "url": a.get_absolute_url(),
                        "title": a.title,
                        "snippet": (a.summary or a.content_md or "")[:180],
                        "score": score,
                        "date": a.updated_at,
                    }
                )

    results.sort(
        key=lambda r: (
            -r["score"],
            -(r["date"].timestamp() if r.get("date") else 0),
            r["title"],
        )
    )
    for r in results:
        r.pop("score", None)
        r.pop("date", None)

    types = sorted({r["type"] for r in results})
    return render(
        request, "search/results.html", {"q": q, "results": results, "types": types}
    )


def _suggest_pack(arr, title, slug, url, source, q_norm, slug_q):
    title_norm = normalize(title)
    slug_norm = slug or ""
    if q_norm and (title_norm.startswith(q_norm) or slug_norm.startswith(slug_q)):
        score = 2
    elif q_norm and q_norm in title_norm:
        score = 1
    else:
        score = 0
    if score:
        arr.append({"title": title, "url": url, "source": source, "score": score})


def suggest(request):
    q = (request.GET.get("q") or "").strip()
    q_norm = normalize(q)
    slug_q = slugify(q)
    results: List[Dict] = []

    if q_norm:
        wiki_qs = Article.objects.filter(
            Q(title__icontains=q) | Q(slug__icontains=slug_q)
        ).order_by("-updated_at")[:20]
        for a in wiki_qs:
            _suggest_pack(
                results, a.title, a.slug, a.get_absolute_url(), "wiki", q_norm, slug_q
            )

        if MsaPlayer:
            qs = MsaPlayer.objects.filter(
                Q(name__icontains=q) | Q(slug__icontains=slug_q)
            )[:20]
            for p in qs:
                _suggest_pack(
                    results,
                    p.name,
                    p.slug,
                    f"/msasquashtour/players/{p.slug}/",
                    "msa",
                    q_norm,
                    slug_q,
                )
        if MsaTournament:
            qs = MsaTournament.objects.filter(
                Q(name__icontains=q) | Q(slug__icontains=slug_q)
            )[:20]
            for t in qs:
                _suggest_pack(
                    results,
                    t.name,
                    t.slug,
                    f"/msasquashtour/tournaments/{t.slug}/",
                    "msa",
                    q_norm,
                    slug_q,
                )
        if MsaNews:
            qs = MsaNews.objects.filter(
                Q(title__icontains=q) | Q(slug__icontains=slug_q)
            )[:20]
            for n in qs:
                _suggest_pack(
                    results,
                    n.title,
                    n.slug,
                    f"/msasquashtour/news/{n.slug}/",
                    "msa",
                    q_norm,
                    slug_q,
                )
        if MmaFighter:
            qs = MmaFighter.objects.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(nickname__icontains=q)
                | Q(slug__icontains=slug_q)
            )[:20]
            for f in qs:
                name = " ".join(filter(None, [f.first_name, f.last_name]))
                _suggest_pack(
                    results,
                    name or f.slug,
                    f.slug,
                    f"/mma/fighters/{f.slug}/",
                    "mma",
                    q_norm,
                    slug_q,
                )
        if MmaEvent:
            qs = MmaEvent.objects.filter(
                Q(name__icontains=q) | Q(slug__icontains=slug_q)
            )[:20]
            for e in qs:
                _suggest_pack(
                    results,
                    e.name,
                    e.slug,
                    f"/mma/events/{e.slug}/",
                    "mma",
                    q_norm,
                    slug_q,
                )
        if MmaNews:
            qs = MmaNews.objects.filter(
                Q(title__icontains=q) | Q(slug__icontains=slug_q)
            )[:20]
            for n in qs:
                _suggest_pack(
                    results,
                    n.title,
                    n.slug,
                    f"/mma/news/{n.slug}/",
                    "mma",
                    q_norm,
                    slug_q,
                )

    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    static = [
        {"title": "Domů", "url": "/", "source": "static"},
        {"title": "Wiki", "url": "/wiki/", "source": "static"},
        {"title": "Mapy", "url": "/maps/", "source": "static"},
        {"title": "OpenFaxMap", "url": "/openfaxmap/", "source": "static"},
        {"title": "LiveSport", "url": "/livesport/", "source": "static"},
        {"title": "MMA", "url": "/mma/", "source": "static"},
        {"title": "MSA Squash Tour", "url": "/msasquashtour/", "source": "static"},
    ]
    results.extend(static)

    seen = set()
    out = []
    for r in results:
        url = r.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append({"title": r["title"], "url": url, "source": r.get("source")})
        if len(out) >= 10:
            break

    return JsonResponse({"results": out})
