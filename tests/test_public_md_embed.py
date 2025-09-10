import pytest

from msa.models import EntryType, TournamentEntry
from tests.factories import make_category_season, make_player, make_tournament


@pytest.mark.django_db
def test_md_embed_no_bye_render(client):
    cs, _, _ = make_category_season(draw_size=24)
    t = make_tournament(cs=cs)
    players = [make_player(str(i)) for i in range(24)]
    for i, p in enumerate(players):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            seed=i + 1 if i < 8 else None,
            wr_snapshot=i + 1,
        )
    resp = client.get(f"/msa/t/{t.slug}/main-draw/")
    assert resp.status_code == 200
    assert "BYE" not in resp.text
    assert 'class="bye"' not in resp.text
