from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from .api_data import DataPointDetail, DataSeriesByCategory, DataSeriesViewSet
from .views_data import (
    DataSeriesCreateView,
    DataSeriesDeleteView,
    DataSeriesDetailView,
    DataSeriesListView,
    DataSeriesUpdateView,
)

app_name = "wiki"

urlpatterns = [
    path("", views.ArticleListView.as_view(), name="article-list"),
    path("suggest/", views.article_suggest, name="article-suggest"),
    path("create/", views.ArticleCreateView.as_view(), name="article-create"),
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path(
        "categories/create/", views.CategoryCreateView.as_view(), name="category-create"
    ),
    path(
        "categories/<slug:slug>/edit/",
        views.CategoryUpdateView.as_view(),
        name="category-edit",
    ),
    path(
        "categories/<slug:slug>/delete/",
        views.CategoryDeleteView.as_view(),
        name="category-delete",
    ),
    path("dataseries/", DataSeriesListView.as_view(), name="dataseries-list"),
    path(
        "dataseries/create/",
        DataSeriesCreateView.as_view(),
        name="dataseries-create",
    ),
    path(
        "dataseries/<path:slug>/edit/",
        DataSeriesUpdateView.as_view(),
        name="dataseries-edit",
    ),
    path(
        "dataseries/<path:slug>/delete/",
        DataSeriesDeleteView.as_view(),
        name="dataseries-delete",
    ),
    path(
        "dataseries/<path:slug>/",
        DataSeriesDetailView.as_view(),
        name="dataseries-detail",
    ),
    path("<slug:slug>/edit/", views.ArticleUpdateView.as_view(), name="article-edit"),
    path(
        "<slug:slug>/delete/",
        views.ArticleDeleteView.as_view(),
        name="article-delete",
    ),
    path(
        "<slug:slug>/history/",
        views.ArticleHistoryView.as_view(),
        name="article-history",
    ),
    path(
        "<slug:slug>/diff/<int:rev_id>/",
        views.ArticleRevisionDiffView.as_view(),
        name="article-diff",
    ),
    path(
        "<slug:slug>/revert/<int:rev_id>/",
        views.ArticleRevisionRevertView.as_view(),
        name="article-revert",
    ),
    path("<slug:slug>/", views.ArticleDetailView.as_view(), name="article-detail"),
]


router = DefaultRouter()
router.register("dataseries", DataSeriesViewSet, basename="dataseries")

api_urlpatterns = [
    path(
        "dataseries/<path:slug>/point/<str:key>/",
        DataPointDetail.as_view(),
        name="dataseries-point",
    ),
    path(
        "dataseries/category/<str:category>/",
        DataSeriesByCategory.as_view(),
        name="dataseries-category",
    ),
] + router.urls
