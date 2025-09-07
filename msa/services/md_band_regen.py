# msa/services/md_band_regen.py
from __future__ import annotations

from typing import Dict, List, Tuple
import random

from django.core.exceptions import ValidationError

from msa.models import (
    Tournament, TournamentEntry, EntryType, EntryStatus, Phase, Match, MatchState
)
from msa.services.tx import atomic, locked
from msa.services.seed_anchors import md_anchor_map, band_sequence_for_S
from msa.services.md_confirm import _pick_seeds_and_unseeded  # reuse interní logiku


def _default_seeds_count(draw_size: int) -> int:
    if draw_size >= 64:
        return 16
    if draw_size >= 32:
        return 8
    if draw_size >= 16:
        return 4
    return 0


def _r1_name(draw_size: int) -> str:
    return f"R{draw_size}"


@atomic()
def regenerate_md_band(t: Tournament, band: str, rng_seed: int, mode: str = "SOFT") -> Dict[int, int]:
    """
    Přelosuje **vybraný band** seedů v MD (např. '3-4','5-8','9-16','17-32') nebo 'Unseeded'.
    - U seed bandů: permutuje rozložení seedů v rámci kotev daného bandu (kotvy zůstávají, mění se to, KTERÝ seed sedí na které kotvě).
    - U 'Unseeded': přelosuje všechny nenasazené mezi jejich sloty.
    Dopad na R1:
      - SOFT: mění jen R1 bez výsledku; DONE páry nechá být.
      - HARD: u dotčených párů smaže výsledky a nastaví PENDING + nové hráče.
    Vrací aktuální mapping {slot -> entry_id}.
    """
    # zámky
    entries_qs = locked(TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE, position__isnull=False))
    draw_size = int(t.category_season.draw_size) if (t.category_season and t.category_season.draw_size) else 0
    if not draw_size:
        raise ValidationError("Tournament.category_season.draw_size není nastaven.")
    r1_qs = locked(Match.objects.filter(tournament=t, phase=Phase.MD, round_name=_r1_name(draw_size)))

    # Build základní sady
    entries = list(entries_qs)
    slot_to_entry = {int(te.position): te for te in entries}
    entry_id_to_te = {te.id: te for te in entries}

    # Určete sady seedů dle WR pořadí (stejně jako confirm_main_draw)
    # reuse _pick_seeds_and_unseeded:
    from msa.services.md_confirm import _collect_active_entries
    evs = _collect_active_entries(t)
    seeds, unseeded, _ = _pick_seeds_and_unseeded(t, evs)
    seed_ids_in_order = [e.id for e in seeds]

    if band == "Unseeded":
        # Přelosovat nenasazené mezi jejich aktuálními sloty
        un_slots = sorted([s for s, te in slot_to_entry.items() if te.id not in seed_ids_in_order])
        pool_ids = [slot_to_entry[s].id for s in un_slots]
        rng = random.Random(rng_seed)
        rng.shuffle(pool_ids)
        # Ulož nové pozice jen pro unseeded
        for s, eid in zip(un_slots, pool_ids):
            te = TournamentEntry.objects.select_for_update().get(pk=eid)
            if te.position != s:
                te.position = s
                te.save(update_fields=["position"])
    else:
        # Seed band
        anchors = md_anchor_map(draw_size)  # OrderedDict
        if band not in anchors:
            raise ValidationError(f"Neznámý band '{band}' pro draw_size={draw_size}.")
        # ověř, že band je „aktivní“ (patří do band_sequence_for_S)
        S = (t.category_season.md_seeds_count
             if (t.category_season and t.category_season.md_seeds_count)
             else _default_seeds_count(draw_size))
        used_bands = set(band_sequence_for_S(draw_size, S))
        if band not in used_bands:
            raise ValidationError(f"Band '{band}' se nepoužívá při S={S}.")

        anchor_slots = anchors[band][:]
        # Kteří seed hráči (Entry) aktuálně sedí na těchto kotvách?
        band_seed_ids = [slot_to_entry[s].id for s in anchor_slots]
        # deterministická permutace
        rng = random.Random(rng_seed)
        rng.shuffle(band_seed_ids)
        # Ulož – přemapuj seed IDs na anchor sloty
        for s, eid in zip(anchor_slots, band_seed_ids):
            te = TournamentEntry.objects.select_for_update().get(pk=eid)
            if te.position != s:
                te.position = s
                te.save(update_fields=["position"])

    # Aktualizace R1 – podle režimu
    # Připrav si nový mapping (po změnách)
    slot_to_entry_after = {int(te.position): te.id for te in TournamentEntry.objects.filter(
        tournament=t, status=EntryStatus.ACTIVE, position__isnull=False
    )}

    # Pomocná: získat player_id podle entry_id
    # Reuse evs map (id -> player_id)
    id2player = {ev.id: ev.player_id for ev in evs}

    def update_match_players(m: Match, hard: bool):
        new_top = id2player.get(slot_to_entry_after.get(m.slot_top))
        new_bot = id2player.get(slot_to_entry_after.get(m.slot_bottom))
        impacted = (m.player_top_id != new_top) or (m.player_bottom_id != new_bot)
        if not impacted:
            return
        if hard:
            m.winner_id = None
            m.score = {}
            m.state = MatchState.PENDING
        # osadit nové hráče (i v SOFT režimu)
        m.player_top_id = new_top
        m.player_bottom_id = new_bot
        m.save(update_fields=["player_top", "player_bottom", "winner", "score", "state"])

    hard = (mode.upper() == "HARD")
    for m in r1_qs:
        if m.winner_id is not None and not hard:
            # SOFT: hotové páry necháme beze změny
            continue
        update_match_players(m, hard)

    return slot_to_entry_after
