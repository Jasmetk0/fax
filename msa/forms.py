from django import forms
from fax_calendar.widgets import WoorldAdminDateWidget

from .models import (
    MediaItem,
    Match,
    NewsPost,
    Player,
    TournamentEntry,
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
            "draw_size",
            "seeds_count",
            "qualifiers_count",
            "lucky_losers",
            "seeding_method",
            "seeding_rank_date",
            "entry_deadline",
            "allow_manual_bracket_edits",
            "flex_mode",
            "draw_policy",
        ]
        widgets = {
            "start_date": WoorldAdminDateWidget(),
            "end_date": WoorldAdminDateWidget(),
            "seeding_rank_date": WoorldAdminDateWidget(),
            "entry_deadline": WoorldAdminDateWidget(),
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


class EntryAddForm(forms.Form):
    player = forms.ModelChoiceField(queryset=Player.objects.all())
    entry_type = forms.ChoiceField(
        choices=TournamentEntry.EntryType.choices,
        initial=TournamentEntry.EntryType.DA,
    )


class EntryBulkForm(forms.Form):
    rows = forms.CharField(
        widget=forms.Textarea,
        help_text="CSV format: player_id[,entry_type]",
    )


class ScheduleBulkSlotsForm(forms.Form):
    rows = forms.CharField(
        widget=forms.Textarea,
        help_text="CSV: match_id,YYYY-MM-DD,SESSION,slot[,court]",
    )


class EntryUpdateTypeForm(forms.Form):
    entry_id = forms.IntegerField(widget=forms.HiddenInput())
    entry_type = forms.ChoiceField(choices=TournamentEntry.EntryType.choices)


class SeedUpdateForm(forms.Form):
    entry_id = forms.IntegerField(widget=forms.HiddenInput())
    seed = forms.IntegerField(required=False, min_value=1)


class SeedsBulkForm(forms.Form):
    rows = forms.CharField(
        widget=forms.Textarea,
        help_text="CSV format: entry_id,seed",
    )
