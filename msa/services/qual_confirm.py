# msa/services/qual_confirm.py
from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError

from msa.models import (
    EntryStatus,
    EntryType,
    Match,
    MatchState,
    Phase,
    Snapshot,
    Tournament,
    TournamentEntry,
)
from msa.services.admin_gate import require_admin_mode
from msa.services.archiver import archive
from msa.services.licenses import assert_all_licensed_or_raise
from msa.services.qual_generator import generate_qualification_mapping, seeds_per_bracket
from msa.services.round_format import get_round_format
from msa.services.tx import atomic, locked

# ---- Pomocné typy ----


@dataclass(frozen=True)
class EntryView:
    id: int
    player_id: int
    entry_type: str
    wr_snapshot: int | None  # None = NR


def _collect_qual_entries(t: Tournament) -> list[EntryView]:
    """
    Hráči způsobilí pro kvalifikaci: EntryType ∈ {Q, QWC}
    (QWC je label, ale v generátoru se chová jako Q).
    """
    qs = TournamentEntry.objects.filter(
        tournament=t, status=EntryStatus.ACTIVE, entry_type__in=[EntryType.Q, EntryType.QWC]
    ).select_related("player")
    out: list[EntryView] = []
    for te in qs:
        out.append(
            EntryView(
                id=te.id,
                player_id=te.player_id,
                entry_type=te.entry_type,
                wr_snapshot=te.wr_snapshot,
            )
        )
    return out


def _sort_by_wr(entries: list[EntryView]) -> list[EntryView]:
    # WR asc (1 nejlepší), NR (None) až nakonec, tie by PK (id)
    return sorted(
        entries,
        key=lambda ev: (
            1 if ev.wr_snapshot is None else 0,
            ev.wr_snapshot if ev.wr_snapshot is not None else 10**9,
            ev.id,
        ),
    )


def _round_name(size: int) -> str:
    """
    Round names pro kvaldu: Q{size}, například Q16, Q8, Q4, Q2 (finále).
    """
    return f"Q{size}"


