from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from django.conf import settings


class _MatchLike(Protocol):
    id: int
    round_name: str | None
    slot_top: int | None
    slot_bottom: int | None


def day_order_description(matches: Iterable[_MatchLike]) -> str:
    lines = []
    for i, m in enumerate(matches, start=1):
        rn = m.round_name or "R?"
        st = m.slot_top if m.slot_top is not None else "-"
        sb = m.slot_bottom if m.slot_bottom is not None else "-"
        lines.append(f"{i}. {rn} [{st} vs {sb}]")
    return "\n".join(lines)


def is_enabled() -> bool:
    return bool(getattr(settings, "MSA_CALENDAR_SYNC_ENABLED", False))


__all__ = ["day_order_description", "is_enabled"]
