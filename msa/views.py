from django.shortcuts import render


def index(request):
    """MSA landing page with links to sections."""
    return render(request, "msa/index.html")


def h2h(request):
    """Placeholder Head to Head page."""
    return render(request, "msa/h2h.html")


def players(request):
    """Placeholder Players page."""
    return render(request, "msa/players.html")


def squash_tv(request):
    """Placeholder Squash TV page."""
    return render(request, "msa/squash_tv.html")
