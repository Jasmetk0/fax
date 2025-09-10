# msa/services/wc.py
from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError

from msa.models import EntryStatus, EntryType, Tournament, TournamentEntry

from .admin_gate import require_admin_mode
from .tx import atomic, locked


@dataclass(frozen=True)
class EntryView:
    id: int
    player_id: int
    entry_type: str
    wr_snapshot: int | None  # None = NR
    is_wc: bool
    is_qwc: bool
    promoted_by_wc: bool
    promoted_by_qwc: bool


# ---------- helpers ----------


def _eff_wc_slots(t: Tournament) -> int:
    cs = t.category_season
    base = int(cs.wc_slots_default or 0) if cs else 0
    return int(t.wc_slots) if t.wc_slots is not None else base


def _eff_qwc_slots(t: Tournament) -> int:
    cs = t.category_season
    base = int(cs.q_wc_slots_default or 0) if cs else 0
    return int(t.q_wc_slots) if t.q_wc_slots is not None else base


def _collect_entries(t: Tournament) -> list[EntryView]:
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
                is_wc=bool(te.is_wc),
                is_qwc=bool(te.is_qwc),
                promoted_by_wc=bool(te.promoted_by_wc),
                promoted_by_qwc=bool(te.promoted_by_qwc),
            )
        )
    return out


def _rank_key(ev: EntryView):
    # WR asc (1 nejlepší), NR (None) až nakonec; tie → stabilně podle id
    return (
        1 if ev.wr_snapshot is None else 0,
        ev.wr_snapshot if ev.wr_snapshot is not None else 10**9,
        ev.id,
    )


def _sorted_registration_pool(entries: list[EntryView]) -> list[EntryView]:
    # Registraci řadíme podle WR; NONE režim (free-drag) UI řeší mimo backend — tady držíme deterministiku.
    return sorted(entries, key=_rank_key)


def _cutline_D(t: Tournament) -> int:
    cs = t.category_season
    if not cs or not cs.draw_size:
        raise ValidationError("Chybí CategorySeason.draw_size.")
    qualifiers_count = t.qualifiers_count_effective
    return int(cs.draw_size) - qualifiers_count


def _used_wc_promotions(t: Tournament) -> int:
    return TournamentEntry.objects.filter(
        tournament=t, status=EntryStatus.ACTIVE, promoted_by_wc=True
    ).count()


def _used_qwc_promotions(t: Tournament) -> int:
    return TournamentEntry.objects.filter(
        tournament=t, status=EntryStatus.ACTIVE, promoted_by_qwc=True
    ).count()


# ---------- veřejné API ----------


@require_admin_mode
@atomic()
def set_wc_slots(t: Tournament, slots: int) -> None:
    """Nastaví wc_slots na turnaji; nesmí být pod aktuálním využitím (promoted_by_wc)."""
    if slots < 0:
        raise ValidationError("wc_slots nesmí být záporné.")
    used = _used_wc_promotions(t)
    if slots < used:
        raise ValidationError(
            f"Nelze snížit wc_slots na {slots}, použito {used}. Nejprve odeber přebytečná WC."
        )
    t.wc_slots = slots
    t.save(update_fields=["wc_slots"])


@require_admin_mode
@atomic()
def set_q_wc_slots(t: Tournament, slots: int) -> None:
    """Nastaví q_wc_slots; nesmí být pod aktuálním využitím (promoted_by_qwc)."""
    if slots < 0:
        raise ValidationError("q_wc_slots nesmí být záporné.")
    used = _used_qwc_promotions(t)
    if slots < used:
        raise ValidationError(
            f"Nelze snížit q_wc_slots na {slots}, použito {used}. Nejprve odeber přebytečné QWC."
        )
    t.q_wc_slots = slots
    t.save(update_fields=["q_wc_slots"])


