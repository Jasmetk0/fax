"""REST API for wiki data series."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers, viewsets
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models_data import DataPoint, DataSeries
from .utils_data import get_series_by_category, get_value_for_year


class BurstAnonThrottle(AnonRateThrottle):
    rate = "100/min"


class DataPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataPoint
        fields = ["key", "value", "note"]


class DataSeriesListSerializer(serializers.ModelSerializer):
    categories = serializers.SlugRelatedField(many=True, read_only=True, slug_field="slug")

    class Meta:
        model = DataSeries
        fields = ["slug", "title", "unit", "categories"]


class DataSeriesCategorySerializer(serializers.ModelSerializer):
    value_for_year = serializers.CharField(read_only=True)

    class Meta:
        model = DataSeries
        fields = ["slug", "title", "unit", "value_for_year"]


class DataSeriesDetailSerializer(serializers.ModelSerializer):
    points = DataPointSerializer(many=True, read_only=True)
    categories = serializers.SlugRelatedField(many=True, read_only=True, slug_field="slug")

    class Meta:
        model = DataSeries
        fields = ["slug", "title", "unit", "description", "points", "categories"]


class StaffWritePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class DataSeriesViewSet(viewsets.ModelViewSet):
    queryset = DataSeries.objects.all()
    lookup_field = "slug"
    lookup_value_regex = ".+"
    permission_classes = [StaffWritePermission]
    throttle_classes = [BurstAnonThrottle]

    def get_serializer_class(self):  # pragma: no cover - simple switch
        if self.action == "retrieve":
            return DataSeriesDetailSerializer
        return DataSeriesListSerializer


class DataPointDetail(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BurstAnonThrottle]

    def get(self, request, slug: str, key: str) -> Response:
        series = get_object_or_404(DataSeries, slug=slug)
        point = get_object_or_404(DataPoint, series=series, key=key)
        return Response({"key": point.key, "value": str(point.value), "unit": series.unit})


class DataSeriesByCategory(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BurstAnonThrottle]
    serializer_class = DataSeriesCategorySerializer

    def get_queryset(self):  # pragma: no cover - simple access
        category = self.kwargs["category"]
        return get_series_by_category(category)

    def get(self, request, *args, **kwargs) -> Response:
        year = request.GET.get("year")
        ordering = request.GET.get("ordering", "slug")
        limit = request.GET.get("limit")
        qs = list(self.get_queryset())
        data_list = []
        by_slug = {}
        for s in qs:
            value = get_value_for_year(s, year) if year else None
            item = {
                "slug": s.slug,
                "title": s.title,
                "unit": s.unit,
                "value_for_year": str(value) if value is not None else None,
                "_sort_value": value,
            }
            if value is not None:
                by_slug[s.slug] = str(value)
            data_list.append(item)
        reverse = False
        if ordering.startswith("-"):
            reverse = True
            ordering = ordering[1:]
        if ordering == "value_for_year":
            data_list.sort(
                key=lambda d: (d["_sort_value"] is None, d["_sort_value"]),
                reverse=reverse,
            )
        else:
            data_list.sort(key=lambda d: d.get(ordering) or "", reverse=reverse)
        if limit:
            data_list = data_list[: int(limit)]
        for item in data_list:
            item.pop("_sort_value", None)
        return Response({"results": data_list, "by_slug": by_slug})
