from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.db import OperationalError
from django.db.models.fields.related import ForeignKey
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from msa.utils.dates import find_season_for_date, get_active_date

from .utils import enumerate_fax_months


def _to_iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


DEFAULT_BADGE = "bg-slate-600/10 text-slate-800 border-slate-300"

CATEGORY_BADGES = {
    "Diamond": "bg-indigo-600/10 text-indigo-700 border-indigo-200",
    "Emerald": "bg-emerald-600/10 text-emerald-700 border-emerald-200",
    "Platinum": "bg-slate-700/10 text-slate-800 border-slate-300",
    "Gold": "bg-amber-500/10 text-amber-700 border-amber-200",
    "Silver": "bg-gray-500/10 text-gray-700 border-gray-300",
    "Bronze": "bg-orange-500/10 text-orange-700 border-orange-200",
}

TOUR_BADGES = {
    "World Tour": "bg-blue-600/10 text-blue-700 border-blue-200",
    "Elite Tour": "bg-purple-600/10 text-purple-700 border-purple-200",
    "Challenger Tour": "bg-teal-600/10 text-teal-700 border-teal-200",
    "Development Tour": "bg-lime-600/10 text-lime-700 border-lime-200",
}

STATUS_BADGES = {
    "planned": ("Plánován", "bg-sky-500/10 text-sky-700 border-sky-200"),
    "running": ("Probíhá", "bg-emerald-500/10 text-emerald-700 border-emerald-200"),
    "completed": ("Dokončeno", "bg-slate-500/10 text-slate-700 border-slate-300"),
}


def _badge_class(value: str | None, mapping: dict[str, str]) -> str:
    if not value:
        return DEFAULT_BADGE
    return mapping.get(str(value), DEFAULT_BADGE)


def _parse_fax_iso(value: str | None):
    if not value:
        return None
    parts = str(value).split("-")
    if len(parts) < 3:
        return None
    try:
        return tuple(int(p) for p in parts[:3])
    except (TypeError, ValueError):
        return None


def _normalize_woorld_value(value) -> str | None:
    if value in (None, "", "None"):
        return None
    if isinstance(value, dict):
        y = value.get("year") or value.get("y")
        m = value.get("month") or value.get("m")
        d = value.get("day") or value.get("d")
        try:
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        except (TypeError, ValueError):
            return None
    try:
        from fax_calendar.utils import parse_woorld_date, to_storage
    except Exception:
        parse_woorld_date = None
        to_storage = None

    if parse_woorld_date and to_storage:
        try:
            y, m, d = parse_woorld_date(value)
        except Exception:
            y = m = d = None
        if None not in (y, m, d):
            try:
                return to_storage(int(y), int(m), int(d))
            except Exception:
                return None

    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            parts = cleaned.split("-")
            if len(parts) >= 3:
                try:
                    y, m, d = (int(parts[0]), int(parts[1]), int(parts[2]))
                except ValueError:
                    return None
                return f"{y:04d}-{m:02d}-{d:02d}"
    return None


def _current_fax_iso(request) -> str:
    candidates = [
        getattr(request, "session", {}).get("woorld_today"),
        getattr(request, "session", {}).get("woorld_date"),
        request.COOKIES.get("woorld_today"),
        request.COOKIES.get("woorld_date"),
    ]
    for value in candidates:
        iso = _normalize_woorld_value(value)
        if iso:
            return iso
    today = timezone.now().date()
    return f"{today.year:04d}-{today.month:02d}-{today.day:02d}"


def _resolve_tournament_status(request, start_iso: str | None, end_iso: str | None):
    now_iso = _current_fax_iso(request)
    now_tuple = _parse_fax_iso(now_iso)
    start_tuple = _parse_fax_iso(start_iso)
    end_tuple = _parse_fax_iso(end_iso)

    status_key = "planned"
    if now_tuple and start_tuple and now_tuple < start_tuple:
        status_key = "planned"
    elif now_tuple and start_tuple and end_tuple and start_tuple <= now_tuple <= end_tuple:
        status_key = "running"
    elif now_tuple and end_tuple and now_tuple > end_tuple:
        status_key = "completed"

    label, css_class = STATUS_BADGES.get(status_key, STATUS_BADGES["planned"])
    return {"label": label, "class": css_class, "key": status_key, "now": now_iso}


