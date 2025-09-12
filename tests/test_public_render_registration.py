import pytest

from msa.models import EntryType, TournamentEntry
from tests.factories import make_category_season, make_player, make_tournament

pytestmark = pytest.mark.legacy_msa_public


@pytest.mark.django_db
def test_registration_separators_render(client):
    cs, _, _ = make_category_season(draw_size=4)
    t = make_tournament(cs=cs)
    players = [make_player(str(i)) for i in range(4)]
    TournamentEntry.objects.create(
        tournament=t, player=players[0], entry_type=EntryType.DA, seed=1, wr_snapshot=1
    )
    TournamentEntry.objects.create(
        tournament=t, player=players[1], entry_type=EntryType.DA, seed=2, wr_snapshot=2
    )
    TournamentEntry.objects.create(
        tournament=t, player=players[2], entry_type=EntryType.DA, wr_snapshot=3
    )
    TournamentEntry.objects.create(
        tournament=t, player=players[3], entry_type=EntryType.DA, wr_snapshot=4
    )
    resp = client.get(f"/msa/t/{t.slug}/registration/")
    assert resp.status_code == 200
    assert resp.text.count("<hr") >= 1
