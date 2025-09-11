from django import forms
from django.db import models as djm
from django.forms.widgets import SplitDateTimeWidget

from admin_extras.autoregister import _patch_formfield_for_dbfield


def _simulate_hidden(ff, value):
    form = forms.Form()
    form.fields["x"] = ff
    bf = forms.BoundField(form, ff, "x")
    form.initial = {"x": value}
    bf.as_hidden()


def _make_ff_from_admin():
    class Adm:
        def formfield_for_dbfield(self, db_field, request=None, **kwargs):
            return forms.DateTimeField(widget=SplitDateTimeWidget(), initial="")

    adm = Adm()
    _patch_formfield_for_dbfield(adm)
    db_field = djm.DateTimeField()
    ff = adm.formfield_for_dbfield(db_field, request=None)
    return ff


def test_hidden_initial_empty_string():
    ff = _make_ff_from_admin()
    assert ff.initial is None
    _simulate_hidden(ff, "")


def test_hidden_initial_string_parseable():
    ff = _make_ff_from_admin()
    _simulate_hidden(ff, "2025-01-01 00:00:00")


def test_hidden_initial_none():
    ff = _make_ff_from_admin()
    _simulate_hidden(ff, None)


def test_hidden_initial_inline_class():
    class Adm:
        def formfield_for_dbfield(self, db_field, **kwargs):
            return forms.DateTimeField(widget=SplitDateTimeWidget(), initial="")

    _patch_formfield_for_dbfield(Adm)
    inst = Adm()
    db_field = djm.DateTimeField()
    ff = inst.formfield_for_dbfield(db_field)
    assert ff.initial is None
    _simulate_hidden(ff, "")
