from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from search import views as search_views
from wiki.urls import api_urlpatterns as wiki_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("shell.urls")),
    path("wiki/", include("wiki.urls")),
    path("api/", include((wiki_api, "wiki"), namespace="wiki-api")),
    path("maps/", include("maps.urls")),
    path("openfaxmap/", include("openfaxmap.urls")),
    path("livesport/", include("sports.urls")),
    path("msasquashtour/", include("msa.urls")),
    path("woorld/", include("fax_calendar.urls")),
    path("search", search_views.search, name="search"),
    path(
        "manifest.json",
        TemplateView.as_view(
            template_name="manifest.json", content_type="application/json"
        ),
        name="manifest",
    ),
    path(
        "service-worker.js",
        TemplateView.as_view(
            template_name="service-worker.js", content_type="application/javascript"
        ),
        name="service-worker",
    ),
]
