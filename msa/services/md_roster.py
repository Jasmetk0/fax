# msa/services/md_roster.py
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models import Q

from msa.models import (
    EntryStatus,
    EntryType,
    Match,
    MatchState,
    Phase,
    Schedule,
    Tournament,
    TournamentEntry,
)
from msa.services.admin_gate import require_admin_mode
from msa.services.ll_prefix import (
    enforce_ll_prefix_in_md,
    fill_vacant_slot_prefer_ll_then_alt,
)
from msa.services.md_embed import r1_name_for_md
from msa.services.tx import atomic, locked


def _get_r1_match(t: Tournament, slot: int) -> Match | None:
    r1 = r1_name_for_md(t)
    qs = Match.objects.filter(tournament=t, phase=Phase.MD, round_name=r1).filter(
        Q(slot_top=slot) | Q(slot_bottom=slot)
    )
    return locked(qs).first()


def _update_match_for_slot(m: Match, slot: int, player_id: int | None) -> None:
    if m.winner_id is not None or m.state == MatchState.DONE:
        raise ValidationError("R1 match already has result.")
    if m.slot_top == slot:
        m.player_top_id = player_id
    elif m.slot_bottom == slot:
        m.player_bottom_id = player_id
    m.winner_id = None
    m.score = {}
    m.state = MatchState.PENDING
    m.save(update_fields=["player_top", "player_bottom", "winner", "score", "state"])
    Schedule.objects.filter(match=m).delete()


@require_admin_mode
@atomic()
def remove_player_from_md(t: Tournament, slot: int) -> int | None:
    m = _get_r1_match(t, slot)
    if m and (m.winner_id is not None or m.state == MatchState.DONE):
        raise ValidationError("Nelze odebrat hráče, R1 zápas má výsledek.")

    te_qs = TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE, position=slot)
    te = locked(te_qs).first()
    if te:
        te.position = None
        te.save(update_fields=["position"])

    if m:
        _update_match_for_slot(m, slot, None)

    try:
        new_te = fill_vacant_slot_prefer_ll_then_alt(t, slot)
    except ValidationError as e:
        if "není volný" in str(e):
            return None
        return None
    else:
        m2 = m or _get_r1_match(t, slot)
        if m2:
            _update_match_for_slot(m2, slot, new_te.player_id)
        return new_te.id


@require_admin_mode
@atomic()
def ensure_vacancies_filled(t: Tournament) -> int:
    r1 = r1_name_for_md(t)
    slots: set[int] = set()
    for m in Match.objects.filter(tournament=t, phase=Phase.MD, round_name=r1):
        if m.slot_top:
            slots.add(int(m.slot_top))
        if m.slot_bottom:
            slots.add(int(m.slot_bottom))
    for pos in TournamentEntry.objects.filter(tournament=t, position__isnull=False).values_list(
        "position", flat=True
    ):
        slots.add(int(pos))

    active_slots = set(
        TournamentEntry.objects.filter(
            tournament=t, status=EntryStatus.ACTIVE, position__isnull=False
        ).values_list("position", flat=True)
    )
    vacant_slots = [s for s in slots if s not in active_slots]

    filled = 0
    for slot in sorted(vacant_slots):
        try:
            te = fill_vacant_slot_prefer_ll_then_alt(t, slot)
        except ValidationError as e:
            if "není volný" in str(e):
                continue
            continue
        else:
            m = _get_r1_match(t, slot)
            if m:
                try:
                    _update_match_for_slot(m, slot, te.player_id)
                except ValidationError:
                    pass
            filled += 1
    return filled


@require_admin_mode
@atomic()
def use_reserve_now(t: Tournament, slot: int) -> TournamentEntry:
    """Force ALT to occupy `slot`, even if an LL sits there."""
    m = _get_r1_match(t, slot)
    if not m:
        raise ValidationError("Neplatný MD slot.")
    if m.winner_id is not None or m.state == MatchState.DONE:
        raise ValidationError("Nelze měnit obsazení slotu: první kolo má výsledek.")

    occ_qs = TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE, position=slot)
    occ = locked(occ_qs).first()
    if occ:
        if occ.entry_type != EntryType.LL:
            raise ValidationError("Slot je obsazen; nejprve odeber hráče.")
        occ.position = None
        occ.save(update_fields=["position"])

    alt_qs = TournamentEntry.objects.filter(
        tournament=t,
        status=EntryStatus.ACTIVE,
        entry_type=EntryType.ALT,
        position__isnull=True,
    )
    alt = locked(alt_qs.order_by("id")).first()
    if not alt:
        raise ValidationError("Žádný dostupný ALT pro Use Reserve now.")

    alt.position = slot
    alt.save(update_fields=["position"])

    _update_match_for_slot(m, slot, alt.player_id)
    enforce_ll_prefix_in_md(t)
    return alt
