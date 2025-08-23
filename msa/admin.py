from urllib.parse import urlparse
from django.contrib import admin

from .models import (
    MediaItem,
    Match,
    NewsPost,
    Player,
    RankingEntry,
    RankingSnapshot,
    Tournament,
)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "active")
    search_fields = ("name", "country")
    list_filter = ("country", "active")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "start_date", "city", "country", "status")
    list_filter = ("status", "category", "country", "start_date")
    search_fields = ("name", "city", "country")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "tournament",
        "round",
        "player1",
        "player2",
        "winner",
        "live_status",
        "scheduled_at",
    )
    list_filter = ("tournament", "round", "live_status")
    search_fields = ("player1__name", "player2__name", "tournament__name")
    autocomplete_fields = ("tournament", "player1", "player2", "winner")
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )


class RankingEntryInline(admin.TabularInline):
    model = RankingEntry
    extra = 0
    autocomplete_fields = ("player",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )


@admin.register(RankingSnapshot)
class RankingSnapshotAdmin(admin.ModelAdmin):
    list_display = ("as_of", "items_count")
    inlines = [RankingEntryInline]
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    def items_count(self, obj):
        return obj.entries.count()


@admin.register(RankingEntry)
class RankingEntryAdmin(admin.ModelAdmin):
    list_display = ("snapshot", "player", "rank", "points")
    list_filter = ("snapshot",)
    search_fields = ("player__name",)
    autocomplete_fields = ("snapshot", "player")
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )


@admin.register(NewsPost)
class NewsPostAdmin(admin.ModelAdmin):
    list_display = ("title", "published_at", "is_published")
    list_filter = ("is_published", "published_at")
    search_fields = ("title", "excerpt", "body")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = ("title", "published_at", "video_host")
    search_fields = ("title", "video_url", "tags")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    def video_host(self, obj):
        return urlparse(obj.video_url).netloc

    video_host.short_description = "Video host"
