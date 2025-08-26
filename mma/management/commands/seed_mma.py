"""Seed MMA data into the database."""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed initial MMA data"

    def handle(self, *args, **options):  # pragma: no cover - placeholder
        self.stdout.write("Seeding MMA data not yet implemented.")
