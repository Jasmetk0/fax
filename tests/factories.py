from msa.models import CategorySeason, Player, Tournament
from tests.woorld_helpers import woorld_date


def make_player(name: str = "P") -> Player:
    return Player.objects.create(name=name)


def make_category_season(
    *,
    draw_size=24,
    qual_rounds=0,
    scoring_md=None,
    scoring_qual_win=None,
    qualifiers_count=0,
    third_place=False,
):
    from msa.models import Category, Season

    cat = Category.objects.create(name="CAT")
    season = Season.objects.create(
        name="S",
        start_date=woorld_date(2025, 1, 1),
        end_date=woorld_date(2025, 12),
        best_n=10,
    )
    cs = CategorySeason(
        category=cat,
        season=season,
        draw_size=draw_size,
        qual_rounds=qual_rounds,
        scoring_md=scoring_md or {},
        scoring_qual_win=scoring_qual_win or {},
    )
    if third_place:
        cs.third_place_enabled = third_place
    cs.save()
    return cs, season, cat


def make_tournament(*, cs=None, qualifiers_count=0, third_place=None):
    cs = cs or make_category_season()[0]
    if third_place is None:
        tp = None
        for name in (
            "third_place_enabled",
            "third_place",
            "has_third_place",
            "bronze_match",
        ):
            if tp is None:
                tp = getattr(cs, name, None)
        third_place = bool(tp)
    return Tournament.objects.create(
        name="T",
        slug="t",
        category_season=cs,
        start_date=woorld_date(2025, 6, 1),
        end_date=woorld_date(2025, 6, 2),
        md_best_of=5,
        q_best_of=3,
        third_place_enabled=third_place,
        qualifiers_count=qualifiers_count,
    )
