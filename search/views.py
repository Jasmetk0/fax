from datetime import datetime
from typing import Dict, List

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.text import slugify

from .utils import fuzzy1_token_match, normalize
from wiki.models import Article

try:  # optional apps
    from msa.models import (
        Player as MsaPlayer,
        Tournament as MsaTournament,
        NewsPost as MsaNews,
    )
except Exception:  # pragma: no cover - optional
    MsaPlayer = MsaTournament = MsaNews = None

try:
    from mma.models import (
        Fighter as MmaFighter,
        Event as MmaEvent,
        Organization as MmaOrg,
    )
except Exception:  # pragma: no cover - optional
    MmaFighter = MmaEvent = MmaOrg = None


MAX_CANDIDATES_PER_MODEL = 200


def _tokenize(text: str) -> set[str]:
    return {normalize(t) for t in text.replace("-", " ").split() if t}


def _score_match(
    q_norm: str, slug_q: str, title: str, slug: str | None, content: str | None
) -> int:
    title_norm = normalize(title)
    slug_norm = normalize(slug or "")
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
        # Wiki articles
        base = Article.objects.filter(is_deleted=False).order_by("-updated_at")
        filtered = base.filter(
            Q(title__icontains=q)
            | Q(summary__icontains=q)
            | Q(content_md__icontains=q)
            | Q(slug__icontains=slug_q)
        )
        wiki_qs = list(filtered[:600])
        if len(wiki_qs) < 600:
            wiki_qs += list(
                base.exclude(id__in=[a.id for a in wiki_qs])[: 600 - len(wiki_qs)]
            )
        for a in wiki_qs:
            snippet = a.summary or a.content_md
            score = _score_match(q_norm, slug_q, a.title, a.slug, snippet)
            if score:
                results.append(
                    {
                        "type": "Wiki",
                        "url": a.get_absolute_url(),
                        "title": a.title,
                        "snippet": (snippet or "")[:180],
                        "score": score,
                        "date": a.updated_at,
                    }
                )

        # MSA players
        if MsaPlayer:
            base = MsaPlayer.objects.order_by("-updated_at")
            filtered = base.filter(Q(name__icontains=q) | Q(slug__icontains=slug_q))
            players = list(filtered[:600])
            if len(players) < 600:
                players += list(
                    base.exclude(id__in=[p.id for p in players])[: 600 - len(players)]
                )
            for p in players:
                snippet = p.country or ""
                score = _score_match(q_norm, slug_q, p.name, p.slug, snippet)
                if score:
                    results.append(
                        {
                            "type": "MSA",
                            "url": f"/msasquashtour/players/{p.slug}/",
                            "title": p.name,
                            "snippet": snippet,
                            "score": score,
                            "date": p.updated_at,
                        }
                    )

        # MSA tournaments
        if MsaTournament:
            base = MsaTournament.objects.order_by("-updated_at")
            filtered = base.filter(Q(name__icontains=q) | Q(slug__icontains=slug_q))
            tournaments = list(filtered[:600])
            if len(tournaments) < 600:
                tournaments += list(
                    base.exclude(id__in=[t.id for t in tournaments])[
                        : 600 - len(tournaments)
                    ]
                )
            for t in tournaments:
                snippet = ", ".join(filter(None, [t.city, t.country]))
                score = _score_match(q_norm, slug_q, t.name, t.slug, snippet)
                if score:
                    results.append(
                        {
                            "type": "MSA",
                            "url": f"/msasquashtour/tournaments/{t.slug}/",
                            "title": t.name,
                            "snippet": snippet,
                            "score": score,
                            "date": t.updated_at,
                        }
                    )

        # MSA news
        if MsaNews:
            base = MsaNews.objects.order_by("-published_at")
            filtered = base.filter(
                Q(title__icontains=q)
                | Q(excerpt__icontains=q)
                | Q(body__icontains=q)
                | Q(slug__icontains=slug_q)
            )
            news = list(filtered[:600])
            if len(news) < 600:
                news += list(
                    base.exclude(id__in=[n.id for n in news])[: 600 - len(news)]
                )
            for n in news:
                snippet = n.excerpt
                score = _score_match(q_norm, slug_q, n.title, n.slug, snippet)
                if score:
                    results.append(
                        {
                            "type": "MSA",
                            "url": f"/msasquashtour/news/{n.slug}/",
                            "title": n.title,
                            "snippet": (snippet or "")[:180],
                            "score": score,
                            "date": n.published_at,
                        }
                    )

        # MMA fighters
        if MmaFighter:
            base = MmaFighter.objects.order_by("-id")
            filtered = base.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(nickname__icontains=q)
                | Q(slug__icontains=slug_q)
            )
            fighters = list(filtered[:600])
            if len(fighters) < 600:
                fighters += list(
                    base.exclude(id__in=[f.id for f in fighters])[: 600 - len(fighters)]
                )
            for f in fighters:
                title = " ".join(filter(None, [f.first_name, f.last_name])) or f.slug
                snippet = f.nickname or f.country or ""
                score = _score_match(q_norm, slug_q, title, f.slug, snippet)
                if score:
                    results.append(
                        {
                            "type": "MMA",
                            "url": f"/mma/fighters/{f.slug}/",
                            "title": title,
                            "snippet": snippet,
                            "score": score,
                            "date": None,
                        }
                    )

        # MMA events
        if MmaEvent:
            base = MmaEvent.objects.order_by("-date_start")
            filtered = base.filter(Q(name__icontains=q) | Q(slug__icontains=slug_q))
            events = list(filtered[:600])
            if len(events) < 600:
                events += list(
                    base.exclude(id__in=[e.id for e in events])[: 600 - len(events)]
                )
            for e in events:
                snippet = getattr(e.organization, "name", "")
                score = _score_match(q_norm, slug_q, e.name, e.slug, snippet)
                if score:
                    results.append(
                        {
                            "type": "MMA",
                            "url": f"/mma/events/{e.slug}/",
                            "title": e.name,
                            "snippet": snippet,
                            "score": score,
                            "date": datetime.combine(e.date_start, datetime.min.time()),
                        }
                    )

        # MMA organizations
        if MmaOrg:
            base = MmaOrg.objects.order_by("-id")
            filtered = base.filter(
                Q(name__icontains=q)
                | Q(short_name__icontains=q)
                | Q(slug__icontains=slug_q)
            )
            orgs = list(filtered[:600])
            if len(orgs) < 600:
                orgs += list(
                    base.exclude(id__in=[o.id for o in orgs])[: 600 - len(orgs)]
                )
            for o in orgs:
                snippet = o.short_name or ""
                score = _score_match(q_norm, slug_q, o.name, o.slug, snippet)
                if score:
                    results.append(
                        {
                            "type": "MMA",
                            "url": f"/mma/organizations/{o.slug}/",
                            "title": o.name,
                            "snippet": snippet,
                            "score": score,
                            "date": None,
                        }
                    )

        # Static app homes
        static_pages = [
            ("FAX – Domů", "/", "fax"),
            ("Wiki – Domů", "/wiki/", "wiki"),
            ("Mapy – Domů", "/maps/", "maps"),
            ("OpenFaxMap – Domů", "/openfaxmap/", "openfaxmap"),
            ("LiveSport – Domů", "/livesport/", "livesport"),
            ("MMA – Domů", "/mma/", "mma"),
            ("MSA Squash – Domů", "/msasquashtour/", "msa"),
        ]
        if q_norm and len(q_norm) >= 3:
            for title, url, key in static_pages:
                if normalize(key).startswith(q_norm):
                    results.append(
                        {
                            "type": "App",
                            "url": url,
                            "title": title,
                            "snippet": "",
                            "score": 10,
                            "date": None,
                        }
                    )

    results.sort(
        key=lambda r: (
            -r["score"],
            -(r["date"].timestamp() if r.get("date") else 0),
            r["title"],
        )
    )
    results = results[:150]
    for r in results:
        r.pop("score", None)

    found_urls = {r["url"] for r in results}
    q_tokens = _tokenize(q)
    fuzzy_hits: List[Dict] = []

    if q_tokens:
        for a in Article.objects.filter(is_deleted=False).order_by("-updated_at")[
            :MAX_CANDIDATES_PER_MODEL
        ]:
            url = a.get_absolute_url()
            if url in found_urls:
                continue
            tokens = _tokenize(a.title) | _tokenize(a.slug or "")
            if any(fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens):
                snippet = a.summary or a.content_md
                fuzzy_hits.append(
                    {
                        "type": "Wiki",
                        "url": url,
                        "title": a.title,
                        "snippet": (snippet or "")[:180],
                        "date": a.updated_at,
                    }
                )
                found_urls.add(url)

        if MsaPlayer:
            for p in MsaPlayer.objects.order_by("-updated_at")[
                :MAX_CANDIDATES_PER_MODEL
            ]:
                url = f"/msasquashtour/players/{p.slug}/"
                if url in found_urls:
                    continue
                tokens = _tokenize(p.name) | _tokenize(p.slug or "")
                if any(fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens):
                    fuzzy_hits.append(
                        {
                            "type": "MSA",
                            "url": url,
                            "title": p.name,
                            "snippet": p.country or "",
                            "date": p.updated_at,
                        }
                    )
                    found_urls.add(url)

        if MsaTournament:
            for t in MsaTournament.objects.order_by("-updated_at")[
                :MAX_CANDIDATES_PER_MODEL
            ]:
                url = f"/msasquashtour/tournaments/{t.slug}/"
                if url in found_urls:
                    continue
                tokens = _tokenize(t.name) | _tokenize(t.slug or "")
                if any(fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens):
                    snippet = ", ".join(filter(None, [t.city, t.country]))
                    fuzzy_hits.append(
                        {
                            "type": "MSA",
                            "url": url,
                            "title": t.name,
                            "snippet": snippet,
                            "date": t.updated_at,
                        }
                    )
                    found_urls.add(url)

        if MsaNews:
            for n in MsaNews.objects.order_by("-published_at")[
                :MAX_CANDIDATES_PER_MODEL
            ]:
                url = f"/msasquashtour/news/{n.slug}/"
                if url in found_urls:
                    continue
                tokens = _tokenize(n.title) | _tokenize(n.slug or "")
                if any(fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens):
                    snippet = n.excerpt
                    fuzzy_hits.append(
                        {
                            "type": "MSA",
                            "url": url,
                            "title": n.title,
                            "snippet": (snippet or "")[:180],
                            "date": n.published_at,
                        }
                    )
                    found_urls.add(url)

        if MmaFighter:
            for f in MmaFighter.objects.order_by("-id")[:MAX_CANDIDATES_PER_MODEL]:
                url = f"/mma/fighters/{f.slug}/"
                if url in found_urls:
                    continue
                title = " ".join(filter(None, [f.first_name, f.last_name])) or f.slug
                tokens = _tokenize(title) | _tokenize(f.slug or "")
                if any(fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens):
                    snippet = f.nickname or f.country or ""
                    fuzzy_hits.append(
                        {
                            "type": "MMA",
                            "url": url,
                            "title": title,
                            "snippet": snippet,
                            "date": None,
                        }
                    )
                    found_urls.add(url)

        if MmaEvent:
            for e in MmaEvent.objects.order_by("-date_start")[
                :MAX_CANDIDATES_PER_MODEL
            ]:
                url = f"/mma/events/{e.slug}/"
                if url in found_urls:
                    continue
                tokens = _tokenize(e.name) | _tokenize(e.slug or "")
                if any(fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens):
                    snippet = getattr(e.organization, "name", "")
                    fuzzy_hits.append(
                        {
                            "type": "MMA",
                            "url": url,
                            "title": e.name,
                            "snippet": snippet,
                            "date": datetime.combine(e.date_start, datetime.min.time()),
                        }
                    )
                    found_urls.add(url)

        if MmaOrg:
            for o in MmaOrg.objects.order_by("-id")[:MAX_CANDIDATES_PER_MODEL]:
                url = f"/mma/organizations/{o.slug}/"
                if url in found_urls:
                    continue
                tokens = _tokenize(o.name) | _tokenize(o.slug or "")
                if any(fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens):
                    snippet = o.short_name or ""
                    fuzzy_hits.append(
                        {
                            "type": "MMA",
                            "url": url,
                            "title": o.name,
                            "snippet": snippet,
                            "date": None,
                        }
                    )
                    found_urls.add(url)

    fuzzy_hits.sort(key=lambda r: r["title"])
    results.extend(fuzzy_hits)

    types = sorted({r["type"] for r in results})
    return render(
        request, "search/results.html", {"q": q, "results": results, "types": types}
    )


