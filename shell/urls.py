from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin-toggle/", views.admin_toggle, name="admin-toggle"),
]
