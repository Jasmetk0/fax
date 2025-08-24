"""Data series models for the wiki app."""

from __future__ import annotations

from django.db import models


class DataCategory(models.Model):
    """Category used to group :class:`DataSeries`."""

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=100, blank=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title or self.slug


class DataSeries(models.Model):
    """Container for numeric data points identified by a slug."""

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    categories = models.ManyToManyField(DataCategory, related_name="series", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "data series"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title or self.slug


class DataPoint(models.Model):
    """Single numeric value within a :class:`DataSeries`."""

    series = models.ForeignKey(
        DataSeries, on_delete=models.CASCADE, related_name="points"
    )
    key = models.CharField(max_length=50)
    value = models.DecimalField(max_digits=20, decimal_places=4)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("series", "key")
        ordering = ["key"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.series}:{self.key}={self.value}"
