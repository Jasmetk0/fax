"""Views for Woorld calendar utilities."""

from django.http import (
    JsonResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.views.decorators.http import require_POST

from .utils import parse_woorld_ddmmyyyy, format_woorld_ddmmyyyy


@require_POST
def set_woorld_date(request):
    """Store current Woorld date in session."""
    date_str = request.POST.get("woorld_date", "")
    try:
        year, month, day = parse_woorld_ddmmyyyy(date_str)
    except ValueError as exc:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"error": str(exc)}, status=400)
        return HttpResponseBadRequest(str(exc))
    formatted = format_woorld_ddmmyyyy(year, month, day)
    request.session["woorld_current_date"] = formatted
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "value": formatted})
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
