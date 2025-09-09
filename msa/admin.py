import random

from django.contrib import admin, messages
from django.utils.html import format_html

from .models import (
    Category,
    CategorySeason,
    Match,
    Player,
    PlayerLicense,
    RankingAdjustment,
    Schedule,
    Season,
    Snapshot,
    Tournament,
    TournamentEntry,
)
from .services.audit_badges import audit_badges_for_tournament
from .services.player_dedup import merge_players


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "best_n")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(CategorySeason)
class CategorySeasonAdmin(admin.ModelAdmin):
    list_display = ("category", "season", "draw_size", "md_seeds_count", "qualifiers_count")
    list_filter = ("category", "season")


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "country")

    @admin.action(description="Merge selected players into the first")
    def merge_selected_into_first(self, request, queryset):
        ids = list(queryset.order_by("id").values_list("id", flat=True))
        if len(ids) < 2:
            messages.warning(request, "Select at least two players to merge.")
            return
        master_id = ids[0]
        summary = {"updated": {}, "licenses": 0, "adjustments": 0}
        for dup_id in ids[1:]:
            try:
                result = merge_players(master_id, dup_id)
            except Exception as e:  # pragma: no cover - admin feedback
                messages.error(request, f"Merge {dup_id} failed: {e!r}")
                continue
            for k, v in result.get("updated", {}).items():
                summary["updated"][k] = summary["updated"].get(k, 0) + v
            summary["licenses"] += result.get("licenses_merged", 0)
            summary["adjustments"] += result.get("adjustments_merged", 0)
        msg = (
            f"Merged into {master_id}. Updated: {summary['updated']}, "
            f"licenses merged: {summary['licenses']}, adjustments merged: {summary['adjustments']}. "
            "This action cannot be undone."
        )
        messages.success(request, msg)

    actions = ["merge_selected_into_first"]


@admin.register(PlayerLicense)
class PlayerLicenseAdmin(admin.ModelAdmin):
    list_display = ("player", "season")
    list_filter = ("season",)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "season",
        "category",
        "state",
        "start_date",
        "end_date",
        "seeding_badge",
        "snapshot_badge",
    )
    list_filter = ("state", "season", "category")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("seeding_badge", "snapshot_badge")

    @staticmethod
    def _render_badge(badge: dict) -> str:
        color_map = {"ok": "#5cb85c", "warn": "#f0ad4e", "unknown": "#777"}
        color = color_map.get(badge.get("status"), "#777")
        return format_html(
            '<span style="border-radius:3px;padding:2px 4px;color:#fff;background:{};">{}</span>',
            color,
            badge.get("label", ""),
        )

    @admin.display(description="Seeding")
    def seeding_badge(self, obj):
        badges = audit_badges_for_tournament(obj)
        return self._render_badge(badges["seeding"])

    @admin.display(description="Snapshot")
    def snapshot_badge(self, obj):
        badges = audit_badges_for_tournament(obj)
        return self._render_badge(badges["snapshot"])

    def rng_seed_active_display(self, obj):
        seed = getattr(obj, "rng_seed_active", 0) or 0
        onclick = (
            f"navigator.clipboard.writeText('{seed}');"
            "this.textContent='Copied';"
            "setTimeout(()=>this.textContent='Copy',1000);"
            "return false;"
        )
        return format_html(
            '<code id="rng-seed">{}</code> '
            '<button type="button" class="button" onclick="{}">Copy</button>',
            seed,
            onclick,
        )

    rng_seed_active_display.short_description = "RNG seed (copy)"
    rng_seed_active_display.admin_order_field = "rng_seed_active"

    @admin.action(description="Preview RNG diff")
    def preview_rng_diff(self, request, queryset):
        for t in queryset:
            try:
                from .services.recalculate import preview_recalculate_registration

                preview = preview_recalculate_registration(t)
                summary = str(preview)
                lines = summary.splitlines()
                count = len(lines) if lines else len(summary)
                if len(lines) > 5:
                    summary = "\n".join(lines[:5]) + "\n…"
                messages.info(
                    request,
                    f"[{getattr(t, 'slug', t.pk)}] {count} change(s):\n{summary}",
                )
            except Exception as e:
                messages.error(request, f"[{getattr(t, 'slug', t.pk)}] Preview failed: {e!r}")

    @admin.action(description="Regenerate RNG seed")
    def regenerate_rng_seed(self, request, queryset):
        for t in queryset:
            try:
                t.rng_seed_active = random.getrandbits(63)
                t.save(update_fields=["rng_seed_active"])
                messages.success(
                    request,
                    f"[{getattr(t, 'slug', t.pk)}] RNG seed set to {t.rng_seed_active}",
                )
            except Exception as e:
                messages.error(request, f"[{getattr(t, 'slug', t.pk)}] Seed failed: {e!r}")

    @admin.action(description="Apply preview changes")
    def apply_preview_changes(self, request, queryset):
        for t in queryset:
            try:
                from .services.recalculate import confirm_recalculate_registration

                confirm_recalculate_registration(t)
                messages.success(request, f"[{getattr(t, 'slug', t.pk)}] Preview applied")
            except Exception as e:
                messages.error(request, f"[{getattr(t, 'slug', t.pk)}] Apply failed: {e!r}")

    actions = [
        "preview_rng_diff",
        "regenerate_rng_seed",
        "apply_preview_changes",
    ]


# --- append fields safely (after the class definition) ---
try:
    # readonly_fields
    ro = tuple(getattr(TournamentAdmin, "readonly_fields", ()))
    if "rng_seed_active" not in ro:
        TournamentAdmin.readonly_fields = ro + ("rng_seed_active",)

    # list_display
    ld = tuple(getattr(TournamentAdmin, "list_display", ()))
    if "rng_seed_active_display" not in ld:
        TournamentAdmin.list_display = ld + ("rng_seed_active_display",)
except Exception:
    pass


@admin.register(TournamentEntry)
class TournamentEntryAdmin(admin.ModelAdmin):
    list_display = (
        "tournament",
        "player",
        "entry_type",
        "seed",
        "wr_snapshot",
        "status",
        "position",
    )
    list_filter = ("tournament", "entry_type", "status")
    search_fields = ("player__name",)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "tournament",
        "phase",
        "round_name",
        "slot_top",
        "slot_bottom",
        "state",
        "needs_review",
    )
    list_filter = ("tournament", "phase", "round_name", "state", "needs_review")


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("tournament", "play_date", "order", "match")
    list_filter = ("tournament", "play_date")


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ("tournament", "type", "created_at")
    list_filter = ("tournament", "type")


@admin.register(RankingAdjustment)
class RankingAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        "player",
        "scope",
        "points_delta",
        "start_monday",
        "duration_weeks",
        "best_n_penalty",
    )
    list_filter = ("scope",)
