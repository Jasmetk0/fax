import pytest

from msa.services.recalculate import EntryState, SeedingSource, _proposed_layout
from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_separator_after_marks_group_end():
    cs, _, _ = make_category_season(draw_size=16)
    cs.md_seeds_count = 2
    cs.save(update_fields=["md_seeds_count"])
    t = make_tournament(cs=cs)
    entries = [
        EntryState(
            id=i,
            player_id=i,
            wr=i,
            entry_type="DA",
            seed=None,
            is_wc=False,
            promoted_by_wc=False,
            is_qwc=False,
            promoted_by_qwc=False,
            position=None,
        )
        for i in range(1, 4)
    ]
    rows, _ = _proposed_layout(t, entries, SeedingSource.SNAPSHOT)
    assert rows[1].separator_after is True
    assert rows[2].separator_after is True
