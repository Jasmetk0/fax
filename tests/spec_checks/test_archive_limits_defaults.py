from importlib import reload

import pytest
from django.test import override_settings

import fax_portal.settings as project_settings
from msa.models import Snapshot
from msa.services.archiver import enforce_archive_limits
from tests.factories import make_category_season, make_tournament


def test_defaults():
    reload(project_settings)
    from django.conf import settings

    assert settings.MSA_ARCHIVE_LIMIT_COUNT == 50
    assert settings.MSA_ARCHIVE_LIMIT_MB == 50


@pytest.mark.django_db
@override_settings(MSA_ARCHIVE_LIMIT_COUNT=10, MSA_ARCHIVE_LIMIT_MB=5)
def test_override_limits(settings):
    cs, _, _ = make_category_season()
    t = make_tournament(cs=cs)
    for _ in range(12):
        Snapshot.objects.create(tournament=t, type="TEST", payload={})
    enforce_archive_limits(t)
    assert Snapshot.objects.filter(tournament=t).count() == 10
    assert settings.MSA_ARCHIVE_LIMIT_COUNT == 10
    assert settings.MSA_ARCHIVE_LIMIT_MB == 5
