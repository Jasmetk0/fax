from django.shortcuts import render


def index(request):
    """Render the OpenFaxMap page."""
    return render(request, "openfaxmap/index.html")
