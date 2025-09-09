# msa/services/bestof_tools.py
from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from msa.models import Match, Phase, Tournament
from msa.services.admin_gate import require_admin_mode
from msa.services.tx import atomic

Mode = Literal["BO3", "BO5"]


@require_admin_mode
@atomic()
def bulk_set_best_of(
    tournament: Tournament,
    *,
    phase: Phase,
    rounds: Iterable[str] | None = None,
    match_ids: Iterable[int] | None = None,
    mode: Mode = "BO3",
    only_unplayed: bool = True,
) -> dict:
    """Přepne best_of na vybrané zápasy a vrací shrnutí."""

    target_best_of = 3 if mode == "BO3" else 5

    qs = Match.objects.filter(tournament=tournament, phase=phase)
    if rounds is not None:
        qs = qs.filter(round_name__in=set(rounds))
    match_ids_set: set[int] | None = None
    if match_ids is not None:
        match_ids_set = set(match_ids)
        qs = qs.filter(id__in=match_ids_set)

    matches = list(qs)
    matches_scanned = len(matches)

    matches_skipped_filtered = 0
    if match_ids_set is not None:
        matches_skipped_filtered = len(match_ids_set) - matches_scanned

    update_ids: list[int] = []
    matches_updated = 0
    matches_skipped_played = 0

    for m in matches:
        if only_unplayed and (m.winner_id is not None or (m.score or {}).get("sets")):
            matches_skipped_played += 1
            continue
        if m.best_of != target_best_of:
            update_ids.append(m.id)
            matches_updated += 1

    if update_ids:
        Match.objects.filter(id__in=update_ids).update(best_of=target_best_of)

    return {
        "target_best_of": target_best_of,
        "matches_scanned": matches_scanned,
        "matches_updated": matches_updated,
        "matches_skipped_played": matches_skipped_played,
        "matches_skipped_filtered": matches_skipped_filtered,
    }
