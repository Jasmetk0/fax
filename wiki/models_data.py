"""Data series models for the wiki app."""

from __future__ import annotations

from django.db import models


class DataSeries(models.Model):
    """Container for numeric data points identified by a slug."""

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, db_index=True, blank=True)
    sub_category = models.CharField(max_length=100, db_index=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "data series"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title or self.slug

    def save(self, *args, **kwargs) -> None:
        """Ensure ``category`` and ``sub_category`` are derived from ``slug``."""

        if not self.category or not self.sub_category:
            from .utils_data import parse_series_slug  # local import to avoid circular

            category, sub_category, _ = parse_series_slug(self.slug)
            if not self.category:
                self.category = category
            if not self.sub_category:
                self.sub_category = sub_category
        super().save(*args, **kwargs)


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
