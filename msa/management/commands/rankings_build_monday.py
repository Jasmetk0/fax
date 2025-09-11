from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand

from msa.models import RankingSnapshot
from msa.services.standings_snapshot import build_preview, confirm_snapshot


class Command(BaseCommand):
    help = "Build and confirm ranking snapshot for a Monday"

    def add_arguments(self, parser):
        parser.add_argument("--type", required=True, choices=RankingSnapshot.Type.values)
        parser.add_argument("--monday", required=True)
        parser.add_argument("--expected-hash", dest="expected_hash")
        parser.add_argument("--auto", action="store_true")
        parser.add_argument("--manual", action="store_true")

    def handle(self, *args, **opts):
        rtype = opts["type"]
        monday = date.fromisoformat(opts["monday"])
        preview = build_preview(rtype, monday)
        expected = opts.get("expected_hash") or preview["hash"]
        created_by = "manual" if opts.get("manual") else "auto"
        snap = confirm_snapshot(rtype, monday, expected, created_by=created_by)
        self.stdout.write(str(snap.id))
