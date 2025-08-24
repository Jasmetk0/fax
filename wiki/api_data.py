"""REST API for wiki data series."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers, viewsets
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models_data import DataPoint, DataSeries


class BurstAnonThrottle(AnonRateThrottle):
    rate = "100/min"


class DataPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataPoint
        fields = ["key", "value", "note"]


class DataSeriesListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSeries
        fields = ["slug", "title", "unit"]


class DataSeriesDetailSerializer(serializers.ModelSerializer):
    points = DataPointSerializer(many=True, read_only=True)

    class Meta:
        model = DataSeries
        fields = ["slug", "title", "unit", "description", "points"]


class StaffWritePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class DataSeriesViewSet(viewsets.ModelViewSet):
    queryset = DataSeries.objects.all()
    lookup_field = "slug"
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
        return Response(
            {"key": point.key, "value": str(point.value), "unit": series.unit}
        )
