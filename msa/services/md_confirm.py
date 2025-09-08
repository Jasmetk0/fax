# msa/services/md_confirm.py
from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError

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
from msa.services.md_embed import (
    effective_template_size_for_md,
    generate_md_mapping_with_byes,
    pairings_round1,
    r1_name_for_md,
)
from msa.services.md_generator import generate_main_draw_mapping
from msa.services.tx import atomic, locked

# ---------- pomocné datové struktury ----------

ENTRY_PRIORITY = {
    EntryType.DA: 0,
    EntryType.WC: 1,
    EntryType.Q: 2,
    EntryType.LL: 3,
    EntryType.ALT: 4,
}


@dataclass(frozen=True)
class EntryView:
    id: int
    player_id: int
    entry_type: str
    wr_snapshot: int | None  # None = NR
    seed: int | None  # volitelné, ale nepoužíváme pro pořadí (zatím)


# ---------- utilitky ----------


def _default_seeds_count(draw_size: int) -> int:
    """Fallback, když není nastaveno md_seeds_count (měkké modely)."""
    if draw_size >= 64:
        return 16
    if draw_size >= 32:
        return 8
    if draw_size >= 16:
        return 4
    return 0


def _collect_active_entries(t: Tournament) -> list[EntryView]:
    qs = TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE).select_related(
        "player"
    )
    out: list[EntryView] = []
    for te in qs:
        out.append(
            EntryView(
                id=te.id,
                player_id=te.player_id,
                entry_type=te.entry_type,
                wr_snapshot=te.wr_snapshot,
                seed=te.seed,
            )
        )
    return out


def _sort_key_for_unseeded(ev: EntryView):
    # bloky: DA → WC → Q → LL → ALT; uvnitř WR asc, NR (None) až nakonec
    return (
        ENTRY_PRIORITY.get(ev.entry_type, 99),
        1 if ev.wr_snapshot is None else 0,
        ev.wr_snapshot if ev.wr_snapshot is not None else 10**9,
        ev.id,
    )


def _pick_seeds_and_unseeded(
    t: Tournament, entries: list[EntryView]
) -> tuple[list[EntryView], list[EntryView], int]:
    draw_size = (
        t.category_season.draw_size if t.category_season and t.category_season.draw_size else 0
    )
    if not draw_size:
        raise ValidationError("Tournament.category_season.draw_size není nastaven.")

    S = (
        t.category_season.md_seeds_count
        if (t.category_season and t.category_season.md_seeds_count)
        else _default_seeds_count(draw_size)
    )

    # seedy bereme **podle WR** (nejlepší první), NR na konec
    sorted_by_wr = sorted(
        entries,
        key=lambda ev: (
            1 if ev.wr_snapshot is None else 0,
            ev.wr_snapshot if ev.wr_snapshot is not None else 10**9,
            ev.id,
        ),
    )
    seeds = sorted_by_wr[:S]
    seed_ids = {e.id for e in seeds}

    # zbytek tvoří nenasazené v blocích DA→WC→Q→LL→ALT (jen pořadí poolu; do slotů půjde shuffle)
    unseeded = [e for e in entries if e.id not in seed_ids]
    unseeded.sort(key=_sort_key_for_unseeded)

    needed_unseeded = draw_size - len(seeds)
    if len(unseeded) < needed_unseeded:
        raise ValidationError(
            f"Nedostatek hráčů: draw_size={draw_size}, seeds={len(seeds)}, unseeded={len(unseeded)}"
        )

    return seeds, unseeded[:needed_unseeded], draw_size


# (odstraněno) Lokální _pairings_round1 – používáme md_embed.pairings_round1


def _entry_map_by_id(entries: list[EntryView]) -> dict[int, EntryView]:
    return {e.id: e for e in entries}


def _slot_to_entry_id(mapping: dict[int, int]) -> dict[int, int]:
    """mapping {slot -> entry_id} už je v ID, takže jen typový alias."""
    return mapping


# ---------- veřejné služby ----------


@atomic()
def confirm_main_draw(t: Tournament, rng_seed: int) -> dict[int, int]:
    """
    Podporuje i embed (např. draw 24 → šablona 32, BYE pro top (32-24) seedů).
    """
    # zamkni entries
    entries_qs = locked(TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE))
    entries = _collect_active_entries(t)

    # parametry
    draw_size = (
        int(t.category_season.draw_size)
        if (t.category_season and t.category_season.draw_size)
        else 0
    )
    if not draw_size:
        raise ValidationError("Tournament.category_season.draw_size není nastaven.")
    template_size = effective_template_size_for_md(t)
    bye_count = template_size - draw_size

    seeds, unseeded, _ = _pick_seeds_and_unseeded(t, entries)
    seeds_in_order = [e.id for e in seeds]
    unseeded_ids = [e.id for e in unseeded]

    if bye_count <= 0:
        # klasika (power-of-two)
        slot_to_entry_id = generate_main_draw_mapping(
            draw_size=draw_size,
            seeds_in_order=seeds_in_order,
            unseeded_players=unseeded_ids,
            rng_seed=rng_seed,
        )
        r1_name = f"R{draw_size}"
        pairs = pairings_round1(draw_size)
    else:
        # embed do šablony
        slot_to_entry_id = generate_md_mapping_with_byes(
            template_size=template_size,
            seeds_in_order=seeds_in_order,
            unseeded_players=unseeded_ids,
            bye_count=bye_count,
            rng_seed=rng_seed,
        )
        r1_name = r1_name_for_md(t)
        pairs = pairings_round1(template_size)

    # 1) ulož pozice
    id_to_slot = {eid: slot for slot, eid in slot_to_entry_id.items()}
    for te in entries_qs:
        new_pos = id_to_slot.get(te.id)
        if new_pos is not None:
            if te.position != new_pos:
                te.position = new_pos
                te.save(update_fields=["position"])
        else:
            if te.position is not None:
                te.position = None
                te.save(update_fields=["position"])

    # 2) R1 zápasy — smaž a vytvoř jen páry, kde máme OBA hráče
    Match.objects.filter(tournament=t, phase=Phase.MD, round_name=r1_name).delete()
    id2entry = {e.id: e for e in entries}
    slot_to_player = {slot: id2entry[eid].player_id for slot, eid in slot_to_entry_id.items()}

    bulk: list[Match] = []
    for a, b in pairs:
        pa = slot_to_player.get(a)
        pb = slot_to_player.get(b)
        if pa is None or pb is None:
            # BYE zápasy se nevytváří — vítěz „čeká“ do dalšího kola.
            continue
        bulk.append(
            Match(
                tournament=t,
                phase=Phase.MD,
                round_name=r1_name,
                slot_top=a,
                slot_bottom=b,
                player_top_id=pa,
                player_bottom_id=pb,
                best_of=t.md_best_of or 5,
                win_by_two=True,
                state=MatchState.PENDING,
            )
        )
    Match.objects.bulk_create(bulk, ignore_conflicts=True)

    # 3) rng seed
    if t.rng_seed_active != rng_seed:
        t.rng_seed_active = rng_seed
        t.save(update_fields=["rng_seed_active"])

    return slot_to_entry_id


