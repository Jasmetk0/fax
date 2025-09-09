import pytest
from django.test import override_settings

from msa.models import Match, Schedule, Tournament
from msa.services.calendar_sync import build_ics_for_days, escape_ics


@pytest.mark.django_db
@override_settings(MSA_CALENDAR_SYNC_ENABLED=True)
def test_build_ics_returns_events_for_multiple_days_when_enabled():
    t = Tournament.objects.create(name="TT", slug="tt")
    m1 = Match.objects.create(tournament=t, round_name="R1", slot_top=1, slot_bottom=2)
    m2 = Match.objects.create(tournament=t, round_name="R1", slot_top=3, slot_bottom=4)
    Schedule.objects.create(tournament=t, play_date="2025-08-01", order=1, match=m1)
    Schedule.objects.create(tournament=t, play_date="2025-08-02", order=1, match=m2)

    ics = build_ics_for_days(t, ["2025-08-01", "2025-08-02"])
    assert "BEGIN:VCALENDAR" in ics
    assert ics.count("BEGIN:VEVENT") == 2
    assert "DTSTART;VALUE=DATE:20250801" in ics
    assert "DTSTART;VALUE=DATE:20250802" in ics
    assert f"SUMMARY:{t.name} – Day Order (2025-08-01)" in ics


@pytest.mark.django_db
@override_settings(MSA_CALENDAR_SYNC_ENABLED=False)
def test_build_ics_returns_empty_when_disabled():
    t = Tournament.objects.create(name="TT2", slug="tt2")
    result = build_ics_for_days(t, ["2025-08-01"])
    assert result == ""


def test_escape_ics_escapes_commas_semicolons_and_newlines():
    text = "a,b;c\nnext"
    assert escape_ics(text) == "a\\,b\\;c\\nnext"
