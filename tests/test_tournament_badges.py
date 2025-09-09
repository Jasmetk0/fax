import pytest

from msa.models import Tournament
from msa.services.audit_badges import audit_badges_for_tournament


@pytest.mark.django_db
def test_audit_badges_returns_values_and_statuses():
    t = Tournament.objects.create(
        name="T",
        slug="t",
        seeding_source="seed_anchors",
        snapshot_label="MD-R32-2025-09-09",
    )
    badges = audit_badges_for_tournament(t)
    assert badges == {
        "seeding": {
            "value": "seed_anchors",
            "label": "Seeding: seed_anchors",
            "status": "ok",
        },
        "snapshot": {
            "value": "MD-R32-2025-09-09",
            "label": "Snapshot: MD-R32-2025-09-09",
            "status": "ok",
        },
    }


@pytest.mark.django_db
def test_audit_badges_warn_on_missing_values():
    t = Tournament.objects.create(name="T2", slug="t2", seeding_source="", snapshot_label="")
    badges = audit_badges_for_tournament(t)
    assert badges["seeding"] == {
        "value": "",
        "label": "Seeding: —",
        "status": "warn",
    }
    assert badges["snapshot"] == {
        "value": "",
        "label": "Snapshot: —",
        "status": "warn",
    }
