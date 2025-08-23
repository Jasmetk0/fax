from django.urls import path
from . import views

app_name = "msa"

urlpatterns = [
    path("", views.index, name="index"),
    path("h2h/", views.h2h, name="h2h"),
    path("players/", views.players, name="players"),
    path("squash-tv/", views.squash_tv, name="squash-tv"),
]
