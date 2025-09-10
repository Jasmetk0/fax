from __future__ import annotations

import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from msa.models import PlanningUndoState, Schedule, Snapshot, Tournament
from msa.services.admin_gate import require_admin_mode


def _limits():
    count = getattr(settings, "MSA_PLANNING_SNAPSHOT_LIMIT_COUNT", 300)
    size_mb = getattr(settings, "MSA_PLANNING_SNAPSHOT_LIMIT_MB", 8)
    return count, int(size_mb * 1024 * 1024)


@transaction.atomic
def push_planning_snapshot(t: Tournament, day: str, snapshot_id: int) -> None:
    state, _ = PlanningUndoState.objects.select_for_update().get_or_create(tournament=t, day=day)
    undo = list(state.undo_stack or [])
    undo.append(snapshot_id)
    state.undo_stack = undo
    state.redo_stack = []
    state.save(update_fields=["undo_stack", "redo_stack", "updated_at"])
    enforce_planning_snapshot_limits(t, day)


@require_admin_mode
@transaction.atomic
def undo_planning_day(t: Tournament, day: str) -> None:
    from msa.services.planning import restore_planning_snapshot

    state = PlanningUndoState.objects.select_for_update().filter(tournament=t, day=day).first()
    if not state or not state.undo_stack:
        raise ValidationError("undo stack is empty")
    undo = list(state.undo_stack)
    redo = list(state.redo_stack or [])
    current_id = undo.pop()
    redo.append(current_id)
    state.undo_stack = undo
    state.redo_stack = redo
    state.save(update_fields=["undo_stack", "redo_stack", "updated_at"])
    if undo:
        restore_planning_snapshot(t, undo[-1])
    else:
        Schedule.objects.filter(tournament=t, play_date=day).delete()


@require_admin_mode
@transaction.atomic
def redo_planning_day(t: Tournament, day: str) -> None:
    from msa.services.planning import restore_planning_snapshot

    state = PlanningUndoState.objects.select_for_update().filter(tournament=t, day=day).first()
    if not state or not state.redo_stack:
        raise ValidationError("redo stack is empty")
    undo = list(state.undo_stack or [])
    redo = list(state.redo_stack)
    snapshot_id = redo.pop()
    undo.append(snapshot_id)
    state.undo_stack = undo
    state.redo_stack = redo
    state.save(update_fields=["undo_stack", "redo_stack", "updated_at"])
    restore_planning_snapshot(t, snapshot_id)
    enforce_planning_snapshot_limits(t, day)


@transaction.atomic
def enforce_planning_snapshot_limits(t: Tournament, day: str) -> None:
    limit_count, limit_bytes = _limits()
    state = PlanningUndoState.objects.select_for_update().filter(tournament=t, day=day).first()
    if not state:
        return
    undo = list(state.undo_stack or [])
    if len(undo) > limit_count:
        undo = undo[-limit_count:]
    snapshots = Snapshot.objects.filter(tournament=t, pk__in=undo)
    sizes = {s.id: len(json.dumps(s.payload, ensure_ascii=False)) for s in snapshots}
    total = sum(sizes.get(sid, 0) for sid in undo)
    while total > limit_bytes and undo:
        removed = undo.pop(0)
        total -= sizes.get(removed, 0)
    state.undo_stack = undo
    state.save(update_fields=["undo_stack", "updated_at"])
