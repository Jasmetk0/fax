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
        EntryState(
            id=1,
            player_id=1,
            wr=1,
            entry_type="DA",
            seed=1,
            is_wc=False,
            promoted_by_wc=False,
            is_qwc=False,
            promoted_by_qwc=False,
            position=None,
        ),
        EntryState(
            id=2,
            player_id=2,
            wr=2,
            entry_type="DA",
            seed=2,
            is_wc=False,
            promoted_by_wc=False,
            is_qwc=False,
            promoted_by_qwc=False,
            position=None,
        ),
        EntryState(
            id=3,
            player_id=3,
            wr=3,
            entry_type="DA",
            seed=None,
            is_wc=False,
            promoted_by_wc=False,
            is_qwc=False,
            promoted_by_qwc=False,
            position=None,
        ),
        EntryState(
            id=4,
            player_id=4,
            wr=4,
            entry_type="Q",
            seed=None,
            is_wc=False,
            promoted_by_wc=False,
            is_qwc=False,
            promoted_by_qwc=False,
            position=None,
        ),
        EntryState(
            id=5,
            player_id=5,
            wr=5,
            entry_type="Q",
            seed=None,
            is_wc=False,
            promoted_by_wc=False,
            is_qwc=False,
            promoted_by_qwc=False,
            position=None,
        ),
        EntryState(
            id=6,
            player_id=6,
            wr=6,
            entry_type="ALT",
            seed=None,
            is_wc=False,
            promoted_by_wc=False,
            is_qwc=False,
            promoted_by_qwc=False,
            position=None,
        ),
    ]
    rows, _ = _proposed_layout(t, entries, SeedingSource.SNAPSHOT)
    assert rows[0].separator_after is False  # seeds interior
    assert rows[1].separator_after is True  # last seed
    assert rows[2].separator_after is True  # only DA
    assert rows[3].separator_after is False  # Q interior
    assert rows[4].separator_after is True  # last Q
    assert rows[5].separator_after is True  # only reserve
