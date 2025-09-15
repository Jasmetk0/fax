import pytest

from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_scoring_skeleton_autofill():
    cs, _, _ = make_category_season(draw_size=32, qual_rounds=2, scoring_md={}, scoring_qual_win={})
    cs.refresh_from_db()
    assert cs.scoring_md == {"R32": 0, "R16": 0, "QF": 0, "SF": 0, "F": 0, "W": 0}
    assert cs.scoring_qual_win == {"Q-R1": 0, "Q-R2": 0, "Q-W": 0}
    t = make_tournament(cs=cs)
    assert t.scoring_md == cs.scoring_md
    assert t.scoring_qual_win == cs.scoring_qual_win
