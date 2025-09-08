# msa/services/standings.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError

from msa.models import Category, RankingAdjustment, RankingScope, Season, Tournament
from msa.services.scoring import compute_tournament_points

# ---------- datové typy ----------


@dataclass(frozen=True)
class SeasonRow:
    player_id: int
    total: int
    counted: list[int]  # body jednotlivých započtených turnajů (seřazeno desc)
    dropped: list[int]  # vyřazené body (desc)
    average: float


@dataclass(frozen=True)
class RollingRow:
    player_id: int
    total: int
    counted: list[int]
    dropped: list[int]
    average: float
    window_start_monday: date
    window_end_monday: date
    best_n_used: int


@dataclass(frozen=True)
class RtFRow:
    player_id: int
    total: int
    counted: list[int]
    dropped: list[int]
    average: float
    pinned_category: str | None = None  # pokud je hráč „připíchnutý“ jako vítěz auto-TOP
    pinned_rank: int | None = None  # pořadí v rámci pinned sekce


# ---------- pomocné datumové utilitky ----------


def _to_date(d: date | str) -> date:
    if isinstance(d, date):
        return d
    return datetime.fromisoformat(d).date()


def _next_monday_strictly_after(d: date) -> date:
    # pondělí striktně po d (i kdyby d bylo pondělí)
    dow = d.weekday()  # 0=Mon
    days_to_next_mon = (7 - dow) % 7 or 7
    return d + timedelta(days=days_to_next_mon)


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _week_window(start_monday, duration_weeks):
    # vrátí (start_date, end_date_exclusive) pro jednoduché "start <= x < end"
    if not start_monday or not duration_weeks:
        return None, None
    from datetime import timedelta

    return start_monday, start_monday + timedelta(weeks=int(duration_weeks))


def _intersects_weekly_window(range_start, range_end, win_start, win_end):
    # true, pokud [range_start, range_end] (včetně) má průnik s [win_start, win_end) (exclusive)
    if not (win_start and win_end and range_start and range_end):
        return False
    # posuň season range na "pondělí" hranice
    rs = _monday_of(range_start)
    re = _monday_of(range_end)
    # průnik existuje, pokud okna se nepřekrývají opačně
    return not (re < win_start or rs >= win_end)


# ---------- vnitřní sklizeň bodů ----------


def _tournaments_in_season(s: Season) -> list[Tournament]:
    return list(Tournament.objects.filter(season=s).exclude(end_date=None))


def _tournament_total_points_map(t: Tournament, *, only_completed_rounds: bool) -> dict[int, int]:
    # compute_tournament_points vrací breakdowny; posbíráme total per player
    totals = compute_tournament_points(t, only_completed_rounds=only_completed_rounds)
    return {pid: pb.total for pid, pb in totals.items()}


def _sorted_points_desc(points: list[int]) -> list[int]:
    return sorted(points, reverse=True)


def _season_adjustments_map(season: Season) -> dict[int, tuple[int, int]]:
    """
    Vrátí {player_id: (sum_points_delta, sum_best_n_penalty)} pro úpravy,
    které mají scope SEASON nebo BOTH a jejich (start_monday, duration) se
    protíná s oknem sezóny.
    """
    if not season.start_date or not season.end_date:
        return {}
    rows = RankingAdjustment.objects.all()
    out: dict[int, tuple[int, int]] = {}
    for ra in rows:
        if ra.scope not in (RankingScope.SEASON, RankingScope.BOTH):
            continue
        ws, we = _week_window(ra.start_monday, ra.duration_weeks or 0)
        if not ws or not we:
            continue
        if _intersects_weekly_window(season.start_date, season.end_date, ws, we):
            cur = out.get(ra.player_id, (0, 0))
            out[ra.player_id] = (
                cur[0] + int(ra.points_delta or 0),
                cur[1] + int(ra.best_n_penalty or 0),
            )
    return out


def _rolling_adjustments_map(snapshot_monday) -> dict[int, tuple[int, int]]:
    """
    Vrátí {player_id: (sum_points_delta, sum_best_n_penalty)} pro úpravy,
    které mají scope ROLLING_ONLY nebo BOTH a jsou AKTIVNÍ v den snapshot_monday:
    start_monday <= snapshot_monday < start_monday + duration_weeks.
    """
    snap = _monday_of(_to_date(snapshot_monday))
    rows = RankingAdjustment.objects.all()
    out: dict[int, tuple[int, int]] = {}
    for ra in rows:
        if ra.scope not in (RankingScope.ROLLING_ONLY, RankingScope.BOTH):
            continue
        ws, we = _week_window(ra.start_monday, ra.duration_weeks or 0)
        if not ws or not we:
            continue
        if ws <= snap < we:
            cur = out.get(ra.player_id, (0, 0))
            out[ra.player_id] = (
                cur[0] + int(ra.points_delta or 0),
                cur[1] + int(ra.best_n_penalty or 0),
            )
    return out