def _suggest_pack(
    arr: List[Dict],
    title: str,
    slug: str | None,
    url: str,
    source: str,
    q_norm: str,
    slug_q: str,
):
    title_norm = normalize(title)
    slug_norm = normalize(slug or "")
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
            ).order_by("-updated_at")[:20]
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
            ).order_by("-updated_at")[:20]
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
            ).order_by("-published_at")[:20]
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
            ).order_by("-id")[:20]
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
            ).order_by("-date_start")[:20]
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

        if MmaOrg:
            qs = MmaOrg.objects.filter(
                Q(name__icontains=q)
                | Q(short_name__icontains=q)
                | Q(slug__icontains=slug_q)
            ).order_by("-id")[:20]
            for o in qs:
                _suggest_pack(
                    results,
                    o.name,
                    o.slug,
                    f"/mma/organizations/{o.slug}/",
                    "mma",
                    q_norm,
                    slug_q,
                )

    results.sort(key=lambda r: (-r.get("score", 0), r["title"]))

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
    if len(out) < 10:
        q_tokens = _tokenize(q)
        fuzzy_hits: List[Dict] = []
        if q_tokens:
            for a in Article.objects.filter(is_deleted=False).order_by("-updated_at")[
                :MAX_CANDIDATES_PER_MODEL
            ]:
                url = a.get_absolute_url()
                if url in seen:
                    continue
                tokens = _tokenize(a.title) | _tokenize(a.slug or "")
                if any(fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens):
                    fuzzy_hits.append({"title": a.title, "url": url, "source": "wiki"})
                    seen.add(url)

            if MsaPlayer:
                for p in MsaPlayer.objects.order_by("-updated_at")[
                    :MAX_CANDIDATES_PER_MODEL
                ]:
                    url = f"/msasquashtour/players/{p.slug}/"
                    if url in seen:
                        continue
                    tokens = _tokenize(p.name) | _tokenize(p.slug or "")
                    if any(
                        fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens
                    ):
                        fuzzy_hits.append(
                            {"title": p.name, "url": url, "source": "msa"}
                        )
                        seen.add(url)

            if MsaTournament:
                for t in MsaTournament.objects.order_by("-updated_at")[
                    :MAX_CANDIDATES_PER_MODEL
                ]:
                    url = f"/msasquashtour/tournaments/{t.slug}/"
                    if url in seen:
                        continue
                    tokens = _tokenize(t.name) | _tokenize(t.slug or "")
                    if any(
                        fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens
                    ):
                        fuzzy_hits.append(
                            {"title": t.name, "url": url, "source": "msa"}
                        )
                        seen.add(url)

            if MsaNews:
                for n in MsaNews.objects.order_by("-published_at")[
                    :MAX_CANDIDATES_PER_MODEL
                ]:
                    url = f"/msasquashtour/news/{n.slug}/"
                    if url in seen:
                        continue
                    tokens = _tokenize(n.title) | _tokenize(n.slug or "")
                    if any(
                        fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens
                    ):
                        fuzzy_hits.append(
                            {"title": n.title, "url": url, "source": "msa"}
                        )
                        seen.add(url)

            if MmaFighter:
                for f in MmaFighter.objects.order_by("-id")[:MAX_CANDIDATES_PER_MODEL]:
                    url = f"/mma/fighters/{f.slug}/"
                    if url in seen:
                        continue
                    title = (
                        " ".join(filter(None, [f.first_name, f.last_name])) or f.slug
                    )
                    tokens = _tokenize(title) | _tokenize(f.slug or "")
                    if any(
                        fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens
                    ):
                        fuzzy_hits.append({"title": title, "url": url, "source": "mma"})
                        seen.add(url)

            if MmaEvent:
                for e in MmaEvent.objects.order_by("-date_start")[
                    :MAX_CANDIDATES_PER_MODEL
                ]:
                    url = f"/mma/events/{e.slug}/"
                    if url in seen:
                        continue
                    tokens = _tokenize(e.name) | _tokenize(e.slug or "")
                    if any(
                        fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens
                    ):
                        fuzzy_hits.append(
                            {"title": e.name, "url": url, "source": "mma"}
                        )
                        seen.add(url)

            if MmaOrg:
                for o in MmaOrg.objects.order_by("-id")[:MAX_CANDIDATES_PER_MODEL]:
                    url = f"/mma/organizations/{o.slug}/"
                    if url in seen:
                        continue
                    tokens = _tokenize(o.name) | _tokenize(o.slug or "")
                    if any(
                        fuzzy1_token_match(qt, tt) for qt in q_tokens for tt in tokens
                    ):
                        fuzzy_hits.append(
                            {"title": o.name, "url": url, "source": "mma"}
                        )
                        seen.add(url)

        fuzzy_hits.sort(key=lambda r: r["title"])
        for fh in fuzzy_hits:
            if len(out) >= 10:
                break
            url = fh["url"]
            if url in seen:
                continue
            seen.add(url)
            out.append(fh)

    return JsonResponse({"results": out})
