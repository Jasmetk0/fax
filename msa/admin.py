from django.contrib import admin

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


@admin.register(PlayerLicense)
class PlayerLicenseAdmin(admin.ModelAdmin):
    list_display = ("player", "season")
    list_filter = ("season",)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "season", "category", "state", "start_date", "end_date")
    list_filter = ("state", "season", "category")
    prepopulated_fields = {"slug": ("name",)}


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