def _best_n_for_date(all_seasons: list[Season], snap_day: date) -> int:
    # Najdi season, která obsahuje snap_day; pokud žádná, vezmi poslední dle end_date
    if not all_seasons:
        return 10  # bezpečný fallback
    containing = [
        s
        for s in all_seasons
        if s.start_date and s.end_date and (s.start_date <= snap_day <= s.end_date)
    ]
    if containing:
        s = containing[0]
        return int(getattr(s, "best_n", 10) or 10)
    # fallback: poslední sezóna
    s_last = sorted([s for s in all_seasons if s.end_date], key=lambda x: x.end_date)[-1]
    return int(getattr(s_last, "best_n", 10) or 10)


# ---------- Season standings ----------


def season_standings(
    season: Season, *, best_n: int | None = None, only_completed_rounds: bool = True
) -> list[SeasonRow]:
    """
    Sezónní tabulka: bere turnaje s end_date uvnitř sezóny.
    Pro každého hráče sečte **top N** výsledků (N = best_n nebo Season.best_n).
    """
    if not season.start_date or not season.end_date:
        raise ValidationError("Season musí mít start_date i end_date.")
    N = int(best_n if best_n is not None else (getattr(season, "best_n", 10) or 10))
    adj = _season_adjustments_map(season)

    rows: dict[int, list[int]] = {}
    for t in _tournaments_in_season(season):
        pts = _tournament_total_points_map(t, only_completed_rounds=only_completed_rounds)
        for pid, val in pts.items():
            rows.setdefault(pid, []).append(val)

    out: list[SeasonRow] = []
    for pid, arr in rows.items():
        arr_sorted = _sorted_points_desc(arr)
        pen = adj.get(pid, (0, 0))[1]
        N_eff = max(1, min(len(arr_sorted), N + pen))
        counted = arr_sorted[:N_eff]
        dropped = arr_sorted[N_eff:]
        adj_points = adj.get(pid, (0, 0))[0]
        total = sum(counted) + adj_points
        avg = (sum(counted) / len(counted)) if counted else 0.0
        out.append(
            SeasonRow(player_id=pid, total=total, counted=counted, dropped=dropped, average=avg)
        )

    # řadíme podle total desc, při shodě vyšší average
    out.sort(key=lambda r: (r.total, r.average, -r.player_id), reverse=True)
    return out


# ---------- Rolling standings (61 týdnů okno) ----------


def _activation_monday_for_tournament(t: Tournament) -> date:
    if not t.end_date:
        raise ValidationError("Tournament.end_date je vyžadováno pro Rolling.")
    endd = _to_date(t.end_date)
    act = _next_monday_strictly_after(endd)
    return act


def rolling_standings(
    snapshot_monday: date | str, *, only_completed_rounds: bool = True
) -> list[RollingRow]:
    """
    Rolling k „pondělí“ = snapshot_monday (datum pondělí). Vezme turnaje, které:
      activation_monday <= snapshot_monday < activation_monday + 61 týdnů.
    Best-N bere z té sezóny, do níž spadá snapshot den (fallback poslední sezóna).
    """
    snap = _to_date(snapshot_monday)
    if snap.weekday() != 0:
        # zaokrouhli na pondělí směrem dolů (srozumitelnější pro uživatele)
        snap = _monday_of(snap)

    all_t = list(Tournament.objects.exclude(end_date=None))
    # filtr okna
    eligible: list[Tournament] = []
    windows: dict[int, tuple[date, date]] = {}
    for t in all_t:
        act = _activation_monday_for_tournament(t)
        end = act + timedelta(weeks=61)
        if act <= snap < end:
            eligible.append(t)
            windows[t.id] = (act, end)

    # Best-N v Rolling: podle sezóny obsahující snap
    seasons = list(Season.objects.exclude(start_date=None).exclude(end_date=None))
    N = _best_n_for_date(seasons, snap)
    adj = _rolling_adjustments_map(snap)

    per_player_points: dict[int, list[int]] = {}
    for t in eligible:
        pts = _tournament_total_points_map(t, only_completed_rounds=only_completed_rounds)
        for pid, val in pts.items():
            per_player_points.setdefault(pid, []).append(val)

    out: list[RollingRow] = []
    for pid, arr in per_player_points.items():
        arr_sorted = _sorted_points_desc(arr)
        pen = adj.get(pid, (0, 0))[1]
        N_eff = max(1, min(len(arr_sorted), N + pen))
        counted = arr_sorted[:N_eff]
        dropped = arr_sorted[N_eff:]
        adj_points = adj.get(pid, (0, 0))[0]
        total = sum(counted) + adj_points
        avg = (sum(counted) / len(counted)) if counted else 0.0
        # okno per player = průnik (ale pro jednoduchost přidáme globální okno: min act, max end v eligible)
        global_start = min((windows[t.id][0] for t in eligible), default=snap)
        global_end = max((windows[t.id][1] for t in eligible), default=snap)
        out.append(
            RollingRow(
                player_id=pid,
                total=total,
                counted=counted,
                dropped=dropped,
                average=avg,
                window_start_monday=global_start,
                window_end_monday=global_end,
                best_n_used=N_eff,
            )
        )

    out.sort(key=lambda r: (r.total, r.average, -r.player_id), reverse=True)
    return out


