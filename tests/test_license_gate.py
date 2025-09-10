import pytest
from django.core.exceptions import ValidationError

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
from msa.services.licenses import grant_license_for_tournament_season
from msa.services.md_confirm import confirm_main_draw
from msa.services.qual_confirm import confirm_qualification


@pytest.mark.django_db
def test_confirm_qualification_blocks_when_any_active_player_missing_license():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, qual_rounds=2)
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T",
        slug="t",
        qualifiers_count=4,
    )

    # 16 hráčů v kvalifikaci, jednomu licenci nedáme
    players = [Player.objects.create(name=f"Q{i}") for i in range(16)]
    for i, p in enumerate(players):
        TournamentEntry.objects.create(
            tournament=t, player=p, entry_type=EntryType.Q, status=EntryStatus.ACTIVE
        )
        if i != 7:  # všem kromě Q7 dáme licenci
            PlayerLicense.objects.create(player=p, season=s)

    with pytest.raises(ValidationError):
        confirm_qualification(t, rng_seed=123)

    # Přidáme chybějící licenci a projde
    grant_license_for_tournament_season(t, players[7].id)
    branches = confirm_qualification(t, rng_seed=123)
    assert len(branches) == t.qualifiers_count


@pytest.mark.django_db
def test_confirm_main_draw_blocks_without_licenses_and_allows_after_grant():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="M", slug="m")

    # 16 entries, ale jednomu chybí licence
    players = [Player.objects.create(name=f"P{i}") for i in range(16)]
    for i, p in enumerate(players):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )
        if i != 7:  # všem kromě P7 dáme licenci
            PlayerLicense.objects.create(player=p, season=s)

    with pytest.raises(ValidationError):
        confirm_main_draw(t, rng_seed=42)

    # Dořešíme licenci P7 a confirm projde
    grant_license_for_tournament_season(t, players[7].id)
    mapping = confirm_main_draw(t, rng_seed=42)
    # sanity: mapping má mít draw_size položek
    assert len(mapping) == cs.draw_size
