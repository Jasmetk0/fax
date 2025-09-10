import pytest
from django.conf import settings

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Player,
    PlayerLicense,
    Season,
    Tournament,
    TournamentEntry,
)
from msa.services.md_confirm import confirm_main_draw
from msa.services.md_soft_regen import soft_regenerate_unseeded_md


@pytest.mark.django_db
def test_soft_regenerate_unseeded_md_deterministic():
    settings.MSA_ADMIN_MODE = True

    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)

    players = [Player.objects.create(name=f"P{i}") for i in range(16)]
    for p in players:
        PlayerLicense.objects.create(player=p, season=s)

    def prepare_tournament(name):
        t = Tournament.objects.create(
            season=s, category=c, category_season=cs, name=name, slug=name
        )
        for i, p in enumerate(players):
            TournamentEntry.objects.create(
                tournament=t,
                player=p,
                entry_type=EntryType.DA,
                status=EntryStatus.ACTIVE,
                wr_snapshot=i + 1,
            )
        confirm_main_draw(t, rng_seed=1)
        return t

    t1 = prepare_tournament("T1")
    mapping1_ids = soft_regenerate_unseeded_md(t1, rng_seed=777)
    t1.refresh_from_db()
    assert t1.rng_seed_active == 777
    mapping1 = {
        slot: TournamentEntry.objects.get(pk=eid).player_id for slot, eid in mapping1_ids.items()
    }

    t2 = prepare_tournament("T2")
    mapping2_ids = soft_regenerate_unseeded_md(t2, rng_seed=777)
    mapping2 = {
        slot: TournamentEntry.objects.get(pk=eid).player_id for slot, eid in mapping2_ids.items()
    }

    assert mapping2 == mapping1