def _pairs_for_size(size: int) -> list[tuple[int, int]]:
    """
    Standardní zrcadlové párování v rámci jedné větve (lokální sloty 1..size).
    """
    return [(i, size + 1 - i) for i in range(1, size // 2 + 1)]


@require_admin_mode
@atomic()
def confirm_qualification(t: Tournament, rng_seed: int) -> list[dict[int, int]]:
    """
    Vygeneruje a POTVRDÍ K kvalifikačních větví po R kolech:
      - vybere Q-seedy (globálně) dle WR: K * 2^(R-2) nejlepších,
      - rozloží je do větví po TIERECH (TOP, BOTTOM, MIDDLE_A, MIDDLE_B...),
      - nenasazené deterministicky promíchá a dosadí,
      - vytvoří celou stromovou strukturu zápasů: Q{2^R}, Q{2^(R-1)}, ..., Q2,
        ale hráče naplní jen v první rundě (Q{2^R}), zbytek zatím bez hráčů.
    Každá větev používá globálně unikátní sloty díky offsetu base = branch_index * 1000.
    Vrací seznam K dictů {local_slot -> entry_id} (mapping kvalifikací).
    """
    if (not t.qualifiers_count) or not (t.category_season and t.category_season.qual_rounds):
        raise ValidationError(
            "Tournament.qualifiers_count a CategorySeason.qual_rounds musí být nastavené."
        )

    # Licenční gate — musí mít licenci všichni ACTIVE (MVP: napříč typy)
    assert_all_licensed_or_raise(t)

    K = int(t.qualifiers_count or 0)
    R = int(t.category_season.qual_rounds)
    size = 2**R
    spb = seeds_per_bracket(R)  # 2^(R-2) nebo 0

    # zamkni všechny kvalifikační entries pro stabilitu
    _ = locked(TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE))

    entries = _collect_qual_entries(t)
    if not entries:
        raise ValidationError("Žádní hráči v kvalifikaci (EntryType Q/QWC).")

    # Seřadit WR + vybrat seedy
    sorted_by_wr = _sort_by_wr(entries)
    expected_seeds = K * spb
    if len(sorted_by_wr) < K * size:
        raise ValidationError(
            f"Nedostatek hráčů: potřeba {K*size}, máme {len(sorted_by_wr)} (Q + QWC)."
        )

    seeds = sorted_by_wr[:expected_seeds]
    unseeded = sorted_by_wr[
        expected_seeds:
    ]  # pořadí tady vlastně nevadí (generator stejně dělá shuffle)
    q_seed_ids = [e.id for e in seeds]
    q_unseed_ids = [e.id for e in unseeded[: (K * size - expected_seeds)]]

    # Vygenerovat mapping pro K větví
    branches = generate_qualification_mapping(
        K=K,
        R=R,
        q_seeds_in_order=q_seed_ids,
        unseeded_players=q_unseed_ids,
        rng_seed=rng_seed,
    )

    # Vytvořit zápasy pro všechny kola a větve, první kolo osadit hráči
    # Aby byly sloty globálně unikátní v rámci turnaje, použijeme offset base = b * 1000
    # (předpokládáme, že 1000 > max lokálních slotů).
    # Pokud už existují Q-zápasy (např. přegenerace), smažeme je a vytvoříme znovu.
    Match.objects.filter(tournament=t, phase=Phase.QUAL).delete()

    bulk_matches: list[Match] = []
    # Pro každou větev
    for b, mapping in enumerate(branches):
        base = b * 1000
        # 1) Vytvoř první kolo (Q{size}) s hráči
        for a, bslot in _pairs_for_size(size):
            slot_top = base + a
            slot_bot = base + bslot
            entry_top_id = mapping[a]
            entry_bot_id = mapping[bslot]
            # načíst player_id
            top = TournamentEntry.objects.get(pk=entry_top_id)
            bot = TournamentEntry.objects.get(pk=entry_bot_id)
            bo, wbt = get_round_format(t, Phase.QUAL, _round_name(size))
            m = Match(
                tournament=t,
                phase=Phase.QUAL,
                round_name=_round_name(size),
                slot_top=slot_top,
                slot_bottom=slot_bot,
                player_top_id=top.player_id,
                player_bottom_id=bot.player_id,
                best_of=bo,
                win_by_two=wbt,
                state=MatchState.PENDING,
            )
            bulk_matches.append(m)

        # 2) Vytvoř zbylá kola prázdná (bez hráčů) – Q{size/2}, ..., Q2
        cur = size // 2
        while cur >= 2:
            for a, bslot in _pairs_for_size(cur):
                slot_top = base + a
                slot_bot = base + bslot
                bo, wbt = get_round_format(t, Phase.QUAL, _round_name(cur))
                m = Match(
                    tournament=t,
                    phase=Phase.QUAL,
                    round_name=_round_name(cur),
                    slot_top=slot_top,
                    slot_bottom=slot_bot,
                    player_top_id=None,
                    player_bottom_id=None,
                    best_of=bo,
                    win_by_two=wbt,
                    state=MatchState.PENDING,
                )
                bulk_matches.append(m)
            cur //= 2

    Match.objects.bulk_create(bulk_matches, ignore_conflicts=True)

    # uložit rng_seed do turnaje (poslední použitý)
    if t.rng_seed_active != rng_seed:
        t.rng_seed_active = rng_seed
        t.save(update_fields=["rng_seed_active"])

    # archivní snapshot (CONFIRM_QUAL)
    archive(t, type=Snapshot.SnapshotType.CONFIRM_QUAL, label="confirm_qualification")

    return branches


@require_admin_mode
@atomic()
def update_ll_after_qual_finals(t: Tournament) -> int:
    """
    Najde všechny odehrané finále kvaldy (round_name='Q2') a pro poražené finalisty
    upraví jejich TournamentEntry.entry_type na LL (pokud už LL nejsou).
    Vrací počet nově „povýšených“ LL.
    """
    finals = list(
        Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name="Q2").exclude(
            winner_id=None
        )
    )
    promoted = 0
    for m in finals:
        # loser = druhý hráč ve finále
        if m.winner_id == m.player_top_id:
            loser_id = m.player_bottom_id
        else:
            loser_id = m.player_top_id
        if not loser_id:
            continue
        te = TournamentEntry.objects.filter(
            tournament=t, player_id=loser_id, status=EntryStatus.ACTIVE
        ).first()
        if not te:
            continue
        if te.entry_type != EntryType.LL:
            te.entry_type = EntryType.LL
            te.save(update_fields=["entry_type"])
            promoted += 1
    return promoted
