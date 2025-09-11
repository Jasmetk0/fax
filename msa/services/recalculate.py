# msa/services/recalculate.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from django.core.exceptions import ValidationError

from msa.models import EntryStatus, EntryType, SeedingSource, Snapshot, Tournament, TournamentEntry
from msa.services.admin_gate import require_admin_mode
from msa.services.standings_snapshot import ensure_seeding_baseline
from msa.services.tx import atomic, locked


class Group(str, Enum):
    SEED = "SEED"
    DA = "DA"
    Q = "Q"
    RESERVE = "RESERVE"


@dataclass(frozen=True)
class EntryState:
    id: int
    player_id: int
    wr: int | None
    entry_type: str
    seed: int | None
    is_wc: bool
    promoted_by_wc: bool
    is_qwc: bool
    promoted_by_qwc: bool
    position: int | None  # registrace/MD slot


@dataclass(frozen=True)
class Row:
    entry_id: int
    group: Group
    index: int  # pořadí uvnitř skupiny (0-based)
    separator_after: bool = False


@dataclass(frozen=True)
class Preview:
    current: list[Row]
    proposed: list[Row]
    moves: list[tuple[int, Group, Group]]  # (entry_id, from_group, to_group)
    counters: dict[str, int]  # S / D / Q_draw_size / WC_used / WC_limit / QWC_used / QWC_limit
    rng_seed: int | None = None


# --------- utils ---------


def _eff_draw_params(t: Tournament) -> tuple[int, int, int]:
    """
    Vrací (draw_size, qualifiers_count, qual_rounds).
    """
    if not t.category_season:
        raise ValidationError("Tournament nemá nastavený CategorySeason.")
    cs = t.category_season
    if not cs.draw_size:
        raise ValidationError("CategorySeason.draw_size není nastaven.")
    draw_size = int(cs.draw_size)
    qualifiers_count = t.qualifiers_count_effective
    qual_rounds = int(cs.qual_rounds or 0)
    return draw_size, qualifiers_count, qual_rounds


def _default_md_seeds(draw_size: int) -> int:
    if draw_size >= 64:
        return 16
    if draw_size >= 32:
        return 8
    if draw_size >= 16:
        return 4
    return 0


def _eff_md_seeds(t: Tournament) -> int:
    draw_size, _, _ = _eff_draw_params(t)
    cs = t.category_season
    return int(cs.md_seeds_count or _default_md_seeds(draw_size))


def _eff_wc_limit(t: Tournament) -> int:
    cs = t.category_season
    base = int(cs.wc_slots_default or 0)
    return int(t.wc_slots) if getattr(t, "wc_slots", None) is not None else base


def _eff_qwc_limit(t: Tournament) -> int:
    cs = t.category_season
    base = int(cs.q_wc_slots_default or 0)
    return int(t.q_wc_slots) if getattr(t, "q_wc_slots", None) is not None else base


def _entries_active(t: Tournament) -> list[EntryState]:
    qs = TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE).select_related(
        "player"
    )
    out: list[EntryState] = []
    for te in qs:
        out.append(
            EntryState(
                id=te.id,
                player_id=te.player_id,
                wr=te.wr_snapshot,
                entry_type=te.entry_type,
                seed=te.seed,
                is_wc=bool(getattr(te, "is_wc", False)),
                promoted_by_wc=bool(getattr(te, "promoted_by_wc", False)),
                is_qwc=bool(getattr(te, "is_qwc", False)),
                promoted_by_qwc=bool(getattr(te, "promoted_by_qwc", False)),
                position=te.position,
            )
        )
    return out


def _sort_by_wr(entries: list[EntryState]) -> list[EntryState]:
    return sorted(
        entries, key=lambda e: (1 if e.wr is None else 0, e.wr if e.wr is not None else 10**9, e.id)
    )


