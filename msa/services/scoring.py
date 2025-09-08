# msa/services/scoring.py
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from django.core.exceptions import ValidationError

from msa.models import Match, Phase, Tournament
from msa.services.md_embed import effective_template_size_for_md

# ---------- datové typy ----------


@dataclass
class PointsBreakdown:
    player_id: int
    q_wins: int = 0
    md_points: int = 0
    third_place: int = 0  # pokud existuje 3P a tabulka ho definuje
    total: int = 0

    def add_q(self, pts: int) -> None:
        self.q_wins += pts
        self.total += pts

    def add_md(self, pts: int) -> None:
        self.md_points += pts
        self.total += pts

    def add_third(self, pts: int) -> None:
        self.third_place += pts
        self.total += pts


# ---------- utilitky ----------


def _round_size_from_name(round_name: str) -> int:
    # "R16" -> 16, "Q8" -> 8, "Q2" -> 2
    if not round_name or len(round_name) < 2:
        raise ValidationError(f"Invalid round_name: {round_name}")
    try:
        return int(round_name[1:])
    except Exception as err:
        raise ValidationError(f"Invalid round_name: {round_name}") from err


def _is_round_fully_completed(matches: Iterable[Match]) -> bool:
    """Kolo je „fully completed“, pokud KAŽDÝ zápas v něm má winner."""
    ms = list(matches)
    return len(ms) > 0 and all(m.winner_id for m in ms)


def _last_completed_md_round_size(t: Tournament) -> int | None:
    """
    Najde nejnižší „R{N}“ (blíž finále), které je plně dokončené.
    Pokud není dokončené ani R{template}, vrátí None (žádné MD body).
    """
    template = effective_template_size_for_md(t)
    sizes = []
    n = template
    while n >= 2:
        sizes.append(n)
        n //= 2
    # R{template}, R{template/2}, ..., R2
    for s in sizes:
        ms = Match.objects.filter(tournament=t, phase=Phase.MD, round_name=f"R{s}")
        if not ms.exists():
            # kolo ani neexistuje → pokud je to první kolo (R{template}), znamená embed/bye — to je OK,
            # „fully completed“ posoudíme podle existujících kol; chybějící kolo nepovažujeme za stop.
            continue
        if not _is_round_fully_completed(ms):
            # poslední plně dokončené je to PŘED tímto
            idx = sizes.index(s)
            # když s je první (idx==0), neexistuje předchozí → None
            return sizes[idx - 1] if idx > 0 else None
    # pokud vše, co existuje, je hotové, poslední dokončené je nejnižší existující (typicky R2)
    # najdi nejnižší R s nějakým zápasem
    for s in reversed(sizes):
        ms = Match.objects.filter(tournament=t, phase=Phase.MD, round_name=f"R{s}")
        if ms.exists():
            return s
    return None


def _md_label_for_losing_round(round_size: int) -> str:
    """Mapování velikosti kola na label tabulky scoring_md pro poražené v tom kole."""
    if round_size >= 64:
        return "R64"
    if round_size == 32:
        return "R32"
    if round_size == 16:
        return "R16"
    if round_size == 8:
        return "QF"
    if round_size == 4:
        return "SF"
    if round_size == 2:
        return "RunnerUp"  # pro „porážku ve finále“ použijeme RunnerUp
    # fallback (pro raritní šablony)
    return f"R{round_size}"


def _safe_get(d: dict[str, int], key: str) -> int:
    """Bezpečný přístup: chybějící klíč = 0 bodů (měkké modely)."""
    return int(d.get(key, 0))


# ---------- Q-wins (kvalifikační výhry) ----------


def compute_q_wins_points(t: Tournament) -> dict[int, int]:
    """
    Vrací {player_id -> body} za výhry v kvaldě. Tabulka bodů je v
    t.category_season.scoring_qual_win (dict podle round_name: 'Q8','Q4','Q2'...).
    """
    cs = t.category_season
    if not cs:
        raise ValidationError("Tournament.category_season chybí.")
    qual_table: dict[str, int] = getattr(cs, "scoring_qual_win", {}) or {}

    pts: dict[int, int] = {}
    q_matches = Match.objects.filter(tournament=t, phase=Phase.QUAL).exclude(winner_id=None)
    for m in q_matches:
        label = m.round_name  # "Q16","Q8","Q4","Q2"
        add = _safe_get(qual_table, label)
        if add:
            pts[m.winner_id] = pts.get(m.winner_id, 0) + add
    return pts


