from django.contrib import admin

from .forms import TournamentForm
from .models import Country, Player, Tournament

admin.site.register(Country)
admin.site.register(Player)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    form = TournamentForm
    prepopulated_fields = {"slug": ("name",)}
    list_display = ["name", "start_date", "end_date"]
