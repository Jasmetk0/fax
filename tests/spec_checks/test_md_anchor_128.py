from msa.services.md_embed import _seed_anchor_slots_in_order
from msa.services.seed_anchors import md_anchor_map


def test_anchor_permutation_128():
    slots = _seed_anchor_slots_in_order(128, 128)
    assert sorted(slots) == list(range(1, 129))
    assert slots[:4] == [1, 128, 65, 64]

    m16 = md_anchor_map(16)
    assert m16["3-4"] == [9, 8]
    m32 = md_anchor_map(32)
    assert m32["3-4"] == [17, 16]
    m64 = md_anchor_map(64)
    assert m64["5-8"][:2] == [16, 17]
