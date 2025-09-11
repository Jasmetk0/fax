from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand

from msa.models import RankingSnapshot
from msa.services.standings_snapshot import build_preview, confirm_snapshot


def weekly_snapshot_dates(d_from: date, d_to: date):
    d = d_from
    while d <= d_to:
        yield d
        d += timedelta(weeks=1)


class Command(BaseCommand):
    help = "Build snapshots for a range of Mondays"

    def add_arguments(self, parser):
        parser.add_argument("--type", required=True, choices=RankingSnapshot.Type.values)
        parser.add_argument("--from", dest="from_date", required=True)
        parser.add_argument("--to", dest="to_date", required=True)

    def handle(self, *args, **opts):
        rtype = opts["type"]
        d_from = date.fromisoformat(opts["from_date"])
        d_to = date.fromisoformat(opts["to_date"])
        for m in weekly_snapshot_dates(d_from, d_to):
            preview = build_preview(rtype, m)
            confirm_snapshot(rtype, m, preview["hash"], created_by="auto")