def _current_layout(
    t: Tournament, entries: list[EntryState], S: int, D: int, Qdraw: int
) -> list[Row]:
    """
    Aktuální obraz registrace/MD:
    - „SEED“: ti, kteří mají te.seed 1..S (řadíme podle te.seed),
    - „DA“: ti, jejichž entry_type == DA a nejsou v SEED,
    - „Q“: EntryType.Q,
    - „RESERVE“: ostatní (ALT/LL/QWC placeholders atd.).
    """
    seeds = [
        e
        for e in entries
        if (e.entry_type == EntryType.DA and (e.seed or 0) >= 1 and (e.seed or 0) <= S)
    ]
    seeds.sort(key=lambda e: (e.seed or 10**9, e.id))
    seed_ids = {e.id for e in seeds}

    das = [e for e in entries if e.entry_type == EntryType.DA and e.id not in seed_ids]
    # u DA pořadí zkusíme držet podle WR (nemáme „manuální index“)
    das = _sort_by_wr(das)

    qs = [e for e in entries if e.entry_type == EntryType.Q]
    qs = _sort_by_wr(qs)

    res = [
        e
        for e in entries
        if e.id not in seed_ids and e.entry_type not in (EntryType.DA, EntryType.Q)
    ]
    res = _sort_by_wr(res)

    rows: list[Row] = []
    rows += [Row(entry_id=e.id, group=Group.SEED, index=i) for i, e in enumerate(seeds)]
    rows += [Row(entry_id=e.id, group=Group.DA, index=i) for i, e in enumerate(das)]
    rows += [Row(entry_id=e.id, group=Group.Q, index=i) for i, e in enumerate(qs)]
    rows += [Row(entry_id=e.id, group=Group.RESERVE, index=i) for i, e in enumerate(res)]
    return rows


def _proposed_layout(
    t: Tournament, entries: list[EntryState], seeding_source: str
) -> tuple[list[Row], dict[str, int]]:
    """
    Navrhovaný layout podle aktuálních S/K/R/draw_size a seeding_source.
    - WC pravidla: kdokoli s promoted_by_wc=True MUSÍ být v DA; pokud to překročí D,
      vyhazujeme z DA nejhorší (WR) nepovýšené.
    - Pořadí v blocích: podle WR (ties stabilně id); NONE → necháme stávající pořadí (aktuální layout),
      ale přepočítáme pouze hranice (SEED/DA/Q/RESERVE).
    """
    draw_size, qualifiers_count, qual_rounds = _eff_draw_params(t)
    S = _eff_md_seeds(t)
    D = draw_size - qualifiers_count
    Qdraw = qualifiers_count * (2**qual_rounds)

    # Aktuální layout — použijeme, pokud seeding_source == NONE
    cur_rows = _current_layout(t, entries, S, D, Qdraw)

    # 1) Základní pořadí pro řazení
    if seeding_source == SeedingSource.NONE:
        # zachovej aktuální pořadí; poskládáme list v aktuálním pořadí WR jen pro hranice
        ordered = [
            next(e for e in entries if e.id == r.entry_id) for r in cur_rows
        ]  # SEED→DA→Q→RESERVE
    else:
        # SNAPSHOT/CURRENT (zatím oboje = podle Entry.wr)
        ordered = _sort_by_wr(entries)

    # 2) Vytvoř DA kandidáty (prvních D podle `ordered`), ale respektuj promoted_by_wc
    da_candidates = ordered[:D]
    extra_wc = [e for e in ordered[D:] if e.promoted_by_wc]
    da_all = da_candidates + extra_wc
    # Pokud překročíme D, musíme „vyhodit“ nejhorší nepovýšené
    if len(da_all) > D:
        # seřaď da_all podle WR; vyhazuj ty, co nejsou promoted_by_wc, od nejhorších
        da_sorted = _sort_by_wr(da_all)
        # kolik musíme vyhodit
        to_drop = len(da_all) - D
        kept: list[EntryState] = []
        dropped = 0
        for e in da_sorted:
            if not e.promoted_by_wc and dropped < to_drop:
                dropped += 1
                continue
            kept.append(e)
        da_all = kept  # přesně D kusů

    # 3) SEEDS = top S uvnitř DA_all (podle WR)
    seeds_sorted = _sort_by_wr(da_all)[:S]
    seed_ids = {e.id for e in seeds_sorted}

    # 4) Zbytek DA = DA_all bez seeds (po WR)
    da_rest = [e for e in _sort_by_wr(da_all) if e.id not in seed_ids]

    # 5) Q = další Qdraw hráčů z `ordered` mimo DA_all, s povýšením QWC
    taken_ids = {e.id for e in da_all}
    q_base_pool = [e for e in ordered if e.id not in taken_ids]
    q_initial = q_base_pool[:Qdraw]
    # QWC povýšení: každý s promoted_by_qwc=True MUSÍ být v Q (pokud je místo),
    # QWC, kteří by byli v Q i bez povýšení, limit NEčerpají (flag promoted_by_qwc=True by neměl být nastaven).
    promoted_qwc = [e for e in q_base_pool if e.promoted_by_qwc]
    q_final = list(q_initial)
    for e in promoted_qwc:
        if e not in q_final and len(q_final) < Qdraw:
            q_final.append(e)
    if len(q_final) > Qdraw:
        # drop nejhorší NE-QWC, aby se vešli povýšení; pokud i tak přetéká (všichni jsou QWC),
        # zkrať stabilně podle WR (MVP tolerance).
        q_final_sorted = _sort_by_wr(q_final)  # best→worst
        keep: list[EntryState] = []
        to_keep = Qdraw
        # nejdřív přidej všechny QWC (v WR pořadí)
        for e in [x for x in q_final_sorted if x.promoted_by_qwc]:
            if len(keep) < to_keep:
                keep.append(e)
        # doplň zbytkem ne-QWC v WR pořadí
        for e in [x for x in q_final_sorted if not x.promoted_by_qwc]:
            if len(keep) < to_keep:
                keep.append(e)
        q_final = keep
    q_final = _sort_by_wr(q_final)
    q_ids = {e.id for e in q_final}

    # 6) RESERVE = zbytek
    taken_ids |= q_ids
    reserve = [e for e in ordered if e.id not in taken_ids]

    def _rows(group: Group, items: list[EntryState]) -> list[Row]:
        return [
            Row(entry_id=e.id, group=group, index=i, separator_after=(i == len(items) - 1))
            for i, e in enumerate(items)
        ]

    rows: list[Row] = []
    rows += _rows(Group.SEED, seeds_sorted)
    rows += _rows(Group.DA, da_rest)
    rows += _rows(Group.Q, q_final)
    rows += _rows(Group.RESERVE, reserve)

    # počty WC/QWC (počítáme skutečně využité – v navržených blocích)
    wc_used = sum(1 for e in da_all if e.promoted_by_wc)
    qwc_used = sum(1 for e in q_final if e.promoted_by_qwc)

    counters = dict(
        S=S,
        D=D,
        Q_draw_size=Qdraw,
        WC_used=wc_used,
        WC_limit=_eff_wc_limit(t),
        QWC_used=qwc_used,
        QWC_limit=_eff_qwc_limit(t),
    )
    return rows, counters


