import logging
from django.db import transaction

from ..models import Match, TournamentEntry, Tournament
from .draw import pair_first_round_slots
from .rounds import next_power_of_two

logger = logging.getLogger(__name__)


@transaction.atomic
def generate_qualifying(tournament: Tournament, force: bool = False, user=None) -> bool:
    entries_qs = tournament.entries.filter(
        entry_type=TournamentEntry.EntryType.Q, status="active"
    ).select_related("player")
    if not entries_qs.exists():
        return False
    if force:
        tournament.matches.filter(round__startswith="Q").delete()
    elif tournament.matches.filter(round__startswith="Q").exists():
        return False
    entries = list(entries_qs.order_by("player__name"))
    n = len(entries)
    start = next_power_of_two(n)
    if start < 2:
        return False
    round_size = n if n & (n - 1) == 0 else start // 2
    round_code = f"Q{round_size}"
    created = False
    for a, b in pair_first_round_slots(round_size):
        if a > n or b > n:
            continue
        e1 = entries[a - 1]
        e2 = entries[b - 1]
        m = Match(
            tournament=tournament,
            player1=e1.player,
            player2=e2.player,
            round=round_code,
            section="",
            best_of=5,
        )
        if user:
            m.updated_by = user
        m.save()
        created = True
    return created


@transaction.atomic
def progress_qualifying(tournament: Tournament, user=None) -> bool:
    qs = tournament.matches.select_for_update().filter(round__startswith="Q")
    if not qs.exists():
        return False
    rounds = sorted({int(m.round[1:]) for m in qs}, reverse=True)
    current = None
    for r in rounds:
        if qs.filter(round=f"Q{r}", winner__isnull=True).exists():
            continue
        next_r = r // 2
        if next_r < 2:
            return False
        if qs.filter(round=f"Q{next_r}").exists():
            continue
        current = r
        break
    if not current:
        return False
    matches = list(
        qs.filter(round=f"Q{current}").select_related("winner", "player1", "player2")
    )
    winners = [m.winner for m in matches if m.winner]
    all_played = {m.player1_id for m in qs} | {m.player2_id for m in qs}
    extra_entries = (
        tournament.entries.select_for_update()
        .filter(entry_type=TournamentEntry.EntryType.Q, status="active")
        .exclude(player_id__in=all_played)
        .select_related("player")
    )
    winners.extend(e.player for e in extra_entries)
    if len(winners) < 2:
        return False
    next_code = f"Q{current // 2}"
    for i in range(0, len(winners), 2):
        if i + 1 >= len(winners):
            break
        m = Match(
            tournament=tournament,
            player1=winners[i],
            player2=winners[i + 1],
            round=next_code,
            section="",
            best_of=5,
        )
        if user:
            m.updated_by = user
        m.save()
    return True


@transaction.atomic
def promote_qualifiers(tournament: Tournament, user=None) -> bool:
    qs = tournament.matches.select_for_update().filter(round__startswith="Q")
    if not qs.exists():
        return False
    last = min(int(m.round[1:]) for m in qs)
    final_matches = qs.filter(round=f"Q{last}").select_related("winner")
    winners = [(m.winner, m) for m in final_matches if m.winner]
    if not winners:
        return False
    entries_map = {
        e.player_id: e
        for e in tournament.entries.select_for_update().filter(
            entry_type=TournamentEntry.EntryType.Q, status="active"
        )
    }
    to_place = []
    for player, match in winners:
        if not player:
            continue
        entry = entries_map.get(player.id)
        if not entry:
            entry = TournamentEntry(
                tournament=tournament,
                player=player,
                entry_type=TournamentEntry.EntryType.Q,
                status=TournamentEntry.Status.ACTIVE,
            )
        if entry.position:
            continue
        to_place.append((entry, match))
    if not to_place:
        return False
    occupied = set(
        tournament.entries.filter(status="active", position__isnull=False).values_list(
            "position", flat=True
        )
    )
    draw_size = tournament.draw_size or 0
    free = sorted(p for p in range(1, draw_size + 1) if p not in occupied)
    if len(free) < len(to_place):
        return False
    for (entry, match), pos in zip(to_place, free):
        entry.position = pos
        entry.origin_note = "Q"
        entry.origin_match = match
        if user:
            entry.updated_by = user
            entry.save(
                update_fields=["position", "origin_note", "origin_match", "updated_by"]
            )
        else:
            entry.save(update_fields=["position", "origin_note", "origin_match"])
    return True
