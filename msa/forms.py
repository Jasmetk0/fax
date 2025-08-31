from django import forms
from fax_calendar.widgets import WoorldAdminDateWidget

from .models import (
    MediaItem,
    Match,
    NewsPost,
    Player,
    RankingEntry,
    RankingSnapshot,
    Tournament,
    Season,
    Category,
    CategorySeason,
    EventEdition,
)


class WoorldDateWidgetMixin:
    """Provides WoorldAdminDateWidget for Woorld date fields."""

    @staticmethod
    def woorld_widgets(*field_names: str) -> dict[str, WoorldAdminDateWidget]:
        """Return widgets mapping for given Woorld date field names."""
        return {field: WoorldAdminDateWidget() for field in field_names}


class PlayerForm(WoorldDateWidgetMixin, forms.ModelForm):
    class Meta:
        model = Player
        fields = [
            "name",
            "slug",
            "first_name",
            "last_name",
            "nickname",
            "country",
            "birthdate",
            "handedness",
            "height",
            "weight",
            "turned_pro",
            "active",
            "bio",
            "photo_url",
            "current_rank",
            "current_points",
            "rtf_current_rank",
            "rtf_current_points",
        ]
        widgets = WoorldDateWidgetMixin.woorld_widgets("birthdate", "turned_pro")


class TournamentForm(WoorldDateWidgetMixin, forms.ModelForm):
    class Meta:
        model = Tournament
        fields = [
            "name",
            "slug",
            "category",
            "start_date",
            "end_date",
            "city",
            "country",
            "venue",
            "prize_money",
            "status",
        ]
        widgets = WoorldDateWidgetMixin.woorld_widgets("start_date", "end_date")


class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        exclude = ["tournament", "created_at", "updated_at", "created_by", "updated_by"]


class RankingSnapshotForm(WoorldDateWidgetMixin, forms.ModelForm):
    class Meta:
        model = RankingSnapshot
        fields = ["as_of"]
        widgets = WoorldDateWidgetMixin.woorld_widgets("as_of")


class RankingEntryForm(forms.ModelForm):
    class Meta:
        model = RankingEntry
        fields = ["snapshot", "player", "rank", "points"]


class NewsPostForm(forms.ModelForm):
    class Meta:
        model = NewsPost
        fields = [
            "title",
            "slug",
            "published_at",
            "author",
            "excerpt",
            "body",
            "cover_url",
            "is_published",
        ]


class MediaItemForm(forms.ModelForm):
    class Meta:
        model = MediaItem
        fields = [
            "title",
            "slug",
            "published_at",
            "video_url",
            "thumbnail_url",
            "tags",
        ]


class SeasonForm(WoorldDateWidgetMixin, forms.ModelForm):
    class Meta:
        model = Season
        fields = ["name", "code", "start_date", "end_date"]
        widgets = WoorldDateWidgetMixin.woorld_widgets("start_date", "end_date")


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]


class SeasonCategoryForm(forms.ModelForm):
    class Meta:
        model = CategorySeason
        fields = [
            "season",
            "category",
            "label",
            "points_table",
            "prize_table",
            "bracket_policy",
            "seeding_policy",
        ]


class EventEditionForm(WoorldDateWidgetMixin, forms.ModelForm):
    class Meta:
        model = EventEdition
        fields = [
            "name",
            "brand",
            "season",
            "category_season",
            "start_date",
            "end_date",
            "venue",
            "city",
            "scoring_rules",
            "best_of",
            "sanction_status",
            "points_eligible",
            "draw_template",
        ]
        widgets = WoorldDateWidgetMixin.woorld_widgets("start_date", "end_date")
