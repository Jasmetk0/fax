from msa.services.md_embed import generate_md_mapping_with_byes, pairings_round1


def _make_players(count):
    return list(range(1, count + 1))


def _assert_no_bye_matches(template, mapping):
    for a, b in pairings_round1(template):
        assert (a in mapping) or (b in mapping)


def test_embed_56_into_64():
    seeds = _make_players(16)
    unseeded = _make_players(40)
    mapping = generate_md_mapping_with_byes(
        template_size=64,
        seeds_in_order=seeds,
        unseeded_players=[s + 16 for s in unseeded],
        bye_count=8,
        rng_seed=0,
    )
    assert len(mapping) == 56
    bye_matches = [(a, b) for a, b in pairings_round1(64) if (a in mapping) ^ (b in mapping)]
    assert len(bye_matches) == 8
    _assert_no_bye_matches(64, mapping)


def test_embed_96_into_128():
    seeds = _make_players(32)
    unseeded = _make_players(64)
    mapping = generate_md_mapping_with_byes(
        template_size=128,
        seeds_in_order=seeds,
        unseeded_players=[s + 32 for s in unseeded],
        bye_count=32,
        rng_seed=0,
    )
    assert len(mapping) == 96
    bye_matches = [(a, b) for a, b in pairings_round1(128) if (a in mapping) ^ (b in mapping)]
    assert len(bye_matches) == 32
    _assert_no_bye_matches(128, mapping)
