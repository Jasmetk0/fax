from __future__ import annotations

from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework import serializers

from mma.models import Event, NewsItem, Organization, Venue

PRAGUE_TZ = ZoneInfo("Europe/Prague")


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["slug", "name", "short_name"]


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ["name", "city", "country"]


class EventListSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer()
    venue = VenueSerializer()
    date_start = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ["slug", "name", "date_start", "organization", "venue"]

    def get_date_start(self, obj: Event) -> str:
        return timezone.localtime(obj.date_start, PRAGUE_TZ).isoformat()


class EventDetailSerializer(EventListSerializer):
    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + ["is_completed"]


class NewsListSerializer(serializers.ModelSerializer):
    published_at = serializers.SerializerMethodField()

    class Meta:
        model = NewsItem
        fields = ["slug", "title", "summary", "published_at"]

    def get_published_at(self, obj: NewsItem) -> str:
        return timezone.localtime(obj.published_at, PRAGUE_TZ).isoformat()


class NewsDetailSerializer(NewsListSerializer):
    class Meta(NewsListSerializer.Meta):
        fields = NewsListSerializer.Meta.fields + ["content", "source_url"]
