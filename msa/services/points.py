import logging
from collections import defaultdict

from django.db import transaction

from ..models import Player, Tournament

logger = logging.getLogger(__name__)


def round_order_for_draw(draw_size: int) -> list[str]:
    """Return round codes from first round to champion."""
    rounds: list[str] = []
    n = draw_size
    if not n:
        return ["W"]
    while n >= 2:
        if n > 8:
            rounds.append(f"R{n}")
        elif n == 8:
            rounds.append("QF")
        elif n == 4:
            rounds.append("SF")
        elif n == 2:
            rounds.append("F")
        elif n == 1:
            rounds.append("W")
        if n == 1:
            break
        n = 64 if n == 96 else n // 2
    if rounds[-1] != "W":
        rounds.append("W")
    return rounds


DEFAULT_POINTS = {
    "R96": 0,
    "R64": 0,
    "R32": 10,
    "R16": 25,
    "QF": 45,
    "SF": 75,
    "F": 120,
    "W": 200,
}


def load_points_table(category_season) -> dict[str, int]:
    table = {}
    if category_season and category_season.points_table:
        rows = category_season.points_table.rows.all()
        if rows:
            table = {r.round_code: r.points for r in rows}
    return table or DEFAULT_POINTS


def compute_tournament_points(tournament: Tournament) -> dict[int, int]:
    table = load_points_table(tournament.season_category)
    order = round_order_for_draw(tournament.draw_size)
    index = {code: i for i, code in enumerate(order)}
    player_round: dict[int, tuple[int, str]] = {}
    for m in tournament.matches.filter(winner__isnull=False).select_related(
        "player1", "player2", "winner"
    ):
        for pid in [m.player1_id, m.player2_id]:
            code = "W" if m.round == "F" and m.winner_id == pid else m.round
            idx = index.get(code, index.get(m.round, -1))
            if idx == -1:
                continue
            prev = player_round.get(pid)
            if not prev or idx > prev[0]:
                player_round[pid] = (idx, code)
    points: dict[int, int] = {}
    for pid, (_, code) in player_round.items():
        points[pid] = table.get(code, 0)
    return points


def rebuild_season_live_points(season, *, persist: bool = True, user=None) -> dict:
    totals: defaultdict[int, int] = defaultdict(int)
    for tournament in season.tournaments.all():
        for pid, pts in compute_tournament_points(tournament).items():
            totals[pid] += pts
    if persist:
        with transaction.atomic():
            for p in Player.objects.all():
                new_pts = totals.get(p.id, 0)
                if p.rtf_current_points != new_pts:
                    p.rtf_current_points = new_pts
                    if user:
                        p.updated_by = user
                        fields = ["rtf_current_points", "updated_by"]
                    else:
                        fields = ["rtf_current_points"]
                    p.save(update_fields=fields)
    logger.info(
        "points.rebuild user=%s season=%s players=%s",
        getattr(user, "id", None),
        getattr(season, "id", None),
        len(totals),
    )
    return dict(totals)
