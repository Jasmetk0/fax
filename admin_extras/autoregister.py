from __future__ import annotations

from django import forms as djf
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.db import models
from django.db import models as djm

from admin_extras.admixins import (
    FAX_DATE_FORMAT,
    FAX_INPUT_FORMATS,
    WorldDateAdminMixin,
    _resolve_date_widget,
)

# --- Woorld helpers (module-level) ---
_WOORLD_WIDGET_MODULES = ("fax_calendar.widgets",)
_WOORLD_WIDGET_NAME_HINTS = ("woorld", "world", "fax")  # case-insensitive


def is_woorld_widget(w) -> bool:
    if not w:
        return False
    mod = (getattr(w, "__module__", "") or "").lower()
    name = w.__class__.__name__.lower()
    if any(mod.startswith(m) for m in _WOORLD_WIDGET_MODULES):
        return True
    return any(k in name for k in _WOORLD_WIDGET_NAME_HINTS)


def is_woorld_dbfield(f) -> bool:
    # Nezasahuj do reálných Date/DateTime polí – ty jsou gregoriánská.
    if isinstance(f, djm.DateField) or isinstance(f, djm.DateTimeField):
        return False
    # Opt-in flagy na samotném model field objektu (volitelné)
    if getattr(f, "fax_date", False) or getattr(f, "woorld_date", False):
        return True
    # Konzervativně povol jen Char/TextField – přesně jak je to teď
    return isinstance(f, djm.CharField) or isinstance(f, djm.TextField)


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
    for name in ["monday_date", "start_date", "end_date", "created_at", "updated_at"]:
        try:
            fld = model._meta.get_field(name)
        except Exception:
            continue
        if isinstance(fld, djm.DateField | djm.DateTimeField):
            return name
    return None


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


def _model_has_any_datefield(model):
    for f in model._meta.get_fields():
        if isinstance(f, djm.DateField) and not f.auto_now and not f.auto_now_add:
            return True
    return False


def attach_conservative_date_inline():
    CANDIDATE_NAMES = ("play_date", "date", "date_start", "monday_date", "start_date")
    for _model, adm in list(admin.site._registry.items()):
        parent = _model
        if _model_has_any_datefield(parent):
            continue
        rels = []
        for f in parent._meta.get_fields():
            if not getattr(f, "auto_created", False):
                continue
            rel_model = getattr(f, "related_model", None)
            if not rel_model:
                continue
            for cand in CANDIDATE_NAMES:
                try:
                    fld = rel_model._meta.get_field(cand)
                    if isinstance(fld, djm.DateField):
                        rels.append((rel_model, cand))
                        break
                except Exception:
                    continue
        if len(rels) != 1:
            continue
        rel_model, date_name = rels[0]
        if any(getattr(ic, "model", None) is rel_model for ic in getattr(adm, "inlines", []) or []):
            continue
        Inline = type(
            f"{rel_model.__name__}AutoDateInline",
            (admin.TabularInline,),
            {"model": rel_model, "extra": 0, "fields": (date_name,)},
        )
        _patch_formfield_for_dbfield(Inline)
        inls = list(getattr(adm, "inlines", []) or [])
        inls.append(Inline)
        adm.inlines = inls


