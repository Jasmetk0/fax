from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db.models import Q

from msa.models import Match, MatchState, Phase, Schedule, Tournament
from msa.services.admin_gate import require_admin_mode
from msa.services.qual_generator import bracket_anchor_tiers
from msa.services.tx import atomic, locked


@dataclass(frozen=True)
class SwapResult:
    slot_a: int
    slot_b: int
    player_a_before: int | None
    player_b_before: int | None
    player_a_after: int | None
    player_b_after: int | None


def _qual_size_and_anchors(t: Tournament) -> tuple[int, set[int]]:
    cs = t.category_season
    if not cs or not cs.qual_rounds:
        raise ValidationError("CategorySeason.qual_rounds musí být nastaveno.")
    R = int(cs.qual_rounds)
    size = 2**R
    tiers = bracket_anchor_tiers(R)  # OrderedDict tier -> [local_slot]
    anchor_locals = {s for slots in tiers.values() for s in slots}
    return size, anchor_locals


def _local_slot(global_slot: int) -> tuple[int, int]:
    """Vrátí (base, local_slot). base je násobek 1000; local 1..size."""
    base = (global_slot // 1000) * 1000
    return base, global_slot - base


def _r1_name_for_size(size: int) -> str:
    return f"Q{size}"


def _fetch_r1_for_slot(t: Tournament, size: int, global_slot: int) -> Match:
    r1 = _r1_name_for_size(size)
    qs = Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name=r1).filter(
        Q(slot_top=global_slot) | Q(slot_bottom=global_slot)
    )
    m = locked(qs).first()
    if not m:
        raise ValidationError("Nenalezen R1 kvalifikační zápas pro zadaný slot.")
    return m


def _side_is_top(m: Match, slot: int) -> bool:
    if m.slot_top == slot:
        return True
    if m.slot_bottom == slot:
        return False
    raise ValidationError("Slot nepatří danému zápasu.")


@require_admin_mode
@atomic()
def swap_slots_in_qualification(t: Tournament, slot_a: int, slot_b: int) -> SwapResult:
    """
    Bezpečné prohození dvou R1 slotů v kvalifikaci (napříč větvemi).
    Pravidla:
      - seed kotvy smí swapovat jen mezi stejnými anchor local_slot (stejný tier),
      - nenasazení pouze mezi nenasazenými,
      - blokace pokud jakýkoli z dotčených R1 zápasů má výsledek,
      - po provedení reset winner/score/state a smazání Schedule u obou zápasů.
    """
    if slot_a == slot_b:
        raise ValidationError("Sloty musí být různé.")

    size, anchor_locals = _qual_size_and_anchors(t)
    _, la = _local_slot(slot_a)
    _, lb = _local_slot(slot_b)

    a_is_anchor = la in anchor_locals
    b_is_anchor = lb in anchor_locals

    # Pravidla pohybu
    if a_is_anchor != b_is_anchor:
        raise ValidationError("Nelze míchat seed kotvu s nenasazeným slotem.")
    if a_is_anchor and (la != lb):
        # seedy musí být ve stejném tieru (lokální slot stejné číslo)
        raise ValidationError("Seedy lze prohodit jen mezi stejnými kotvami (stejný tier).")

    # Najdi zápasy
    ma = _fetch_r1_for_slot(t, size, slot_a)
    mb = _fetch_r1_for_slot(t, size, slot_b)

    # Blokace na výsledek
    for m in (ma, mb):
        if (m.winner_id is not None) or (m.state == MatchState.DONE):
            raise ValidationError("Nelze měnit obsazení: některý z vybraných zápasů má výsledek.")

    # Urči strany a hráče
    a_top = _side_is_top(ma, slot_a)
    b_top = _side_is_top(mb, slot_b)

    pa_before = ma.player_top_id if a_top else ma.player_bottom_id
    pb_before = mb.player_top_id if b_top else mb.player_bottom_id

    # Prohoď hráče
    if a_top:
        ma.player_top_id = pb_before
    else:
        ma.player_bottom_id = pb_before

    if b_top:
        mb.player_top_id = pa_before
    else:
        mb.player_bottom_id = pa_before

    # Reset obou zápasů
    for m in (ma, mb):
        m.winner_id = None
        m.score = {}
        m.state = MatchState.PENDING

    # Ulož a zruš plán (Schedule)
    ma.save(update_fields=["player_top", "player_bottom", "winner", "score", "state"])
    mb.save(update_fields=["player_top", "player_bottom", "winner", "score", "state"])
    Schedule.objects.filter(match__in=[ma, mb]).delete()

    pa_after = ma.player_top_id if a_top else ma.player_bottom_id
    pb_after = mb.player_top_id if b_top else mb.player_bottom_id

    return SwapResult(
        slot_a=slot_a,
        slot_b=slot_b,
        player_a_before=pa_before,
        player_b_before=pb_before,
        player_a_after=pa_after,
        player_b_after=pb_after,
    )
