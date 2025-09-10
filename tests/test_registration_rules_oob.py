import pytest

from msa.services.registration_rules import EntryView, Move, validate_reorder


def _entries():
    return [
        EntryView(id=1, section="DA", wr_snapshot=10),
        EntryView(id=2, section="DA", wr_snapshot=10),
        EntryView(id=3, section="DA", wr_snapshot=20),
    ]


@pytest.mark.parametrize("section", ["SEEDS", "DA", "Q"])
def test_validate_reorder_index_oob_and_cross_bucket(section):
    entries = _entries()
    with pytest.raises(ValueError) as ex:
        validate_reorder(section, entries, [Move(entry_id=1, new_index=5)])
    assert str(ex.value) == "move.index_oob"
    with pytest.raises(ValueError) as ex2:
        validate_reorder(section, entries, [Move(entry_id=1, new_index=2)])
    assert str(ex2.value) == "move.cross_bucket"


@pytest.mark.django_db
def test_validate_reorder_reserve_allows_any_and_checks_oob():
    entries = [
        EntryView(id=10, section="RESERVE", wr_snapshot=100),
        EntryView(id=11, section="RESERVE", wr_snapshot=None),
    ]
    validate_reorder("RESERVE", entries, [Move(entry_id=11, new_index=0)])
    with pytest.raises(ValueError) as ex:
        validate_reorder("RESERVE", entries, [Move(entry_id=10, new_index=5)])
    assert str(ex.value) == "move.index_oob"
