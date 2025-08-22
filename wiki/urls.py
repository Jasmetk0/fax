"""URL configuration for wiki app."""

from django.urls import path
from . import views

app_name = "wiki"

urlpatterns = [
    path("", views.ArticleListView.as_view(), name="article-list"),
    path("create/", views.ArticleCreateView.as_view(), name="article-create"),
    path("<slug:slug>/edit/", views.ArticleUpdateView.as_view(), name="article-edit"),
    path("<slug:slug>/", views.ArticleDetailView.as_view(), name="article-detail"),
]
