from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import (
    AdvancementEdge,
    EventEdition,
    EventMatch,
    EventPhase,
    PhaseRound,
)
from .rounds import round_label


def _round_code(size: int) -> str:
    if size > 8:
        return f"R{size}"
    if size == 8:
        return "QF"
    if size == 4:
        return "SF"
    if size == 2:
        return "F"
    return f"R{size}"


def _mk_rounds_for_single_elim(phase: EventPhase, draw: int, best_of_map: dict):
    order = 1
    size = draw
    rounds = []
    default_best = best_of_map.get("default", phase.config.get("best_of", 5))
    while size >= 2:
        code = _round_code(size)
        label = round_label(size)
        matches = size // 2
        best_of = best_of_map.get(code, default_best)
        rnd = PhaseRound.objects.create(
            phase=phase,
            order=order,
            code=code,
            label=label,
            entrants=size,
            matches=matches,
            best_of=best_of,
        )
        for m in range(1, matches + 1):
            EventMatch.objects.create(phase=phase, round=rnd, order=m)
        rounds.append(rnd)
        size //= 2
        order += 1
    third = phase.config.get("third_place")
    if third:
        rnd = PhaseRound.objects.create(
            phase=phase,
            order=order,
            code="3P",
            label="3rd place",
            entrants=2,
            matches=1,
            best_of=third.get("best_of", default_best),
        )
        EventMatch.objects.create(phase=phase, round=rnd, order=1)
        rounds.append(rnd)
    return rounds


def _wire_single_elim_edges(phase: EventPhase):
    rounds = list(phase.rounds.order_by("order"))
    for cur, nxt in zip(rounds, rounds[1:]):
        if nxt.code == "3P":
            continue
        for i in range(1, cur.matches + 1, 2):
            next_match = (i + 1) // 2
            AdvancementEdge.objects.create(
                phase=phase,
                from_ref=f"{cur.code}:M{i}:W",
                to_ref=f"{nxt.code}:M{next_match}:A",
            )
            if i + 1 <= cur.matches:
                AdvancementEdge.objects.create(
                    phase=phase,
                    from_ref=f"{cur.code}:M{i+1}:W",
                    to_ref=f"{nxt.code}:M{next_match}:B",
                )
    # third place wiring
    try:
        sf = next(r for r in rounds if r.code == "SF")
        third = next(r for r in rounds if r.code == "3P")
        AdvancementEdge.objects.create(
            phase=phase,
            from_ref=f"{sf.code}:M1:L",
            to_ref=f"{third.code}:M1:A",
        )
        AdvancementEdge.objects.create(
            phase=phase,
            from_ref=f"{sf.code}:M2:L",
            to_ref=f"{third.code}:M1:B",
        )
    except StopIteration:
        pass


def _create_rr_groups_rounds_matches(phase: EventPhase):
    # Placeholder for round robin logic
    PhaseRound.objects.create(
        phase=phase,
        order=1,
        code="RR",
        label="Round robin",
        entrants=0,
        matches=0,
        best_of=phase.config.get("best_of", 5),
    )


@transaction.atomic
def expand_template(event_id: int):
    event = EventEdition.objects.get(pk=event_id)
    template = event.draw_template
    if not template:
        raise ValidationError("Event has no draw template")
    data = template.dsl_json or {}
    phases = data.get("phases", [])
    for idx, phase_def in enumerate(phases, start=1):
        phase = EventPhase.objects.create(
            event=event,
            order=idx,
            type=phase_def.get("type"),
            name=phase_def.get("name", f"Phase {idx}"),
            config=phase_def.get("config", {}),
        )
        if phase.type in ("single_elim", "qualifying"):
            draw = phase.config.get("draw")
            if not draw:
                raise ValidationError("Missing draw size")
            rounds = _mk_rounds_for_single_elim(
                phase, draw, phase.config.get("best_of_map", {})
            )
            _wire_single_elim_edges(phase)
        elif phase.type == "round_robin":
            _create_rr_groups_rounds_matches(phase)
        elif phase.type == "swiss":
            rounds = phase.config.get("rounds", 0)
            for r in range(1, rounds + 1):
                PhaseRound.objects.create(
                    phase=phase,
                    order=r,
                    code=f"R{r}",
                    label=f"Round {r}",
                    entrants=0,
                    matches=0,
                    best_of=phase.config.get("best_of", 5),
                )
    return event
