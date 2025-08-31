import json
import logging
from math import ceil

from django.db import transaction

from ..models import Match
from .scheduling import load_section_dict
from .draw import progress_bracket
from .state import update_tournament_state
from .points import rebuild_season_live_points

logger = logging.getLogger(__name__)


def _parse_scoreline(scoreline: str, best_of: int, *, require_winner: bool = True):
    scoreline = (scoreline or "").strip()
    if not scoreline:
        if require_winner:
            raise ValueError("scoreline required")
        return "", 0, 0, None
    p1_sets = p2_sets = 0
    sets: list[str] = []
    for token in scoreline.split():
        if "-" not in token:
            raise ValueError("invalid set")
        a_str, b_str = token.split("-", 1)
        if not a_str.isdigit() or not b_str.isdigit():
            raise ValueError("invalid set")
        a = int(a_str)
        b = int(b_str)
        if a == 0 and b == 0:
            raise ValueError("invalid set")
        sets.append(f"{a}-{b}")
        if a > b:
            p1_sets += 1
        elif b > a:
            p2_sets += 1
        else:
            raise ValueError("invalid set")
    needed = ceil(best_of / 2)
    winner = None
    if require_winner:
        if max(p1_sets, p2_sets) < needed or p1_sets == p2_sets:
            raise ValueError("invalid scoreline")
        winner = 1 if p1_sets > p2_sets else 2
    normalized = " ".join(sets)
    return normalized, p1_sets, p2_sets, winner


def record_match_result(
    match: Match,
    *,
    result_type: str,
    scoreline_str: str | None = None,
    retired_player_id: int | None = None,
    user=None,
) -> None:
    """Parse, validate and store a match result.

    Stores metadata into Match.section[result_meta] and updates winner,
    scoreline and live_status. Transactional and idempotent.
    """
    result_type = (result_type or "").upper()
    if result_type not in {"NORMAL", "WO", "RET"}:
        raise ValueError("invalid result_type")
    with transaction.atomic():
        m = Match.objects.select_for_update().get(pk=match.pk)
        meta = {"type": result_type, "retired_player_id": None}
        if result_type == "NORMAL":
            normalized, _, _, winner_side = _parse_scoreline(
                scoreline_str or "", m.best_of, require_winner=True
            )
            winner = m.player1 if winner_side == 1 else m.player2
        elif result_type == "WO":
            normalized = ""
            winner = m.player2
        else:  # RET
            if retired_player_id not in {m.player1_id, m.player2_id}:
                raise ValueError("retired_player_id required")
            normalized, _, _, _ = _parse_scoreline(
                scoreline_str or "", m.best_of, require_winner=False
            )
            meta["retired_player_id"] = retired_player_id
            winner = m.player2 if retired_player_id == m.player1_id else m.player1
        data = load_section_dict(m) or {}
        data["result_meta"] = meta
        m.section = json.dumps(data)
        m.winner = winner
        m.scoreline = normalized
        m.live_status = "finished"
        fields = ["section", "winner", "scoreline", "live_status"]
        if user:
            m.updated_by = user
            fields.append("updated_by")
        m.save(update_fields=fields)
        progress_bracket(m.tournament)
        update_tournament_state(m.tournament, user)
        if m.tournament.season:
            rebuild_season_live_points(m.tournament.season, persist=True, user=user)
        logger.info(
            "match_results.save user=%s match=%s type=%s score=%s",
            getattr(user, "id", None),
            m.id,
            result_type,
            normalized,
        )
