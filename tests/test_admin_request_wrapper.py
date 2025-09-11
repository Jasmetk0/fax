# tests/test_admin_request_wrapper.py
from types import SimpleNamespace

import pytest  # noqa: F401

from admin_extras.autoregister import _patch_formfield_for_dbfield


class DummyFF:
    """Minimální návratová hodnota formfield_for_dbfield s widgetem."""

    def __init__(self):
        self.widget = SimpleNamespace(attrs={})


def _make_fake_datefield(monkeypatch):
    # Přenastavíme typ DateField v modulu wrapperu na jednoduchou třídu,
    # aby isinstance(db_field, djm.DateField) vyšlo True bez DB/modelu.
    import admin_extras.autoregister as mod

    class FakeDF:  # jednoduchý typ reprezentující DateField
        pass

    monkeypatch.setattr(mod.djm, "DateField", FakeDF, raising=True)
    return mod.djm.DateField()


def test_wrapper_deduplicates_request_when_both_positional_and_kw(monkeypatch):
    db_field = _make_fake_datefield(monkeypatch)

    calls = {"count": 0, "last_req": None}

    class AdmReq:
        # Původní signatura s requestem
        def formfield_for_dbfield(self, db_field, request, **kwargs):
            calls["count"] += 1
            calls["last_req"] = request
            return DummyFF()

    adm = AdmReq()
    _patch_formfield_for_dbfield(adm)

    fake_request = object()

    # Simuluj volání, kde Django (nebo jiný kód) předá request dvakrát:
    # 1) pozičně i 2) v kwargs -- nesmí spadnout a musí zavolat orig jen 1×
    ff = adm.formfield_for_dbfield(db_field, fake_request, request=fake_request, some="x")
    assert calls["count"] == 1
    assert calls["last_req"] is fake_request
    assert hasattr(ff, "widget")


def test_wrapper_handles_admin_without_request_param(monkeypatch):
    db_field = _make_fake_datefield(monkeypatch)

    calls = {"count": 0}

    class AdmNoReq:
        # Původní signatura bez requestu
        def formfield_for_dbfield(self, db_field, **kwargs):
            calls["count"] += 1
            return DummyFF()

    # Patchujeme třídu (inline-like); wrapper naváže metodu při instanciaci
    _patch_formfield_for_dbfield(AdmNoReq)
    inst = AdmNoReq()

    # I když pošleme request v kwargs, wrapper ho nesmí předat orig (signatura ho nezná)
    ff = inst.formfield_for_dbfield(db_field, request=object(), other="y")
    assert calls["count"] == 1
    assert hasattr(ff, "widget")
