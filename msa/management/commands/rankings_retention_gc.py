from __future__ import annotations

from django.core.management.base import BaseCommand

from msa.services.standings_snapshot import retention_gc


class Command(BaseCommand):
    help = "Run retention garbage collection for ranking snapshots"

    def handle(self, *args, **opts):
        retention_gc({})