# ---------- MD points (hlavní pavouk) ----------


def _players_with_bye_in_r1(t: Tournament) -> set[int]:
    """
    Zjistí hráče, kteří měli BYE v prvním kole šablony (R{template}).
    V embed režimu (24→32, 48→64) R{template} neobsahuje jejich zápas.
    """
    template = effective_template_size_for_md(t)
    r1 = list(Match.objects.filter(tournament=t, phase=Phase.MD, round_name=f"R{template}"))
    if r1:
        # power-of-two: BYE neexistují (v našem modelu)
        return set()
    # Když R{template} neexistuje, BYE detekujeme podle prvního výskytu hráče v MD.
    all_md = Match.objects.filter(tournament=t, phase=Phase.MD)
    earliest_round: dict[int, int] = {}
    for m in all_md:
        if not (m.round_name or "").startswith("R"):
            continue
        size = _round_size_from_name(m.round_name)
        for pid in (m.player_top_id, m.player_bottom_id):
            if not pid:
                continue
            prev = earliest_round.get(pid)
            if prev is None or size > prev:
                earliest_round[pid] = size
    return {pid for pid, size in earliest_round.items() if size == template // 2}


def _collect_player_md_matches(t: Tournament) -> dict[int, list[Match]]:
    """Pro každého hráče (player_id) vrať seznam jeho MD zápasů podle vzestupné obtížnosti (R{template} → R2 → 3P)."""
    all_md = list(Match.objects.filter(tournament=t, phase=Phase.MD))
    by_player: dict[int, list[Match]] = {}

    # řazení podle round_size od největšího (R{template}) k nejmenšímu (R2), 3P necháme úplně nakonec
    def sort_key(m: Match):
        if (m.round_name or "").startswith("R"):
            return (0, _round_size_from_name(m.round_name))
        if m.round_name == "3P":
            return (1, 0)
        return (2, 0)

    all_md.sort(key=sort_key, reverse=True)

    for m in all_md:
        for pid in (m.player_top_id, m.player_bottom_id):
            if not pid:
                continue
            by_player.setdefault(pid, []).append(m)
    return by_player


def compute_md_points(t: Tournament, *, only_completed_rounds: bool = True) -> dict[int, int]:
    """
    Vrací {player_id -> MD body} dle t.category_season.scoring_md.
    Pravidla:
      - BYE rule: prohra v prvním odehraném zápase po BYE → body za předchozí kolo.
      - RunnerUp / Winner / SF / QF / R16 / R32 / R64 … podle kola, kde hráč prohrál (nebo vyhrál finále).
      - Pokud only_completed_rounds=True, započítá se body pouze do POSLEDNÍHO plně dokončeného kola.
    """
    cs = t.category_season
    if not cs:
        raise ValidationError("Tournament.category_season chybí.")
    md_table: dict[str, int] = getattr(cs, "scoring_md", {}) or {}

    # limit „do posledního plně dokončeného kola“
    last_full: int | None = _last_completed_md_round_size(t) if only_completed_rounds else None

    bye_candidates = _players_with_bye_in_r1(t)
    by_player = _collect_player_md_matches(t)

    out: dict[int, int] = {}

    for pid, matches in by_player.items():
        # najdi finále, pokud hráč vyhrál celé (R2)
        final = next((m for m in matches if (m.round_name == "R2" and m.winner_id == pid)), None)
        if final:
            # Pokud limit kol nepovoluje R2, body 0
            if (last_full is None) or (last_full >= 2):
                out[pid] = out.get(pid, 0) + _safe_get(md_table, "Winner")
            continue

        # RunnerUp – prohrál ve finále?
        lost_final = next(
            (m for m in matches if (m.round_name == "R2" and m.winner_id and m.winner_id != pid)),
            None,
        )
        if lost_final:
            if (last_full is None) or (last_full >= 2):
                out[pid] = out.get(pid, 0) + _safe_get(md_table, "RunnerUp")
            continue

        # Třetí místo (volitelné): zápas 3P (pokud existuje)
        third = next((m for m in matches if m.round_name == "3P" and m.winner_id == pid), None)
        fourth = next(
            (m for m in matches if m.round_name == "3P" and m.winner_id and m.winner_id != pid),
            None,
        )
        if third:
            # body za „Third“, pokud tabulka definuje
            if (last_full is None) or (
                last_full >= 2
            ):  # 3P je po SF, takže když je hotové finále/3P, určitě >= R2
                out[pid] = out.get(pid, 0) + _safe_get(md_table, "Third")
            continue
        if fourth:
            if (last_full is None) or (last_full >= 2):
                out[pid] = out.get(pid, 0) + _safe_get(md_table, "Fourth")
            continue

        # Jinak hráč někde prohrál před finále – najdi NEJPOZDĚJI hraný zápas s výsledkem
        played = [m for m in matches if m.winner_id]
        if not played:
            # žádný výsledek → 0 bodů (např. turnaj uprostřed)
            continue

        # poslední odehraný (nejblíže finále)
        # díky řazení matches je první v listu nejvyšší kolo; my chceme „nejpozději odehraný“ = nejmenší round_size s výsledkem
        played_sorted = sorted(
            played,
            key=lambda m: (
                _round_size_from_name(m.round_name) if (m.round_name or "").startswith("R") else 1
            ),
        )
        last = played_sorted[0]  # nejmenší R (nejblíž finále)

        rsize = _round_size_from_name(last.round_name)
        # respektuj limit: pokud toto kolo není <= last_full, nedávej nic
        if (last_full is not None) and (rsize < last_full):
            # poslední plně dokončené je „větší“ číslo (dřívější kolo) – pokud hráč prohrál později v nedokončeném kole → 0
            continue

        # prohrál-li tenhle zápas, standardní label je _md_label_for_losing_round(rsize)
        lost_here = last.winner_id != pid
        if not lost_here:
            # vyhrál a nemáme info o dalším kole (asi turnaj nedokončen) → zatím body 0 (čeká na další kolo)
            continue

        # BYE pravidlo: pokud tenhle last je zároveň PRVNÍ zápas hráče a hráč je v množině „bye_candidates“,
        # přiznáme body za předchozí kolo (dvojnásobný round_size).
        player_first_played = None
        for m in matches:
            if m.winner_id is not None or (m.player_top_id and m.player_bottom_id):
                # díky řazení `matches` je toto skutečně PRVNÍ zápas, kde hráč nastoupil
                if (m.player_top_id == pid) or (m.player_bottom_id == pid):
                    player_first_played = m
                    break
        adjusted_label = None
        if player_first_played and (player_first_played.id == last.id) and (pid in bye_candidates):
            prev_round = rsize * 2
            adjusted_label = _md_label_for_losing_round(prev_round)

        label = adjusted_label or _md_label_for_losing_round(rsize)
        out[pid] = out.get(pid, 0) + _safe_get(md_table, label)

    return out


# ---------- Top-level kombinace ----------


def compute_tournament_points(
    t: Tournament, *, only_completed_rounds: bool = True
) -> dict[int, PointsBreakdown]:
    """
    Vrací {player_id -> PointsBreakdown} = Q-wins + MD (s BYE pravidlem),
    respektuje „award up to last fully completed round“, pokud je zapnuto.
    """
    q = compute_q_wins_points(t)
    md = compute_md_points(t, only_completed_rounds=only_completed_rounds)

    players = set(q.keys()) | set(md.keys())
    out: dict[int, PointsBreakdown] = {}
    for pid in players:
        pb = PointsBreakdown(player_id=pid)
        if pid in q:
            pb.add_q(q[pid])
        if pid in md:
            pb.add_md(md[pid])
        out[pid] = pb
    return out
