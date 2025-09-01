from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from msa.models import Tournament


def test_admin_tournament_change_empty_dates(db):
    User = get_user_model()
    user = User.objects.create_superuser("admin", "admin@example.com", "pass")
    client = Client()
    client.force_login(user)

    tournament = Tournament.objects.create(
        name="T",
        slug="t",
        start_date=None,
        end_date=None,
        seeding_rank_date=None,
        entry_deadline=None,
    )

    url = reverse("admin:msa_tournament_change", args=[tournament.pk])
    resp = client.get(url)
    assert resp.status_code == 200