def _get_tournament_model():
    return apps.get_model("msa", "Tournament") if apps.is_installed("msa") else None


def _get_tournament_or_404(tournament_id: int):
    Tournament = _get_tournament_model()
    if not Tournament:
        raise Http404("Tournament model unavailable")
    try:
        qs = Tournament.objects.all()
        qs = qs.select_related("season", "category", "category__tour")
        return qs.get(pk=tournament_id)
    except (Tournament.DoesNotExist, OperationalError) as err:
        raise Http404("Tournament not found") from err


def _tournament_base_context(request, tournament):
    season = getattr(tournament, "season", None)
    category_obj = getattr(tournament, "category", None)
    tour_obj = getattr(category_obj, "tour", None)

    start_iso = getattr(tournament, "start_date", "") or ""
    end_iso = getattr(tournament, "end_date", "") or ""

    category_label = None
    if category_obj:
        category_label = getattr(category_obj, "name", None) or str(category_obj)
    elif getattr(tournament, "category", None):
        category_label = str(getattr(tournament, "category", ""))

    tour_label = None
    if tour_obj:
        tour_label = getattr(tour_obj, "name", None) or str(tour_obj)

    status_meta = _resolve_tournament_status(request, start_iso, end_iso)

    return {
        "tournament": tournament,
        "season": season,
        "fax_range_start": start_iso or "",
        "fax_range_end": end_iso or "",
        "category_label": category_label,
        "category_badge_class": _badge_class(category_label, CATEGORY_BADGES),
        "tour_label": tour_label,
        "tour_badge_class": _badge_class(tour_label, TOUR_BADGES),
        "status": status_meta,
    }


def home(request):
    return render(request, "msa/home/index.html")


def seasons_list(request):
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    seasons = []
    if Season:
        try:
            seasons = list(Season.objects.all().order_by("id"))
        except OperationalError:
            seasons = []
    return render(request, "msa/seasons/list.html", {"seasons": seasons})


def tournaments_list(request):
    d = get_active_date(request)
    season = find_season_for_date(d)
    if not season:
        return seasons_list(request)

    Tournament = apps.get_model("msa", "Tournament") if apps.is_installed("msa") else None
    tournaments = []
    if Tournament:
        qs = Tournament.objects.all()
        fields = {f.name for f in Tournament._meta.get_fields()}
        if "season" in fields:
            tournaments = qs.filter(season=season)
        elif {"start_date", "end_date"}.issubset(fields):
            start = getattr(season, "start_date", None)
            end = getattr(season, "end_date", None)
            if start and end:
                tournaments = qs.filter(start_date__lte=end, end_date__gte=start)
        elif "start_date" in fields:
            start = getattr(season, "start_date", None)
            end = getattr(season, "end_date", None)
            if start and end:
                tournaments = qs.filter(start_date__range=(start, end))
        elif "date" in fields:
            start = getattr(season, "start_date", None)
            end = getattr(season, "end_date", None)
            if start and end:
                tournaments = qs.filter(date__range=(start, end))

    context = {
        "tournaments": tournaments,
        "active_season": season,
        "active_date": d,
    }
    return render(request, "msa/tournaments/list.html", context)


def tournaments_seasons(request):
    """
    Seznam sezón pro Tournaments landing page, seřazený od nejnovější po nejstarší.
    Preferuje řazení podle start_date/end_date, fallback na -id.
    """
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    seasons = []
    if Season:
        try:
            model_fields = {f.name for f in Season._meta.get_fields()}
            if {"start_date", "end_date"} <= model_fields:
                seasons = list(Season.objects.all().order_by("-start_date", "-end_date", "-id"))
            else:
                seasons = list(Season.objects.all().order_by("-id"))
        except OperationalError:
            seasons = []
    ctx = {"seasons": seasons}
    return render(request, "msa/tournaments/seasons.html", ctx)


