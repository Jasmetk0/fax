from __future__ import annotations

from typing import Any


def tiebreak_key(mode: str, rec: dict[str, Any]) -> tuple:
    if mode == "SEASON":
        return (
            -rec["points"],
            -rec.get("average", 0.0),
            -rec.get("best_n_points", rec["points"]),
            -rec.get("events_in_window", 0),
            -rec.get("best_single", 0),
            rec["player_id"],
        )
    return (
        -rec["points"],
        -rec.get("best_n_points", rec["points"]),
        -rec.get("events_in_window", 0),
        -rec.get("best_single", 0),
        rec["player_id"],
    )


def row_to_item(row: Any) -> dict[str, Any]:
    counted = list(getattr(row, "counted", []) or [])
    dropped = list(getattr(row, "dropped", []) or [])
    return {
        "player_id": row.player_id,
        "points": row.total,
        "average": getattr(row, "average", 0.0),
        "best_n_points": sum(counted),
        "events_in_window": len(counted) + len(dropped),
        "best_single": max(counted) if counted else 0,
        "best_n": len(counted),
    }
