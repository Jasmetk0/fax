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
from msa.services.md_band_regen import regenerate_md_band
from msa.services.md_confirm import confirm_main_draw, hard_regenerate_unseeded_md
from msa.services.md_soft_regen import soft_regenerate_unseeded_md


def _prepare_confirmed_tournament() -> Tournament:
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="T", slug="t")

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

    confirm_main_draw(t, rng_seed=123)
    return t


@pytest.mark.django_db
def test_soft_regen_creates_snapshot():
    t = _prepare_confirmed_tournament()

    soft_regenerate_unseeded_md(t, rng_seed=123)

    assert Snapshot.objects.filter(tournament=t, type=Snapshot.SnapshotType.REGENERATE).exists()


@pytest.mark.django_db
def test_band_regen_creates_snapshot():
    t = _prepare_confirmed_tournament()

    regenerate_md_band(t, band="Unseeded", rng_seed=456, mode="SOFT")

    assert Snapshot.objects.filter(tournament=t, type=Snapshot.SnapshotType.REGENERATE).exists()


@pytest.mark.django_db
def test_hard_regen_unseeded_creates_snapshot():
    t = _prepare_confirmed_tournament()

    hard_regenerate_unseeded_md(t, rng_seed=789)

    assert Snapshot.objects.filter(tournament=t, type=Snapshot.SnapshotType.REGENERATE).exists()
