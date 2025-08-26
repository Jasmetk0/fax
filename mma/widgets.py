"""Widget registrations for the MMA app."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class Widget:
    """Simple widget representation."""

    title: str
    render: Callable[..., str]


def upcoming_widget() -> Widget:
    """Placeholder upcoming events widget."""
    return Widget(title="MMA: Upcoming", render=lambda: "")


def results_widget() -> Widget:
    """Placeholder recent results widget."""
    return Widget(title="MMA: Results", render=lambda: "")
