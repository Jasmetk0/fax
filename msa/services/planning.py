# msa/services/planning.py
from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError

from msa.models import Match, Schedule, Snapshot, Tournament
from msa.services.tx import atomic, locked


@dataclass(frozen=True)
class ScheduledItem:
    match_id: int
    play_date: str | None
    order: int | None
    phase: str
    round_name: str
    slot_top: int
    slot_bottom: int
    player_top_id: int | None
    player_bottom_id: int | None
    state: str


# ---------- helpers ----------


def _list_day(t: Tournament, play_date: str) -> list[Schedule]:
    return list(
        Schedule.objects.filter(tournament=t, play_date=play_date)
        .select_related("match")
        .order_by("order", "match_id")
    )


def _list_all(t: Tournament) -> list[Schedule]:
    return list(
        Schedule.objects.filter(tournament=t)
        .select_related("match")
        .order_by("play_date", "order", "match_id")
    )


def _compact_day(t: Tournament, play_date: str) -> None:
    """Přečísluje pořadí v daném dni na 1..N beze škod a stabilně dle stávajícího pořadí."""
    day = _list_day(t, play_date)
    for i, sch in enumerate(day, start=1):
        if sch.order != i:
            sch.order = i
            sch.save(update_fields=["order"])


def _snapshot_payload(t: Tournament) -> dict:
    rows = [
        dict(
            match_id=sch.match_id,
            play_date=str(sch.play_date) if sch.play_date else None,
            order=sch.order,
        )
        for sch in _list_all(t)
    ]
    return dict(kind="PLANNING", rows=rows)


def _restore_payload(t: Tournament, payload: dict) -> None:
    if payload.get("kind") != "PLANNING":
        raise ValidationError("Snapshot neobsahuje plánování.")
    # vymaž existující plán
    Schedule.objects.filter(tournament=t).delete()
    # znovu vytvoř podle payloadu
    bulk: list[Schedule] = []
    for r in payload.get("rows", []):
        m = Match.objects.filter(pk=r["match_id"], tournament=t).first()
        if not m:
            # přeskoč neexistující zápasy (snapshot může být starší)
            continue
        bulk.append(Schedule(tournament=t, match=m, play_date=r["play_date"], order=r["order"]))
    Schedule.objects.bulk_create(bulk, ignore_conflicts=True)


def _ensure_not_scheduled_elsewhere(t: Tournament, match_id: int) -> Schedule | None:
    """Vrátí existující Schedule pro match (pokud je), abychom ho mohli přesunout/odstranit."""
    return Schedule.objects.filter(tournament=t, match_id=match_id).first()


def _serialize_day_items(day: list[Schedule]) -> list[ScheduledItem]:
    out: list[ScheduledItem] = []
    for sch in day:
        m = sch.match
        out.append(
            ScheduledItem(
                match_id=m.id,
                play_date=str(sch.play_date) if sch.play_date else None,
                order=sch.order,
                phase=m.phase,
                round_name=m.round_name,
                slot_top=m.slot_top or 0,
                slot_bottom=m.slot_bottom or 0,
                player_top_id=m.player_top_id,
                player_bottom_id=m.player_bottom_id,
                state=m.state,
            )
        )
    return out


# ---------- Public API ----------


@atomic()
def list_day_order(t: Tournament, play_date: str) -> list[ScheduledItem]:
    """Vrať očíslovaný seznam zápasů pro den."""
    day = (
        locked(Schedule.objects.filter(tournament=t, play_date=play_date))
        .select_related("match")
        .order_by("order", "match_id")
    )
    return _serialize_day_items(list(day))


