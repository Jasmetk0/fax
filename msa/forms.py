from django import forms

from .models import (
    MediaItem,
    Match,
    NewsPost,
    Player,
    RankingEntry,
    RankingSnapshot,
    Tournament,
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


class TournamentForm(forms.ModelForm):
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


class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        exclude = ["tournament", "created_at", "updated_at", "created_by", "updated_by"]


class RankingSnapshotForm(forms.ModelForm):
    class Meta:
        model = RankingSnapshot
        fields = ["as_of"]


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
