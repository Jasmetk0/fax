from __future__ import annotations

from msa.models import Match, MatchState, Phase, Schedule, Tournament
from msa.services.tx import atomic

THIRD_PLACE_ROUND_NAME = "3P"


@atomic()
def ensure_third_place_match(t: Tournament) -> Match | None:
    """
    Udržuje zápas o 3. místo v konzistentním stavu.

    Pokud t.third_place_enabled:
      - Pokud existují přesně 2 SF v MD a oba mají winner, vytvoř/aktualizuj 3P s poraženými semifinalisty.
      - 3P je PENDING (dokud nemá výsledek) s best_of=t.md_best_of, win_by_two=True.
      - Pokud 3P existuje a není DOHRANÝ, aktualizuje player_top/bottom dle aktuálních loserů.

    Pokud t.third_place_enabled = False:
      - Smaže všechny existující 3P (a jejich Schedule).

    Funkce je idempotentní. Vrací Match nebo None (pokud 3P nevzniká).
    """
    # Flag vypnutý → smazat případné 3P a skončit
    if not getattr(t, "third_place_enabled", False):
        existing = list(
            Match.objects.filter(tournament=t, phase=Phase.MD, round_name=THIRD_PLACE_ROUND_NAME)
        )
        for m in existing:
            Schedule.objects.filter(match=m).delete()
            m.delete()
        return None

    # Najdi přesně 2 semifinále (deterministické pořadí)
    sfs = list(
        Match.objects.filter(tournament=t, phase=Phase.MD, round_name="SF").order_by(
            "slot_top", "slot_bottom", "id"
        )
    )

    if len(sfs) != 2:
        return None
    if any(m.winner_id is None for m in sfs):
        return None
    if any(not (m.player_top_id and m.player_bottom_id) for m in sfs):
        return None

    # Poražení semifinalisté ve stabilním pořadí (podle seřazených SF výše)
    losers: list[int] = []
    for m in sfs:
        loser_id = m.player_bottom_id if m.winner_id == m.player_top_id else m.player_top_id
        losers.append(loser_id)

    # Ujisti se, že existuje nejvýše jeden 3P; DONE 3P ponecháme beze změny
    m3ps = list(
        Match.objects.filter(
            tournament=t, phase=Phase.MD, round_name=THIRD_PLACE_ROUND_NAME
        ).order_by("id")
    )

    if m3ps:
        # ponecháme první, ostatní (duplicitní) smažeme
        keep = m3ps[0]
        for extra in m3ps[1:]:
            Schedule.objects.filter(match=extra).delete()
            extra.delete()

        # pokud už je hotový, neaktualizujeme
        if keep.state == MatchState.DONE:
            return keep

        changed = False
        if keep.player_top_id != losers[0]:
            keep.player_top_id = losers[0]
            changed = True
        if keep.player_bottom_id != losers[1]:
            keep.player_bottom_id = losers[1]
            changed = True
        # Ujisti se, že formát zůstává korektní
        to_update = []
        if changed:
            to_update += ["player_top", "player_bottom"]
        # best_of je od turnaje; při vytvoření/úpravě beze změny stavu zachováme PENDING
        if to_update:
            keep.save(update_fields=to_update)
        return keep

    # Vytvoř nový 3P (sloty 1 a 2; unikát round_name+sloty držíme konzistentní)
    m3p = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name=THIRD_PLACE_ROUND_NAME,
        slot_top=1,
        slot_bottom=2,
        player_top_id=losers[0],
        player_bottom_id=losers[1],
        best_of=t.md_best_of or 5,
        win_by_two=True,
        state=MatchState.PENDING,
    )
    return m3p
