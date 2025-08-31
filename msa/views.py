from django.db.models import Q
import unicodedata

from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import (
    CategorySeason,
    PointsRow,
    EventEdition,
    EventMatch,
    AdvancementEdge,
    Match,
    MediaItem,
    NewsPost,
    Player,
    RankingSnapshot,
    Season,
    Tournament,
)
from .services.seeding_service import preview_seeding, apply_seeding
import json
from .utils import filter_by_tour  # MSA-REDESIGN


tab_choices = [("live", "Live"), ("upcoming", "Upcoming"), ("results", "Results")]


def _is_admin(request):
    return request.user.is_staff and request.session.get("admin_mode")


def _admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not _is_admin(request):
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)

    return wrapper


def home(request):
    tour = request.GET.get("tour")  # MSA-REDESIGN
    upcoming_tournaments = filter_by_tour(
        Tournament.objects.filter(status="upcoming"), tour=tour
    ).order_by("start_date")[:5]
    live_matches = filter_by_tour(
        Match.objects.filter(live_status="live"),
        tour_field="tournament__category",
        tour=tour,
    )[:5]
    snapshot = RankingSnapshot.objects.order_by("-as_of").first()
    top_players = snapshot.entries.select_related("player")[:10] if snapshot else []
    news = NewsPost.objects.filter(is_published=True).order_by("-published_at")[:5]
    media = MediaItem.objects.order_by("-published_at")[:5]
    return render(
        request,
        "msa/home.html",
        {
            "upcoming_tournaments": upcoming_tournaments,
            "live_matches": live_matches,
            "top_players": top_players,
            "news": news,
            "media": media,
            "tour": tour,
            "admin": _is_admin(request),
        },
    )


def tournaments(request):
    season_id = request.GET.get("season")
    seasons = Season.objects.all()
    selected_season = None
    events = EventEdition.objects.none()
    if season_id:
        selected_season = get_object_or_404(Season, pk=season_id)
    elif seasons:
        selected_season = seasons.first()
    if selected_season:
        events = (
            EventEdition.objects.filter(season=selected_season)
            .select_related("brand", "category_season__category")
            .prefetch_related("phases__rounds")
        )
    return render(
        request,
        "msa/tournaments.html",
        {
            "seasons": seasons,
            "selected_season": selected_season,
            "events": events,
        },
    )


def tournament_detail(request, pk):
    event = get_object_or_404(EventEdition, pk=pk)
    return render(request, "msa/tournament_detail.html", {"event": event})


def live(request):
    """Redirect old /live/ to scores."""  # MSA-REDESIGN
    url = reverse("msa:scores") + "?tab=live"
    if request.GET.get("tour"):
        url += f"&tour={request.GET.get('tour')}"
    return redirect(url)


def rankings(request):
    tour = request.GET.get("tour")  # MSA-REDESIGN
    as_of = request.GET.get("as_of")
    snapshot = (
        RankingSnapshot.objects.filter(as_of=as_of).first()
        if as_of
        else RankingSnapshot.objects.order_by("-as_of").first()
    )
    entries = snapshot.entries.select_related("player") if snapshot else []
    admin = _is_admin(request)
    return render(
        request,
        "msa/rankings.html",
        {"snapshot": snapshot, "entries": list(entries), "tour": tour, "admin": admin},
    )


def players(request):
    qs = Player.objects.all()
    country = request.GET.get("country")
    if country:
        qs = qs.filter(country__iexact=country)
    q = request.GET.get("q")
    if q:
        qs = qs.filter(name__icontains=q)
    qs = qs.order_by("name")
    admin = _is_admin(request)
    return render(
        request,
        "msa/player_list.html",
        {"players": qs, "admin": admin},
    )


def player_detail(request, slug):
    player = get_object_or_404(Player, slug=slug)
    matches = (
        Match.objects.filter(Q(player1=player) | Q(player2=player))
        .select_related(
            "player1",
            "player2",
            "tournament",
            "winner",
        )
        .order_by("-scheduled_at")[:5]
    )
    return render(
        request,
        "msa/player_detail.html",
        {"player": player, "matches": matches},
    )