@require_admin_mode
@atomic()
def apply_wc(t: Tournament, entry_id: int) -> None:
    """
    WC (hlavní pole):
      - hráč NAD čarou → jen štítek is_wc=True (nečerpá limit).
      - hráč POD čarou → povýší do DA (promoted_by_wc=True) a čerpá wc_slots; poslední DA padá do Q.
    """
    D = _cutline_D(t)
    entries = _sorted_registration_pool(_collect_entries(t))
    # Pozice v registraci (0-based, menší = lepší)
    index = {e.id: i for i, e in enumerate(entries)}
    if entry_id not in index:
        raise ValidationError("Entry neexistuje nebo není aktivní.")
    i_target = index[entry_id]

    te = locked(TournamentEntry.objects.filter(pk=entry_id)).get()
    # mark label
    te.is_wc = True

    if i_target < D:
        # nad čarou → jen label
        te.promoted_by_wc = False
        te.entry_type = EntryType.DA
        te.save(update_fields=["is_wc", "promoted_by_wc", "entry_type"])
        return

    # pod čarou → potřebujeme slot
    max_slots = _eff_wc_slots(t)
    used = _used_wc_promotions(t)
    if used >= max_slots:
        raise ValidationError(f"Nedostatek WC slotů (použito {used}/{max_slots}).")

    # povýšit target do DA
    te.entry_type = EntryType.DA
    te.promoted_by_wc = True
    te.save(update_fields=["is_wc", "promoted_by_wc", "entry_type"])

    # poslední DA padá do Q (vyber nejhoršího DA nepovýšeného WC)
    # přepočti pool (kvůli změně) a vezmi DA kandidáty
    entries2 = _sorted_registration_pool(_collect_entries(t))
    da_ids_in_order = [e.id for e in entries2[:D]]
    # Z DA sestavy vyber posledního, který NENÍ promoted_by_wc a NENÍ target (bezpečnost)
    last_da = None
    for eid in reversed(da_ids_in_order):
        if eid == te.id:
            continue
        x = TournamentEntry.objects.get(pk=eid)
        if not x.promoted_by_wc:
            last_da = x
            break
    if last_da:
        last_da.entry_type = EntryType.Q
        # Pozn.: index bereme ze snapshotu před povýšením targetu do DA.
        # Pokud byl last_da „nad čarou“ (měl index < D), zachováme mu vizuální WC label.
        last_da.is_wc = bool(last_da.is_wc and index.get(last_da.id, 0) < D)
        last_da.save(update_fields=["entry_type", "is_wc"])


@require_admin_mode
@atomic()
def remove_wc(t: Tournament, entry_id: int) -> None:
    """
    Odebere WC label. Pokud byl hráč povýšen (promoted_by_wc=True), vrátí ho do Q
    a do DA dosadí nejlepšího mimo čáru (WR nejblíž čáře).
    """
    te = locked(TournamentEntry.objects.filter(pk=entry_id)).get()
    if not te.is_wc:
        return
    was_promoted = bool(te.promoted_by_wc)
    te.is_wc = False
    te.promoted_by_wc = False
    if was_promoted:
        te.entry_type = EntryType.Q
    te.save(update_fields=["is_wc", "promoted_by_wc", "entry_type"])

    if was_promoted:
        # doplnit DA: vezmi nejlepšího mimo čáru
        D = _cutline_D(t)
        entries = _sorted_registration_pool(_collect_entries(t))
        # kandidáti pod čarou, kteří nejsou promoted_by_wc
        for ev in entries[D:]:
            cand = locked(TournamentEntry.objects.filter(pk=ev.id)).get()
            if not cand.promoted_by_wc:
                cand.entry_type = EntryType.DA
                cand.save(update_fields=["entry_type"])
                break


@require_admin_mode
@atomic()
def apply_qwc(t: Tournament, entry_id: int) -> None:
    """
    QWC:
      - hráč v Q → jen is_qwc=True (nečerpá slot),
      - hráč v Reserve/ALT → povýší do Q (promoted_by_qwc=True), čerpá q_wc_slots.
    """
    te = locked(TournamentEntry.objects.filter(pk=entry_id)).get()
    te.is_qwc = True

    if te.entry_type == EntryType.Q:
        te.promoted_by_qwc = False
        te.save(update_fields=["is_qwc", "promoted_by_qwc"])
        return

    # ALT → Q s čerpáním
    if te.entry_type != EntryType.ALT:
        raise ValidationError("QWC lze aplikovat jen na hráče v Q nebo Reserve (ALT).")

    max_slots = _eff_qwc_slots(t)
    used = _used_qwc_promotions(t)
    if used >= max_slots:
        raise ValidationError(f"Nedostatek QWC slotů (použito {used}/{max_slots}).")

    te.entry_type = EntryType.Q
    te.promoted_by_qwc = True
    te.save(update_fields=["is_qwc", "promoted_by_qwc", "entry_type"])


@require_admin_mode
@atomic()
def remove_qwc(t: Tournament, entry_id: int) -> None:
    """
    Odebere QWC label; pokud byl hráč povýšen QWC (ALT→Q), vrátí ho zpět do ALT.
    """
    te = locked(TournamentEntry.objects.filter(pk=entry_id)).get()
    if not te.is_qwc:
        return
    was_promoted = bool(te.promoted_by_qwc)
    te.is_qwc = False
    te.promoted_by_qwc = False
    if was_promoted:
        te.entry_type = EntryType.ALT
    te.save(update_fields=["is_qwc", "promoted_by_qwc", "entry_type"])
