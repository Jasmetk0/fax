from msa.services.ranking_common import tiebreak_key


def test_season_ties_use_average_then_shared_places():
    a = {
        "player_id": 1,
        "points": 100,
        "average": 10.0,
        "best_n_points": 100,
        "events_in_window": 2,
        "best_single": 60,
    }
    b = {
        "player_id": 2,
        "points": 100,
        "average": 9.0,
        "best_n_points": 100,
        "events_in_window": 3,
        "best_single": 70,
    }
    ordered = sorted([a, b], key=lambda r: tiebreak_key("SEASON", r))
    assert [r["player_id"] for r in ordered] == [1, 2]
