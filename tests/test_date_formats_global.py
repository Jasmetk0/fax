from datetime import date

import pytest
from django import forms
from django.conf import settings
from django.test import override_settings


class _F(forms.Form):
    d = forms.DateField()


@override_settings(LANGUAGE_CODE="cs")
def test_django_form_accepts_dd_mm_yyyy():
    f = _F(data={"d": "31-12-2026"})
    assert f.is_valid()
    assert f.cleaned_data["d"] == date(2026, 12, 31)


@override_settings(LANGUAGE_CODE="cs")
def test_django_form_accepts_iso():
    f = _F(data={"d": "2026-12-31"})
    assert f.is_valid()
    assert f.cleaned_data["d"] == date(2026, 12, 31)


@override_settings(LANGUAGE_CODE="cs")
@pytest.mark.skipif(
    "rest_framework" not in [a.split(".")[-1] for a in settings.INSTALLED_APPS],
    reason="DRF not installed",
)
def test_drf_serializer_accepts_dd_mm_yyyy():
    from rest_framework import serializers

    class S(serializers.Serializer):
        d = serializers.DateField()

    s = S(data={"d": "31-12-2026"})
    assert s.is_valid(), s.errors
    assert s.validated_data["d"] == date(2026, 12, 31)
