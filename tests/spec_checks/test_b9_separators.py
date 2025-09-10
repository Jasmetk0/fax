import pytest

from msa.services.recalculate import EntryState, SeedingSource, _proposed_layout
from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_separator_after_marks_group_end():
    cs, _, _ = make_category_season(draw_size=4, qualifiers_count=1, qual_rounds=1)
    cs.md_seeds_count = 2
    cs.save(update_fields=["md_seeds_count"])
    t = make_tournament(cs=cs)
    entries = [
        EntryState(1, 1, 1, "DA", 1, False, False, False, False, None),
        EntryState(2, 2, 2, "DA", 2, False, False, False, False, None),
        EntryState(3, 3, 3, "DA", None, False, False, False, False, None),
        EntryState(4, 4, 4, "Q", None, False, False, False, False, None),
        EntryState(5, 5, 5, "Q", None, False, False, False, False, None),
        EntryState(6, 6, 6, "ALT", None, False, False, False, False, None),
    ]
    rows, _ = _proposed_layout(t, entries, SeedingSource.SNAPSHOT)
    assert rows[0].separator_after is False  # seeds interior
    assert rows[1].separator_after is True  # last seed
    assert rows[2].separator_after is True  # only DA
    assert rows[3].separator_after is False  # Q interior
    assert rows[4].separator_after is True  # last Q
    assert rows[5].separator_after is True  # only reserve
