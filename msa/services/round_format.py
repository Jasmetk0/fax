from __future__ import annotations

from msa.models import Phase, RoundFormat, Tournament


def get_round_format(t: Tournament, phase: str, round_name: str) -> tuple[int, bool]:
    rf = RoundFormat.objects.filter(tournament=t, phase=phase, round_name=round_name).first()
    if rf:
        return rf.best_of, rf.win_by_two
    if phase == Phase.QUAL:
        return int(t.q_best_of or 3), True
    return int(t.md_best_of or 5), True
