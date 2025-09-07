from django.db import IntegrityError

from msa.models import Match, TournamentEntry
from msa.services._concurrency import atomic_tournament, lock_qs


def pair_first_round_slots(bracket_size: int) -> list[tuple[int, int]]:
    return [(i, i + 1) for i in range(1, bracket_size + 1, 2)]


def next_power_of_two(n: int) -> int:
    return 1 << (n - 1).bit_length() if n > 0 else 1


def code_to_size(code: str) -> int:
    if code.startswith("R") and code[1:].isdigit():
        return int(code[1:])
    mapping = {"QF": 8, "SF": 4, "F": 2}
    return mapping.get(code, 0)


def _rounds_numeric(code: str) -> int:
    return code_to_size(code)


_BRACKET_ORDER = ["R128", "R96", "R64", "R56", "R48", "R32", "R16", "QF", "SF", "F"]


def _next_round_code(code: str) -> str | None:
    try:
        idx = _BRACKET_ORDER.index(code)
    except ValueError:
        return None
    if idx + 1 >= len(_BRACKET_ORDER):
        return None
    return _BRACKET_ORDER[idx + 1]


def _find_highest_complete_round_code(tournament) -> str | None:
    codes = Match.objects.filter(tournament=tournament).values_list("round", flat=True).distinct()
    ordered = sorted(codes, key=_rounds_numeric, reverse=True)
    for code in ordered:
        qs = Match.objects.filter(tournament=tournament, round=code)
        if qs.exists() and not qs.filter(winner__isnull=True).exists():
            return code
    return None


@atomic_tournament
def progress_bracket(tournament) -> bool:
    lock_qs(Match.objects.filter(tournament=tournament))

    current_code = _find_highest_complete_round_code(tournament)
    if not current_code:
        return False
    next_code = _next_round_code(current_code)
    if not next_code:
        return False

    cur_qs = list(
        lock_qs(
            Match.objects.filter(tournament=tournament, round=current_code).order_by(
                "position", "id"
            )
        )
    )

    for idx, m in enumerate(cur_qs, start=1):
        if m.position is None:
            m.position = idx
            m.save(update_fields=["position"])
    match_by_pos = {m.position: m for m in cur_qs}

    bracket = next_power_of_two(tournament.draw_size or 0)
    entries = list(
        lock_qs(
            tournament.entries.filter(position__isnull=False, status="active").select_related(
                "player"
            )
        )
    )
    by_pos = {e.position: e for e in entries}

    winners: list[TournamentEntry | None] = []
    for pair_idx, (a, b) in enumerate(pair_first_round_slots(bracket), start=1):
        ea = by_pos.get(a)
        eb = by_pos.get(b)
        winner_entry = None
        if ea and eb:
            match = match_by_pos.get(pair_idx)
            if match and match.winner_id is not None:
                winner_entry = ea if match.winner_id == ea.player_id else eb
            else:
                winners.append(None)
                continue
        elif ea or eb:
            winner_entry = ea or eb
        winners.append(winner_entry)

    created_any = False
    for i in range(0, len(winners), 2):
        w1 = winners[i]
        w2 = winners[i + 1] if i + 1 < len(winners) else None
        if not w1 or not w2:
            continue
        pos = i // 2 + 1
        try:
            match, created = Match.objects.get_or_create(
                tournament=tournament,
                round=next_code,
                position=pos,
                defaults={
                    "player1": w1.player,
                    "player2": w2.player,
                    "best_of": 5,
                },
            )
        except IntegrityError:
            match = Match.objects.get(tournament=tournament, round=next_code, position=pos)
            created = False
        fields = []
        if getattr(match, "player1_id", None) is None:
            match.player1 = w1.player
            fields.append("player1")
        if getattr(match, "player2_id", None) is None:
            match.player2 = w2.player
            fields.append("player2")
        if fields:
            match.save(update_fields=fields)
        created_any = created_any or created

    return created_any
