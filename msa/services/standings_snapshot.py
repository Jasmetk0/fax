from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import transaction

from msa.conf import (
    DEDUP_ENABLED,
    FIRST_OFFICIAL_MONDAY,
    RETENTION_FULL_WEEKS,
    SEEDING_STRICT,
)
from msa.models import RankingSnapshot, Season, Tournament
from msa.services.ranking_common import row_to_item, tiebreak_key
from msa.services.standings import rolling_standings, rtf_standings, season_standings


class StalePreviewError(Exception):
    pass


def activation_monday(dt: datetime | date, tz_name: str = "Europe/Prague") -> date:
    tz = ZoneInfo(tz_name)
    if isinstance(dt, datetime):
        dt = dt.astimezone(tz)
        d = dt.date()
    else:
        d = datetime(dt.year, dt.month, dt.day, tzinfo=tz).date()
    dow = d.weekday()
    days = (7 - dow) % 7 or 7
    return d + timedelta(days=days)


def official_monday(now: datetime | date, tz_name: str = "Europe/Prague") -> date:
    tz = ZoneInfo(tz_name)
    if isinstance(now, datetime):
        now = now.astimezone(tz)
        d = now.date()
    else:
        d = datetime(now.year, now.month, now.day, tzinfo=tz).date()
    return d - timedelta(days=d.weekday())


def _season_for_monday(monday: date) -> Season:
    season = (
        Season.objects.filter(start_date__lte=monday, end_date__gte=monday).first()
        or Season.objects.filter(end_date__lte=monday).order_by("-end_date").first()
    )
    if not season:
        raise ValidationError("No season for given monday")
    return season


def build_preview(rtype: str, monday: date) -> dict:
    monday = official_monday(monday)
    if rtype == RankingSnapshot.Type.ROLLING:
        rows = rolling_standings(monday)
    elif rtype == RankingSnapshot.Type.SEASON:
        season = _season_for_monday(monday)
        rows = season_standings(season, end_date_limit=monday)
    elif rtype == RankingSnapshot.Type.RTF:
        season = _season_for_monday(monday)
        rows = rtf_standings(season)
    else:
        raise ValidationError("Unknown ranking type")
    items = [row_to_item(r) for r in rows]
    items.sort(key=lambda rec: tiebreak_key(rtype, rec))
    payload_str = json.dumps(items, separators=(",", ":"), sort_keys=True)
    h = hashlib.sha256(payload_str.encode()).hexdigest()
    return {"items": items, "hash": h}


@transaction.atomic
def confirm_snapshot(
    rtype: str, monday: date, expected_hash: str, created_by: str = "auto"
) -> RankingSnapshot:
    monday = official_monday(monday)
    preview = build_preview(rtype, monday)
    if preview["hash"] != expected_hash:
        raise StalePreviewError("preview hash mismatch")
    hash_val = preview["hash"]
    if DEDUP_ENABLED:
        existing = (
            RankingSnapshot.objects.filter(type=rtype, hash=hash_val)
            .order_by("-monday_date")
            .first()
        )
        if existing:
            return RankingSnapshot.objects.create(
                type=rtype,
                monday_date=monday,
                hash=hash_val,
                payload=None,
                created_by=created_by,
                is_alias=True,
                alias_of=existing,
            )
    return RankingSnapshot.objects.create(
        type=rtype,
        monday_date=monday,
        hash=hash_val,
        payload=preview["items"],
        created_by=created_by,
        is_alias=False,
    )


def get_official_snapshot(rtype: str, monday: date) -> RankingSnapshot | None:
    monday = official_monday(monday)
    snap = RankingSnapshot.objects.filter(type=rtype, monday_date=monday).first()
    if not snap:
        return None
    if snap.is_alias and snap.alias_of:
        return snap.alias_of
    return snap


def retention_gc(policy: dict | None = None) -> None:
    policy = policy or {}
    keep = int(policy.get("full_weeks", RETENTION_FULL_WEEKS))
    if keep <= 0:
        return
    for rtype in RankingSnapshot.Type.values:
        snaps = RankingSnapshot.objects.filter(type=rtype).order_by("-monday_date")
        for idx, snap in enumerate(snaps):
            if idx < keep:
                continue
            if snap.is_alias:
                continue
            newer = (
                RankingSnapshot.objects.filter(
                    type=rtype, hash=snap.hash, monday_date__gt=snap.monday_date
                )
                .order_by("-monday_date")
                .first()
            )
            if newer:
                snap.is_alias = True
                snap.alias_of = newer
                snap.payload = None
                snap.save(update_fields=["is_alias", "alias_of", "payload"])


def ensure_seeding_baseline(t: Tournament) -> RankingSnapshot | None:
    if not t.start_date:
        raise ValidationError("tournament.start_date required")
    if not t.seeding_monday:
        t.seeding_monday = official_monday(t.start_date)
        t.save(update_fields=["seeding_monday"])
    snap = get_official_snapshot(RankingSnapshot.Type.ROLLING, t.seeding_monday)
    if not snap and SEEDING_STRICT and t.seeding_monday >= FIRST_OFFICIAL_MONDAY:
        raise ValidationError("Official snapshot missing")
    return snap