def _get_season_by_query_param(request):
    """
    Pokud je v URL ?season=<id>, vrať konkrétní Season; jinak None.
    """
    season_id = request.GET.get("season")
    if not season_id:
        return None
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    if not Season:
        return None
    try:
        return Season.objects.get(pk=season_id)
    except Season.DoesNotExist as err:
        raise Http404("Season not found") from err
    except OperationalError as err:
        raise Http404("Season not found") from err


def rankings_list(request):
    return render(request, "msa/rankings/list.html")


def players_list(request):
    return render(request, "msa/players/list.html")


def calendar(request):
    """
    Kalendář – respektuje ?season=<id>, jinak vybere sezónu dle aktivního data.
    """
    d = get_active_date(request)

    try:
        season = _get_season_by_query_param(request)
    except OperationalError:
        season = None

    if not season:
        try:
            season = find_season_for_date(d)
        except OperationalError:
            season = None

    if not season:
        return seasons_list(request)

    season_id = request.GET.get("season")
    if not season_id:
        season_id = getattr(season, "id", "")
    season_id = str(season_id) if season_id not in {None, ""} else ""

    context = {
        "active_season": season,
        "active_date": d,
        "season": season,
        "season_id": season_id,
    }
    return render(request, "msa/calendar/index.html", context)


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


