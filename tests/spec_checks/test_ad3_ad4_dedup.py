import pytest

from msa.models import Country, Player
from msa.services.player_dedup import quick_add


@pytest.mark.django_db
def test_quick_add_warns_on_similarity():
    usa = Country.objects.create(iso3="USA")
    Country.objects.create(iso3="CAN")
    Player.objects.create(name="John Doe", country=usa)
    warn = quick_add("Jon Doe", "USA")
    assert warn and "John Doe" in warn
    assert quick_add("John Doe", "CAN") is None
