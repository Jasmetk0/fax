from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import Match, MediaItem, NewsPost, Player, RankingSnapshot, Tournament


def _is_admin(request):
    return request.user.is_staff and request.session.get("admin_mode")


def _admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not _is_admin(request):
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)

    return wrapper


def home(request):
    upcoming_tournaments = Tournament.objects.filter(status="upcoming").order_by(
        "start_date"
    )[:5]
    live_matches = Match.objects.filter(live_status="live")[:5]
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
            "admin": _is_admin(request),
        },
    )


def tournaments(request):
    qs = Tournament.objects.all()
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)
    category = request.GET.get("category")
    if category:
        qs = qs.filter(category__iexact=category)
    country = request.GET.get("country")
    if country:
        qs = qs.filter(country__iexact=country)
    month = request.GET.get("month")
    if month:
        qs = qs.filter(start_date__month=month)
    qs = qs.order_by("start_date")
    admin = _is_admin(request)
    return render(
        request,
        "msa/tournament_list.html",
        {"tournaments": qs, "admin": admin},
    )


def tournament_detail(request, slug):
    tournament = get_object_or_404(Tournament, slug=slug)
    matches = tournament.matches.select_related("player1", "player2", "winner")
    admin = _is_admin(request)
    return render(
        request,
        "msa/tournament_detail.html",
        {"tournament": tournament, "matches": matches, "admin": admin},
    )


def live(request):
    matches = Match.objects.filter(live_status="live").select_related(
        "player1", "player2", "tournament"
    )
    return render(
        request,
        "msa/live.html",
        {"matches": matches, "admin": _is_admin(request)},
    )


def rankings(request):
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
        {"snapshot": snapshot, "entries": list(entries), "admin": admin},
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


def squashtv(request):
    items = MediaItem.objects.order_by("-published_at")
    admin = _is_admin(request)
    return render(
        request,
        "msa/squashtv.html",
        {"media": items, "admin": admin},
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
