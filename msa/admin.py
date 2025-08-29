from urllib.parse import urlparse

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AdvancementEdge,
    Category,
    CategorySeason,
    BracketPolicy,
    DrawTemplate,
    EventBrand,
    EventEdition,
    EventEntry,
    EventMatch,
    EventPhase,
    PhaseRound,
    PointsTable,
    PointsRow,
    PrizeTable,
    PrizeRow,
    ScoringRule,
    SeedingPolicy,
    MediaItem,
    Match,
    NewsPost,
    Player,
    Season,
    RankingEntry,
    RankingSnapshot,
    Tournament,
)

from .services.draw_engine import expand_template


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "nickname",
        "country",
        "active",
        "current_rank",
        "current_points",
        "rtf_current_rank",
        "rtf_current_points",
    )
    search_fields = ("name", "first_name", "last_name", "nickname", "country")
    list_filter = ("country", "active", "handedness")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = (
        "photo_preview",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    def photo_preview(self, obj):  # pragma: no cover - small utility
        if obj.photo_url:
            return format_html('<img src="{}" style="height:50px;"/>', obj.photo_url)
        return ""


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "start_date", "end_date")
    search_fields = ("name", "code")
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
    search_fields = ("as_of",)  # 👈 přidej tenhle řádek
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


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(CategorySeason)
class CategorySeasonAdmin(admin.ModelAdmin):
    list_display = ("season", "category", "label")
    list_filter = ("season", "category")
    search_fields = ("label", "season__name", "category__name")
    autocomplete_fields = (
        "season",
        "category",
        "points_table",
        "prize_table",
        "bracket_policy",
        "seeding_policy",
    )
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


class PointsRowInline(admin.TabularInline):
    model = PointsRow
    extra = 0


@admin.register(PointsTable)
class PointsTableAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [PointsRowInline]


class PrizeRowInline(admin.TabularInline):
    model = PrizeRow
    extra = 0


@admin.register(PrizeTable)
class PrizeTableAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [PrizeRowInline]


@admin.register(BracketPolicy)
class BracketPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "draw_size", "format")
    search_fields = ("name",)


@admin.register(SeedingPolicy)
class SeedingPolicyAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(ScoringRule)
class ScoringRuleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(DrawTemplate)
class DrawTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "version")
    search_fields = ("code", "name")


@admin.register(EventBrand)
class EventBrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.action(description="Expandovat z šablony")
def expand_from_template(modeladmin, request, queryset):
    for event in queryset:
        expand_template(event.pk)


@admin.register(EventEdition)
class EventEditionAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "season")
    actions = [expand_from_template]
    autocomplete_fields = ("brand", "season", "draw_template", "uses_snapshot")
    search_fields = ("name", "brand__name", "season__name")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


class PhaseRoundInline(admin.TabularInline):
    model = PhaseRound
    extra = 0
    readonly_fields = ("order",)


class EventMatchInline(admin.TabularInline):
    model = EventMatch
    fk_name = "phase"
    extra = 0
    fields = ("round", "order", "a_player", "b_player", "a_score", "b_score", "winner")
    autocomplete_fields = ("round", "a_player", "b_player", "winner")


@admin.register(EventPhase)
class EventPhaseAdmin(admin.ModelAdmin):
    list_display = ("event", "order", "type", "name")
    inlines = [PhaseRoundInline, EventMatchInline]
    autocomplete_fields = (
        "event",
        "points_table",
        "scoring_rules",
        "seeding_policy",
        "uses_snapshot",
    )
    search_fields = ("name", "event__name")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(PhaseRound)
class PhaseRoundAdmin(admin.ModelAdmin):
    list_display = ("phase", "order", "code", "label")
    autocomplete_fields = ("phase",)
    search_fields = ("code", "label")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(EventMatch)
class EventMatchAdmin(admin.ModelAdmin):
    list_display = ("phase", "round", "order", "a_player", "b_player", "winner")
    autocomplete_fields = ("phase", "round", "a_player", "b_player", "winner")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(AdvancementEdge)
class AdvancementEdgeAdmin(admin.ModelAdmin):
    list_display = ("phase", "from_ref", "to_ref")
    autocomplete_fields = ("phase",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(EventEntry)
class EventEntryAdmin(admin.ModelAdmin):
    list_display = ("event", "player", "entry_type", "seed_no")
    list_filter = ("entry_type",)
    autocomplete_fields = ("event", "player")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
