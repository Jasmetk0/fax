"""Views for Woorld calendar utilities."""

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .utils import parse_woorld_ddmmyyyy, format_woorld_ddmmyyyy


@require_POST
def set_woorld_date(request):
    """Store current Woorld date in session."""
    date_str = request.POST.get("date", "")
    try:
        year, month, day = parse_woorld_ddmmyyyy(date_str)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    request.session["woorld_current_date"] = format_woorld_ddmmyyyy(year, month, day)
    return JsonResponse({"status": "ok"})
