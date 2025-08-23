from django.urls import path

from . import views

app_name = "msa"

urlpatterns = [
    path("", views.home, name="home"),
    path("tournaments/", views.tournaments, name="tournament-list"),
    path(
        "tournaments/<slug:slug>/",
        views.tournament_detail,
        name="tournament-detail",
    ),
    path("live/", views.live, name="live"),
    path("rankings/", views.rankings, name="rankings"),
    path("players/", views.players, name="player-list"),
    path("players/<slug:slug>/", views.player_detail, name="player-detail"),
    path("h2h/", views.h2h, name="h2h"),
    path("squashtv/", views.squashtv, name="squashtv"),
    path("news/", views.news, name="news"),
    path("news/<slug:slug>/", views.news_detail, name="news-detail"),
    # API
    path("api/players/", views.api_players, name="api_players"),
    path("api/players/<slug:slug>/", views.api_player_detail, name="api_player"),
    path("api/tournaments/", views.api_tournaments, name="api_tournaments"),
    path(
        "api/tournaments/<slug:slug>/",
        views.api_tournament_detail,
        name="api_tournament",
    ),
    path(
        "api/tournaments/<slug:slug>/matches/",
        views.api_tournament_matches,
        name="api_tournament_matches",
    ),
    path("api/rankings/", views.api_rankings, name="api_rankings"),
    path("api/h2h/", views.api_h2h, name="api_h2h"),
    path("api/live/", views.api_live, name="api_live"),
]
