from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "msa"

urlpatterns = [
    path(
        "",
        RedirectView.as_view(pattern_name="msa:tournaments_list", permanent=False),
        name="home",
    ),
    path("admin/action", views.admin_action, name="admin_action"),
    path("export/tournaments.csv", views.export_tournaments_csv, name="export_tournaments_csv"),
    path("export/calendar.ics", views.export_calendar_ics, name="export_calendar_ics"),
    path(
        "export/tournament/<int:tournament_id>/players.csv",
        views.export_tournament_players_csv,
        name="export_tournament_players_csv",
    ),
    # Landing na seznam sezón pro Tournaments
    path("tournaments/", views.tournaments_seasons, name="tournaments_list"),
    path("seasons/", views.seasons_list, name="seasons_list"),
    path("calendar/", views.calendar, name="calendar"),
    path("rankings", views.rankings_list, name="rankings_list"),
    path("players", views.players_list, name="players_list"),
    path("media", views.media, name="media"),
    path("docs", views.docs, name="docs"),
    path("search", views.search, name="search"),
    path(
        "tournament/<int:tournament_id>/",
        views.tournament_info,
        name="tournament_info",
    ),
    path(
        "tournament/<int:tournament_id>/program/",
        views.tournament_program,
        name="tournament_program",
    ),
    path(
        "tournament/<int:tournament_id>/draws/",
        views.tournament_draws,
        name="tournament_draws",
    ),
    path(
        "tournament/<int:tournament_id>/players/",
        views.tournament_players,
        name="tournament_players",
    ),
    path(
        "tournament/<int:tournament_id>/media/",
        views.tournament_media,
        name="tournament_media",
    ),
]
