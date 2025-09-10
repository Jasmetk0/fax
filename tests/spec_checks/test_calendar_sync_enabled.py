import datetime as dt

import pytest
from django.test import override_settings

from msa.models import Match, Schedule
from msa.services.calendar_sync import build_ics_for_days, is_enabled
from tests.factories import make_category_season, make_tournament


@pytest.mark.django_db
@override_settings(MSA_CALENDAR_SYNC_ENABLED=False)
def test_tournament_flag_generates_ics():
    cs, _, _ = make_category_season()
    t = make_tournament(cs=cs)
    t.calendar_sync_enabled = True
    t.save(update_fields=["calendar_sync_enabled"])
    m = Match.objects.create(tournament=t, round_name="R1")
    Schedule.objects.create(tournament=t, match=m, play_date=dt.date.today())
    ics = build_ics_for_days(t, [dt.date.today().isoformat()])
    assert "BEGIN:VCALENDAR" in ics
    assert f"UID:msa-{t.id}-" in ics
    assert is_enabled(t)
