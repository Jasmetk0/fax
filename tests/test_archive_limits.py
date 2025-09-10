import json

import pytest

from msa.models import Snapshot, Tournament
from msa.services.archiver import archive
from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_archive_enforces_limits_per_tournament(settings):
    settings.MSA_ARCHIVE_LIMIT_COUNT = 50
    settings.MSA_ARCHIVE_LIMIT_MB = 1
    cs, _, _ = make_category_season()
    t1 = make_tournament(cs=cs)
    t2 = Tournament.objects.create(
        name="T2",
        slug="t2",
        category_season=cs,
        start_date=t1.start_date,
        end_date=t1.end_date,
        md_best_of=5,
        q_best_of=3,
        third_place_enabled=False,
    )
    created_ids = []
    for _ in range(300):
        sid = archive(t1, type=Snapshot.SnapshotType.MANUAL, extra={"blob": "x" * 40000})
        created_ids.append(sid)
    snaps_t1 = Snapshot.objects.filter(tournament=t1).order_by("id")
    remaining_ids = list(snaps_t1.values_list("id", flat=True))
    assert remaining_ids == created_ids[-len(remaining_ids) :]
    assert len(remaining_ids) <= 50
    total = sum(len(json.dumps(s.payload).encode()) for s in snaps_t1)
    assert total <= 1 * 1024 * 1024

    for _ in range(10):
        archive(t2, type=Snapshot.SnapshotType.MANUAL, extra={"blob": "y" * 100})
    assert Snapshot.objects.filter(tournament=t2).count() == 10
