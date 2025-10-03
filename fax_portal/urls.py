from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from fax_calendar import views as calendar_views
from msa import views as msa_views
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
    path("api/msa/ranking", msa_views.ranking_api, name="msa-ranking-api"),
    path("api/msa/season", msa_views.season_api, name="msa-season-api"),
    path("api/msa/tournaments", msa_views.tournaments_api, name="msa-tournaments-api"),
    path(
        "api/msa/tournament/<int:tournament_id>/matches",
        msa_views.tournament_matches_api,
        name="msa-tournament-matches-api",
    ),
    path(
        "api/msa/tournament/<int:tournament_id>/courts",
        msa_views.tournament_courts_api,
        name="msa-tournament-courts-api",
    ),
    path(
        "api/msa/tournament/<int:tournament_id>/entries",
        msa_views.tournament_entries_api,
        name="msa-tournament-entries-api",
    ),
    path(
        "api/msa/tournament/<int:tournament_id>/qualification",
        msa_views.tournament_qualification_api,
        name="msa-tournament-qualification-api",
    ),
    path(
        "api/msa/tournament/<int:tournament_id>/maindraw",
        msa_views.tournament_maindraw_api,
        name="msa-tournament-maindraw-api",
    ),
    path(
        "api/msa/tournament/<int:tournament_id>/history",
        msa_views.tournament_history_api,
        name="msa-tournament-history-api",
    ),
    # pouze nový MSA mount s namespace "msa"
    path("msa/", include("msa.urls", namespace="msa")),
    path("status/live-badge", msa_views.nav_live_badge, name="nav_live_badge"),
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
    path(
        "squashengine",
        TemplateView.as_view(template_name="squashengine.html"),
        name="squashengine",
    ),
    path("squashengine/", TemplateView.as_view(template_name="squashengine.html")),
]
