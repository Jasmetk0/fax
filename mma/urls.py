from django.urls import path

from . import views

app_name = "mma"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