def _patch_formfield_for_dbfield(obj):
    """Wrap formfield_for_dbfield so DateField uses custom formats and widget (Django-version safe)."""
    if getattr(obj, "_fax_date_patched", False):
        return
    orig = getattr(obj, "formfield_for_dbfield", None)
    if orig is None:
        return

    # Detekuj signaturu (některé verze Django nemají 'request' v signatuře)
    try:
        import inspect

        sig = inspect.signature(orig)
        expects_request = "request" in sig.parameters
    except Exception:
        expects_request = True  # bezpečný default pro novější Django

    def _wrapped(self, db_field, *args, **kwargs):
        """
        Zavolej původní formfield_for_dbfield s deduplikovaným 'request':
        - pokud signatura očekává 'request', předáme ho jednou (pozičně),
        - pokud ne, nepředáváme ho vůbec (odstraníme ze vstupů).
        """
        # --- 1) Detekce, zda orig očekává 'request' (už existuje proměnná expects_request nad námi) ---
        # Pozn.: proměnná expects_request je definovaná výše v _patch_formfield_for_dbfield pomocí inspect.signature(orig)

        # --- 2) Normalizace requestu z args/kwargs, aby nebyl předán dvakrát ---
        req = None
        rest_args = list(args)

        # Pokud někdo poslal request pozičně, vytáhni ho z prvního místa (typicky tak Django volá admin metody)
        if rest_args:
            req = rest_args.pop(0)

        # Pokud je request i v kwargs, vezmeme hodnotu z kwargs a poziční případně zahodíme,
        # abychom předešli "multiple values for argument 'request'"
        if "request" in kwargs:
            req = kwargs.pop("request")

        # --- 3) Zavolej původní metodu správným stylem ---
        caller = getattr(orig, "__func__", orig)
        try:
            if expects_request:
                # Předáme request jednou pozičně; pokud chybí, posíláme None (bezpečný default v adminu)
                ff = caller(self, db_field, req, **kwargs)
            else:
                # Původní signatura 'request' nezná – voláme bez něj
                ff = caller(self, db_field, **kwargs)
        except TypeError:
            # Poslední záchrana pro atypické kombinace – zkus bez requestu
            ff = caller(self, db_field, **kwargs)

        from fax_calendar.forms import WoorldDateFormField

        if (
            ff
            and getattr(settings, "FAX_WOORLD_ADMIN_SWAP", True)
            and is_woorld_dbfield(db_field)
            and is_woorld_widget(ff.widget)
        ):
            orig_widget = ff.widget
            required = ff.required
            initial = ff.initial
            help_text = getattr(ff, "help_text", "") or ""

            new_ff = WoorldDateFormField(required=required)
            new_ff.widget = orig_widget
            new_ff.initial = initial if isinstance(initial, str) else (initial or "")
            if not help_text:
                new_ff.help_text = "Woorld datum (15 měsíců). Formát: DD-MM-YYYY nebo YYYY-MM-DD."
            else:
                new_ff.help_text = help_text
            return new_ff

        # --- 4) Aplikuj naše úpravy pro DateField a DateTimeField (BEZ změny původní logiky) ---
        if isinstance(db_field, djm.DateTimeField) and ff:
            if isinstance(ff.initial, str):
                ff.initial = None
            w = ff.widget
            if isinstance(w, djf.MultiWidget) and hasattr(w, "decompress"):
                if not getattr(w, "_fax_dt_safe", False):
                    orig_decompress = w.decompress
                    num_widgets = len(getattr(w, "widgets", []) or [None, None])

                    def _safe_decompress(value):
                        if value in (None, "", []):
                            return [None] * num_widgets
                        if isinstance(value, str):
                            from django.utils.dateparse import parse_datetime

                            dt = parse_datetime(value)
                            if dt is None:
                                return [None] * num_widgets
                            value = dt
                        return orig_decompress(value)

                    w.decompress = _safe_decompress
                    w._fax_dt_safe = True
        elif isinstance(db_field, djm.DateField) and ff:
            ff.input_formats = FAX_INPUT_FORMATS
            w = ff.widget
            if not isinstance(w, djf.DateInput) or getattr(w, "format", None) != FAX_DATE_FORMAT:
                ff.widget = _resolve_date_widget()
                w = ff.widget
            if hasattr(w, "format"):
                try:
                    w.format = FAX_DATE_FORMAT
                except Exception:
                    pass
            w.attrs.setdefault("placeholder", "DD-MM-YYYY")
            for k in ("min", "max"):
                w.attrs.pop(k, None)
        return ff

    if isinstance(obj, type):
        # patchujeme třídu (Inline); metoda se správně naváže až při instanciaci
        obj.formfield_for_dbfield = _wrapped
    else:
        # patchujeme instanci (registrovaný ModelAdmin)
        import types as _types

        obj.formfield_for_dbfield = _types.MethodType(_wrapped, obj)
    obj._fax_date_patched = True


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
        _patch_formfield_for_dbfield(adm)


def apply_date_widget_to_inlines():
    """
    U všech již zaregistrovaných ModelAdminů projde jejich inlines (třídy)
    a merge-ne formfield_overrides tak, aby DateField používal náš sjednocený widget.
    Idempotentní – bezpečné volat opakovaně.
    """
    from django.db import models as djm

    for _model, adm in list(admin.site._registry.items()):
        inline_classes = getattr(adm, "inlines", None) or []
        for inline_cls in inline_classes:
            # Zajisti dict a merge – nenič existující overrides
            ffo = getattr(inline_cls, "formfield_overrides", {}) or {}
            widget = WorldDateAdminMixin.formfield_overrides[djm.DateField]["widget"]
            ffo[djm.DateField] = {"widget": widget}
            inline_cls.formfield_overrides = ffo
            _patch_formfield_for_dbfield(inline_cls)


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
    # 3) Patch i všech Inline adminů
    apply_date_widget_to_inlines()
    attach_conservative_date_inline()
