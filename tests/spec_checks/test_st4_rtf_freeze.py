from datetime import date

import pytest

from msa.models import Tournament
from msa.services import standings
from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
def test_rtf_freezes_after_finals(monkeypatch):
    cs, season, _ = make_category_season()
    t_final = make_tournament(cs=cs)
    t_final.season = season
    t_final.is_finals = True
    t_final.end_date = date(2025, 5, 1)
    t_final.save(update_fields=["season", "is_finals", "end_date"])

    def fake_points(t, only_completed_rounds):
        return {1: 100} if t.id == t_final.id else {2: 50}

    monkeypatch.setattr(standings, "_tournament_total_points_map", fake_points)
    rows_before = standings.rtf_standings(season)

    Tournament.objects.create(
        name="T2",
        slug="t2",
        category_season=cs,
        season=season,
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 1),
    )

    rows_after = standings.rtf_standings(season)
    assert rows_before == rows_after
    assert [r.player_id for r in rows_after] == [1]
