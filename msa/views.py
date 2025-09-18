from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.db import OperationalError
from django.db.models import Q
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
    Schedule = apps.get_model("msa", "Schedule") if apps.is_installed("msa") else None

    try:
        limit = min(max(int(request.GET.get("limit", 100)), 1), 500)
    except (TypeError, ValueError):
        limit = 100
    try:
        offset = max(int(request.GET.get("offset", 0)), 0)
    except (TypeError, ValueError):
        offset = 0

    def _base_response(matches: list[dict] | None = None) -> JsonResponse:
        return JsonResponse(
            {
                "matches": matches or [],
                "count": len(matches or []),
                "limit": limit,
                "offset": offset,
                "next_offset": None,
            }
        )

    if not Match:
        return _base_response([])

    def _model_has_field(model, field_name: str) -> bool:
        if not model:
            return False
        try:
            model._meta.get_field(field_name)
            return True
        except FieldDoesNotExist:
            return False

    def _combine_or(filters: list[Q]) -> Q | None:
        if not filters:
            return None
        combined = filters[0]
        for item in filters[1:]:
            combined |= item
        return combined

    def _serialize_court(candidate):
        if not candidate:
            return None
        if isinstance(candidate, dict):
            cid = candidate.get("id") or candidate.get("pk")
            name = (
                candidate.get("name")
                or candidate.get("label")
                or candidate.get("title")
                or candidate.get("court")
            )
            if cid is None and name is None and candidate:
                name = str(candidate)
            if cid is None and name is None:
                return None
            return {"id": cid, "name": name}
        if isinstance(candidate, str):
            cleaned = candidate.strip()
            if not cleaned:
                return None
            return {"id": None, "name": cleaned}
        cid = getattr(candidate, "id", None)
        name = getattr(candidate, "name", None)
        if name:
            return {"id": cid, "name": name}
        text = str(candidate)
        if text:
            return {"id": cid, "name": text}
        return None

    def _resolve_court(match, schedule):
        for obj in (schedule, match):
            if not obj:
                continue
            for attr in ("court", "court_name"):
                resolved = _serialize_court(getattr(obj, attr, None))
                if resolved:
                    return resolved
        score = getattr(match, "score", None)
        if isinstance(score, dict):
            for key in ("court", "court_name"):
                resolved = _serialize_court(score.get(key))
                if resolved:
                    return resolved
            meta = score.get("meta")
            if isinstance(meta, dict):
                for key in ("court", "court_name"):
                    resolved = _serialize_court(meta.get(key))
                    if resolved:
                        return resolved
        return None

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

    status_param = (request.GET.get("status", "") or "").strip().lower()
    status_filter = status_param if status_param not in {"", "all"} else None
    explicit_live_state = False
    try:
        state_field = Match._meta.get_field("state")
        explicit_live_state = any(
            str(choice[0]).upper() == "LIVE" for choice in getattr(state_field, "choices", [])
        )
    except FieldDoesNotExist:
        state_field = None

    if status_filter == "live":
        live_states = ["LIVE"] if explicit_live_state else ["SCHEDULED", "PENDING"]
        if state_field:
            qs = qs.filter(state__in=live_states)
    elif status_filter == "finished":
        if state_field:
            qs = qs.filter(state__in=["DONE"])
    elif status_filter == "scheduled":
        if state_field:
            qs = qs.filter(state__in=["SCHEDULED", "PENDING"])
    elif status_filter == "pending":
        if state_field:
            qs = qs.filter(state__in=["PENDING"])

    best_of_param = request.GET.get("best_of")
    if best_of_param and best_of_param not in {"default", ""}:
        if str(best_of_param).lower() == "win_only":
            # TODO: implement dedicated filter once "win only" matches are modeled explicitly.
            pass
        else:
            try:
                qs = qs.filter(best_of=int(best_of_param))
            except (TypeError, ValueError):
                pass

    fax_day_param = (request.GET.get("fax_day") or "").strip()
    if fax_day_param:
        day_filters = []
        if _model_has_field(Schedule, "play_date"):
            day_filters.append(Q(schedule__play_date=fax_day_param))
        if _model_has_field(Match, "play_date"):
            day_filters.append(Q(play_date=fax_day_param))
        combined = _combine_or(day_filters)
        if combined is not None:
            qs = qs.filter(combined)

    fax_month_param = request.GET.get("fax_month")
    if fax_month_param:
        try:
            month_int = int(fax_month_param)
        except (TypeError, ValueError):
            month_int = None
        if month_int and 1 <= month_int <= 15:
            mm = f"{month_int:02d}"
            month_re = rf"^\d{{4}}-{mm}-"
            month_filters = []
            if _model_has_field(Schedule, "play_date"):
                month_filters.append(Q(schedule__play_date__regex=month_re))
            if _model_has_field(Match, "play_date"):
                month_filters.append(Q(play_date__regex=month_re))
            combined = _combine_or(month_filters)
            if combined is not None:
                qs = qs.filter(combined)

    court_param = (request.GET.get("court") or "").strip()
    if court_param:
        court_filters = []
        if _model_has_field(Schedule, "court"):
            court_filters.extend(
                [
                    Q(schedule__court__id__iexact=court_param),
                    Q(schedule__court__name__icontains=court_param),
                    Q(schedule__court__iexact=court_param),
                ]
            )
        if _model_has_field(Schedule, "court_name"):
            court_filters.append(Q(schedule__court_name__icontains=court_param))
        if _model_has_field(Match, "court"):
            court_filters.extend(
                [
                    Q(court__id__iexact=court_param),
                    Q(court__name__icontains=court_param),
                    Q(court__iexact=court_param),
                ]
            )
        if _model_has_field(Match, "court_name"):
            court_filters.append(Q(court_name__icontains=court_param))
        # Fallback for court information stored in JSON score payloads.
        court_filters.extend(
            [
                Q(score__court__id__iexact=court_param),
                Q(score__court__name__icontains=court_param),
                Q(score__court__icontains=court_param),
                Q(score__meta__court__id__iexact=court_param),
                Q(score__meta__court__name__icontains=court_param),
            ]
        )
        combined = _combine_or(court_filters)
        if combined is not None:
            qs = qs.filter(combined)

    search_param = (request.GET.get("q") or "").strip()
    if search_param:
        search_filters = [
            Q(player1__full_name__icontains=search_param),
            Q(player1__name__icontains=search_param),
            Q(player2__full_name__icontains=search_param),
            Q(player2__name__icontains=search_param),
            Q(player_top__full_name__icontains=search_param),
            Q(player_top__name__icontains=search_param),
            Q(player_bottom__full_name__icontains=search_param),
            Q(player_bottom__name__icontains=search_param),
            Q(round_name__icontains=search_param),
            Q(round__icontains=search_param),
        ]
        if _model_has_field(Match, "notes"):
            search_filters.append(Q(notes__icontains=search_param))
        combined = _combine_or(search_filters)
        if combined is not None:
            qs = qs.filter(combined)

    ordering_fields = []
    if _model_has_field(Schedule, "play_date"):
        ordering_fields.append("schedule__play_date")
    if _model_has_field(Match, "play_date"):
        ordering_fields.append("play_date")
    if _model_has_field(Schedule, "court"):
        ordering_fields.append("schedule__court__name")
    if _model_has_field(Schedule, "court_name"):
        ordering_fields.append("schedule__court_name")
    if _model_has_field(Match, "court"):
        ordering_fields.append("court__name")
    if _model_has_field(Match, "court_name"):
        ordering_fields.append("court_name")
    if _model_has_field(Schedule, "order"):
        ordering_fields.append("schedule__order")
    if _model_has_field(Match, "position"):
        ordering_fields.append("position")
    ordering_fields.append("id")

    seen = []
    final_ordering = []
    for field in ordering_fields:
        if field not in seen:
            seen.append(field)
            final_ordering.append(field)
    qs = qs.order_by(*final_ordering) if final_ordering else qs.order_by("id")

    matches = []
    raw_matches = list(qs)

    def _parse_sets(score_payload):
        sets = []
        has_partial = False
        raw_sets = []
        if isinstance(score_payload, dict):
            raw_sets = score_payload.get("sets") or []
        for item in raw_sets:
            if isinstance(item, dict):
                raw_a = item.get("a", item.get("top"))
                raw_b = item.get("b", item.get("bottom"))
                status_raw = item.get("status")
                if raw_a in (None, "", "-") or raw_b in (None, "", "-"):
                    has_partial = True
                try:
                    a_val = int(raw_a)
                    b_val = int(raw_b)
                except (TypeError, ValueError):
                    if raw_a is not None or raw_b is not None:
                        has_partial = True
                    continue
                if status_raw:
                    status_norm = str(status_raw).strip().lower()
                    if status_norm and status_norm not in {"finished", "done", "completed"}:
                        has_partial = True
                sets.append({"a": a_val, "b": b_val, "status": status_raw})
            elif isinstance(item, list | tuple) and len(item) >= 2:
                raw_a, raw_b = item[0], item[1]
                try:
                    a_val = int(raw_a)
                    b_val = int(raw_b)
                except (TypeError, ValueError):
                    if raw_a is not None or raw_b is not None:
                        has_partial = True
                    continue
                sets.append({"a": a_val, "b": b_val, "status": None})
        if isinstance(score_payload, dict) and len(sets) < len(raw_sets):
            has_partial = True
        return sets, has_partial

    for match in raw_matches:
        schedule = getattr(match, "schedule", None)
        fax_day = getattr(schedule, "play_date", None) or getattr(match, "play_date", None)
        fax_day = _to_iso(fax_day) if fax_day else fax_day
        order_value = getattr(schedule, "order", None)
        if order_value is None:
            order_value = getattr(match, "position", None)

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
        sets, has_partial = _parse_sets(score)

        state_value = (getattr(match, "state", None) or "").upper()
        base_status = {
            "DONE": "finished",
            "SCHEDULED": "scheduled",
            "PENDING": "scheduled",
            "LIVE": "live",
        }.get(state_value, state_value.lower() or "scheduled")

        if base_status != "finished":
            in_progress_flag = bool(getattr(match, "in_progress", False))
            has_recorded_sets = bool(sets)
            if base_status == "live" or in_progress_flag:
                base_status = "live"
            elif has_partial and (base_status != "scheduled" or has_recorded_sets):
                base_status = "live"

        phase_value = (getattr(match, "phase", None) or "").lower()
        if phase_value in {"qual", "qualification"}:
            phase_value = "qual"
        elif phase_value in {"md", "main", "main_draw"}:
            phase_value = "md"

        if status_filter == "live" and base_status != "live":
            continue
        if status_filter == "finished" and base_status != "finished":
            continue
        if status_filter == "scheduled" and base_status != "scheduled":
            continue
        if status_filter == "pending" and state_value != "PENDING":
            continue

        court_value = _resolve_court(match, schedule)

        matches.append(
            {
                "id": getattr(match, "id", None),
                "phase": phase_value,
                "round_label": getattr(match, "round_name", None) or getattr(match, "round", None),
                "court": court_value,
                "fax_day": fax_day,
                "order": order_value,
                "players": players,
                "best_of": getattr(match, "best_of", None),
                "sets": sets,
                "winner_id": getattr(match, "winner_id", None),
                "status": base_status,
                "needs_review": bool(getattr(match, "needs_review", False)),
            }
        )

    def _sort_key(item):
        fax_day_val = str(item.get("fax_day") or "")
        court_val = item.get("court")
        if isinstance(court_val, dict):
            court_key = court_val.get("name") or court_val.get("id") or ""
        else:
            court_key = court_val or ""
        order_val = item.get("order")
        try:
            order_key = int(order_val)
        except (TypeError, ValueError):
            order_key = 10**6
        return (fax_day_val, str(court_key), order_key, item.get("id") or 0)

    matches.sort(key=_sort_key)

    total = len(matches)
    paginated = matches[offset : offset + limit]
    next_offset = offset + limit if offset + limit < total else None

    return JsonResponse(
        {
            "matches": paginated,
            "count": total,
            "limit": limit,
            "offset": offset,
            "next_offset": next_offset,
        }
    )


