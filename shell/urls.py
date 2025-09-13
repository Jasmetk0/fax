from django.urls import path

from shell import views

urlpatterns = [
    path("set-date/", views.set_global_date, name="set_date"),
    path("", views.home, name="home"),
    path("admin-toggle/", views.admin_toggle, name="admin-toggle"),
]
