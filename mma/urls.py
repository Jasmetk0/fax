from django.urls import path

from . import views

app_name = "mma"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("organizations/", views.organization_list, name="organization_list"),
    path(
        "organizations/<slug:slug>/",
        views.organization_detail,
        name="organization_detail",
    ),
    path("events/", views.event_list, name="event_list"),
    path("events/<slug:slug>/", views.event_detail, name="event_detail"),
    path("fighters/", views.fighter_list, name="fighter_list"),
    path("fighters/<slug:slug>/", views.fighter_detail, name="fighter_detail"),
    path("rankings/", views.ranking_list, name="ranking_list"),
    path(
        "rankings/<slug:org_slug>/<slug:weight_slug>/",
        views.ranking_detail,
        name="ranking_detail",
    ),
]
