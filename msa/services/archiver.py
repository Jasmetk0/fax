from __future__ import annotations

from typing import Any

from django.utils import timezone

from msa.models import Match, Schedule, Snapshot, Tournament, TournamentEntry


def _serialize_entries(t: Tournament) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    qs = TournamentEntry.objects.filter(tournament=t).values(
        "id",
        "player_id",
        "entry_type",
        "seed",
        "wr_snapshot",
        "status",
        "position",
        "is_wc",
        "is_qwc",
        "promoted_by_wc",
        "promoted_by_qwc",
    )
    rows.extend(qs)
    return rows


def _serialize_matches(t: Tournament) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for m in Match.objects.filter(tournament=t).order_by("phase", "round_name", "slot_top"):
        rows.append(
            dict(
                id=m.id,
                phase=m.phase,
                round_name=m.round_name,
                slot_top=m.slot_top,
                slot_bottom=m.slot_bottom,
                player_top_id=m.player_top_id,
                player_bottom_id=m.player_bottom_id,
                winner_id=m.winner_id,
                state=m.state,
                score=m.score,
            )
        )
    return rows


def _serialize_schedule(t: Tournament) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in (
        Schedule.objects.filter(tournament=t)
        .select_related("match")
        .order_by("play_date", "order", "match_id")
    ):
        rows.append(
            dict(
                match_id=s.match_id,
                play_date=str(s.play_date) if s.play_date else None,
                order=s.order,
            )
        )
    return rows


def archive(
    t: Tournament, *, type: str, label: str | None = None, extra: dict | None = None
) -> int:
    """
    Uloží snapshot aktuálního stavu turnaje (entries + matches + schedule + rng_seed).
    Vrací ID snapshotu.
    """
    payload = dict(
        label=label or "",
        saved_at=str(timezone.now()),
        rng_seed=getattr(t, "rng_seed_active", None),
        entries=_serialize_entries(t),
        matches=_serialize_matches(t),
        schedule=_serialize_schedule(t),
        kind="TOURNAMENT_STATE",
    )
    if extra:
        payload.update(extra)
    s = Snapshot.objects.create(tournament=t, type=type, payload=payload)
    return s.id
