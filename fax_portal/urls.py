from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView  # RedirectView už nepotřebujeme

from fax_calendar import views as calendar_views
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
    path("mma/", include("mma.urls")),
    path("api/mma/", include("mma.api.urls")),
<<<<<<< HEAD
=======
    # ✅ NOVĚ: jediný mount MSA pod /msa/ s namespace "msa"
>>>>>>> 17c27c8 (MSA FE: Tournaments → Seasons list (dynamic), robust Season lookup, debug header [fmt])
    path("msa/", include("msa.urls", namespace="msa")),
    path("woorld/", include("fax_calendar.urls")),
    path(
        "api/fax_calendar/year/<int:y>/meta",
        calendar_views.year_meta,
        name="fax-calendar-year-meta",
    ),
    path("search/suggest", search_views.suggest, name="search-suggest"),
    path("search", search_views.search, name="search"),
    path(
        "manifest.json",
        TemplateView.as_view(template_name="manifest.json", content_type="application/json"),
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