def h2h(request):
    player_a_slug = request.GET.get("a")
    player_b_slug = request.GET.get("b")
    player_a = (
        Player.objects.filter(slug=player_a_slug).first() if player_a_slug else None
    )
    player_b = (
        Player.objects.filter(slug=player_b_slug).first() if player_b_slug else None
    )
    record = None
    matches = []
    if player_a and player_b:
        matches = Match.objects.filter(
            (Q(player1=player_a) & Q(player2=player_b))
            | (Q(player1=player_b) & Q(player2=player_a))
        )
        a_wins = matches.filter(winner=player_a).count()
        b_wins = matches.filter(winner=player_b).count()
        record = f"{a_wins}-{b_wins}"
    return render(
        request,
        "msa/h2h.html",
        {
            "player_a": player_a,
            "player_b": player_b,
            "record": record,
            "matches": matches,
            "players": Player.objects.all(),
            "admin": _is_admin(request),
        },
    )


def scores(request):
    tour = request.GET.get("tour")  # MSA-REDESIGN
    tab = request.GET.get("tab", "live")
    qs = Match.objects.select_related("tournament", "player1", "player2")
    qs = filter_by_tour(qs, tour_field="tournament__category", tour=tour)
    now = timezone.now()
    live = qs.filter(live_status__in=["live", "warmup"])
    upcoming = qs.filter(
        Q(scheduled_at__gte=now) & ~Q(live_status__in=["live", "finished"])
    )
    results = qs.filter(live_status__in=["finished", "result"])
    ctx = {
        "tab": tab,
        "tour": tour,
        "tab_choices": tab_choices,
        "live": live[:100],
        "upcoming": upcoming[:100],
        "results": results[:100],
    }
    return render(request, "msa/scores.html", ctx)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.lower().strip()


