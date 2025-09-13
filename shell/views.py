import json

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from msa.utils.dates import _parse_date, _woorld_to_gregorian


def home(request):
    return render(request, "shell/index.html")


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_toggle(request):
    request.session["admin_mode"] = not request.session.get("admin_mode", False)
    return redirect(request.META.get("HTTP_REFERER", "/"))


@csrf_exempt
@require_POST
def set_global_date(request):
    """Ulož vybrané datum do session + cookie a vrať ISO."""
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        payload = request.POST
    raw = payload.get("date") or payload.get("d")
    if not raw:
        return HttpResponseBadRequest("missing date")

    d = _parse_date(str(raw)) or _woorld_to_gregorian(raw)
    if not d:
        return HttpResponseBadRequest("invalid date")

    iso = d.isoformat()
    # Session
    request.session["topbar_date"] = iso
    request.session["global_date"] = iso
    request.session.modified = True

    # Odpověď + cookie
    resp = JsonResponse({"ok": True, "iso": iso})
    # ~6 měsíců
    max_age = 60 * 60 * 24 * 180
    resp.set_cookie("topbar_date", iso, max_age=max_age, samesite="Lax")
    resp.set_cookie("global_date", iso, max_age=max_age, samesite="Lax")
    return resp
