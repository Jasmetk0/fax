"""Views for the MMA app."""

from django.shortcuts import render


def dashboard(request):
    """Render the MMA dashboard."""
    return render(request, "mma/dashboard.html")
