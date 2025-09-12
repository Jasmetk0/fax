import pytest

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Player,
    Season,
    Snapshot,
    Tournament,
    TournamentEntry,
)
from msa.services.md_confirm import confirm_main_draw
from msa.services.qual_confirm import confirm_qualification
from tests.woorld_helpers import woorld_date


@pytest.mark.django_db
def test_snapshot_created_on_confirm_qualification():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, qual_rounds=2)
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="Q",
        slug="q",
        qualifiers_count=2,
    )

    # naplníme kvalifikaci (K * 2^R = 2 * 4 = 8 hráčů)
    players = [Player.objects.create(name=f"P{i}") for i in range(8)]
    for i, p in enumerate(players):
        # dáme jim licence, aby neblokovala gate
        from msa.models import PlayerLicense

        PlayerLicense.objects.create(player=p, season=s)
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.Q,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )

    confirm_qualification(t, rng_seed=7)
    snap = Snapshot.objects.filter(tournament=t, type=Snapshot.SnapshotType.CONFIRM_QUAL).first()
    assert snap is not None
    assert snap.payload and snap.payload.get("kind") == "TOURNAMENT_STATE"


@pytest.mark.django_db
def test_snapshot_created_on_confirm_main_draw():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date=woorld_date(2025, 12))
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="M", slug="m")

    players = [Player.objects.create(name=f"P{i}") for i in range(16)]
    from msa.models import PlayerLicense

    for i, p in enumerate(players):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )
        PlayerLicense.objects.create(player=p, season=s)

    confirm_main_draw(t, rng_seed=11)
    snap = Snapshot.objects.filter(tournament=t, type=Snapshot.SnapshotType.CONFIRM_MD).first()
    assert snap is not None
    assert snap.payload and snap.payload.get("kind") == "TOURNAMENT_STATE"
