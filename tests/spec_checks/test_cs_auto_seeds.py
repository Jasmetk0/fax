import pytest

from msa.models import Category, CategorySeason, Season


@pytest.mark.django_db
def test_md_seeds_auto_calc():
    c = Category.objects.create(name="C")
    s = Season.objects.create(name="S")
    cs1 = CategorySeason.objects.create(category=c, season=s, draw_size=24)
    assert cs1.md_seeds_count == 8
    cs2 = CategorySeason.objects.create(category=c, season=s, draw_size=28)
    assert cs2.md_seeds_count == 8
    cs3 = CategorySeason.objects.create(category=c, season=s, draw_size=120)
    assert cs3.md_seeds_count == 32
