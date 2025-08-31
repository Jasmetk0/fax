import logging
from collections import OrderedDict
from django.db import transaction
from django.db.models import Case, IntegerField, Q, When
import unicodedata

from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib import messages

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
    TournamentEntry,
)
from .services.draw import (
    generate_draw,
    has_completed_main_matches,
    replace_slot,
    progress_bracket,
)
from .services.qual import (
    generate_qualifying,
    progress_qualifying,
    promote_qualifiers,
)
from .services.points import rebuild_season_live_points
from .services.snapshot import create_ranking_snapshot
from .services.alt_ll import (
    auto_fill_with_alternates,
    promote_lucky_losers_to_slot,
    withdraw_slot_and_fill_ll,
)
from .services.seeding_service import preview_seeding, apply_seeding
from .forms import (
    EntryAddForm,
    EntryBulkForm,
    EntryUpdateTypeForm,
    SeedUpdateForm,
    SeedsBulkForm,
    ScheduleBulkSlotsForm,
    ScheduleSwapForm,
    ScheduleMoveForm,
)
from .services.entries import (
    add_entry,
    bulk_add_entries,
    compute_capacity,
    set_entry_status,
    update_entry_type,
    lock_entries,
    unlock_entries,
    validate_pre_draw,
    set_seed,
    bulk_set_seeds,
    export_entries_csv,
)
from .services.scheduling import (
    parse_bulk_schedule_slots,
    apply_bulk_schedule_slots,
    find_conflicts_slots,
    generate_tournament_ics_date_only,
    swap_scheduled_matches,
    move_scheduled_match,
    export_schedule_csv,
)
from .services.match_results import record_match_result
import json
from .utils import filter_by_tour  # MSA-REDESIGN


logger = logging.getLogger(__name__)


tab_choices = [("live", "Live"), ("upcoming", "Upcoming"), ("results", "Results")]


def admin_mode_toggle(request):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    on = request.GET.get("on") == "1"
    request.session["admin_mode"] = on
    return redirect(request.META.get("HTTP_REFERER", "/"))


def _is_admin(request):
    return request.user.is_staff and request.session.get("admin_mode")


def _admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not _is_admin(request):
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)

    return wrapper


def _handle_match_result(request, tournament):
    try:
        match_id = int(request.POST.get("match_id"))
    except (TypeError, ValueError):  # pragma: no cover - guard
        messages.error(request, "Invalid match")
        logger.info(
            "match_result fail user=%s tournament=%s match=%s",
            request.user.id,
            tournament.id,
            request.POST.get("match_id"),
        )
        return redirect(request.path)
    result_type = (request.POST.get("result_type") or "NORMAL").upper()
    scoreline = request.POST.get("scoreline") or None
    retired_player_id = request.POST.get("retired_player_id")
    if retired_player_id:
        try:
            retired_player_id = int(retired_player_id)
        except ValueError:
            retired_player_id = None
    match = get_object_or_404(Match, pk=match_id, tournament=tournament)
    try:
        record_match_result(
            match,
            result_type=result_type,
            scoreline_str=scoreline,
            retired_player_id=retired_player_id,
            user=request.user,
        )
    except ValueError as e:
        messages.error(request, str(e))
        logger.info(
            "match_result fail user=%s tournament=%s match=%s err=%s",
            request.user.id,
            tournament.id,
            match_id,
            e,
        )
    else:
        messages.success(request, "Result saved")
        logger.info(
            "match_result success user=%s tournament=%s match=%s type=%s",
            request.user.id,
            tournament.id,
            match_id,
            result_type,
        )
    return redirect(request.path)


