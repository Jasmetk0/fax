from django.urls import path

from . import views

app_name = "msa"

urlpatterns = [
    path("", views.home, name="home"),
    path("tournaments", views.tournaments_list, name="tournaments_list"),
    path("rankings", views.rankings_list, name="rankings_list"),
    path("players", views.players_list, name="players_list"),
    path("calendar", views.calendar, name="calendar"),
    path("media", views.media, name="media"),
    path("docs", views.docs, name="docs"),
    path("search", views.search, name="search"),
    path("status/live-badge", views.nav_live_badge, name="nav_live_badge"),
]
# Vysvětlení: simple routes bez trailing slashe pro čisté URL; lze změnit dle projektu.
