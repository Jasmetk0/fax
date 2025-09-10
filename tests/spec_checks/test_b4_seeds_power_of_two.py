import pytest
from django.core.exceptions import ValidationError

from msa.models import CategorySeason


def test_md_seeds_count_power_of_two():
    cs = CategorySeason(draw_size=16, md_seeds_count=3)
    with pytest.raises(ValidationError):
        cs.full_clean()
