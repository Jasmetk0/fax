import pytest

from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_scoring_snapshot_on_creation():
    cs, season, _ = make_category_season(scoring_md={"Winner": 100}, scoring_qual_win={"Q": 10})
    t = make_tournament(cs=cs)
    assert t.scoring_md == {"Winner": 100}
    assert t.scoring_qual_win == {"Q": 10}
    cs.scoring_md["Winner"] = 200
    cs.scoring_qual_win["Q"] = 20
    cs.save(update_fields=["scoring_md", "scoring_qual_win"])
    t.refresh_from_db()
    assert t.scoring_md == {"Winner": 100}
    assert t.scoring_qual_win == {"Q": 10}
