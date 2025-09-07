"""Base provider interface for MMA data."""

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping


class MMADataProvider(ABC):
    """Abstract base class for MMA data providers."""

    @abstractmethod
    def events(self) -> Iterable[Mapping]:
        """Return iterable of event data."""

    @abstractmethod
    def results(self) -> Iterable[Mapping]:
        """Return iterable of result data."""

    @abstractmethod
    def fighters(self) -> Iterable[Mapping]:
        """Return iterable of fighter data."""

    @abstractmethod
    def rankings(self) -> Iterable[Mapping]:
        """Return iterable of ranking data."""

    @abstractmethod
    def news(self) -> Iterable[Mapping]:
        """Return iterable of news items."""
