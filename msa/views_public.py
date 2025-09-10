from __future__ import annotations

from datetime import date

from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView, TemplateView

from .models import Match, Player, Schedule, Season, Tournament, TournamentEntry
from .services import md_embed, qual_generator, recalculate, standings
from .services.md_embed import pairings_round1


class TournamentListView(ListView):
    model = Tournament
    template_name = "msa/tournament_list.html"
    context_object_name = "tournaments"


class TournamentDetailView(DetailView):
    model = Tournament
    slug_field = "slug"
    template_name = "msa/tournament_detail.html"
    context_object_name = "t"


class RegistrationView(TemplateView):
    template_name = "msa/partials/registration.html"

    def get_context_data(self, slug: str, **kwargs):
        t = get_object_or_404(Tournament, slug=slug)
        preview = recalculate.preview_recalculate_registration(t)
        entry_ids = [r.entry_id for r in preview.proposed]
        entries = {
            e.id: e
            for e in TournamentEntry.objects.filter(id__in=entry_ids).select_related("player")
        }
        rows = [(r, entries.get(r.entry_id)) for r in preview.proposed]
        return {"rows": rows}


class QualificationView(TemplateView):
    template_name = "msa/partials/qualification.html"

    def get_context_data(self, slug: str, **kwargs):
        t = get_object_or_404(Tournament, slug=slug)
        cs = t.category_season
        branches: list[list[str]] = []
        try:
            K = t.qualifiers_count_effective
            R = cs.qual_rounds if cs else None
            if K and R:
                seeds = list(
                    TournamentEntry.objects.filter(tournament=t, entry_type="Q", seed__isnull=False)
                    .order_by("seed")
                    .values_list("id", flat=True)
                )
                unseeded = list(
                    TournamentEntry.objects.filter(
                        tournament=t, entry_type="Q", seed__isnull=True
                    ).values_list("id", flat=True)
                )
                mapping = qual_generator.generate_qualification_mapping(
                    K, R, seeds, unseeded, rng_seed=t.rng_seed_active
                )
                players = {
                    e.id: e.player.name
                    for e in TournamentEntry.objects.filter(
                        id__in=[pid for b in mapping for pid in b.values()]
                    ).select_related("player")
                }
                branches = [[players[pid] for slot, pid in sorted(br.items())] for br in mapping]
        except Exception:  # pragma: no cover - graceful fallback
            branches = []
        return {"branches": branches}


class MainDrawView(TemplateView):
    template_name = "msa/partials/main_draw.html"

    def get_context_data(self, slug: str, **kwargs):
        t = get_object_or_404(Tournament, slug=slug)
        cs = t.category_season
        matches: list[tuple[str, str]] = []
        try:
            template_size = 1
            while template_size < cs.draw_size:
                template_size *= 2
            seeds = list(
                TournamentEntry.objects.filter(tournament=t, seed__isnull=False)
                .order_by("seed")
                .values_list("id", flat=True)
            )
            unseeded = list(
                TournamentEntry.objects.filter(tournament=t, seed__isnull=True, entry_type="DA")
                .order_by("position")
                .values_list("id", flat=True)
            )
            bye_count = template_size - cs.draw_size
            mapping = md_embed.generate_md_mapping_with_byes(
                template_size=template_size,
                seeds_in_order=seeds,
                unseeded_players=unseeded,
                bye_count=bye_count,
                rng_seed=t.rng_seed_active,
            )
            pairings = pairings_round1(template_size)
            players = {
                e.id: e.player.name
                for e in TournamentEntry.objects.filter(id__in=mapping.values()).select_related(
                    "player"
                )
            }
            for a, b in pairings:
                eid_a = mapping.get(a)
                eid_b = mapping.get(b)
                if eid_a and eid_b:
                    matches.append((players.get(eid_a, "?"), players.get(eid_b, "?")))
        except Exception:  # pragma: no cover
            matches = []
        return {"matches": matches}


class ScheduleView(TemplateView):
    template_name = "msa/partials/schedule.html"

    def get_context_data(self, slug: str, **kwargs):
        t = get_object_or_404(Tournament, slug=slug)
        schedule = (
            Schedule.objects.filter(tournament=t)
            .select_related("match")
            .order_by("play_date", "order")
        )
        return {"schedule": schedule}


class ResultsView(TemplateView):
    template_name = "msa/partials/results.html"

    def get_context_data(self, slug: str, **kwargs):
        t = get_object_or_404(Tournament, slug=slug)
        matches = (
            Match.objects.filter(tournament=t)
            .select_related("player_top", "player_bottom")
            .order_by("id")
        )
        return {"matches": matches}


class SeasonStandingsView(TemplateView):
    template_name = "msa/standings/season.html"

    def get_context_data(self, season_id: int, **kwargs):
        season = get_object_or_404(Season, pk=season_id)
        rows = standings.season_standings(season)
        players = {p.id: p.name for p in Player.objects.filter(id__in=[r.player_id for r in rows])}
        rows_named = [(r, players.get(r.player_id, str(r.player_id))) for r in rows]
        return {"rows": rows_named, "season": season}


class RollingStandingsView(TemplateView):
    template_name = "msa/standings/rolling.html"

    def get_context_data(self, **kwargs):
        snap = date.today()
        rows = standings.rolling_standings(snap)
        players = {p.id: p.name for p in Player.objects.filter(id__in=[r.player_id for r in rows])}
        rows_named = [(r, players.get(r.player_id, str(r.player_id))) for r in rows]
        return {"rows": rows_named, "snap": snap}


class RtFStandingsView(TemplateView):
    template_name = "msa/standings/rtf.html"

    def get_context_data(self, **kwargs):
        season = Season.objects.order_by("-start_date").first()
        rows = standings.rtf_standings(season) if season else []
        players = {p.id: p.name for p in Player.objects.filter(id__in=[r.player_id for r in rows])}
        rows_named = [(r, players.get(r.player_id, str(r.player_id))) for r in rows]
        return {"rows": rows_named, "season": season}
