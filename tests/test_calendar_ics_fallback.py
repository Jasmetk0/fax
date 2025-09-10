from datetime import date

import pytest

from msa.models import Match, MatchState, Phase, Schedule
from msa.services.calendar_sync import build_match_vevent
from tests.factories import make_player, make_tournament


@pytest.mark.django_db
def test_ics_fallback_order_via_schedule_lookup():
    t = make_tournament()
    a = make_player("A")
    b = make_player("B")

    m = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=16,
        player_top_id=a.id,
        player_bottom_id=b.id,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,
    )

    play_date = date(2025, 6, 1)
    Schedule.objects.create(tournament=t, match=m, play_date=play_date, order=3)
    m._schedule_cache = None

    vevent = build_match_vevent(m, play_date.isoformat())
    assert "Order: 3" in vevent
    assert "R16" in vevent
