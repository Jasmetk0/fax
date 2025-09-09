import pytest

from msa.services.registration_rules import EntryView, Move, validate_reorder


def _mk(section, wrs):
    # helper to create entries with sequential ids and given wr snapshots (None = NR)
    return [EntryView(id=i, section=section, wr_snapshot=wr) for i, wr in enumerate(wrs, start=1)]


def test_da_within_tie_bucket_ok():
    entries = _mk("DA", [10, 10, 12, 13])
    # swap two 10s (same bucket) -> OK
    validate_reorder("DA", entries, [Move(entry_id=1, new_index=1), Move(entry_id=2, new_index=0)])


def test_da_cross_bucket_forbidden():
    entries = _mk("DA", [10, 10, 12, 13])
    # moving id=1 (wr=10) into 12-bucket -> forbidden
    with pytest.raises(ValueError):
        validate_reorder("DA", entries, [Move(entry_id=1, new_index=2)])


def test_seeds_tie_only_ok():
    entries = _mk("SEEDS", [1, 1, 2, 2])
    # move inside second tie bucket bounds -> OK (new_index=3 for id=3)
    validate_reorder("SEEDS", entries, [Move(entry_id=3, new_index=3)])


def test_reserve_is_free_block():
    entries = _mk("RESERVE", [None, None, None, None])
    # any internal reorder is allowed
    validate_reorder(
        "RESERVE", entries, [Move(entry_id=1, new_index=3), Move(entry_id=4, new_index=0)]
    )


def test_cross_section_guard():
    entries = _mk("Q", [20, 21, 21])
    # reference id not in this section list -> error
    with pytest.raises(ValueError):
        validate_reorder("Q", entries, [Move(entry_id=999, new_index=0)])
