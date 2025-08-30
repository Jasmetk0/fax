from typing import List, Dict, Any, Tuple

from django.db import transaction

from ..models import (
    EventEdition,
    EventEntry,
    EventMatch,
    RankingEntry,
)


def _bracket_positions(size: int) -> List[int]:
    if size == 1:
        return [1]
    prev = _bracket_positions(size // 2)
    res: List[int] = []
    for seed in prev:
        res.append(seed)
        res.append(size + 1 - seed)
    return res


def _seed_players(event: EventEdition) -> Tuple[List[int], List[EventEntry]]:
    phase = event.phases.order_by("order").first()
    if not phase:
        return [], []
    rnd = phase.rounds.order_by("order").first()
    if not rnd:
        return [], []
    size = rnd.entrants
    entries = list(event.entries.select_related("player"))[:size]
    ranks: Dict[int, int] = {}
    if event.uses_snapshot_id:
        for r in RankingEntry.objects.filter(snapshot=event.uses_snapshot):
            ranks[r.player_id] = r.rank
    entries.sort(key=lambda e: ranks.get(e.player_id, 10_000_000))
    positions = _bracket_positions(size)
    slot_players: List[int] = [None] * size  # type: ignore
    index_map = {seed: idx for idx, seed in enumerate(positions)}
    for seed_no, entry in enumerate(entries, start=1):
        pos = index_map.get(seed_no)
        if pos is not None and pos < size:
            slot_players[pos] = entry.player_id
            entry.seed_no = seed_no
    return slot_players, entries


def preview_seeding(event_id: int) -> List[Dict[str, Any]]:
    event = EventEdition.objects.get(pk=event_id)
    slots, entries = _seed_players(event)
    id_to_entry = {e.player_id: e for e in entries}
    pairs = []
    for i in range(0, len(slots), 2):
        a_id = slots[i]
        b_id = slots[i + 1]
        a_entry = id_to_entry.get(a_id)
        b_entry = id_to_entry.get(b_id)
        pairs.append(
            {
                "a": {
                    "id": a_entry.player_id if a_entry else None,
                    "name": a_entry.player.name if a_entry else None,
                    "seed": a_entry.seed_no if a_entry else None,
                },
                "b": {
                    "id": b_entry.player_id if b_entry else None,
                    "name": b_entry.player.name if b_entry else None,
                    "seed": b_entry.seed_no if b_entry else None,
                },
            }
        )
    return pairs


@transaction.atomic
def apply_seeding(event_id: int) -> Dict[str, int]:
    event = EventEdition.objects.get(pk=event_id)
    slots, entries = _seed_players(event)
    phase = event.phases.order_by("order").first()
    if not phase:
        return {"assigned": 0}
    rnd = phase.rounds.order_by("order").first()
    matches = list(EventMatch.objects.filter(phase=phase, round=rnd).order_by("order"))
    assigned = 0
    for i, match in enumerate(matches):
        a_id = slots[2 * i]
        b_id = slots[2 * i + 1]
        if a_id:
            match.a_player_id = a_id
            assigned += 1
        if b_id:
            match.b_player_id = b_id
            assigned += 1
        match.save()
    for entry in entries:
        entry.save(update_fields=["seed_no"])
    return {"assigned": assigned}
