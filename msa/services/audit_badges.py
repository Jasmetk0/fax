from __future__ import annotations

from typing import Any

BADGE_STATUSES = {"ok", "warn", "unknown"}


def _badge(value: Any, prefix: str) -> dict[str, str]:
    if value in (None, ""):
        return {"value": "", "label": f"{prefix}: —", "status": "warn"}
    return {"value": str(value), "label": f"{prefix}: {value}", "status": "ok"}


def audit_badges_for_tournament(tournament: Any) -> dict[str, dict[str, str]]:
    """Return audit badges for seeding source and snapshot label."""
    try:
        seeding = tournament.seeding_source
    except Exception:
        return {
            "seeding": {"value": "", "label": "Seeding: ?", "status": "unknown"},
            "snapshot": {"value": "", "label": "Snapshot: ?", "status": "unknown"},
        }

    snapshot = getattr(tournament, "snapshot_label", "")
    return {
        "seeding": _badge(seeding, "Seeding"),
        "snapshot": _badge(snapshot, "Snapshot"),
    }
