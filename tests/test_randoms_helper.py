import pytest

from msa.services.randoms import rng_from_seed_or_tournament_and_persist, seeded_shuffle
from tests.factories import make_tournament


@pytest.mark.django_db
def test_rng_from_seed_or_tournament_and_persist():
    t = make_tournament()

    rng1, used1 = rng_from_seed_or_tournament_and_persist(t, rng_seed=123)
    assert used1 == 123
    t.refresh_from_db()
    assert t.rng_seed_active == 123
    perm1 = seeded_shuffle(list(range(10)), rng1)

    rng2, used2 = rng_from_seed_or_tournament_and_persist(t, rng_seed=None)
    assert used2 == 123
    perm2 = seeded_shuffle(list(range(10)), rng2)
    assert perm2 == perm1

    rng3, used3 = rng_from_seed_or_tournament_and_persist(t, rng_seed=999)
    assert used3 == 999
    perm3 = seeded_shuffle(list(range(10)), rng3)
    assert perm3 != perm1
    t.refresh_from_db()
    assert t.rng_seed_active == 999
