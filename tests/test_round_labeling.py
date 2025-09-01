from msa.services.rounds import round_label


def test_round_labeling():
    assert round_label(96) == "Round of 96"
    assert round_label(8) == "Quarter Final"
