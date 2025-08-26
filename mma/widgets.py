"""Widget registrations for the MMA app."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class Widget:
    """Simple widget representation."""

    title: str
    render: Callable[..., str]


def dashboard_widget() -> Widget:
    """Placeholder MMA dashboard widget."""
    return Widget(title="MMA", render=lambda: "")
