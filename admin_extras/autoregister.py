from __future__ import annotations

from django.apps import apps
from django.contrib import admin
from django.db import models

from admin_extras.admixins import WorldDateAdminMixin


def _fields(model):
    return [f for f in model._meta.get_fields() if not f.many_to_many and not f.one_to_many]


def _has_field(model, name: str) -> bool:
    return any(getattr(f, "name", None) == name for f in _fields(model))


def _first_existing(model, names: list[str]) -> str | None:
    for n in names:
        if _has_field(model, n):
            return n
    return None


def _list_display_for(model) -> tuple:
    # Preferované sloupce, co existují
    prefs = (
        "id",
        "name",
        "title",
        "slug",
        "type",
        "monday_date",
        "start_date",
        "end_date",
        "created_at",
        "updated_at",
    )
    cols = [n for n in prefs if _has_field(model, n)]
    # doplň max do 8 sloupců podle jednoduché heuristiky
    if len(cols) < 8:
        for f in _fields(model):
            n = getattr(f, "name", "")
            if n and n not in cols and not n.endswith("_id"):
                cols.append(n)
            if len(cols) >= 8:
                break
    return tuple(cols[:8]) or ("id",)


def _search_fields_for(model) -> tuple:
    cands = ("name", "title", "slug", "hash")
    return tuple(n for n in cands if _has_field(model, n))


def _list_filter_for(model) -> tuple:
    out = []
    for n in ("type", "is_alias", "monday_date", "start_date", "end_date", "created_at"):
        if _has_field(model, n):
            out.append(n)
    # boolean pole (jednoduchá heuristika)
    for f in _fields(model):
        if isinstance(f, models.BooleanField):
            n = getattr(f, "name", None)
            if n and n not in out:
                out.append(n)
    return tuple(out[:6])


def _date_hierarchy_for(model) -> str | None:
    return _first_existing(
        model, ["monday_date", "start_date", "end_date", "created_at", "updated_at"]
    )


def _readonly_for(model) -> tuple:
    ro = []
    for n in ("created_at", "updated_at"):
        if _has_field(model, n):
            ro.append(n)
    return tuple(ro)


def _raw_id_for(model) -> tuple:
    # Z důvodu výkonu preferuj raw_id pro všechny ForeignKey
    return tuple(f.name for f in _fields(model) if isinstance(f, models.ForeignKey))


def _build_generic_admin(model):
    attrs = {}
    dh = _date_hierarchy_for(model)
    if dh:
        attrs["date_hierarchy"] = dh
    attrs["list_display"] = _list_display_for(model)
    sf = _search_fields_for(model)
    if sf:
        attrs["search_fields"] = sf
    lf = _list_filter_for(model)
    if lf:
        attrs["list_filter"] = lf
    ro = _readonly_for(model)
    if ro:
        attrs["readonly_fields"] = ro
    rif = _raw_id_for(model)
    if rif:
        attrs["raw_id_fields"] = rif

    return type(
        f"{model.__name__}AutoAdmin",
        (WorldDateAdminMixin, admin.ModelAdmin),
        attrs,
    )


def apply_date_widget_to_registered_admins():
    # Dodatečně napatchuj všechny již zaregistrované ModelAdminy tak,
    # aby jejich formfield_overrides zahrnoval náš Date widget
    for _model, adm in list(admin.site._registry.items()):
        ffo = getattr(adm, "formfield_overrides", {}) or {}
        # merge – nenič existující overrides
        from django.db import models as djm

        ffo[djm.DateField] = {
            "widget": WorldDateAdminMixin.formfield_overrides[djm.DateField]["widget"]
        }
        adm.formfield_overrides = ffo


def autoregister_all_models():
    # Zaregistruj všechny modely, které zatím v adminu nejsou
    registered = set(admin.site._registry.keys())
    for app in apps.get_app_configs():
        for model in app.get_models():
            if model in registered:
                continue
            try:
                admin.site.register(model, _build_generic_admin(model))
            except admin.sites.AlreadyRegistered:
                pass


def run():
    # 1) Autoregistrace chybějících modelů
    autoregister_all_models()
    # 2) Patch existujících adminů na sjednocený date widget
    apply_date_widget_to_registered_admins()
