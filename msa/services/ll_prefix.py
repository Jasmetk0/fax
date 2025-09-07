# msa/services/ll_prefix.py
from typing import List, Tuple, Optional
from dataclasses import dataclass

from django.db.models import Q
from django.core.exceptions import ValidationError

from msa.models import Tournament, TournamentEntry, EntryType, EntryStatus
from msa.services.tx import atomic


@dataclass(frozen=True)
class LLEntryView:
    id: int
    player_id: int
    wr_snapshot: Optional[int]  # None = NR
    position: Optional[int]     # None = ještě nepřiřazen v MD


def _ll_queryset(t: Tournament):
    # Všichni LL (ať už přiřazení do MD/slotu, nebo volní v poolu)
    return (
        TournamentEntry.objects
        .filter(tournament=t, entry_type=EntryType.LL, status=EntryStatus.ACTIVE)
    )


def _assigned_ll_queryset(t: Tournament):
    # LL, kteří už sedí v MD (mají pozici/slot)
    return _ll_queryset(t).filter(position__isnull=False)


def _free_ll_queryset(t: Tournament):
    # LL k dispozici (prefix fronty, dosud nepřiřazeni do MD)
    return _ll_queryset(t).filter(position__isnull=True)


def _alt_queryset(t: Tournament):
    # Rezervy/alternates, dosud neobsazené v MD
    return (
        TournamentEntry.objects
        .filter(tournament=t, entry_type=EntryType.ALT, status=EntryStatus.ACTIVE, position__isnull=True)
    )


def _md_slot_taken(t: Tournament, slot: int) -> bool:
    return TournamentEntry.objects.filter(
        tournament=t, status=EntryStatus.ACTIVE, position=slot
    ).exists()


def _ll_queue_sorted(qs) -> List[LLEntryView]:
    """
    Fronta LL dle specifikace: WR snapshot vzestupně, NR (None) na konec.
    Tie-break stabilně podle PK.
    """
    items = [
        LLEntryView(id=te.id, player_id=te.player_id, wr_snapshot=te.wr_snapshot, position=te.position)
        for te in qs.order_by("wr_snapshot__isnull", "wr_snapshot", "id")
    ]
    # Pozn.: order_by("wr_snapshot__isnull", "wr_snapshot", "id") → None (NR) až za čísly.
    return items


def get_ll_queue(t: Tournament) -> List[LLEntryView]:
    """Vrátí celou LL frontu (přiřazení i volní), v pořadí pravidel."""
    return _ll_queue_sorted(_ll_queryset(t))


@atomic()
def fill_vacant_slot_prefer_ll_then_alt(t: Tournament, slot: int) -> TournamentEntry:
    """
    Když vznikne díra v MD (slot bez hráče), dosadí:
      1) LL #1 z fronty, který zatím není v MD (position is NULL),
      2) jinak ALT (Reserve) s position=NULL.
    Zachovává prefix invariant (po dosazení).
    """
    if _md_slot_taken(t, slot):
        raise ValidationError(f"Slot {slot} není volný.")

    # Kandidát LL
    ll_free = _ll_queue_sorted(_free_ll_queryset(t))
    if ll_free:
        chosen_ll_id = ll_free[0].id  # první volný z fronty
        te = TournamentEntry.objects.select_for_update().get(pk=chosen_ll_id)
        te.position = slot
        te.save(update_fields=["position"])
        # Po dosazení jen pro jistotu srovnáme prefix (kdyby někdo manuálně přehodil).
        enforce_ll_prefix_in_md(t)
        return te

    # Fallback: ALT
    alt = _alt_queryset(t).order_by("id").first()
    if alt:
        alt = TournamentEntry.objects.select_for_update().get(pk=alt.pk)
        alt.position = slot
        alt.save(update_fields=["position"])
        return alt

    raise ValidationError("Nejsou k dispozici LL ani ALT k obsazení slotu.")


