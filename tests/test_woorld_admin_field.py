from django import forms
from django.db import models as djm

from admin_extras.autoregister import _patch_formfield_for_dbfield
from fax_calendar.forms import WoorldDateFormField


class DummyWidget(forms.TextInput):
    pass


DummyWidget.__module__ = "fax_calendar.widgets"


class M(djm.Model):
    class Meta:
        app_label = "tests"


def _make_admin_for(db_field):
    class Adm:
        def formfield_for_dbfield(self, f, request=None, **kwargs):
            if isinstance(f, djm.CharField):
                ff = forms.CharField(widget=DummyWidget())
            else:
                ff = forms.DateField()
            return ff

    a = Adm()
    _patch_formfield_for_dbfield(a)
    return a


def test_woorld_accepts_month_14(monkeypatch):
    adm = _make_admin_for(djm.CharField())
    ff = adm.formfield_for_dbfield(djm.CharField(), request=None)
    assert isinstance(ff, WoorldDateFormField)
    val = ff.clean("08-14-2000")
    assert val == "2000-14-08"


def test_regular_datefield_untouched():
    adm = _make_admin_for(djm.DateField())
    ff = adm.formfield_for_dbfield(djm.DateField(), request=None)
    try:
        ff.clean("08-14-2000")
        ok = False
    except Exception:
        ok = True
    assert ok


def test_woorld_help_text_default_added_when_missing():
    class Adm:
        def formfield_for_dbfield(self, f, request=None, **kwargs):
            return forms.CharField(widget=DummyWidget(), help_text="")

    a = Adm()
    _patch_formfield_for_dbfield(a)
    ff = a.formfield_for_dbfield(djm.CharField(), request=None)
    assert isinstance(ff, WoorldDateFormField)
    assert "Woorld" in (ff.help_text or "")
    assert "15" in ff.help_text


def test_existing_help_text_preserved():
    class Adm:
        def formfield_for_dbfield(self, f, request=None, **kwargs):
            return forms.CharField(widget=DummyWidget(), help_text="Vlastní nápověda.")

    a = Adm()
    _patch_formfield_for_dbfield(a)
    ff = a.formfield_for_dbfield(djm.CharField(), request=None)
    assert ff.help_text == "Vlastní nápověda."