def home(request):
    tour = request.GET.get("tour")  # MSA-REDESIGN
    upcoming_tournaments = filter_by_tour(
        Tournament.objects.filter(status="upcoming"),
        tour_field="category__name",
        tour=tour,
    ).order_by("start_date")[:5]
    live_matches = filter_by_tour(
        Match.objects.filter(live_status="live"),
        tour_field="tournament__category__name",
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
    tournaments = Tournament.objects.none()
    if season_id:
        selected_season = get_object_or_404(Season, pk=season_id)
    elif seasons:
        selected_season = seasons.first()
    if selected_season:
        tournaments = Tournament.objects.filter(season=selected_season).select_related(
            "category",
            "season_category__category",
        )
    return render(
        request,
        "msa/tournaments.html",
        {
            "seasons": seasons,
            "selected_season": selected_season,
            "tournaments": tournaments,
        },
    )


def tournament_overview(request, slug):
    tournament = get_object_or_404(Tournament, slug=slug)
    return render(
        request,
        "msa/tournament_overview.html",
        {"tournament": tournament},
    )


def tournament_players(request, slug):
    tournament = get_object_or_404(Tournament, slug=slug)
    if request.method == "POST":
        if not _is_admin(request):
            return HttpResponseForbidden()
        action = request.POST.get("action")
        if action == "entry_add":
            form = EntryAddForm(request.POST)
            if form.is_valid():
                ok, msg = add_entry(
                    tournament,
                    form.cleaned_data["player"],
                    form.cleaned_data["entry_type"],
                    request.user,
                )
                if ok and "ALT" in msg:
                    messages.warning(request, msg)
                elif ok:
                    messages.success(request, msg)
                else:
                    messages.error(request, msg)
            else:
                messages.error(request, "Invalid data")
            return redirect(request.path)
        if action == "entry_bulk_add":
            form = EntryBulkForm(request.POST)
            if form.is_valid():
                result = bulk_add_entries(
                    tournament, form.cleaned_data["rows"], request.user
                )
                messages.info(
                    request,
                    f"added {result['added']}, skipped {result['skipped']}, errors {result['errors']}",
                )
                for m in result["messages"]:
                    if "ALT" in m:
                        messages.warning(request, m)
                    else:
                        messages.info(request, m)
            else:
                messages.error(request, "Invalid data")
            return redirect(request.path)
        if action == "entry_update_type":
            form = EntryUpdateTypeForm(request.POST)
            if form.is_valid():
                entry = get_object_or_404(
                    tournament.entries, pk=form.cleaned_data["entry_id"]
                )
                ok, msg = update_entry_type(
                    entry, form.cleaned_data["entry_type"], request.user
                )
                if ok and "ALT" in msg:
                    messages.warning(request, msg)
                elif ok:
                    messages.success(request, msg)
                else:
                    messages.error(request, msg)
            else:
                messages.error(request, "Invalid data")
            return redirect(request.path)
        if action == "entry_withdraw":
            entry_id = request.POST.get("entry_id")
            entry = get_object_or_404(tournament.entries, pk=entry_id)
            ok, msg = set_entry_status(
                entry, TournamentEntry.Status.WITHDRAWN, request.user
            )
            if ok:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
            return redirect(request.path)
        if action == "entry_reactivate":
            entry_id = request.POST.get("entry_id")
            entry = get_object_or_404(tournament.entries, pk=entry_id)
            ok, msg = set_entry_status(
                entry, TournamentEntry.Status.ACTIVE, request.user
            )
            if ok and "ALT" in msg:
                messages.warning(request, msg)
            elif ok:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
            return redirect(request.path)
        if action == "entries_lock":
            ok, msg = lock_entries(tournament, request.user)
            if ok:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
            return redirect(request.path)
        if action == "entries_unlock":
            ok, msg = unlock_entries(tournament, request.user)
            if ok:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
            return redirect(request.path)
        if action == "seed_update":
            form = SeedUpdateForm(request.POST)
            if form.is_valid():
                entry = get_object_or_404(
                    tournament.entries, pk=form.cleaned_data["entry_id"]
                )
                seed = form.cleaned_data.get("seed")
                ok, msg = set_seed(entry, seed, request.user)
                if ok and "warning" in msg:
                    messages.warning(request, msg)
                elif ok:
                    messages.success(request, msg)
                else:
                    messages.error(request, msg)
            else:
                messages.error(request, "Invalid data")
            return redirect(request.path)
        if action == "seeds_bulk_update":
            form = SeedsBulkForm(request.POST)
            if form.is_valid():
                mapping = {}
                parse_errors = {}
                for line in form.cleaned_data["rows"].splitlines():
                    row = line.strip()
                    if not row or row.startswith("#"):
                        continue
                    parts = [p.strip() for p in row.split(",")]
                    if not parts[0]:
                        continue
                    try:
                        eid = int(parts[0])
                    except ValueError:
                        parse_errors[parts[0]] = "Invalid entry id"
                        continue
                    seed = None
                    if len(parts) > 1 and parts[1] != "":
                        try:
                            seed = int(parts[1])
                        except ValueError:
                            parse_errors[eid] = "Invalid seed"
                            continue
                    mapping[eid] = seed
                result = bulk_set_seeds(tournament, mapping, request.user)
                result["errors"].update(parse_errors)
                messages.info(
                    request,
                    f"updated {result['updated']}, errors {len(result['errors'])}",
                )
                for eid, emsg in result["errors"].items():
                    messages.error(request, f"{eid}: {emsg}")
            else:
                messages.error(request, "Invalid data")
            return redirect(request.path)
        if action == "set_origin":
            entry_id = request.POST.get("entry_id")
            origin_note = request.POST.get("origin_note", "")
            origin_match_id = request.POST.get("origin_match_id")
            try:
                entry = tournament.entries.get(pk=entry_id)
            except TournamentEntry.DoesNotExist:
                messages.error(request, "Entry not found")
                logger.info(
                    "set_origin fail user=%s tournament=%s entry=%s",
                    request.user.id,
                    tournament.id,
                    entry_id,
                )
                return redirect(request.path)
            if entry.entry_type not in {
                TournamentEntry.EntryType.Q,
                TournamentEntry.EntryType.LL,
            }:
                messages.error(request, "Only Q/LL entries allowed")
                logger.info(
                    "set_origin fail user=%s tournament=%s entry=%s",
                    request.user.id,
                    tournament.id,
                    entry_id,
                )
                return redirect(request.path)
            origin_match = None
            if origin_match_id:
                origin_match = Match.objects.filter(
                    pk=origin_match_id, tournament=tournament
                ).first()
                if not origin_match:
                    messages.error(request, "Invalid match")
                    logger.info(
                        "set_origin fail user=%s tournament=%s entry=%s match=%s",
                        request.user.id,
                        tournament.id,
                        entry_id,
                        origin_match_id,
                    )
                    return redirect(request.path)
            with transaction.atomic():
                entry.origin_note = origin_note or ""
                entry.origin_match = origin_match
                entry.updated_by = request.user
                entry.save(update_fields=["origin_note", "origin_match", "updated_by"])
            messages.success(request, "Origin updated")
            logger.info(
                "set_origin success user=%s tournament=%s entry=%s note=%s match=%s",
                request.user.id,
                tournament.id,
                entry_id,
                origin_note,
                origin_match_id,
            )
            return redirect(request.path)
    if request.method == "GET" and request.GET.get("action") == "entries_export_csv":
        if not _is_admin(request):
            return HttpResponseForbidden()
        csv_text = export_entries_csv(tournament)
        resp = HttpResponse(csv_text, content_type="text/csv")
        resp["Content-Disposition"] = (
            f"attachment; filename={tournament.slug}_entries.csv"
        )
        return resp
    with transaction.atomic():
        capacity = compute_capacity(tournament)
    pre_draw = validate_pre_draw(tournament)
    order = [
        Case(
            When(status=TournamentEntry.Status.ACTIVE, then=0),
            When(status=TournamentEntry.Status.WITHDRAWN, then=1),
            When(status=TournamentEntry.Status.REPLACED, then=2),
            output_field=IntegerField(),
        ),
        "entry_type",
        "seed",
        "player__name",
    ]
    entries = list(tournament.entries.select_related("player").order_by(*order))
    if not entries:
        players = (
            Player.objects.filter(
                Q(matches_as_player1__tournament=tournament)
                | Q(matches_as_player2__tournament=tournament)
            )
            .distinct()
            .order_by("name")
        )
        from types import SimpleNamespace

        entries = [SimpleNamespace(player=p) for p in players]
    return render(
        request,
        "msa/tournament_players.html",
        {
            "tournament": tournament,
            "entries": entries,
            "is_admin": _is_admin(request),
            "add_form": EntryAddForm(),
            "bulk_form": EntryBulkForm(),
            "entry_type_choices": TournamentEntry.EntryType.choices,
            "capacity": capacity,
            "pre_draw": pre_draw,
            "seeds_bulk_form": SeedsBulkForm(),
            "seed_editor_allowed": tournament.seeding_method == "manual"
            or tournament.flex_mode,
        },
    )


def tournament_draw(request, slug):
    tournament = get_object_or_404(Tournament, slug=slug)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "match_result":
            if not _is_admin(request):
                return HttpResponseForbidden()
            return _handle_match_result(request, tournament)
        elif action == "rebuild_live_points":
            if not _is_admin(request):
                return HttpResponseForbidden()
            if tournament.season:
                rebuild_season_live_points(
                    tournament.season, persist=True, user=request.user
                )
            messages.success(request, "Live points rebuilt")
            logger.info(
                "rebuild_live_points success user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
            return redirect(request.path)
        if action == "swap":
            if not (_is_admin(request) and tournament.allow_manual_bracket_edits):
                return HttpResponseForbidden()
            try:
                slot_a = int(request.POST.get("slot_a"))
                slot_b = int(request.POST.get("slot_b"))
            except (TypeError, ValueError):  # pragma: no cover - guard
                messages.error(request, "Invalid slots")
                logger.info(
                    "swap fail user=%s tournament=%s", request.user.id, tournament.id
                )
                return redirect(request.path)
            with transaction.atomic():
                entries_qs = tournament.entries.select_for_update().select_related(
                    "player"
                )
                entry_a = entries_qs.filter(position=slot_a).first()
                entry_b = entries_qs.filter(position=slot_b).first()
                if not entry_a or not entry_b:
                    messages.warning(request, "Cannot swap with empty/BYE slot")
                    logger.info(
                        "swap fail user=%s tournament=%s slot_a=%s slot_b=%s",
                        request.user.id,
                        tournament.id,
                        slot_a,
                        slot_b,
                    )
                    return redirect(request.path)
                mate_a = slot_a + 1 if slot_a % 2 else slot_a - 1
                mate_b = slot_b + 1 if slot_b % 2 else slot_b - 1
                needed = {slot_a, slot_b, mate_a, mate_b}
                by_pos = {e.position: e for e in entries_qs.filter(position__in=needed)}
                pairs = {
                    tuple(sorted([slot_a, mate_a])),
                    tuple(sorted([slot_b, mate_b])),
                }
                matches = {}
                for low, high in pairs:
                    ea = by_pos.get(low)
                    eb = by_pos.get(high)
                    if ea and eb:
                        m = (
                            tournament.matches.select_for_update()
                            .filter(
                                player1__in=[ea.player, eb.player],
                                player2__in=[ea.player, eb.player],
                                round=f"R{tournament.draw_size}",
                            )
                            .first()
                        )
                        if m:
                            matches[(low, high)] = m
                if (
                    any(m.winner_id for m in matches.values())
                    and not tournament.flex_mode
                ):
                    messages.warning(request, "Cannot swap over completed match")
                    logger.info(
                        "swap fail user=%s tournament=%s slot_a=%s slot_b=%s completed",
                        request.user.id,
                        tournament.id,
                        slot_a,
                        slot_b,
                    )
                    return redirect(request.path)
                entry_a.position, entry_b.position = entry_b.position, entry_a.position
                entry_a.updated_by = request.user
                entry_b.updated_by = request.user
                entry_a.save(update_fields=["position", "updated_by"])
                entry_b.save(update_fields=["position", "updated_by"])
                by_pos[entry_a.position] = entry_a
                by_pos[entry_b.position] = entry_b
                for (low, high), m in matches.items():
                    if m.winner_id:
                        messages.warning(
                            request, "Match already completed; players not updated"
                        )
                        continue
                    ea = by_pos.get(low)
                    eb = by_pos.get(high)
                    if ea and eb:
                        m.player1 = ea.player
                        m.player2 = eb.player
                        m.save(update_fields=["player1", "player2"])
                messages.success(request, "Slots swapped")
                logger.info(
                    "swap success user=%s tournament=%s slot_a=%s slot_b=%s",
                    request.user.id,
                    tournament.id,
                    slot_a,
                    slot_b,
                )
            return redirect(request.path)
        elif action == "replace":
            if not (_is_admin(request) and tournament.allow_manual_bracket_edits):
                return HttpResponseForbidden()
            try:
                slot = int(request.POST.get("slot"))
                entry_id = int(request.POST.get("entry_id"))
            except (TypeError, ValueError):  # pragma: no cover - guard
                messages.error(request, "Invalid parameters")
                logger.info(
                    "replace fail user=%s tournament=%s", request.user.id, tournament.id
                )
                return redirect(request.path)
            mate = slot + 1 if slot % 2 else slot - 1
            current = (
                tournament.entries.filter(position=slot, status="active")
                .select_related("player")
                .first()
            )
            partner = (
                tournament.entries.filter(position=mate, status="active")
                .select_related("player")
                .first()
            )
            match = None
            if current and partner:
                match = tournament.matches.filter(
                    player1__in=[current.player, partner.player],
                    player2__in=[current.player, partner.player],
                    round=f"R{tournament.draw_size}",
                ).first()
                if match and match.winner_id and not tournament.flex_mode:
                    messages.warning(request, "Cannot replace over completed match")
                    logger.info(
                        "replace fail user=%s tournament=%s slot=%s completed",
                        request.user.id,
                        tournament.id,
                        slot,
                    )
                    return redirect(request.path)
            ok = replace_slot(
                tournament,
                slot,
                entry_id,
                allow_over_completed=tournament.flex_mode,
                user=request.user,
            )
            if ok:
                if match and match.winner_id:
                    messages.warning(
                        request, "Match already completed; players not updated"
                    )
                else:
                    messages.success(request, "Slot replaced")
                logger.info(
                    "replace success user=%s tournament=%s slot=%s entry=%s",
                    request.user.id,
                    tournament.id,
                    slot,
                    entry_id,
                )
            else:
                messages.error(request, "Replacement failed")
                logger.info(
                    "replace fail user=%s tournament=%s slot=%s entry=%s",
                    request.user.id,
                    tournament.id,
                    slot,
                    entry_id,
                )
            return redirect(request.path)
        elif action == "alt_autofill":
            if not _is_admin(request):
                return HttpResponseForbidden()
            res = auto_fill_with_alternates(tournament, user=request.user)
            filled = res.get("filled", 0)
            if filled:
                messages.success(request, f"Filled {filled} slots")
                logger.info(
                    "alt_autofill success user=%s tournament=%s filled=%s",
                    request.user.id,
                    tournament.id,
                    filled,
                )
            else:
                messages.warning(request, "No alternates placed")
                logger.info(
                    "alt_autofill fail user=%s tournament=%s",
                    request.user.id,
                    tournament.id,
                )
            return redirect(request.path)
        elif action == "withdraw_slot_ll":
            if not _is_admin(request):
                return HttpResponseForbidden()
            try:
                slot = int(request.POST.get("slot"))
            except (TypeError, ValueError):  # pragma: no cover - guard
                messages.error(request, "Invalid slot")
                logger.info(
                    "withdraw_slot_ll fail user=%s tournament=%s",
                    request.user.id,
                    tournament.id,
                )
                return redirect(request.path)
            ok = withdraw_slot_and_fill_ll(tournament, slot, user=request.user)
            if ok:
                messages.success(request, "Slot withdrawn and filled")
                logger.info(
                    "withdraw_slot_ll success user=%s tournament=%s slot=%s",
                    request.user.id,
                    tournament.id,
                    slot,
                )
            else:
                messages.warning(request, "Withdraw/promotion failed")
                logger.info(
                    "withdraw_slot_ll fail user=%s tournament=%s slot=%s",
                    request.user.id,
                    tournament.id,
                    slot,
                )
            return redirect(request.path)
        elif action == "promote_ll_to_slot":
            if not _is_admin(request):
                return HttpResponseForbidden()
            try:
                slot = int(request.POST.get("slot"))
            except (TypeError, ValueError):  # pragma: no cover - guard
                messages.error(request, "Invalid slot")
                logger.info(
                    "promote_ll_to_slot fail user=%s tournament=%s",
                    request.user.id,
                    tournament.id,
                )
                return redirect(request.path)
            ok = promote_lucky_losers_to_slot(tournament, slot, user=request.user)
            if ok:
                messages.success(request, "Lucky loser promoted")
                logger.info(
                    "promote_ll_to_slot success user=%s tournament=%s slot=%s",
                    request.user.id,
                    tournament.id,
                    slot,
                )
            else:
                messages.warning(request, "Promotion failed")
                logger.info(
                    "promote_ll_to_slot fail user=%s tournament=%s slot=%s",
                    request.user.id,
                    tournament.id,
                    slot,
                )
            return redirect(request.path)

    action = request.GET.get("action")
    if action == "generate":
        if tournament.draw_size not in {32, 64, 96, 128}:
            messages.warning(request, "Unsupported draw size")
            logger.info(
                "generate fail user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
        else:
            generate_draw(tournament, force=False, user=request.user)
            logger.info(
                "generate success user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
    elif action == "regenerate":
        if tournament.draw_size not in {32, 64, 96, 128}:
            messages.warning(request, "Unsupported draw size")
            logger.info(
                "regenerate fail user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
        elif tournament.flex_mode or not has_completed_main_matches(tournament):
            generate_draw(tournament, force=True, user=request.user)
            logger.info(
                "regenerate success user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
        else:
            messages.warning(request, "Draw regeneration not allowed.")
            logger.info(
                "regenerate fail user=%s tournament=%s completed",
                request.user.id,
                tournament.id,
            )
    elif action == "progress":
        if progress_bracket(tournament):
            messages.success(request, "Next round generated")
            logger.info(
                "progress success user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
        else:
            messages.warning(request, "Nothing to progress")
            logger.info(
                "progress fail user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
    elif action == "qual_generate":
        if generate_qualifying(tournament, user=request.user):
            messages.success(request, "Qualifying generated")
            logger.info(
                "qual_generate success user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
        else:
            messages.warning(request, "Nothing to generate")
            logger.info(
                "qual_generate fail user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
    elif action == "qual_regenerate":
        if generate_qualifying(tournament, force=True, user=request.user):
            messages.success(request, "Qualifying regenerated")
            logger.info(
                "qual_regenerate success user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
        else:
            messages.warning(request, "Nothing to regenerate")
            logger.info(
                "qual_regenerate fail user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
    elif action == "qual_progress":
        if progress_qualifying(tournament, user=request.user):
            messages.success(request, "Qualifying progressed")
            logger.info(
                "qual_progress success user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
        else:
            messages.warning(request, "Nothing to progress")
            logger.info(
                "qual_progress fail user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
    elif action == "promote_qualifiers":
        if promote_qualifiers(tournament, user=request.user):
            messages.success(request, "Qualifiers promoted")
            logger.info(
                "promote_qualifiers success user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
        else:
            messages.warning(request, "Promotion failed")
            logger.info(
                "promote_qualifiers fail user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )

    entries = tournament.entries.filter(status="active").select_related(
        "player", "origin_match"
    )
    by_player_id = {e.player_id: e for e in entries}
    seeds_by_player_id = {e.player_id: e.seed for e in entries if e.seed}
    by_pos = {e.position: e for e in entries if e.position}

    round_order = ["R128", "R96", "R64", "R32", "R16", "QF", "SF", "F"]
    draw_size = tournament.draw_size or 32
    first_round = f"R{draw_size}"
    bracket = OrderedDict()

    if by_pos:
        for i in range(1, draw_size + 1, 2):
            e1 = by_pos.get(i)
            e2 = by_pos.get(i + 1)
            if not e1 and not e2:
                continue
            if e1 and e2:
                m = (
                    tournament.matches.filter(round=first_round)
                    .filter(
                        Q(player1=e1.player, player2=e2.player)
                        | Q(player1=e2.player, player2=e1.player)
                    )
                    .select_related("player1", "player2", "winner")
                    .first()
                )
                bracket.setdefault(first_round, []).append(
                    {
                        "match": m,
                        "p1": e1.player,
                        "p2": e2.player,
                        "p1_entry": e1,
                        "p2_entry": e2,
                    }
                )
            else:
                if draw_size == 96 and first_round == "R96":
                    continue
                entry = e1 or e2
                bracket.setdefault(first_round, []).append(
                    {
                        "match": None,
                        "p1": entry.player,
                        "p2": None,
                        "p1_entry": entry,
                        "p2_entry": None,
                        "bye": True,
                    }
                )
    else:
        bracket[first_round] = [
            {
                "match": None,
                "p1": e.player,
                "p2": None,
                "p1_entry": e,
                "p2_entry": None,
                "bye": True,
            }
            for e in entries.order_by("player__name")
        ]

    start_idx = round_order.index(first_round)
    for code in round_order[start_idx + 1 :]:
        matches = list(
            tournament.matches.filter(round=code)
            .select_related("player1", "player2", "winner")
            .order_by("id")
        )
        if matches:
            bracket[code] = [
                {
                    "match": m,
                    "p1": m.player1,
                    "p2": m.player2,
                    "p1_entry": by_player_id.get(m.player1_id),
                    "p2_entry": by_player_id.get(m.player2_id),
                }
                for m in matches
            ]
        elif draw_size == 96 and code == "R64":
            for i in range(1, draw_size + 1, 2):
                e1 = by_pos.get(i)
                e2 = by_pos.get(i + 1)
                if e1 and not e2:
                    bracket.setdefault("R64", []).append(
                        {
                            "match": None,
                            "p1": e1.player,
                            "p2": None,
                            "p1_entry": e1,
                            "p2_entry": None,
                            "bye": True,
                        }
                    )
                elif e2 and not e1:
                    bracket.setdefault("R64", []).append(
                        {
                            "match": None,
                            "p1": e2.player,
                            "p2": None,
                            "p1_entry": e2,
                            "p2_entry": None,
                            "bye": True,
                        }
                    )
    round_order = [r for r in round_order if bracket.get(r)]
    bracket_items = [(r, bracket[r]) for r in round_order]

    qual_matches_by_round = {}
    for m in (
        tournament.matches.filter(round__startswith="Q")
        .select_related("player1", "player2", "winner")
        .order_by("id")
    ):
        qual_matches_by_round.setdefault(m.round, []).append(m)
    qual_matches_by_round = dict(
        sorted(
            qual_matches_by_round.items(),
            key=lambda x: int(x[0][1:]) if x[0][1:].isdigit() else 0,
            reverse=True,
        )
    )

    print_mode = request.GET.get("print") == "1"
    template_name = (
        "msa/tournament_draw_print.html" if print_mode else "msa/tournament_draw.html"
    )

    return render(
        request,
        template_name,
        {
            "tournament": tournament,
            "bracket": bracket,
            "round_order": round_order,
            "bracket_items": bracket_items,
            "entries_by_player_id": by_player_id,
            "seeds_by_player_id": seeds_by_player_id,
            "is_admin": _is_admin(request),
            "print_mode": print_mode,
            "qual_matches_by_round": qual_matches_by_round,
        },
    )


def tournament_results(request, slug):
    tournament = get_object_or_404(Tournament, slug=slug)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "match_result":
            if not _is_admin(request):
                return HttpResponseForbidden()
            return _handle_match_result(request, tournament)
        elif action == "rebuild_live_points":
            if not _is_admin(request):
                return HttpResponseForbidden()
            if tournament.season:
                rebuild_season_live_points(
                    tournament.season, persist=True, user=request.user
                )
            messages.success(request, "Live points rebuilt")
            logger.info(
                "rebuild_live_points success user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
            return redirect(request.path)
        elif action == "schedule_bulk_slots":
            if not _is_admin(request):
                return HttpResponseForbidden()
            form = ScheduleBulkSlotsForm(request.POST)
            if form.is_valid():
                try:
                    rows = parse_bulk_schedule_slots(form.cleaned_data["rows"])
                    result = apply_bulk_schedule_slots(
                        tournament, rows, user=request.user
                    )
                except ValueError as e:
                    messages.error(request, str(e))
                else:
                    if result["updated"]:
                        messages.success(
                            request, f"Scheduled {result['updated']} matches"
                        )
                    logger.info(
                        "schedule_bulk_slots user=%s tournament=%s updated=%s",
                        request.user.id,
                        tournament.id,
                        result["updated"],
                    )
            else:
                messages.error(request, "Invalid input")
            return redirect(request.path)
        elif action == "schedule_swap_slots":
            if not _is_admin(request):
                return HttpResponseForbidden()
            form = ScheduleSwapForm(request.POST)
            if form.is_valid():
                ok = swap_scheduled_matches(
                    tournament,
                    form.cleaned_data["match_a"],
                    form.cleaned_data["match_b"],
                    user=request.user,
                )
                if ok:
                    messages.success(request, "Matches swapped")
                    logger.info(
                        "schedule.swap success user=%s tournament=%s a=%s b=%s",
                        request.user.id,
                        tournament.id,
                        form.cleaned_data["match_a"],
                        form.cleaned_data["match_b"],
                    )
                else:
                    messages.error(request, "Swap failed")
                    logger.info(
                        "schedule.swap fail user=%s tournament=%s a=%s b=%s",
                        request.user.id,
                        tournament.id,
                        form.cleaned_data.get("match_a"),
                        form.cleaned_data.get("match_b"),
                    )
            else:
                messages.error(request, "Invalid input")
            return redirect(request.path)
        elif action == "schedule_move_match":
            if not _is_admin(request):
                return HttpResponseForbidden()
            form = ScheduleMoveForm(request.POST)
            if form.is_valid():
                schedule = {
                    "date": form.cleaned_data["date"].isoformat(),
                    "session": form.cleaned_data["session"],
                    "slot": form.cleaned_data["slot"],
                }
                if form.cleaned_data.get("court"):
                    schedule["court"] = form.cleaned_data["court"]
                ok = move_scheduled_match(
                    tournament,
                    form.cleaned_data["match_id"],
                    schedule,
                    user=request.user,
                )
                if ok:
                    messages.success(request, "Match moved")
                    logger.info(
                        "schedule.move success user=%s tournament=%s match=%s",
                        request.user.id,
                        tournament.id,
                        form.cleaned_data["match_id"],
                    )
                else:
                    messages.error(request, "Move failed")
                    logger.info(
                        "schedule.move fail user=%s tournament=%s match=%s",
                        request.user.id,
                        tournament.id,
                        form.cleaned_data["match_id"],
                    )
            else:
                messages.error(request, "Invalid input")
            return redirect(request.path)
        return redirect(request.path)
    action = request.GET.get("action")
    if action == "progress":
        if progress_bracket(tournament):
            messages.success(request, "Next round generated")
            logger.info(
                "progress success user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
        else:
            messages.warning(request, "Nothing to progress")
            logger.info(
                "progress fail user=%s tournament=%s",
                request.user.id,
                tournament.id,
            )
    if action == "export_ics_date_only":
        ics = generate_tournament_ics_date_only(tournament)
        resp = HttpResponse(ics, content_type="text/calendar")
        resp["Content-Disposition"] = f'attachment; filename="{tournament.slug}.ics"'
        return resp
    if action == "export_schedule_csv":
        csv_text = export_schedule_csv(tournament)
        resp = HttpResponse(csv_text, content_type="text/csv")
        resp["Content-Disposition"] = (
            f'attachment; filename="{tournament.slug}_oop.csv"'
        )
        return resp
    matches_by_round = {}
    scheduled = []
    for m in tournament.matches.select_related("player1", "player2", "winner").order_by(
        "id"
    ):
        matches_by_round.setdefault(m.round, []).append(m)
        try:
            data = json.loads(m.section) if m.section else None
            sched = data.get("schedule") if data else None
        except json.JSONDecodeError:  # pragma: no cover - invalid JSON
            sched = None
        if sched:
            scheduled.append((m, sched))
    matches_by_round = dict(
        sorted(
            matches_by_round.items(),
            key=lambda x: int(x[0][1:]) if x[0].startswith("R") else 0,
            reverse=True,
        )
    )
    oop = {}
    for match, sched in scheduled:
        date = sched["date"]
        session = sched["session"]
        slot = sched["slot"]
        court = sched.get("court") or ""
        oop.setdefault(date, {}).setdefault(session, {}).setdefault(
            slot, {}
        ).setdefault(court, []).append(match)
    conflicts_slots = find_conflicts_slots(tournament)
    schedule_form = ScheduleBulkSlotsForm()
    schedule_swap_form = ScheduleSwapForm()
    schedule_move_form = ScheduleMoveForm()
    return render(
        request,
        "msa/tournament_results.html",
        {
            "tournament": tournament,
            "matches_by_round": matches_by_round,
            "is_admin": _is_admin(request),
            "schedule_form": schedule_form,
            "schedule_swap_form": schedule_swap_form,
            "schedule_move_form": schedule_move_form,
            "oop_slots": oop,
            "conflicts_slots": conflicts_slots,
        },
    )


def live(request):
    """Redirect old /live/ to scores."""  # MSA-REDESIGN
    url = reverse("msa:scores") + "?tab=live"
    if request.GET.get("tour"):
        url += f"&tour={request.GET.get('tour')}"
    return redirect(url)


def rankings(request):
    if request.method == "POST":
        if not _is_admin(request):
            return HttpResponseForbidden()
        action = request.POST.get("action")
        if action == "create_snapshot":
            as_of = parse_date(request.POST.get("as_of"))
            if as_of:
                create_ranking_snapshot(as_of, user=request.user)
                messages.success(request, "Snapshot created")
                logger.info(
                    "snapshot.create user=%s as_of=%s",
                    request.user.id,
                    as_of,
                )
            else:
                messages.error(request, "Invalid date")
            return redirect(request.path)
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
    qs = filter_by_tour(qs, tour_field="tournament__category__name", tour=tour)
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
    tournaments = filter_by_tour(
        Tournament.objects.all(), tour_field="category__name", tour=tour
    )
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
    matches = filter_by_tour(
        matches, tour_field="tournament__category__name", tour=tour
    )
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
    matches = filter_by_tour(
        matches, tour_field="tournament__category__name", tour=tour
    )
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
