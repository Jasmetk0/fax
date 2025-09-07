"""Widget registrations for the MMA app."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Widget:
    """Simple widget representation."""

    title: str
    render: Callable[..., str]


def dashboard_widget() -> Widget:
    """Placeholder MMA dashboard widget."""
    return Widget(title="MMA", render=lambda: "")
