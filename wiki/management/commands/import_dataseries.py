"""Management command to import data series from CSV."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from ...models_data import DataSeries
from ...utils_data import import_csv_to_series


class Command(BaseCommand):
    help = "Import CSV data into a DataSeries"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--slug", required=True)
        parser.add_argument("--unit", default="")
        parser.add_argument("--title", default="")
        parser.add_argument("--file", type=Path, required=True)

    def handle(self, *args, **options):
        slug: str = options["slug"]
        unit: str = options["unit"]
        title: str = options["title"]
        file_path: Path = options["file"]

        series, _ = DataSeries.objects.get_or_create(slug=slug)
        if title:
            series.title = title
        if unit:
            series.unit = unit
        series.save()

        with file_path.open("r", encoding="utf-8") as fh:
            created, updated = import_csv_to_series(series, fh)
        self.stdout.write(self.style.SUCCESS(f"Imported {created} created, {updated} updated"))