def _dist_le1(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    i = j = diff = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
        else:
            diff += 1
            if diff > 1:
                return False
            if len(a) == len(b):
                i += 1
                j += 1
            elif len(a) > len(b):
                i += 1
            else:
                j += 1
    return True


def msa_search(request):
    q = request.GET.get("q", "").strip()
    tour = request.GET.get("tour")
    nq = _norm(q)
    players = Player.objects.all()
    tournaments = filter_by_tour(Tournament.objects.all(), tour=tour)
    news = NewsPost.objects.filter(is_published=True)

    def match_q(name):
        n = _norm(name)
        return (nq in n) or _dist_le1(nq, n)

    results = {
        "players": [p for p in players if match_q(p.name)][:25],
        "tournaments": [t for t in tournaments if match_q(t.name)][:25],
        "news": [n for n in news if match_q(n.title)][:10],
    }
    return render(
        request,
        "msa/search.html",
        {"q": q, "tour": tour, "results": results},
    )


def tickets(request):
    tour = request.GET.get("tour")
    return render(request, "msa/tickets.html", {"tour": tour})  # MSA-REDESIGN


def stats(request):
    tour = request.GET.get("tour")
    matches = Match.objects.select_related("tournament", "player1", "player2").filter(
        live_status__in=["finished", "result"]
    )
    matches = filter_by_tour(matches, tour_field="tournament__category", tour=tour)
    from collections import defaultdict

    wins = defaultdict(int)
    total = defaultdict(int)
    streak = defaultdict(int)
    last = defaultdict(int)
    for m in matches:
        p1, p2 = m.player1_id, m.player2_id
        if p1:
            total[p1] += 1
        if p2:
            total[p2] += 1
        if getattr(m, "winner_id", None):
            wins[m.winner_id] += 1
            last[m.winner_id] = 1
            loser = p1 if m.winner_id == p2 else p2
            last[loser] = 0
    for pid, v in last.items():
        if v == 1:
            streak[pid] += 1
    plist = Player.objects.in_bulk(list(set(list(wins.keys()) + list(total.keys()))))
    board = []
    for pid in total:
        name = getattr(plist.get(pid), "name", "Unknown")
        w = wins.get(pid, 0)
        t = total.get(pid, 0)
        wp = (w / t * 100) if t else 0
        board.append(
            {
                "player_id": pid,
                "name": name,
                "wins": w,
                "played": t,
                "win_pct": round(wp, 1),
                "streak": streak.get(pid, 0),
            }
        )
    board.sort(key=lambda x: (-x["win_pct"], -x["wins"], x["name"]))
    return render(
        request,
        "msa/stats.html",
        {"tour": tour, "leaderboard": board[:50]},
    )


def shop(request):
    tour = request.GET.get("tour")
    return render(request, "msa/shop.html", {"tour": tour})  # MSA-REDESIGN


def press(request):
    tour = request.GET.get("tour")
    return render(request, "msa/press.html", {"tour": tour})  # MSA-REDESIGN


def about(request):
    tour = request.GET.get("tour")
    return render(request, "msa/about.html", {"tour": tour})  # MSA-REDESIGN


def squashtv(request):
    tour = request.GET.get("tour")  # MSA-REDESIGN
    matches = Match.objects.filter(video_url__isnull=False).select_related(
        "tournament", "player1", "player2"
    )
    matches = filter_by_tour(matches, tour_field="tournament__category", tour=tour)
    live_matches = matches.filter(live_status="live")
    upcoming = matches.filter(
        Q(scheduled_at__gte=timezone.now())
        & ~Q(live_status__in=["live", "finished", "result"])
    )
    vod = MediaItem.objects.order_by("-published_at")
    admin = _is_admin(request)
    return render(
        request,
        "msa/squashtv.html",
        {
            "live": live_matches,
            "upcoming": upcoming,
            "media": vod,
            "tour": tour,
            "admin": admin,
        },
    )


def news(request):
    posts = NewsPost.objects.filter(is_published=True).order_by("-published_at")
    admin = _is_admin(request)
    return render(
        request,
        "msa/news.html",
        {"posts": posts, "admin": admin},
    )


def news_detail(request, slug):
    post = get_object_or_404(NewsPost, slug=slug)
    return render(
        request,
        "msa/news_detail.html",
        {"post": post, "admin": _is_admin(request)},
    )


# API views -------------------------------------------------------------


def api_players(request):
    data = list(Player.objects.values("name", "slug", "country"))
    return JsonResponse(data, safe=False)


def api_player_detail(request, slug):
    player = get_object_or_404(Player, slug=slug)
    data = {"name": player.name, "slug": player.slug, "country": player.country}
    return JsonResponse(data)


def api_seasons(request):
    data = list(Season.objects.values("name", "code", "start_date", "end_date"))
    return JsonResponse(data, safe=False)


def api_category_seasons(request, pk):
    season = get_object_or_404(Season, pk=pk)
    qs = CategorySeason.objects.filter(season=season).select_related("category")
    data = list(
        qs.values(
            "category__name",
            "label",
            "points_table_id",
            "prize_table_id",
            "bracket_policy_id",
            "seeding_policy_id",
        )
    )
    return JsonResponse(data, safe=False)


def api_category_season_points(request, pk):
    cs = get_object_or_404(CategorySeason, pk=pk)
    if not cs.points_table:
        return JsonResponse([], safe=False)
    rows = (
        PointsRow.objects.filter(points_table=cs.points_table)
        .order_by("round_code")
        .values("round_code", "points", "co_sanction_pct")
    )
    return JsonResponse(list(rows), safe=False)


def api_tournaments(request):
    data = list(
        Tournament.objects.values("name", "slug", "start_date", "end_date", "status")
    )
    return JsonResponse(data, safe=False)


def api_tournament_detail(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    data = {
        "name": t.name,
        "slug": t.slug,
        "start_date": t.start_date,
        "end_date": t.end_date,
        "status": t.status,
    }
    return JsonResponse(data)


def api_tournament_matches(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    data = list(
        t.matches.values(
            "player1__name",
            "player2__name",
            "round",
            "winner__name",
            "scoreline",
        )
    )
    return JsonResponse(data, safe=False)


def api_rankings(request):
    as_of = request.GET.get("as_of")
    snapshot = (
        RankingSnapshot.objects.filter(as_of=as_of).first()
        if as_of
        else RankingSnapshot.objects.order_by("-as_of").first()
    )
    entries = snapshot.entries.select_related("player") if snapshot else []
    data = {
        "as_of": snapshot.as_of if snapshot else None,
        "entries": [
            {"rank": e.rank, "player": e.player.name, "points": e.points}
            for e in entries
        ],
    }
    return JsonResponse(data)


def api_event_structure(request, pk):
    event = get_object_or_404(EventEdition, pk=pk)
    phases = []
    for phase in event.phases.all().order_by("order"):
        rounds = []
        match_count = 0
        for rnd in phase.rounds.all().order_by("order"):
            rounds.append(
                {"code": rnd.code, "label": rnd.label, "matches": rnd.matches}
            )
            match_count += rnd.matches
        phases.append(
            {
                "type": phase.type,
                "name": phase.name,
                "rounds": rounds,
                "matches_count": match_count,
            }
        )
    return JsonResponse({"phases": phases})


def api_event_seeding_preview(request, pk):
    event = get_object_or_404(EventEdition, pk=pk)
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    pairs = preview_seeding(event.pk)
    return JsonResponse({"pairs": pairs})


def api_event_seeding_apply(request, pk):
    event = get_object_or_404(EventEdition, pk=pk)
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    res = apply_seeding(event.pk)
    return JsonResponse(res)


def api_match_result(request, pk):
    match = get_object_or_404(EventMatch, pk=pk)
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:  # pragma: no cover - guard
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    sets = data.get("sets", [])
    a_sets = b_sets = 0
    for s in sets:
        if len(s) != 2:
            continue
        if s[0] > s[1]:
            a_sets += 1
        elif s[1] > s[0]:
            b_sets += 1
    needed = match.round.best_of // 2 + 1
    if a_sets < needed and b_sets < needed:
        return JsonResponse({"error": "Match incomplete"}, status=400)
    winner = match.a_player if a_sets > b_sets else match.b_player
    match.a_score = a_sets
    match.b_score = b_sets
    match.winner = winner
    match.save()
    from_ref = f"{match.round.code}:M{match.order}:W"
    edges = AdvancementEdge.objects.filter(phase=match.phase, from_ref=from_ref)
    for edge in edges:
        try:
            round_code, rest = edge.to_ref.split(":M")
            match_no, slot = rest.split(":")
            target = EventMatch.objects.get(
                phase=edge.phase, round__code=round_code, order=int(match_no)
            )
            if slot == "A":
                target.a_player = winner
            else:
                target.b_player = winner
            target.save()
        except Exception:  # pragma: no cover - safeguard
            continue
    return JsonResponse({"a_score": a_sets, "b_score": b_sets, "winner": winner.id})


def api_h2h(request):
    player_a = get_object_or_404(Player, slug=request.GET.get("a"))
    player_b = get_object_or_404(Player, slug=request.GET.get("b"))
    matches = Match.objects.filter(
        (Q(player1=player_a) & Q(player2=player_b))
        | (Q(player1=player_b) & Q(player2=player_a))
    )
    a_wins = matches.filter(winner=player_a).count()
    b_wins = matches.filter(winner=player_b).count()
    data = {"a": player_a.slug, "b": player_b.slug, "a_wins": a_wins, "b_wins": b_wins}
    return JsonResponse(data)


def api_live(request):
    matches = Match.objects.filter(live_status="live").select_related(
        "player1", "player2", "tournament"
    )
    data = list(
        matches.values(
            "tournament__name",
            "player1__name",
            "player2__name",
            "live_p1_points",
            "live_p2_points",
            "live_game_no",
        )
    )
    return JsonResponse(data, safe=False)
