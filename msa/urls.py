from django.urls import path

from . import manage_views, views

app_name = "msa"

urlpatterns = [
    path("", views.home, name="home"),
    path("tournaments/", views.tournaments, name="tournament-list"),
    path(
        "tournaments/<slug:slug>/",
        views.tournament_detail,
        name="tournament-detail",
    ),
    path("live/", views.live, name="live"),  # MSA-REDESIGN: redirect to scores
    path("scores/", views.scores, name="scores"),  # MSA-REDESIGN
    path("search/", views.msa_search, name="search"),  # MSA-REDESIGN
    path("tickets/", views.tickets, name="tickets"),  # MSA-REDESIGN
    path("stats/", views.stats, name="stats"),  # MSA-REDESIGN
    path("shop/", views.shop, name="shop"),  # MSA-REDESIGN
    path("press/", views.press, name="press"),  # MSA-REDESIGN
    path("about/", views.about, name="about"),  # MSA-REDESIGN
    path("rankings/", views.rankings, name="rankings"),
    path("players/", views.players, name="player-list"),
    path("players/<slug:slug>/", views.player_detail, name="player-detail"),
    path("h2h/", views.h2h, name="h2h"),
    path("squashtv/", views.squashtv, name="squashtv"),
    path("news/", views.news, name="news"),
    path("news/<slug:slug>/", views.news_detail, name="news-detail"),
    # Manage routes
    path("manage/players/new/", manage_views.player_create, name="player-create"),
    path(
        "manage/players/<slug:slug>/edit/", manage_views.player_edit, name="player-edit"
    ),
    path(
        "manage/players/<slug:slug>/delete/",
        manage_views.player_delete,
        name="player-delete",
    ),
    path(
        "manage/tournaments/new/",
        manage_views.tournament_create,
        name="tournament-create",
    ),
    path(
        "manage/tournaments/<slug:slug>/edit/",
        manage_views.tournament_edit,
        name="tournament-edit",
    ),
    path(
        "manage/tournaments/<slug:slug>/delete/",
        manage_views.tournament_delete,
        name="tournament-delete",
    ),
    path("manage/matches/new/", manage_views.match_create, name="match-create"),
    path("manage/matches/<int:pk>/edit/", manage_views.match_edit, name="match-edit"),
    path(
        "manage/matches/<int:pk>/delete/",
        manage_views.match_delete,
        name="match-delete",
    ),
    path(
        "manage/rankings/snapshots/new/",
        manage_views.snapshot_create,
        name="snapshot-create",
    ),
    path(
        "manage/rankings/snapshots/<int:pk>/edit/",
        manage_views.snapshot_edit,
        name="snapshot-edit",
    ),
    path(
        "manage/rankings/snapshots/<int:pk>/delete/",
        manage_views.snapshot_delete,
        name="snapshot-delete",
    ),
    path(
        "manage/rankings/entries/new/", manage_views.entry_create, name="entry-create"
    ),
    path(
        "manage/rankings/entries/<int:pk>/edit/",
        manage_views.entry_edit,
        name="entry-edit",
    ),
    path(
        "manage/rankings/entries/<int:pk>/delete/",
        manage_views.entry_delete,
        name="entry-delete",
    ),
    path("manage/news/new/", manage_views.news_create, name="news-create"),
    path("manage/news/<slug:slug>/edit/", manage_views.news_edit, name="news-edit"),
    path(
        "manage/news/<slug:slug>/delete/", manage_views.news_delete, name="news-delete"
    ),
    path("manage/media/new/", manage_views.media_create, name="media-create"),
    path("manage/media/<slug:slug>/edit/", manage_views.media_edit, name="media-edit"),
    path(
        "manage/media/<slug:slug>/delete/",
        manage_views.media_delete,
        name="media-delete",
    ),
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
