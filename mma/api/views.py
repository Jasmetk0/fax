from __future__ import annotations

from zoneinfo import ZoneInfo

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import generics

from mma.models import Event, NewsItem

from .serializers import (
    EventDetailSerializer,
    EventListSerializer,
    NewsDetailSerializer,
    NewsListSerializer,
)

PRAGUE_TZ = ZoneInfo("Europe/Prague")


class EventList(generics.ListAPIView):
    serializer_class = EventListSerializer

    def get_queryset(self):
        qs = Event.objects.select_related("organization", "venue").order_by(
            "date_start"
        )
        upcoming = self.request.GET.get("upcoming")
        now = timezone.now()
        if upcoming in {"1", "true", "True"}:
            qs = qs.filter(date_start__gte=now)
        elif upcoming in {"0", "false", "False"}:
            qs = qs.filter(date_start__lt=now)
        org = self.request.GET.get("org")
        if org:
            qs = qs.filter(organization__slug=org)
        from_param = self.request.GET.get("from")
        if from_param:
            dt = parse_datetime(from_param)
            if dt is not None:
                qs = qs.filter(date_start__gte=dt)
        to_param = self.request.GET.get("to")
        if to_param:
            dt = parse_datetime(to_param)
            if dt is not None:
                qs = qs.filter(date_start__lte=dt)
        limit = self.request.GET.get("limit")
        if limit:
            try:
                qs = qs[: int(limit)]
            except ValueError:
                pass
        return qs


class EventDetail(generics.RetrieveAPIView):
    queryset = Event.objects.select_related("organization", "venue")
    serializer_class = EventDetailSerializer
    lookup_field = "slug"


class NewsList(generics.ListAPIView):
    serializer_class = NewsListSerializer

    def get_queryset(self):
        qs = NewsItem.objects.order_by("-published_at")
        limit = self.request.GET.get("limit")
        if limit:
            try:
                qs = qs[: int(limit)]
            except ValueError:
                pass
        return qs


class NewsDetail(generics.RetrieveAPIView):
    queryset = NewsItem.objects.all()
    serializer_class = NewsDetailSerializer
    lookup_field = "slug"
