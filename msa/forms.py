from django import forms

from fax_calendar.widgets import WoorldAdminDateWidget

from .models import Tournament


class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ["name", "slug", "start_date", "end_date"]
        widgets = {
            "start_date": WoorldAdminDateWidget(),
            "end_date": WoorldAdminDateWidget(),
        }
