import pytest

from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_tournament_kind_wc_qual():
    cs, _, _ = make_category_season()
    t = make_tournament(cs=cs)
    t.kind = "WC_QUALIFICATION"
    t.full_clean()
