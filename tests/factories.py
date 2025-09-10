from datetime import date

from msa.models import CategorySeason, Player, Tournament


def make_player(name: str = "P") -> Player:
    return Player.objects.create(name=name)


def make_category_season(
    *,
    draw_size=24,
    qualifiers_count=0,
    qual_rounds=0,
    scoring_md=None,
    scoring_qual_win=None,
):
    from msa.models import Category, Season

    cat = Category.objects.create(name="CAT")
    season = Season.objects.create(
        name="S",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        best_n=10,
    )
    cs = CategorySeason.objects.create(
        category=cat,
        season=season,
        draw_size=draw_size,
        qualifiers_count=qualifiers_count,
        qual_rounds=qual_rounds,
        scoring_md=scoring_md or {},
        scoring_qual_win=scoring_qual_win or {},
    )
    return cs, season, cat


def make_tournament(*, cs=None):
    cs = cs or make_category_season()[0]
    return Tournament.objects.create(
        name="T",
        slug="t",
        category_season=cs,
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 2),
        md_best_of=5,
        q_best_of=3,
        third_place_enabled=False,
    )