@atomic()
def enforce_ll_prefix_in_md(t: Tournament) -> None:
    """
    Udrž prefix invariant: množina LL v MD musí být přesně prefix LL fronty délky k,
    kde k = počet aktuálně přiřazených LL v MD.
    Pokud je v MD „špatný“ LL (mimo prefix), nahradí se chybějícím LL z prefixu,
    a zachová se DOLE slot (tj. nový LL přebere slot toho špatného).
    """
    # Zámek na všech LL v turnaji (aby se v race neděly změny).
    ll_all = list(_ll_queryset(t).select_for_update())

    assigned = [te for te in ll_all if te.position is not None]
    k = len(assigned)
    if k == 0:
        return  # nic k řešení

    queue = _ll_queue_sorted(_ll_queryset(t))
    wanted_ids = set(x.id for x in queue[:k])
    assigned_ids = set(te.id for te in assigned)

    if assigned_ids == wanted_ids:
        return  # už je to v pořádku

    # Kdo v MD být má, ale není
    missing_ids = [x.id for x in queue[:k] if x.id not in assigned_ids]
    # Kdo v MD je, ale být nemá
    extra = [te for te in assigned if te.id not in wanted_ids]

    # Pro každý „extra“ LL v MD dosadíme do jeho slotu prvního „missing“
    # a extra LL vyhodíme z MD (position=NULL).
    for extra_te in extra:
        if not missing_ids:
            break
        missing_id = missing_ids.pop(0)
        new_te = TournamentEntry.objects.select_for_update().get(pk=missing_id)
        # Přebírá slot po „extra“
        new_te.position = extra_te.position
        new_te.save(update_fields=["position"])
        # Extra jde z MD pryč
        extra_te.position = None
        extra_te.save(update_fields=["position"])


@atomic()
def reinstate_original_player(t: Tournament, original_entry_id: int, slot: int) -> None:
    """
    Reinstat původního hráče do jeho slotu.
    Dovoleno JEN tak, že se odebere „nejhorší“ právě nasazený LL (poslední v prefixu).
    Postup:
      - najdi nejhorší aktuálně nasazený LL (podle LL fronty),
      - hráče, který sedí v `slot` (typicky LL), přesuneme do slotu nejhoršího LL,
      - nejhorší LL vyhodíme z MD (position=NULL),
      - původního hráče dáme do `slot`.
    Pokud už v `slot` není LL (tj. je prázdný), jen odeber nejhoršího LL a dej tam původního hráče.
    """
    # Lock všech relevantních řádků
    ll_assigned = list(_assigned_ll_queryset(t).select_for_update())
    # Pokud není nasazen žádný LL, prostě jen vrať hráče do slotu
    # (ale ověř, že slot není obsazen)
    original = TournamentEntry.objects.select_for_update().get(pk=original_entry_id)
    if _md_slot_taken(t, slot):
        # slot je obsazen – typicky LL, jinak fail
        occupant = TournamentEntry.objects.select_for_update().get(
            tournament=t, status=EntryStatus.ACTIVE, position=slot
        )
    else:
        occupant = None

    if not ll_assigned:
        # Bez LL jen vrať hráče do slotu, pokud to dává smysl
        if occupant and occupant.id != original.id:
            raise ValidationError("Slot je obsazen jiným hráčem a v MD není LL – nelze reinstat bez manuálního zásahu.")
        original.position = slot
        original.save(update_fields=["position"])
        return

    # Seřaď podle LL fronty a vezmi „nejhoršího“ z nasazených
    queue = get_ll_queue(t)
    # map id -> queue index
    order_index = {v.id: i for i, v in enumerate(queue)}
    worst_ll = max(ll_assigned, key=lambda te: order_index.get(te.id, 1_000_000))

    worst_slot = worst_ll.position
    assert worst_slot is not None

    if occupant and occupant.entry_type == EntryType.LL and occupant.id != worst_ll.id:
        # přesuneme LL ze slotu do slotu „worsta“
        occupant.position = worst_slot
        occupant.save(update_fields=["position"])
        # „worsta“ odstraníme z MD
        worst_ll.position = None
        worst_ll.save(update_fields=["position"])
    else:
        # v cílovém slotu není LL (nebo je tam rovnou worst) → jen odstraníme „worsta“
        worst_ll.position = None
        worst_ll.save(update_fields=["position"])

    # a vrátíme původního hráče do jeho slotu
    original.position = slot
    original.save(update_fields=["position"])

    # pro jistotu sjednotit prefix (např. když někdo ručně kouzlil)
    enforce_ll_prefix_in_md(t)