def _diff(current: list[Row], proposed: list[Row]) -> list[tuple[int, Group, Group]]:
    cur_map = {r.entry_id: r.group for r in current}
    out: list[tuple[int, Group, Group]] = []
    for r in proposed:
        g0 = cur_map.get(r.entry_id)
        if g0 is None:
            continue
        if g0 != r.group:
            out.append((r.entry_id, g0, r.group))
    return out


# --------- public API ---------


@atomic()
def preview_recalculate_registration(
    t: Tournament, *, seeding_source: str | None = None
) -> Preview:
    """
    Vypočítá návrh rozložení (SEED/DA/Q/RESERVE) a vrátí diff vůči aktuálnímu stavu.
    NIC NEUKLÁDÁ.
    """
    src = seeding_source or t.seeding_source or SeedingSource.SNAPSHOT
    if src == SeedingSource.SNAPSHOT:
        ensure_seeding_baseline(t)
    entries = _entries_active(t)
    draw_size, qualifiers_count, qual_rounds = _eff_draw_params(t)
    S = _eff_md_seeds(t)
    D = draw_size - qualifiers_count
    Qdraw = qualifiers_count * (2**qual_rounds)

    current = _current_layout(t, entries, S, D, Qdraw)
    proposed, counters = _proposed_layout(t, entries, src)
    moves = _diff(current, proposed)

    return Preview(
        current=current,
        proposed=proposed,
        moves=moves,
        counters=counters,
        rng_seed=t.rng_seed_active,
    )


