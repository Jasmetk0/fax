import pytest

from msa.models import Category, Tour


@pytest.mark.django_db
def test_category_order_and_kind_choices():
    t1 = Tour.objects.create(name="Tour1", rank=50)
    t2 = Tour.objects.create(name="Tour2", rank=40)
    Category.objects.create(name="A", tour=t1, rank=2)
    c2 = Category.objects.create(name="B", tour=t2, rank=1)
    Category.objects.create(name="C", tour=t1, rank=1, kind=Category.Kind.WC_QUALIFICATION)
    cats = list(Category.objects.all())
    assert cats[0] == c2  # tour rank 40 before 50
    assert Category.Kind.WC_QUALIFICATION in Category.Kind.values
