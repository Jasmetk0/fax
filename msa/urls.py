from django.urls import path

from .views import (
    TournamentCreateView,
    TournamentDetailView,
    TournamentListView,
)

app_name = "msa"

urlpatterns = [
    path("tournaments/", TournamentListView.as_view(), name="tournament_list"),
    path("tournaments/new", TournamentCreateView.as_view(), name="tournament_create"),
    path(
        "tournaments/<slug:slug>/",
        TournamentDetailView.as_view(),
        name="tournament_detail",
    ),
]
