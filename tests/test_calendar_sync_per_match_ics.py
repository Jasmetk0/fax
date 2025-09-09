import pytest
from django.test import override_settings

from msa.models import Match, Player, Schedule, Tournament
from msa.services.calendar_sync import build_ics_for_matches, build_match_vevent


@pytest.mark.django_db
@override_settings(MSA_CALENDAR_SYNC_ENABLED=True)
def test_build_ics_for_matches_emits_one_event_per_scheduled_match():
    t = Tournament.objects.create(name="TT", slug="tt")
    p1 = Player.objects.create(name="A")
    p2 = Player.objects.create(name="B")
    p3 = Player.objects.create(name="C")
    p4 = Player.objects.create(name="D")

    m1 = Match.objects.create(
        tournament=t,
        round_name="R1",
        slot_top=1,
        slot_bottom=2,
        player_top=p1,
        player_bottom=p2,
    )
    m2 = Match.objects.create(
        tournament=t,
        round_name="R1",
        slot_top=3,
        slot_bottom=4,
        player_top=p3,
        player_bottom=p4,
    )
    Schedule.objects.create(tournament=t, play_date="2025-08-01", order=1, match=m1)
    Schedule.objects.create(tournament=t, play_date="2025-08-02", order=1, match=m2)

    ics = build_ics_for_matches(t, ["2025-08-01", "2025-08-02"])
    assert "BEGIN:VCALENDAR" in ics
    assert ics.count("BEGIN:VEVENT") == 2
    assert f"UID:msa-match-{m1.id}" in ics
    assert f"UID:msa-match-{m2.id}" in ics
    assert f"SUMMARY:R1 – {p1.name} vs {p2.name}" in ics
    assert f"SUMMARY:R1 – {p3.name} vs {p4.name}" in ics
    assert "DTSTART;VALUE=DATE:20250801" in ics
    assert "DTSTART;VALUE=DATE:20250802" in ics


@pytest.mark.django_db
@override_settings(MSA_CALENDAR_SYNC_ENABLED=False)
def test_build_ics_for_matches_respects_flag_and_returns_empty_when_disabled():
    t = Tournament.objects.create(name="TT2", slug="tt2")
    m = Match.objects.create(tournament=t, round_name="R1", slot_top=1, slot_bottom=2)
    Schedule.objects.create(tournament=t, play_date="2025-08-01", order=1, match=m)

    result = build_ics_for_matches(t, ["2025-08-01"])
    assert result == ""


@pytest.mark.django_db
def test_build_match_vevent_escapes_text():
    t = Tournament.objects.create(name="TT3", slug="tt3")
    p1 = Player.objects.create(name="A,B;C\nD")
    p2 = Player.objects.create(name="E")
    m = Match.objects.create(
        tournament=t,
        round_name="R1",
        slot_top=1,
        slot_bottom=2,
        player_top=p1,
        player_bottom=p2,
    )
    Schedule.objects.create(tournament=t, play_date="2025-08-01", order=3, match=m)

    vevent = build_match_vevent(m, "2025-08-01")
    assert "SUMMARY:R1 – A\\,B\\;C\\nD vs E" in vevent
    assert "DESCRIPTION:Slot: [1 vs 2]\\, Order: 3" in vevent
