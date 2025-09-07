from django import forms

from .models import (
    Bout,
    Event,
    Fighter,
    NewsItem,
    Organization,
    Ranking,
)


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["slug", "name", "short_name"]


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "slug",
            "organization",
            "name",
            "date_start",
            "venue",
            "is_completed",
        ]


class FighterForm(forms.ModelForm):
    class Meta:
        model = Fighter
        fields = [
            "slug",
            "first_name",
            "last_name",
            "nickname",
            "country",
            "stance",
            "height_cm",
            "reach_cm",
            "birthdate",
        ]


class BoutForm(forms.ModelForm):
    class Meta:
        model = Bout
        fields = [
            "event",
            "weight_class",
            "fighter_red",
            "fighter_blue",
            "result",
            "method",
            "round",
            "time",
            "is_title_fight",
        ]


class RankingForm(forms.ModelForm):
    class Meta:
        model = Ranking
        fields = [
            "organization",
            "weight_class",
            "position",
            "fighter",
            "date_effective",
        ]


class NewsItemForm(forms.ModelForm):
    class Meta:
        model = NewsItem
        fields = [
            "slug",
            "title",
            "summary",
            "content",
            "source_url",
            "published_at",
        ]
