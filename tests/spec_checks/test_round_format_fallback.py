import pytest

from msa.models import Category, CategorySeason, Phase, RoundFormat, Season, Tournament
from msa.services.round_format import get_round_format


@pytest.mark.django_db
def test_round_format_fallback_and_override():
    s = Season.objects.create(name="S")
    c = Category.objects.create(name="C")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16)
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T",
        slug="t",
    )
    assert get_round_format(t, Phase.MD, "QF") == (t.md_best_of, True)
    RoundFormat.objects.create(
        tournament=t, phase=Phase.MD, round_name="QF", best_of=3, win_by_two=True
    )
    assert get_round_format(t, Phase.MD, "QF") == (3, True)
