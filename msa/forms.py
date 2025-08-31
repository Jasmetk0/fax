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


class PlayerForm(forms.ModelForm):
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
        widgets = {
            "birthdate": WoorldAdminDateWidget(),
            "turned_pro": WoorldAdminDateWidget(),
        }


class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = [
            "name",
            "slug",
            "season",
            "category",
            "season_category",
            "start_date",
            "end_date",
            "city",
            "country",
            "venue",
            "prize_money",
            "status",
        ]
        widgets = {
            "start_date": WoorldAdminDateWidget(),
            "end_date": WoorldAdminDateWidget(),
        }


class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        exclude = ["tournament", "created_at", "updated_at", "created_by", "updated_by"]


class RankingSnapshotForm(forms.ModelForm):
    class Meta:
        model = RankingSnapshot
        fields = ["as_of"]
        widgets = {"as_of": WoorldAdminDateWidget()}


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


class SeasonForm(forms.ModelForm):
    class Meta:
        model = Season
        fields = ["name", "code", "start_date", "end_date"]
        widgets = {
            "start_date": WoorldAdminDateWidget(),
            "end_date": WoorldAdminDateWidget(),
        }


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


class EventEditionForm(forms.ModelForm):
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
        widgets = {
            "start_date": WoorldAdminDateWidget(),
            "end_date": WoorldAdminDateWidget(),
        }
