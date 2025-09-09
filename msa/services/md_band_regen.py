# msa/services/md_band_regen.py
from __future__ import annotations

from django.core.exceptions import ValidationError

from msa.models import (
    EntryStatus,
    Match,
    MatchState,
    Phase,
    Schedule,
    Snapshot,
    Tournament,
    TournamentEntry,
)
from msa.services.admin_gate import require_admin_mode
from msa.services.archiver import archive_tournament_state
from msa.services.md_confirm import _pick_seeds_and_unseeded  # reuse interní logiku
from msa.services.md_embed import effective_template_size_for_md, r1_name_for_md
from msa.services.randoms import rng_for, seeded_shuffle
from msa.services.seed_anchors import band_sequence_for_S, md_anchor_map
from msa.services.tx import atomic, locked


def _default_seeds_count(draw_size: int) -> int:
    if draw_size >= 64:
        return 16
    if draw_size >= 32:
        return 8
    if draw_size >= 16:
        return 4
    return 0


# R1 i kotvy vyhodnocujeme podle embed šablony (power-of-two), ne přímo podle draw_size.
@require_admin_mode
@atomic()
def regenerate_md_band(
    t: Tournament, band: str, rng_seed: int | None = None, mode: str = "SOFT"
) -> dict[int, int]:
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
    entries_qs = locked(
        TournamentEntry.objects.filter(
            tournament=t, status=EntryStatus.ACTIVE, position__isnull=False
        )
    )
    draw_size = int(t.category_season.draw_size or 0) if t.category_season else 0
    if not draw_size:
        raise ValidationError("Tournament.category_season.draw_size není nastaven.")
    template_size = effective_template_size_for_md(t)
    r1_qs = locked(Match.objects.filter(tournament=t, phase=Phase.MD, round_name=r1_name_for_md(t)))

    # Build základní sady
    entries = list(entries_qs)
    slot_to_entry = {int(te.position): te for te in entries}

    # Určete sady seedů dle WR pořadí (stejně jako confirm_main_draw)
    # reuse _pick_seeds_and_unseeded:
    from msa.services.md_confirm import _collect_active_entries

    evs = _collect_active_entries(t)
    seeds, unseeded, _ = _pick_seeds_and_unseeded(t, evs)
    seed_ids_in_order = [e.id for e in seeds]

    rng = rng_for(t)
    if band == "Unseeded":
        # Přelosovat nenasazené mezi jejich aktuálními sloty
        un_slots = sorted([s for s, te in slot_to_entry.items() if te.id not in seed_ids_in_order])
        pool_ids = [slot_to_entry[s].id for s in un_slots]
        pool_ids = seeded_shuffle(pool_ids, rng)
        # Ulož nové pozice jen pro unseeded
        TournamentEntry.objects.filter(pk__in=pool_ids).update(position=None)
        for s, eid in zip(un_slots, pool_ids, strict=False):
            TournamentEntry.objects.filter(pk=eid).update(position=s)
    else:
        # Seed band
        anchors = md_anchor_map(template_size)  # OrderedDict
        if band not in anchors:
            raise ValidationError(f"Neznámý band '{band}' pro draw_size={draw_size}.")
        # ověř, že band je „aktivní“ (patří do band_sequence_for_S)
        S = (
            t.category_season.md_seeds_count
            if (t.category_season and t.category_season.md_seeds_count)
            else _default_seeds_count(draw_size)
        )
        used_bands = set(band_sequence_for_S(template_size, S))
        if band not in used_bands:
            raise ValidationError(f"Band '{band}' se nepoužívá při S={S}.")

        anchor_slots = anchors[band][:]
        # Sanity: všechny kotvy daného bandu musí být obsazené seedem
        band_entries = [slot_to_entry.get(s) for s in anchor_slots]
        if any((e is None or e.id not in seed_ids_in_order) for e in band_entries):
            raise ValidationError(
                f"Band '{band}' nelze přelosovat: alespoň jedna kotva neobsahuje seed (pravděpodobně po manuálním zásahu)."
            )
        # Kteří seed hráči (Entry) aktuálně sedí na těchto kotvách?
        band_seed_ids = [slot_to_entry[s].id for s in anchor_slots]
        # deterministická permutace
        band_seed_ids = seeded_shuffle(band_seed_ids, rng)
        TournamentEntry.objects.filter(pk__in=band_seed_ids).update(position=None)
        # Ulož – přemapuj seed IDs na anchor sloty
        for s, eid in zip(anchor_slots, band_seed_ids, strict=False):
            TournamentEntry.objects.filter(pk=eid).update(position=s)

    # Aktualizace R1 – podle režimu
    # Připrav si nový mapping (po změnách)
    slot_to_entry_after = {
        int(te.position): te.id
        for te in TournamentEntry.objects.filter(
            tournament=t, status=EntryStatus.ACTIVE, position__isnull=False
        )
    }

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
        # Plán už nemusí odpovídat nové dvojici → smaž Schedule pro tento match
        Schedule.objects.filter(match=m).delete()

    hard = mode.upper() == "HARD"
    for m in r1_qs:
        if m.winner_id is not None and not hard:
            # SOFT: hotové páry necháme beze změny
            continue
        update_match_players(m, hard)

    archive_tournament_state(t, Snapshot.SnapshotType.REGENERATE)
    return slot_to_entry_after
