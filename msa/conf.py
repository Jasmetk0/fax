from datetime import date

from django.conf import settings

RANKINGS_MODE = getattr(settings, "RANKINGS_MODE", "hybrid")
FIRST_OFFICIAL_MONDAY = getattr(settings, "FIRST_OFFICIAL_MONDAY", date(2025, 9, 15))
LAST_OFFICIAL_MONDAY = getattr(settings, "LAST_OFFICIAL_MONDAY", None)
RETENTION_FULL_WEEKS = getattr(settings, "RETENTION_FULL_WEEKS", 0)
DEDUP_ENABLED = getattr(settings, "DEDUP_ENABLED", True)
SEEDING_STRICT = getattr(settings, "SEEDING_STRICT", True)
