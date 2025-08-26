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
    path(
        "organizations/add/",
        views.OrganizationCreateView.as_view(),
        name="organization_add",
    ),
    path(
        "organizations/<slug:slug>/edit/",
        views.OrganizationUpdateView.as_view(),
        name="organization_edit",
    ),
    path(
        "organizations/<slug:slug>/delete/",
        views.OrganizationDeleteView.as_view(),
        name="organization_delete",
    ),
    path("events/", views.event_list, name="event_list"),
    path("events/<slug:slug>/", views.event_detail, name="event_detail"),
    path("events/add/", views.EventCreateView.as_view(), name="event_add"),
    path(
        "events/<slug:slug>/edit/",
        views.EventUpdateView.as_view(),
        name="event_edit",
    ),
    path(
        "events/<slug:slug>/delete/",
        views.EventDeleteView.as_view(),
        name="event_delete",
    ),
    path(
        "events/<slug:event_slug>/bouts/add/",
        views.BoutCreateView.as_view(),
        name="bout_add",
    ),
    path("bouts/<int:pk>/edit/", views.BoutUpdateView.as_view(), name="bout_edit"),
    path(
        "bouts/<int:pk>/delete/",
        views.BoutDeleteView.as_view(),
        name="bout_delete",
    ),
    path("fighters/", views.fighter_list, name="fighter_list"),
    path("fighters/<slug:slug>/", views.fighter_detail, name="fighter_detail"),
    path("fighters/add/", views.FighterCreateView.as_view(), name="fighter_add"),
    path(
        "fighters/<slug:slug>/edit/",
        views.FighterUpdateView.as_view(),
        name="fighter_edit",
    ),
    path(
        "fighters/<slug:slug>/delete/",
        views.FighterDeleteView.as_view(),
        name="fighter_delete",
    ),
    path("rankings/", views.ranking_list, name="ranking_list"),
    path(
        "rankings/<slug:org_slug>/<slug:weight_slug>/",
        views.ranking_detail,
        name="ranking_detail",
    ),
    path("rankings/add/", views.RankingCreateView.as_view(), name="ranking_add"),
    path(
        "rankings/<int:pk>/edit/",
        views.RankingUpdateView.as_view(),
        name="ranking_edit",
    ),
    path(
        "rankings/<int:pk>/delete/",
        views.RankingDeleteView.as_view(),
        name="ranking_delete",
    ),
    path("news/add/", views.NewsItemCreateView.as_view(), name="news_add"),
    path(
        "news/<slug:slug>/edit/", views.NewsItemUpdateView.as_view(), name="news_edit"
    ),
    path(
        "news/<slug:slug>/delete/",
        views.NewsItemDeleteView.as_view(),
        name="news_delete",
    ),
]
