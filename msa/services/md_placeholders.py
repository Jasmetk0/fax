# msa/services/md_placeholders.py
from __future__ import annotations

from typing import List, Dict
from dataclasses import dataclass

from django.db.models import Q
from django.core.exceptions import ValidationError

from msa.models import (
    Tournament, TournamentEntry, Player,
    EntryType, EntryStatus, Phase, Match, MatchState
)
from msa.services.tx import atomic, locked
from msa.services.md_confirm import confirm_main_draw


PLACEHOLDER_PREFIX = "WINNER K#"


@dataclass(frozen=True)
class PlaceholderInfo:
    branch_index: int  # 0-based
    player_id: int
    entry_id: int


def _ensure_placeholder_player(branch_index: int) -> Player:
    name = f"{PLACEHOLDER_PREFIX}{branch_index+1}"
    p, _ = Player.objects.get_or_create(name=name)
    return p


def _existing_placeholder_entries(t: Tournament) -> List[PlaceholderInfo]:
    out: List[PlaceholderInfo] = []
    for te in TournamentEntry.objects.filter(tournament=t, entry_type=EntryType.Q, status=EntryStatus.ACTIVE).select_related("player"):
        if te.player and te.player.name and te.player.name.startswith(PLACEHOLDER_PREFIX):
            out.append(PlaceholderInfo(branch_index=int(te.player.name.split("#")[-1]) - 1,
                                       player_id=te.player_id, entry_id=te.id))
    return out


@atomic()
def create_md_placeholders(t: Tournament) -> List[PlaceholderInfo]:
    """
    Vytvoří K placeholder hráčů a TournamentEntry typu Q bez WR (NR),
    pokud ještě neexistují. Vrátí seznam placeholderů.
    """
    if not t.category_season or not t.category_season.qualifiers_count:
        raise ValidationError("CategorySeason.qualifiers_count musí být nastaveno.")

    K = int(t.category_season.qualifiers_count)

    existing = {phi.branch_index for phi in _existing_placeholder_entries(t)}
    created: List[PlaceholderInfo] = []
    for b in range(K):
        if b in existing:
            continue
        p = _ensure_placeholder_player(b)
        te = TournamentEntry.objects.create(
            tournament=t,
            player=p,                # placeholder Player
            entry_type=EntryType.Q,  # chová se jako kvalifikant
            status=EntryStatus.ACTIVE,
            wr_snapshot=None,        # NR → v unseeded blocích až za WR hráči stejného typu
            position=None,           # slot dostane až při confirm_main_draw
        )
        created.append(PlaceholderInfo(branch_index=b, player_id=p.id, entry_id=te.id))

    return sorted(_existing_placeholder_entries(t), key=lambda x: x.branch_index)


@atomic()
def confirm_md_with_placeholders(t: Tournament, rng_seed: int) -> Dict[int, int]:
    """
    Připraví placeholdery (pokud nejsou) a zavolá confirm_main_draw.
    Tím se zamkne mapování 'Winner K#b' → konkrétní unseeded slot v MD.
    Vrací {slot -> TournamentEntry.id}.
    """
    create_md_placeholders(t)
    return confirm_main_draw(t, rng_seed=rng_seed)


def _final_winner_player_id_for_branch(t: Tournament, branch_index: int) -> int | None:
    """
    Najde vítěze finále kvaldy ve větvi `branch_index` (0-based).
    Používáme offset z confirm_qualification: base = b * 1000, finále má round_name='Q2'
    a lokální páry (1 vs 2).
    """
    base = branch_index * 1000
    m = (Match.objects
         .filter(tournament=t, phase=Phase.QUAL, round_name="Q2",
                 slot_top=base+1, slot_bottom=base+2)
         .exclude(winner_id=None)
         .first())
    return m.winner_id if m else None


@atomic()
def replace_placeholders_with_qual_winners(t: Tournament) -> int:
    """
    Najde všechny placeholdery WINNER K#* v MD a nahradí jejich Player na skutečného vítěze
    z příslušné kvalifikační větve. Sloty v MD se NEMĚNÍ, jen se přepíše player_id
    v TournamentEntry a promítnou se změny do R1 zápasů, případně dalších kol, kde
    se placeholder vyskytoval.
    Vrací počet úspěšných náhrad.
    """
    placeholders = _existing_placeholder_entries(t)
    if not placeholders:
        return 0

    changed = 0
    # Zámek na všechny MD R1 zápasy, aby se nepřekrývaly editace
    r1 = list(locked(Match.objects.filter(tournament=t, phase=Phase.MD, round_name=f"R{t.category_season.draw_size}")))
    # (R1 nemusí existovat, pokud ještě nebyl confirm_main_draw – v tom případě neděláme nic)
    for phi in placeholders:
        winner_pid = _final_winner_player_id_for_branch(t, phi.branch_index)
        if not winner_pid:
            continue  # finále ještě nemá výsledek

        # přepiš player v entry (slot zůstává)
        te = TournamentEntry.objects.select_for_update().get(pk=phi.entry_id)
        if te.player_id == winner_pid:
            continue  # už je nahrazeno

        te.player_id = winner_pid
        te.save(update_fields=["player"])

        # promítnout do R1 (a případně dalších kol, které referencují sloty) – pro MVP přemapujeme R1
        for m in r1:
            if m.slot_top == te.position:
                m.player_top_id = winner_pid
                # pokud zápas nemá výsledek, resetuj do PENDING pro jistotu konzistence
                if m.winner_id is None:
                    m.state = MatchState.PENDING
                    m.score = {}
                m.save(update_fields=["player_top", "state", "score"])
            elif m.slot_bottom == te.position:
                m.player_bottom_id = winner_pid
                if m.winner_id is None:
                    m.state = MatchState.PENDING
                    m.score = {}
                m.save(update_fields=["player_bottom", "state", "score"])
        changed += 1

    return changed
