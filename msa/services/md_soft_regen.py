# msa/services/md_soft_regen.py
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

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
from msa.services.md_embed import r1_name_for_md
from msa.services.randoms import rng_for, seeded_shuffle
from msa.services.tx import atomic, locked

# ---- Pomocné typy ----


@dataclass(frozen=True)
class EntryView:
    id: int
    player_id: int
    entry_type: str
    wr_snapshot: int | None  # None = NR


# ---- Utilitky ----


def _collect_active_entries(t: Tournament) -> list[EntryView]:
    qs = TournamentEntry.objects.filter(
        tournament=t, status=EntryStatus.ACTIVE, position__isnull=False
    ).select_related("player")
    return [
        EntryView(
            id=te.id, player_id=te.player_id, entry_type=te.entry_type, wr_snapshot=te.wr_snapshot
        )
        for te in qs
    ]


def _default_seeds_count(draw_size: int) -> int:
    if draw_size >= 64:
        return 16
    if draw_size >= 32:
        return 8
    if draw_size >= 16:
        return 4
    return 0


def _seed_ids_by_wr(t: Tournament, all_entries: list[EntryView]) -> list[int]:
    draw_size = (
        t.category_season.draw_size if (t.category_season and t.category_season.draw_size) else 0
    )
    if not draw_size:
        raise ValidationError("Tournament.category_season.draw_size není nastaven.")
    S = (
        t.category_season.md_seeds_count
        if (t.category_season and t.category_season.md_seeds_count)
        else _default_seeds_count(draw_size)
    )
    sorted_by_wr = sorted(
        all_entries,
        key=lambda ev: (
            1 if ev.wr_snapshot is None else 0,
            ev.wr_snapshot if ev.wr_snapshot is not None else 10**9,
            ev.id,
        ),
    )
    return [ev.id for ev in sorted_by_wr[:S]]


# ---- Soft regenerate: jen nenasazení v R1 bez výsledku ----


@require_admin_mode
@atomic()
def soft_regenerate_unseeded_md(t: Tournament, rng_seed: int | None = None) -> dict[int, int]:
    """
    Přelosuje **jen nenasazené** hráče v těch R1 zápasech, kde ještě není výsledek.
    Zachová:
      - všechny seedy (jejich sloty se nemění),
      - všechny páry, kde už je winner (nebo state==DONE),
      - páry bez výsledku změníme jen v rámci nenasazených slotů.
    Dopad na plán: pokud se u R1 bez výsledku změní dvojice, smažeme `Schedule` záznam (ponecháme jen pořadí u nezměněných).
    Vrací aktuální mapping {slot -> entry_id} po změnách.
    """
    # Zámky: všechny aktivní entries a R1 zápasy
    entries_qs = locked(
        TournamentEntry.objects.filter(
            tournament=t, status=EntryStatus.ACTIVE, position__isnull=False
        )
    )
    draw_size = (
        t.category_season.draw_size if (t.category_season and t.category_season.draw_size) else 0
    )
    if not draw_size:
        raise ValidationError("Tournament.category_season.draw_size není nastaven.")
    r1_qs = locked(Match.objects.filter(tournament=t, phase=Phase.MD, round_name=r1_name_for_md(t)))

    entries = _collect_active_entries(t)
    seed_ids = set(_seed_ids_by_wr(t, entries))

    # Sestavíme množinu MUTABLE slotů = sloty R1 zápasů bez výsledku
    mutable_slots: list[int] = []
    for m in r1_qs:
        has_result = (m.winner_id is not None) or (m.state == MatchState.DONE)
        if not has_result:
            mutable_slots.append(m.slot_top)
            mutable_slots.append(m.slot_bottom)

    if not mutable_slots:
        # Nic k přelosování
        return {int(te.position): te.id for te in entries_qs}

    # Z MUTABLE slotů odfiltruj ty, kde sedí seed (seed se NIKDY nehýbe)
    slot_to_entry: dict[int, TournamentEntry] = {int(te.position): te for te in entries_qs}
    mutable_unseeded_slots: list[int] = []
    pool_entry_ids: list[int] = []
    for slot in sorted(mutable_slots):
        te = slot_to_entry.get(slot)
        if not te:
            continue
        if te.id in seed_ids:
            # seed slot je fixní i když je zápas bez výsledku
            continue
        # nenasazený slot je kandidát na přesun
        mutable_unseeded_slots.append(slot)
        pool_entry_ids.append(te.id)

    # Pokud není co měnit (všechny mutable sloty drží seedy), skonči
    if len(pool_entry_ids) <= 1:
        return {int(te.position): te.id for te in entries_qs}

    # Deterministicky zamíchat pool a znovu je přiřadit do STEJNÉ množiny slotů (jiné pořadí)
    # Respect explicit rng_seed if provided; persist it for auditability
    rng_source = SimpleNamespace(rng_seed_active=rng_seed) if rng_seed is not None else t
    rng = rng_for(rng_source)
    if rng_seed is not None and getattr(t, "rng_seed_active", None) != rng_seed:
        t.rng_seed_active = rng_seed
        t.save(update_fields=["rng_seed_active"])
    shuffled = seeded_shuffle(pool_entry_ids, rng)

    # Ulož nové pozice (jen pro nenasazené v mutable_unseeded_slots)
    TournamentEntry.objects.filter(pk__in=pool_entry_ids).update(position=None)
    for slot, eid in zip(sorted(mutable_unseeded_slots), shuffled, strict=False):
        TournamentEntry.objects.filter(pk=eid).update(position=slot)

    # Aktualizuj R1 páry: u bezvýsledkových zápasů nastav hráče podle nových slotů,
    # a pokud se dvojice změnila, smaž případnou Schedule (ponecháme volný pořad).
    for m in r1_qs:
        if (m.winner_id is not None) or (m.state == MatchState.DONE):
            continue
        new_top_e = TournamentEntry.objects.filter(
            tournament=t, status=EntryStatus.ACTIVE, position=m.slot_top
        ).first()
        new_bot_e = TournamentEntry.objects.filter(
            tournament=t, status=EntryStatus.ACTIVE, position=m.slot_bottom
        ).first()
        new_top = new_top_e.player_id if new_top_e else None
        new_bot = new_bot_e.player_id if new_bot_e else None

        if (m.player_top_id, m.player_bottom_id) != (new_top, new_bot):
            # přemapovat hráče, výsledek zatím nebyl → stav PENDING, a smažeme plán
            m.player_top_id = new_top
            m.player_bottom_id = new_bot
            m.state = MatchState.PENDING
            m.winner_id = None
            m.score = {}
            m.save(update_fields=["player_top", "player_bottom", "state", "winner", "score"])
            # plán pryč
            Schedule.objects.filter(match=m).delete()

    # Aktuální mapping
    mapping = {
        int(te.position): te.id
        for te in TournamentEntry.objects.filter(
            tournament=t, status=EntryStatus.ACTIVE, position__isnull=False
        )
    }
    archive_tournament_state(t, Snapshot.SnapshotType.REGENERATE)
    return mapping