@atomic()
def hard_regenerate_unseeded_md(t: Tournament, rng_seed: int) -> dict[int, int]:
    """
    Respektuje BYE páry (embed). Seedy drží kotvy; nenasazené se přelosují.
    U dotčených R1 párů smaže výsledky (HARD). Páry, které jsou BYE, udržuje neexistující.
    """
    entries_qs = locked(TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE))
    draw_size = (
        int(t.category_season.draw_size)
        if (t.category_season and t.category_season.draw_size)
        else 0
    )
    if not draw_size:
        raise ValidationError("Tournament.category_season.draw_size není nastaven.")
    template_size = effective_template_size_for_md(t)
    bye_count = template_size - draw_size
    r1_name = r1_name_for_md(t)

    entries = _collect_active_entries(t)
    seeds, unseeded, _ = _pick_seeds_and_unseeded(t, entries)
    seeds_in_order = [e.id for e in seeds]
    unseeded_ids = [e.id for e in unseeded]

    if bye_count <= 0:
        new_slot_to_entry_id = generate_main_draw_mapping(
            draw_size=draw_size,
            seeds_in_order=seeds_in_order,
            unseeded_players=unseeded_ids,
            rng_seed=rng_seed,
        )
        pairs = pairings_round1(draw_size)
    else:
        new_slot_to_entry_id = generate_md_mapping_with_byes(
            template_size=template_size,
            seeds_in_order=seeds_in_order,
            unseeded_players=unseeded_ids,
            bye_count=bye_count,
            rng_seed=rng_seed,
        )
        pairs = pairings_round1(template_size)

    # starý mapping (z position)
    old_slot_to_entry_id: dict[int, int] = {}
    for te in entries_qs:
        if te.position is not None:
            old_slot_to_entry_id[int(te.position)] = te.id

    # ulož nové pozice
    id_to_slot = {eid: slot for slot, eid in new_slot_to_entry_id.items()}
    for te in entries_qs:
        new_pos = id_to_slot.get(te.id)
        if new_pos is not None:
            if te.position != new_pos:
                te.position = new_pos
                te.save(update_fields=["position"])
        else:
            if te.position is not None:
                te.position = None
                te.save(update_fields=["position"])

    # aktualizuj R1
    id2entry = {e.id: e for e in entries}
    slot_to_player = {slot: id2entry[eid].player_id for slot, eid in new_slot_to_entry_id.items()}

    matches_qs = locked(Match.objects.filter(tournament=t, phase=Phase.MD, round_name=r1_name))
    existing_by_pair = {(m.slot_top, m.slot_bottom): m for m in matches_qs}

    # 1) u párů, které mají nově BYE (některý hráč chybí), zápas smaž
    for a, b in list(existing_by_pair.keys()):
        pa = slot_to_player.get(a)
        pb = slot_to_player.get(b)
        if pa is None or pb is None:
            existing_by_pair[(a, b)].delete()
            existing_by_pair.pop((a, b), None)

    # 2) pro všechny „plné“ páry nastav nové hráče a smaž výsledky (HARD)
    for a, b in pairs:
        pa = slot_to_player.get(a)
        pb = slot_to_player.get(b)
        if pa is None or pb is None:
            continue
        m = existing_by_pair.get((a, b))
        if not m:
            # dříve BYE, nyní plný — u embed by se to stát nemělo (BYE závisí jen na seedech), ale pro úplnost:
            m = Match.objects.create(
                tournament=t,
                phase=Phase.MD,
                round_name=r1_name,
                slot_top=a,
                slot_bottom=b,
                player_top_id=pa,
                player_bottom_id=pb,
                best_of=t.md_best_of or 5,
                win_by_two=True,
                state=MatchState.PENDING,
            )
        else:
            if (m.player_top_id, m.player_bottom_id) != (pa, pb):
                m.player_top_id = pa
                m.player_bottom_id = pb
            m.winner_id = None
            m.score = {}
            m.state = MatchState.PENDING
            m.save(update_fields=["player_top", "player_bottom", "winner", "score", "state"])
            # plán už nemusí odpovídat nové dvojici → smaž Schedule pro tento match
            Schedule.objects.filter(match=m).delete()

    if t.rng_seed_active != rng_seed:
        t.rng_seed_active = rng_seed
        t.save(update_fields=["rng_seed_active"])

    return new_slot_to_entry_id
