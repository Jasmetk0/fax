from msa.services.ranking_common import tiebreak_key


def test_unified_chain_orders_equal_points_consistently_for_all_modes():
    items = [
        {
            "player_id": 1,
            "points": 100,
            "best_n_points": 100,
            "events_in_window": 1,
            "best_single": 100,
        },
        {
            "player_id": 2,
            "points": 100,
            "best_n_points": 100,
            "events_in_window": 2,
            "best_single": 80,
        },
        {
            "player_id": 3,
            "points": 100,
            "best_n_points": 90,
            "events_in_window": 2,
            "best_single": 90,
        },
    ]
    expected_order = [2, 1, 3]
    for mode in ["ROLLING", "SEASON", "RTF"]:
        ordered = sorted(items, key=lambda r: tiebreak_key(mode, r))
        assert [r["player_id"] for r in ordered] == expected_order
