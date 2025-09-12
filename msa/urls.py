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
    path("tournaments", views.tournaments_list, name="tournaments_list"),
    path("calendar", views.calendar, name="calendar"),
    path("rankings", views.rankings_list, name="rankings_list"),
    path("players", views.players_list, name="players_list"),
    path("media", views.media, name="media"),
    path("docs", views.docs, name="docs"),
    path("search", views.search, name="search"),
]