@require_admin_mode
@atomic()
def confirm_recalculate_registration(t: Tournament, preview: Preview) -> None:
    """
    Aplikuje návrh:
      - nastaví TournamentEntry.entry_type podle skupiny (SEED/DA→DA, Q→Q, RESERVE→ALT),
      - u SEED nastaví `seed` = 1..S; ostatním `seed=None`,
      - nastaví `position` = pořadí v rámci registrace (SEED→DA→Q→RESERVE; 1..N).
    """
    src = t.seeding_source or SeedingSource.SNAPSHOT
    if src == SeedingSource.SNAPSHOT:
        ensure_seeding_baseline(t)
    # pro jistotu ověř, že preview odpovídá aktuální sadě entry (alespoň počtem)
    ids_now = set(
        TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE).values_list(
            "id", flat=True
        )
    )
    ids_in_preview = {r.entry_id for r in (preview.current + preview.proposed)}
    if not ids_in_preview.issuperset(ids_now):
        # nejsme tvrdí — jen varování do výjimky
        raise ValidationError(
            "Preview neodpovídá aktuálním registracím (změnily se položky). Vygeneruj znovu."
        )

    # Limity WC/QWC – blokace uložení při překročení
    wc_used = int(preview.counters.get("WC_used", 0))
    wc_limit = int(preview.counters.get("WC_limit", 0))
    qwc_used = int(preview.counters.get("QWC_used", 0))
    qwc_limit = int(preview.counters.get("QWC_limit", 0))
    errs: list[str] = []
    if wc_used > wc_limit:
        errs.append(f"WC limit exceeded: used {wc_used} > limit {wc_limit}.")
    if qwc_used > qwc_limit:
        errs.append(f"QWC limit exceeded: used {qwc_used} > limit {qwc_limit}.")
    if errs:
        raise ValidationError(" | ".join(errs))

    # 1) aplikuj typy a seedy
    # pořadí pro position
    ordered = preview.proposed
    order_index = {r.entry_id: i + 1 for i, r in enumerate(ordered)}  # 1..N
    seed_counter = 0
    for r in ordered:
        te = locked(TournamentEntry.objects.filter(pk=r.entry_id)).get()
        if r.group == Group.SEED:
            seed_counter += 1
            te.entry_type = EntryType.DA
            te.seed = seed_counter
        elif r.group == Group.DA:
            te.entry_type = EntryType.DA
            te.seed = None
        elif r.group == Group.Q:
            te.entry_type = EntryType.Q
            te.seed = None
        else:
            te.entry_type = EntryType.ALT
            te.seed = None
        te.position = order_index[r.entry_id]
        te.save(update_fields=["entry_type", "seed", "position"])

    # u všech, kteří nejsou v ordered (teoreticky žádní), vynuluj seed/position
    other_qs = TournamentEntry.objects.filter(tournament=t).exclude(pk__in=order_index.keys())
    for te in other_qs:
        if te.seed or te.position:
            te.seed = None
            te.position = None
            te.save(update_fields=["seed", "position"])


@require_admin_mode
@atomic()
def brutal_reset_to_registration(t: Tournament, reason: str = "PARAM_CHANGE") -> None:
    """
    Uloží ARCHIVNÍ SNAPSHOT (lightweight) a vyčistí:
      - smaže všechny zápasy (QUAL/MD),
      - smaže plán (Schedule se smaže cascade přes Match),
      - zruší MD sloty (`position`) a seedy,
      - turnaj ponechá v REG fázi bez dotčení registrací (Entry zůstávají ACTIVE).
    """
    # 0) archivní snapshot (jen lehký payload, ať je to rychlé)
    entries = list(
        TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE).values(
            "id", "player_id", "entry_type", "seed", "wr_snapshot", "position"
        )
    )
    payload = dict(
        reason=reason,
        t_id=t.id,
        rng_seed=t.rng_seed_active,
        entries=entries,
        counts=dict(
            matches=t.match_set.count() if hasattr(t, "match_set") else 0,
        ),
    )
    Snapshot.objects.create(tournament=t, type=Snapshot.SnapshotType.BRUTAL, payload=payload)
    from msa.services.archiver import enforce_archive_limits

    enforce_archive_limits(t)

    # 1) smaž zápasy (cascade smaže Schedule)
    from msa.models import Match

    Match.objects.filter(tournament=t).delete()

    # 2) nuluj sloty/seed
    for te in TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE):
        if te.position is not None or te.seed is not None:
            te.position = None
            te.seed = None
            te.save(update_fields=["position", "seed"])

    # 3) nepřepisujeme entry_type (registrace zůstává), jen případně přepneme turnaj do REG
    if t.state != "REG":
        t.state = "REG"
        t.save(update_fields=["state"])
