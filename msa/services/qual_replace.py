from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db.models import F, Q

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
from msa.services.tx import atomic, locked


@dataclass(frozen=True)
class ReplaceResult:
    slot: int
    removed_player_id: int | None
    replacement_entry_id: int
    replacement_player_id: int


def _r1_qual_round_name(t: Tournament) -> str:
    cs = t.category_season
    if not cs or not cs.qual_rounds:
        raise ValidationError("CategorySeason.qual_rounds musí být nastaveno.")
    size = 2 ** int(cs.qual_rounds)
    return f"Q{size}"


def _pick_best_alt_qs(t: Tournament):
    # ALT kandidáti: ACTIVE, position není relevantní pro kvaldu (sloty jsou jen v MD)
    # Pořadí: WR vzestupně, NR (None) na konec, tie stabilně dle PK
    return TournamentEntry.objects.filter(
        tournament=t,
        status=EntryStatus.ACTIVE,
        entry_type=EntryType.ALT,
    ).order_by(F("wr_snapshot").asc(nulls_last=True), "id")


@atomic()
def remove_and_replace_in_qualification(t: Tournament, global_slot: int) -> ReplaceResult:
    """
    Remove & Replace v kvalifikaci:
      - najdi R1 match (Q{2^R}), kde global_slot je top/bottom,
      - pokud zápas má winner nebo state==DONE → blokuj,
      - odeber hráče ze zadané strany (nastav None),
      - vyber nejlepší ALT (viz pořadí), pokud není → ValidationError,
      - dosaď ALT.player_id na danou stranu, resetuj match: winner=None, score={}, state=PENDING,
      - smaž případný Schedule řádek pro tento match,
      - vrať ReplaceResult.
    Pozn.: entry_type u ALT se NEMĚNÍ; kvalifikační zápasy drží Player ID.
    """
    r1_name = _r1_qual_round_name(t)
    qs = Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name=r1_name).filter(
        Q(slot_top=global_slot) | Q(slot_bottom=global_slot)
    )
    m = locked(qs).first()
    if not m:
        raise ValidationError("Nenalezen R1 kvalifikační zápas pro zadaný slot.")

    # blokace na odehraný pár
    if (m.winner_id is not None) or (m.state == MatchState.DONE):
        raise ValidationError("Nelze měnit obsazení: zápas má výsledek.")

    side_top = m.slot_top == global_slot
    removed_pid = m.player_top_id if side_top else m.player_bottom_id

    # vyber ALT
    alt = locked(_pick_best_alt_qs(t)).first()
    if not alt:
        raise ValidationError("Žádný dostupný ALT k dosazení.")

    # dosaď hráče na správnou stranu
    if side_top:
        m.player_top_id = alt.player_id
    else:
        m.player_bottom_id = alt.player_id

    # reset stavu páru
    m.winner_id = None
    m.score = {}
    m.state = MatchState.PENDING
    m.save(update_fields=["player_top", "player_bottom", "winner", "score", "state"])

    # plán už nemusí odpovídat → smazat (ponecháme den volný pro reinsert)
    Schedule.objects.filter(match=m).delete()

    return ReplaceResult(
        slot=global_slot,
        removed_player_id=removed_pid,
        replacement_entry_id=alt.id,
        replacement_player_id=alt.player_id or 0,
    )
