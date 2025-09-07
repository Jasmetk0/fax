# msa/services/results.py
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db.models import Q

from msa.models import Match, MatchState, Phase
from msa.services.tx import atomic, locked


@dataclass(frozen=True)
class SetScore:
    a: int
    b: int


def _round_size_from_name(round_name: str) -> int:
    # "R16" -> 16, "Q8" -> 8
    try:
        return int(round_name[1:])
    except Exception:
        raise ValidationError(f"Invalid round_name: {round_name}")


def _validate_sets(best_of: int, sets: List[SetScore], win_by_two: bool, points_to_win: int) -> int:
    """
    Vrátí 1 pokud vyhrál A (top), 2 pokud vyhrál B (bottom).
    Vyhodí ValidationError při nesmyslu. WIN-ONLY řeší volající.
    """
    if best_of not in (1, 3, 5):
        raise ValidationError("best_of musí být 1/3/5.")
    need = (best_of // 2) + 1

    wa = wb = 0
    for i, s in enumerate(sets, start=1):
        if s.a == s.b:
            raise ValidationError(f"Set #{i}: remíza nedává smysl.")
        # kdo dosáhl bodu vítězství
        if win_by_two:
            # vítěz musí mít >= loser+2 a (>= points_to_win)
            high, low = (s.a, s.b) if s.a > s.b else (s.b, s.a)
            if high < points_to_win or high - low < 2:
                raise ValidationError(f"Set #{i}: potřebné dva body rozdílu a {points_to_win} k vítězství.")
        else:
            # vítěz má přesně points_to_win, poražený <= points_to_win-1
            high, low = (s.a, s.b) if s.a > s.b else (s.b, s.a)
            if high != points_to_win or low > points_to_win - 1:
                raise ValidationError(f"Set #{i}: vítěz má mít {points_to_win} a soupeř <= {points_to_win-1}.")
        if s.a > s.b:
            wa += 1
        else:
            wb += 1
        if wa == need or wb == need:
            # po dosažení potřebných výher nesmí existovat další sety s body
            tail = sets[i:]
            if any(ss.a > 0 or ss.b > 0 for ss in tail):
                raise ValidationError("Po dosažení vítězných setů nemají následovat další sety s body.")
            return 1 if wa == need else 2

    raise ValidationError("Nedosažen potřebný počet vyhraných setů.")


def _collect_downstream_matches_containing_player(m: Match, player_id: int) -> List[Match]:
    """
    Najdi všechny NAVAZUJÍCÍ zápasy v téže fázi (MD/QUAL), kde se daný hráč vyskytuje
    v kterémkoli pozdějším kole. Jednoduše hledáme podle player_top/bottom a round_size menší (blíže finále).
    """
    size_here = _round_size_from_name(m.round_name)
    later_rounds = (
        Match.objects
        .filter(tournament=m.tournament, phase=m.phase)
        .exclude(pk=m.pk)
        .all()
    )
    out: List[Match] = []
    for x in later_rounds:
        try:
            if _round_size_from_name(x.round_name) < size_here:
                if x.player_top_id == player_id or x.player_bottom_id == player_id:
                    out.append(x)
        except ValidationError:
            # ignoruj neznámé round_name (např. 3P)
            continue
    return out


@atomic()
def set_result(
    match_id: int,
    *,
    mode: str,                      # 'WIN_ONLY' | 'SETS' | 'SPECIAL'
    winner: str | int | None = None,# 'top' | 'bottom' | player_id (povinné pro WIN_ONLY a SPECIAL)
    sets: Optional[List[Tuple[int,int]]] = None,  # při mode='SETS'
    special: Optional[str] = None,  # 'WO' | 'RET' | 'DQ' (při mode='SPECIAL')
    points_to_win: int = 11,        # default dle specifikace
) -> Match:
    """
    Uloží výsledek zápasu s validací a provede „needs review“ kaskádu:
      - Při změně vítěze propíše nového vítěze do downstream zápasů (nahrazením player_id)
        a tyto zápasy označí needs_review=True (nemění winner/score).
      - Plán se nemění. Stav DONE jen pro tento match; downstream zápasy zůstávají jak jsou.
    """
    m = locked(Match.objects.filter(pk=match_id)).select_related("tournament").get()

    old_winner = m.winner_id

    # Zjisti identitu hráčů
    a = m.player_top_id
    b = m.player_bottom_id
    if not a or not b:
        # Provisional utkání – dovolíme WIN_ONLY i SPECIAL i SETS (ale hráči musí být známi)
        raise ValidationError("Oba hráči musí být dosazeni, jinak nelze uložit výsledek.")

    # Vyhodnoť podle režimu
    if mode == "WIN_ONLY":
        if winner is None:
            raise ValidationError("WIN_ONLY vyžaduje 'winner'.")
        if winner == "top":
            new_winner = a
        elif winner == "bottom":
            new_winner = b
        else:
            new_winner = int(winner)
            if new_winner not in (a, b):
                raise ValidationError("Zadaný winner neodpovídá žádnému hráči v zápase.")
        score_json = {"mode": "WIN_ONLY"}
        m.score = score_json
        m.winner_id = new_winner
        m.state = MatchState.DONE

    elif mode == "SPECIAL":
        if special not in ("WO", "RET", "DQ"):
            raise ValidationError("SPECIAL musí být WO/RET/DQ.")
        if winner is None:
            raise ValidationError("SPECIAL vyžaduje 'winner'.")
        if winner == "top":
            new_winner = a
        elif winner == "bottom":
            new_winner = b
        else:
            new_winner = int(winner)
            if new_winner not in (a, b):
                raise ValidationError("Zadaný winner neodpovídá žádnému hráči v zápase.")
        m.score = {"mode": "SPECIAL", "type": special}
        m.winner_id = new_winner
        m.state = MatchState.DONE

    elif mode == "SETS":
        if not sets:
            raise ValidationError("SETS vyžaduje nenulový seznam setů.")
        best_of = m.best_of or 5
        win_by_two = bool(m.win_by_two)
        parsed = [SetScore(a=s[0], b=s[1]) for s in sets]
        res = _validate_sets(best_of, parsed, win_by_two, points_to_win)
        new_winner = a if res == 1 else b
        m.score = {
            "mode": "SETS",
            "sets": [[s.a, s.b] for s in parsed],
            "points_to_win": points_to_win,
            "win_by_two": win_by_two,
            "best_of": best_of,
        }
        m.winner_id = new_winner
        m.state = MatchState.DONE

    else:
        raise ValidationError("mode musí být 'WIN_ONLY' | 'SPECIAL' | 'SETS'.")

    m.save(update_fields=["score", "winner", "state"])

    # Kaskáda při změně vítěze
    if old_winner and m.winner_id != old_winner:
        # Nahraď old_winner -> new_winner ve všech downstream zápasech téže fáze
        downstream = locked(Match.objects.filter(tournament=m.tournament, phase=m.phase))
        for x in _collect_downstream_matches_containing_player(m, old_winner):
            # Nepřepisujeme winner/score, jen hráče a flag „needs_review“
            if x.player_top_id == old_winner:
                x.player_top_id = m.winner_id
            if x.player_bottom_id == old_winner:
                x.player_bottom_id = m.winner_id
            x.needs_review = True
            x.save(update_fields=["player_top", "player_bottom", "needs_review"])

    return m


@atomic()
def resolve_needs_review(match_id: int) -> Match:
    """
    „Potvrď“ dotčený downstream zápas po ruční kontrole – pouze resetuje needs_review=False.
    (Úmyslně nemění winner/score; admin rozhoduje ručně, co dál.)
    """
    m = locked(Match.objects.filter(pk=match_id)).get()
    m.needs_review = False
    m.save(update_fields=["needs_review"])
    return m
