from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render


def home(request):
    return render(request, "shell/index.html")


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_toggle(request):
    request.session["admin_mode"] = not request.session.get("admin_mode", False)
    return redirect(request.META.get("HTTP_REFERER", "/"))
