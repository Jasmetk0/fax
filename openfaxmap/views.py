from django.conf import settings
from django.shortcuts import render


def index(request):
    """Render the OpenFaxMap page."""
    context = {
        "tile_url": settings.OFM_TILE_URL,
        "tile_attribution": settings.OFM_TILE_ATTRIBUTION,
        "style_url": settings.OFM_STYLE_URL,
    }
    return render(request, "openfaxmap/index.html", context)
