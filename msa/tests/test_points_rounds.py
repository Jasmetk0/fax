import pytest

from msa.models import Tournament
from msa.utils.rounds import round_labels_from_md_size
from tests.factories import make_category_season, make_tournament


@pytest.mark.parametrize(
    "md_size, expected",
    [
        (32, ["R32", "R16", "QF", "SF", "F", "W"]),
        (8, ["QF", "SF", "F", "W"]),
        (4, ["SF", "F", "W"]),
        (2, ["F", "W"]),
    ],
)
def test_round_labels_no_third_place(md_size, expected):
    assert round_labels_from_md_size(md_size, third_place=False) == expected


@pytest.mark.parametrize(
    "md_size, expected",
    [
        (32, ["R32", "R16", "QF", "4th", "3rd", "F", "W"]),
        (8, ["QF", "4th", "3rd", "F", "W"]),
        (4, ["4th", "3rd", "F", "W"]),
        (2, ["F", "W"]),
    ],
)
def test_round_labels_with_third_place(md_size, expected):
    assert round_labels_from_md_size(md_size, third_place=True) == expected


@pytest.mark.django_db
def test_scoring_skeleton_third_place_wired():
    cs, _, _ = make_category_season(
        draw_size=32, third_place=True, scoring_md={}, scoring_qual_win={}
    )
    t = make_tournament(cs=cs)
    assert list(t.scoring_md.keys()) == ["R32", "R16", "QF", "4th", "3rd", "F", "W"]


@pytest.mark.django_db
def test_qual_skeleton_includes_qw():
    cs, _, _ = make_category_season(draw_size=32, qual_rounds=3, scoring_md={}, scoring_qual_win={})
    t = make_tournament(cs=cs)
    assert list(t.scoring_qual_win.keys()) == ["Q-R1", "Q-R2", "Q-R3", "Q-W"]


@pytest.mark.django_db
@pytest.mark.parametrize("md_size", [128, 96, 64, 48, 32, 8, 4, 2])
def test_default_points_map_includes_w_and_order(md_size):
    cs, _, _ = make_category_season(draw_size=md_size, scoring_md={}, scoring_qual_win={})
    cs.refresh_from_db()
    t = make_tournament(cs=cs)
    expected = round_labels_from_md_size(md_size)
    assert list(t.scoring_md.keys()) == expected
    assert "W" in t.scoring_md and expected[-1] == "W"
    t_db = Tournament.objects.get(pk=t.pk)
    assert list(t_db.scoring_md.keys()) == expected
