import pytest
from django import forms

from msa.models import Player, RankingSnapshot, Schedule, Tournament


class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ["start_date", "end_date"]


def test_tournament_form_accepts_woorld_dates(db):
    form = TournamentForm(data={"start_date": "08-14-2000", "end_date": "21-14-2000"})
    assert form.is_valid(), form.errors
    t = form.save()
    t.refresh_from_db()
    assert t.start_date == "2000-14-08"
    assert t.end_date == "2000-14-21"


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ["play_date"]


def test_schedule_form_accepts_woorld_date(db):
    form = ScheduleForm(data={"play_date": "05-13-2024"})
    assert form.is_valid(), form.errors
    s = form.save()
    s.refresh_from_db()
    assert s.play_date == "2024-13-05"


class RankingSnapshotForm(forms.ModelForm):
    class Meta:
        model = RankingSnapshot
        fields = ["type", "monday_date", "hash"]


def test_rankingstat_monday_date_accepts_month_15_and_index(db):
    form = RankingSnapshotForm(
        data={"type": RankingSnapshot.Type.ROLLING, "monday_date": "2001-15-01", "hash": "h"}
    )
    assert form.is_valid(), form.errors
    snap = form.save()
    snap.refresh_from_db()
    assert snap.monday_date == "2001-15-01"
    assert RankingSnapshot._meta.get_field("monday_date").db_index


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ["full_name", "birthdate"]


def test_player_birthdate_rejects_month_gt_12_not_woorld(db):
    form = PlayerForm(data={"full_name": "X", "birthdate": "2000-13-01"})
    assert not form.is_valid()
    assert "birthdate" in form.errors
