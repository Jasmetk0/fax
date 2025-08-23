from django.conf import settings


def test_installed_apps_no_duplicates():
    apps = settings.INSTALLED_APPS
    assert len(apps) == len(set(apps)), f"Duplicate entries in INSTALLED_APPS: {apps}"
