import pytest
from django.core.exceptions import ValidationError

from msa.models import Country, Player


@pytest.mark.django_db
def test_player_country_fk_and_name_validation():
    c = Country.objects.create(iso3="CZE")
    p = Player(country=c)
    with pytest.raises(ValidationError):
        p.full_clean()
    p.full_name = "Karel Novak"
    p.full_clean()
    p.save()
    assert p.country == c
