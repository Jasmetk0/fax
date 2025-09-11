import pytest

from msa.models import Tournament
from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_qualifiers_per_tournament():
    cs, _, _ = make_category_season()
    t1 = make_tournament(cs=cs, qualifiers_count=2)
    t2 = Tournament.objects.create(
        name="T2",
        slug="t2",
        category_season=cs,
        start_date=t1.start_date,
        end_date=t1.end_date,
        md_best_of=5,
        q_best_of=3,
        qualifiers_count=3,
    )
    assert t1.qualifiers_count_effective == 2
    assert t2.qualifiers_count_effective == 3