def tournament_info(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    context.update({"active_tab": "info"})
    return render(request, "msa/tournament/info.html", context)


def tournament_program(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    context.update({"active_tab": "program"})

    matches_url = None
    courts_url = None
    if getattr(tournament, "id", None) is not None:
        try:
            matches_url = reverse("msa-tournament-matches-api", args=[tournament.id])
        except NoReverseMatch:
            matches_url = f"/api/msa/tournament/{tournament.id}/matches"
        try:
            courts_url = reverse("msa-tournament-courts-api", args=[tournament.id])
        except NoReverseMatch:
            courts_url = f"/api/msa/tournament/{tournament.id}/courts"

    context.update(
        {
            "matches_api_url": matches_url,
            "courts_api_url": courts_url,
        }
    )
    return render(request, "msa/tournament/program.html", context)


def tournament_draws(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    context.update({"active_tab": "draws"})
    return render(request, "msa/tournament/draws.html", context)


def tournament_players(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    context.update({"active_tab": "players"})
    return render(request, "msa/tournament/players.html", context)


def tournament_scoring(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    context.update({"active_tab": "scoring"})
    return render(request, "msa/tournament/scoring.html", context)


def tournament_media(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    context = _tournament_base_context(request, tournament)
    context.update({"active_tab": "media"})
    return render(request, "msa/tournament/media.html", context)


def season_api(request):
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    season_id = request.GET.get("id") or request.GET.get("season")
    data = {}

    if Season and season_id:
        season = Season.objects.filter(pk=season_id).first()
        if season:
            start = getattr(season, "start_date", None)
            end = getattr(season, "end_date", None)
            start_iso = _to_iso(start)
            end_iso = _to_iso(end)
            months = enumerate_fax_months(start_iso, end_iso) if start_iso and end_iso else []
            data = {
                "id": getattr(season, "id", None),
                "name": getattr(season, "name", None),
                "start_date": start_iso,
                "end_date": end_iso,
                "month_sequence": months,
            }

    return JsonResponse(data)


def tournaments_api(request):
    """
    JSON seznam turnajů. Preferuje sezonní filtr ?season=<id>.
    Robustně čte typické sloupce Tournament modelu; když nejsou, vrátí základ.
    """
    Season = apps.get_model("msa", "Season") if apps.is_installed("msa") else None
    Tournament = apps.get_model("msa", "Tournament") if apps.is_installed("msa") else None
    season_id = request.GET.get("season")

    items = []
    if Tournament:
        try:
            qs = Tournament.objects.all()
            fields = {f.name for f in Tournament._meta.get_fields()}
            # filtr podle sezony, pokud existuje FK season
            if season_id and "season" in fields:
                qs = qs.filter(season_id=season_id)
            # fallback: pokud nejsou sezony, ale jsou start/end a máme season interval
            elif (
                season_id
                and Season
                and {"start_date", "end_date"} <= {f.name for f in Season._meta.get_fields()}
                and {"start_date", "end_date"} <= fields
            ):
                try:
                    s = Season.objects.get(pk=season_id)
                    if getattr(s, "start_date", None) and getattr(s, "end_date", None):
                        qs = qs.filter(start_date__lte=s.end_date, end_date__gte=s.start_date)
                except (Season.DoesNotExist, OperationalError):
                    pass
            rels = []
            for fname in ("season", "category"):
                try:
                    field = Tournament._meta.get_field(fname)
                except (FieldDoesNotExist, AttributeError, LookupError):
                    continue
                if getattr(field, "is_relation", False) and isinstance(field, ForeignKey):
                    rels.append(fname)
            if rels:
                qs = qs.select_related(*rels)

            orderable = [fname for fname in ("start_date", "name") if fname in fields]
            if orderable:
                qs = qs.order_by(*orderable)

            def resolve_category(tournament):
                display = getattr(tournament, "get_category_display", None)
                if callable(display):
                    value = display()
                    if value not in (None, ""):
                        return str(value)

                category_attr = getattr(tournament, "category", None)
                if getattr(category_attr, "name", None):
                    return str(category_attr.name)
                if category_attr not in (None, ""):
                    return str(category_attr)

                tier_value = getattr(tournament, "tier", None)
                return "" if tier_value in (None, "") else str(tier_value)

            def resolve_tour(tournament, category_value: str) -> str:
                display = getattr(tournament, "get_tour_display", None)
                if callable(display):
                    value = display()
                    if value not in (None, ""):
                        return str(value)

                tour_attr = getattr(tournament, "tour", None)
                if getattr(tour_attr, "name", None):
                    return str(tour_attr.name)
                if tour_attr not in (None, ""):
                    return str(tour_attr)

                cat = (category_value or "").lower()
                world = {"diamond", "emerald", "platinum", "gold", "silver", "bronze"}
                elite = {"copper", "cobalt", "iron", "nickel", "tin", "zinc"}
                if any(x in cat for x in world):
                    return "World Tour"
                if any(x in cat for x in elite):
                    return "Elite Tour"
                if "challenger" in cat:
                    return "Challenger Tour"
                if "future" in cat or "isd" in cat:
                    return "Development Tour"
                return ""

            def build_url(tournament):
                get_absolute = getattr(tournament, "get_absolute_url", None)
                if callable(get_absolute):
                    try:
                        url_value = get_absolute()
                    except (TypeError, ValueError):
                        url_value = None
                    else:
                        if url_value:
                            return url_value

                if getattr(tournament, "id", None) is not None:
                    try:
                        return reverse("msa:tournament_detail", args=[tournament.id])
                    except NoReverseMatch:
                        return None
                return None

            for t in qs:
                start_attr = getattr(t, "start_date", None) or getattr(t, "start", None)
                end_attr = getattr(t, "end_date", None) or getattr(t, "end", None)
                category_value = resolve_category(t)
                row = {
                    "id": getattr(t, "id", None),
                    "name": getattr(t, "name", None) or getattr(t, "title", None),
                    "city": getattr(t, "city", None),
                    "country": getattr(t, "country", None),
                    "category": category_value,
                    "tour": resolve_tour(t, category_value),
                    "start_date": _to_iso(start_attr),
                    "end_date": _to_iso(end_attr),
                    "url": build_url(t),
                }
                items.append(row)
        except OperationalError:
            items = []
    return JsonResponse({"tournaments": items})


def ranking_api(request):
    """Return ranking entries for the frontend table."""
    return JsonResponse({"entries": []})


def tournament_matches_api(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    Match = apps.get_model("msa", "Match") if apps.is_installed("msa") else None
    if not Match:
        return JsonResponse({"matches": []})

    try:
        qs = Match.objects.filter(tournament=tournament)
        qs = qs.select_related(
            "schedule",
            "player1__country",
            "player2__country",
            "player_top__country",
            "player_bottom__country",
            "winner",
        )
    except OperationalError:
        qs = Match.objects.none()

    phase = request.GET.get("phase", "")
    if phase:
        phase_normalized = phase.strip().lower()
        if phase_normalized in {"md", "main", "main_draw"}:
            qs = qs.filter(phase__iexact="MD")
        elif phase_normalized in {"qual", "qualification", "q"}:
            qs = qs.filter(phase__iexact="QUAL")

    status_param = request.GET.get("status", "").strip().lower()
    status_map = {
        "scheduled": ["SCHEDULED", "PENDING"],
        "pending": ["PENDING"],
        "finished": ["DONE"],
        "live": ["SCHEDULED"],
    }
    if status_param and status_param not in {"all", ""}:
        states = status_map.get(status_param)
        if states:
            qs = qs.filter(state__in=states)

    best_of_param = request.GET.get("best_of")
    if best_of_param and best_of_param not in {"default", ""}:
        try:
            qs = qs.filter(best_of=int(best_of_param))
        except (TypeError, ValueError):
            pass

    matches = []
    for match in qs:
        schedule = getattr(match, "schedule", None)
        fax_day = getattr(schedule, "play_date", None) or getattr(match, "play_date", None)
        order = getattr(schedule, "order", None) or getattr(match, "position", None)

        player_candidates = [
            getattr(match, "player1", None) or getattr(match, "player_top", None),
            getattr(match, "player2", None) or getattr(match, "player_bottom", None),
        ]

        players = []
        for player in player_candidates:
            if not player:
                continue
            name = (
                getattr(player, "full_name", None) or getattr(player, "name", None) or str(player)
            )
            country = getattr(getattr(player, "country", None), "iso3", None) or getattr(
                getattr(player, "country", None), "name", None
            )
            players.append({"id": getattr(player, "id", None), "name": name, "country": country})

        score = getattr(match, "score", None) or {}
        raw_sets = []
        if isinstance(score, dict):
            raw_sets = score.get("sets") or []

        sets = []
        for item in raw_sets:
            if isinstance(item, dict):
                a_val = item.get("a", item.get("top"))
                b_val = item.get("b", item.get("bottom"))
                sets.append({"a": a_val, "b": b_val, "status": item.get("status")})
                continue
            if isinstance(item, list | tuple) and len(item) >= 2:
                try:
                    a_val = int(item[0])
                    b_val = int(item[1])
                except (TypeError, ValueError):
                    continue
                sets.append({"a": a_val, "b": b_val, "status": None})

        state_value = (getattr(match, "state", None) or "").upper()
        status_value = {
            "DONE": "finished",
            "SCHEDULED": "scheduled",
            "PENDING": "scheduled",
        }.get(state_value, state_value.lower() or "scheduled")

        phase_value = (getattr(match, "phase", None) or "").lower()
        if phase_value in {"qual", "qualification"}:
            phase_value = "qual"
        elif phase_value in {"md", "main", "main_draw"}:
            phase_value = "md"

        matches.append(
            {
                "id": getattr(match, "id", None),
                "phase": phase_value,
                "round_label": getattr(match, "round_name", None) or getattr(match, "round", None),
                "court": None,
                "fax_day": fax_day,
                "order": order,
                "players": players,
                "best_of": getattr(match, "best_of", None),
                "sets": sets,
                "winner_id": getattr(match, "winner_id", None),
                "status": status_value,
                "needs_review": bool(getattr(match, "needs_review", False)),
            }
        )

    return JsonResponse({"matches": matches})


def tournament_courts_api(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    Match = apps.get_model("msa", "Match") if apps.is_installed("msa") else None
    if not Match:
        return JsonResponse({"courts": []})

    try:
        qs = Match.objects.filter(tournament=tournament).select_related("schedule")
    except OperationalError:
        return JsonResponse({"courts": []})

    seen = {}
    courts = []

    def _append_court(candidate):
        if not candidate:
            return
        if isinstance(candidate, dict):
            cid = candidate.get("id")
            name = candidate.get("name")
        else:
            cid = getattr(candidate, "id", None)
            name = getattr(candidate, "name", None) or (str(candidate) if candidate else None)
        key = cid or name
        if not key or key in seen:
            return
        seen[key] = True
        courts.append({"id": cid, "name": name})

    for match in qs:
        for attr in ("court", "court_name"):
            _append_court(getattr(match, attr, None))
        schedule = getattr(match, "schedule", None)
        if schedule:
            for attr in ("court", "court_name"):
                _append_court(getattr(schedule, attr, None))

    return JsonResponse({"courts": courts})
