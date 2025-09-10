import pytest

from msa.models import EntryStatus, Snapshot, TournamentEntry
from msa.services.recalculate import brutal_reset_to_registration
from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_brutal_reset_creates_snapshot():
    cs, _, _ = make_category_season()
    t = make_tournament(cs=cs)
    TournamentEntry.objects.create(tournament=t, status=EntryStatus.ACTIVE)
    brutal_reset_to_registration(t)
    assert Snapshot.objects.filter(tournament=t, type=Snapshot.SnapshotType.BRUTAL).exists()
