from django.urls import path

from . import views

urlpatterns = [
    path("events/", views.EventList.as_view(), name="event-list"),
    path("events/<slug:slug>/", views.EventDetail.as_view(), name="event-detail"),
    path("news/", views.NewsList.as_view(), name="news-list"),
    path("news/<slug:slug>/", views.NewsDetail.as_view(), name="news-detail"),
]
