import pytest

from msa.services.recalculate import preview_recalculate_registration
from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_preview_contains_rng_seed():
    cs, _, _ = make_category_season()
    t = make_tournament(cs=cs)
    t.rng_seed_active = 123
    t.save(update_fields=["rng_seed_active"])
    preview = preview_recalculate_registration(t)
    assert preview.rng_seed == 123
