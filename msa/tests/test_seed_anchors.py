import pytest
from msa.services.seed_anchors import md_anchor_map, band_sequence_for_S


@pytest.mark.parametrize("draw_size,total", [(16, 16), (32, 32), (64, 64)])
def test_anchor_counts(draw_size, total):
    m = md_anchor_map(draw_size)
    assert sum(len(v) for v in m.values()) == total
    slots = [s for v in m.values() for s in v]
    assert len(slots) == len(set(slots))
    assert min(slots) >= 1 and max(slots) <= draw_size


def test_band_sequence_for_S_ok():
    assert band_sequence_for_S(32, 8) == ["1", "2", "3-4", "5-8"]
    assert band_sequence_for_S(32, 16) == ["1", "2", "3-4", "5-8", "9-16"]
    assert band_sequence_for_S(64, 32) == ["1", "2", "3-4", "5-8", "9-16", "17-32"]


def test_band_sequence_for_S_invalid():
    with pytest.raises(ValueError):
        band_sequence_for_S(32, 12)