@atomic()
def insert_match(t: Tournament, match_id: int, play_date: str, order: int) -> None:
    """
    Insert (MVP): vyjmi match z případného starého dne, zkompaktuj,
    vlož na cílový (play_date, order): vše s order >= target posuň o +1.
    Poté přečísluj den 1..N.
    """
    # lock cílový den + existující řádek match
    locked(Schedule.objects.filter(tournament=t, play_date=play_date))
    row = _ensure_not_scheduled_elsewhere(t, match_id)
    if row:
        old_day = str(row.play_date) if row.play_date else None
        row.delete()
        if old_day:
            _compact_day(t, old_day)

    # posuň kolize na cílovém dni
    colliders = Schedule.objects.filter(
        tournament=t, play_date=play_date, order__gte=order
    ).order_by("-order")
    for sch in colliders:
        sch.order = (sch.order or 0) + 1
        sch.save(update_fields=["order"])

    # vytvoř řádek
    m = Match.objects.filter(pk=match_id, tournament=t).first()
    if not m:
        raise ValidationError("Match neexistuje v turnaji.")
    Schedule.objects.create(tournament=t, play_date=play_date, order=order, match=m)

    # final compact (pro jistotu)
    _compact_day(t, play_date)

    # snapshot
    Snapshot.objects.create(
        tournament=t, type=Snapshot.SnapshotType.MANUAL, payload=_snapshot_payload(t)
    )


@atomic()
def swap_matches(t: Tournament, match_id_a: int, match_id_b: int) -> None:
    """
    Swap: vymění (play_date, order) dvou zápasů (může být i napříč dny).
    Bezpečně přes dočasné NULL v order (unikát dovolí více NULL).
    """
    a = (
        locked(Schedule.objects.filter(tournament=t, match_id=match_id_a))
        .select_related("match")
        .first()
    )
    b = (
        locked(Schedule.objects.filter(tournament=t, match_id=match_id_b))
        .select_related("match")
        .first()
    )
    if not a or not b:
        raise ValidationError("Oba zápasy musí být naplánované.")
    pa, oa = a.play_date, a.order
    pb, ob = b.play_date, b.order

    # dočasně uvolníme unikát
    a.order = None
    a.save(update_fields=["order"])
    b.order = None
    b.save(update_fields=["order"])

    # prohodíme den i pořadí
    a.play_date, a.order = pb, ob
    b.play_date, b.order = pa, oa
    a.save(update_fields=["play_date", "order"])
    b.save(update_fields=["play_date", "order"])

    # compact obou dnů
    if pa:
        _compact_day(t, str(pa))
    if pb:
        _compact_day(t, str(pb))

    Snapshot.objects.create(
        tournament=t, type=Snapshot.SnapshotType.MANUAL, payload=_snapshot_payload(t)
    )


@atomic()
def normalize_day(t: Tournament, play_date: str) -> None:
    """Normalize Day: přečísluje pořadí na 1..N a uloží snapshot."""
    _compact_day(t, play_date)
    Snapshot.objects.create(
        tournament=t, type=Snapshot.SnapshotType.MANUAL, payload=_snapshot_payload(t)
    )


@atomic()
def clear_day(t: Tournament, play_date: str) -> None:
    """Clear: z daného dne vymaže všechny zápasy (Schedule)."""
    Schedule.objects.filter(tournament=t, play_date=play_date).delete()
    Snapshot.objects.create(
        tournament=t, type=Snapshot.SnapshotType.MANUAL, payload=_snapshot_payload(t)
    )


@atomic()
def move_match(t: Tournament, match_id: int, to_play_date: str, to_order: int) -> None:
    """Alias pro Insert — přesune zápas na jiný den a pozici."""
    insert_match(t, match_id, to_play_date, to_order)


@atomic()
def save_planning_snapshot(t: Tournament, label: str = "manual") -> int:
    """Ulož explicitní snapshot plánu, vrať ID snapshotu."""
    s = Snapshot.objects.create(
        tournament=t,
        type=Snapshot.SnapshotType.MANUAL,
        payload=dict(label=label, **_snapshot_payload(t)),
    )
    return s.id


@atomic()
def restore_planning_snapshot(t: Tournament, snapshot_id: int) -> None:
    """Obnoví plán z dříve uloženého snapshotu."""
    s = Snapshot.objects.filter(
        tournament=t, pk=snapshot_id, type=Snapshot.SnapshotType.MANUAL
    ).first()
    if not s:
        raise ValidationError("Snapshot nenalezen nebo není typu MANUAL.")
    _restore_payload(t, s.payload)