# ---------- Road to Finals (RtF) ----------


def _final_winner_player_id(t: Tournament) -> int | None:
    # Finále je R2; pokud existuje zápas s winner, vrátíme vítěze.
    from msa.models import Match, Phase

    fin = (
        Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R2")
        .exclude(winner_id=None)
        .first()
    )
    return fin.winner_id if fin else None


def rtf_standings(
    season: Season,
    *,
    auto_top_categories: list[str] | None = None,
    finals_slots: int | None = None,
    only_completed_rounds: bool = True,
) -> list[RtFRow]:
    """
    RtF = stejné body jako Season mode (top N), ale vítězové turnajů z auto-TOP kategorií jsou „připíchnuti“ nahoře,
    v pořadí kategorií. Uvnitř pinned sekce řazení podle bodů/average.
    """
    base = season_standings(season, best_n=None, only_completed_rounds=only_completed_rounds)
    base_by_player = {r.player_id: r for r in base}

    auto = [a.strip() for a in (auto_top_categories or []) if a and isinstance(a, str)]
    if not auto:
        # žádné připíchnutí → prosté season standings
        return [
            RtFRow(
                player_id=r.player_id,
                total=r.total,
                counted=r.counted,
                dropped=r.dropped,
                average=r.average,
            )
            for r in base
        ]

    # najdi vítěze těch kategorií v rámci sezóny
    pinned_ordered: list[tuple[str, int]] = []  # (category_name, player_id)
    for cat_name in auto:
        cat = Category.objects.filter(name=cat_name).first()
        if not cat:
            continue
        # všechny turnaje této kategorie v sezóně
        ts = Tournament.objects.filter(season=season, category=cat).exclude(end_date=None)
        # pokud nějaký má vítěze, připíchneme vítěze z „nejprestižnějšího/posledního“? MVP: první nalezený s vítězem
        winner_pid = None
        for t in ts:
            w = _final_winner_player_id(t)
            if w:
                winner_pid = w
                break
        if winner_pid:
            pinned_ordered.append((cat_name, winner_pid))

    # z pinned hráčů vyrob řádky (v jejich pořadí), bez duplicit
    seen = set()
    pinned_rows: list[RtFRow] = []
    for idx, (cat_name, pid) in enumerate(pinned_ordered, start=1):
        if pid in seen:  # jeden hráč mohl vyhrát víc auto-TOP; držíme jeho první výskyt
            continue
        base_row = base_by_player.get(pid)
        if not base_row:
            # hráč nemusí mít žádné body (teoreticky), vytvoříme nulový
            base_row = SeasonRow(player_id=pid, total=0, counted=[], dropped=[], average=0.0)
        pinned_rows.append(
            RtFRow(
                player_id=pid,
                total=base_row.total,
                counted=base_row.counted,
                dropped=base_row.dropped,
                average=base_row.average,
                pinned_category=cat_name,
                pinned_rank=idx,
            )
        )
        seen.add(pid)

    # zbylí hráči (nepinned), v pořadí jako base, ale bez těch v seen
    rest_rows = [
        RtFRow(
            player_id=r.player_id,
            total=r.total,
            counted=r.counted,
            dropped=r.dropped,
            average=r.average,
        )
        for r in base
        if r.player_id not in seen
    ]

    out = pinned_rows + rest_rows
    # finals_slots (pokud dané) slouží ke zvýraznění/řezu; neomezujeme výpočet, admin si to ořízne v UI.
    return out
