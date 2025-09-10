from django.urls import path

from . import views_public

app_name = "msa_public"

urlpatterns = [
    path("", views_public.TournamentListView.as_view(), name="tournament_list"),
    path("t/<slug:slug>/", views_public.TournamentDetailView.as_view(), name="tournament_detail"),
    path(
        "t/<slug:slug>/registration/", views_public.RegistrationView.as_view(), name="registration"
    ),
    path(
        "t/<slug:slug>/qualification/",
        views_public.QualificationView.as_view(),
        name="qualification",
    ),
    path("t/<slug:slug>/main-draw/", views_public.MainDrawView.as_view(), name="main_draw"),
    path("t/<slug:slug>/schedule/", views_public.ScheduleView.as_view(), name="schedule"),
    path("t/<slug:slug>/results/", views_public.ResultsView.as_view(), name="results"),
    path(
        "standings/season/<int:season_id>/",
        views_public.SeasonStandingsView.as_view(),
        name="season_standings",
    ),
    path(
        "standings/rolling/", views_public.RollingStandingsView.as_view(), name="rolling_standings"
    ),
    path("standings/rtf/", views_public.RtFStandingsView.as_view(), name="rtf_standings"),
]
