from django.urls import path

from . import views

app_name = "fax_calendar"

urlpatterns = [
    path("date/set/", views.set_woorld_date, name="set_woorld_date"),
    path("year/<int:y>/meta/", views.year_meta, name="year_meta"),
]