def tournament_courts_api(request, tournament_id: int):
    tournament = _get_tournament_or_404(tournament_id)
    Match = apps.get_model("msa", "Match") if apps.is_installed("msa") else None
    if not Match:
        return JsonResponse({"courts": []})

    try:
        qs = Match.objects.filter(tournament=tournament).select_related("schedule")
    except OperationalError:
        return JsonResponse({"courts": []})

    seen = set()
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
        name_value = name or ""
        key = (cid, name_value)
        if (cid is None and not name_value) or key in seen:
            return
        seen.add(key)
        courts.append({"id": cid, "name": name})

    for match in qs:
        for attr in ("court", "court_name"):
            _append_court(getattr(match, attr, None))
        score_payload = getattr(match, "score", None)
        if isinstance(score_payload, dict):
            for key in ("court", "court_name"):
                _append_court(score_payload.get(key))
            meta = score_payload.get("meta")
            if isinstance(meta, dict):
                for key in ("court", "court_name"):
                    _append_court(meta.get(key))
        schedule = getattr(match, "schedule", None)
        if schedule:
            for attr in ("court", "court_name"):
                _append_court(getattr(schedule, attr, None))

    courts.sort(key=lambda c: ((c.get("name") or "").lower(), str(c.get("id") or "")))

    return JsonResponse({"courts": courts})
