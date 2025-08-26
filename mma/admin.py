"""Admin registrations for MMA models."""

from django.contrib import admin

from . import models

admin.site.register(
    [
        models.Organization,
        models.WeightClass,
        models.Venue,
        models.Event,
        models.Fighter,
        models.Bout,
        models.Ranking,
        models.NewsItem,
    ]
)
