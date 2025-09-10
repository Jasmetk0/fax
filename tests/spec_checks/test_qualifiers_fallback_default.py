import pytest

from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_qualifiers_fallback_default():
    cs, _, _ = make_category_season()
    cs.qualifiers_default = 2
    t = make_tournament(cs=cs, qualifiers_count=None)
    assert t.qualifiers_count_effective == 2
