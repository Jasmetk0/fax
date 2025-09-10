import pytest

from msa.models import Player
from msa.services.player_dedup import quick_add


@pytest.mark.django_db
def test_quick_add_warns_on_similarity():
    Player.objects.create(name="John Doe", country="USA")
    warn = quick_add("Jon Doe", "USA")
    assert warn and "John Doe" in warn
    assert quick_add("John Doe", "CAN") is None
