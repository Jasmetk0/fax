"""Local fixtures provider for MMA data."""

from .base import MMADataProvider


class LocalFixtureProvider(MMADataProvider):
    """Provider implementation that sources data from local fixtures."""

    def events(self):  # type: ignore[override]
        return []

    def results(self):  # type: ignore[override]
        return []

    def fighters(self):  # type: ignore[override]
        return []

    def rankings(self):  # type: ignore[override]
        return []

    def news(self):  # type: ignore[override]
        return []
