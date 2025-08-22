from django.urls import path
from . import views

app_name = "wiki"

urlpatterns = [
    path("", views.ArticleListView.as_view(), name="article-list"),
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
    path("<slug:slug>/edit/", views.ArticleUpdateView.as_view(), name="article-edit"),
    path("<slug:slug>/", views.ArticleDetailView.as_view(), name="article-detail"),
]
