from datetime import date

import pytest
from django.core.exceptions import ValidationError

from msa.models import RankingSnapshot, Tournament
from msa.services.standings_snapshot import ensure_seeding_baseline


@pytest.mark.django_db
def test_seeding_reads_official_monday_snapshot_only():
    monday = date(2024, 5, 6)
    RankingSnapshot.objects.create(
        type=RankingSnapshot.Type.ROLLING,
        monday_date=monday,
        hash="x",
        payload=[],
    )
    t = Tournament.objects.create(start_date=date(2024, 5, 8))
    snap = ensure_seeding_baseline(t)
    assert snap.monday_date == monday


@pytest.mark.django_db
def test_ensure_seeding_baseline_sets_previous_monday_if_missing():
    monday = date(2024, 5, 6)
    RankingSnapshot.objects.create(
        type=RankingSnapshot.Type.ROLLING,
        monday_date=monday,
        hash="x",
        payload=[],
    )
    t = Tournament.objects.create(start_date=date(2024, 5, 8))
    ensure_seeding_baseline(t)
    assert t.seeding_monday == monday


@pytest.mark.django_db
def test_strict_mode_blocks_when_snapshot_missing():
    t = Tournament.objects.create(start_date=date(2025, 10, 8))
    with pytest.raises(ValidationError):
        ensure_seeding_baseline(t)
