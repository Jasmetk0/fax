import pytest

from msa.models import EntryStatus, EntryType, SeedingSource, TournamentEntry, TournamentState
from msa.services.recalculate import preview_recalculate_registration
from tests.factories import make_category_season, make_player, make_tournament


@pytest.mark.django_db
def test_preview_recalculate_preserves_order_when_seeding_source_none():
    cs, _season, _cat = make_category_season(draw_size=16, qualifiers_count=4, qual_rounds=1)
    t = make_tournament(cs=cs, qualifiers_count=4)
    t.seeding_source = SeedingSource.NONE
    t.state = TournamentState.REG
    t.save(update_fields=["seeding_source", "state"])

    players = [make_player(f"P{i}") for i in range(1, 25)]

    # Seeds 1-4
    for i in range(4):
        TournamentEntry.objects.create(
            tournament=t,
            player=players[i],
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            seed=i + 1,
            wr_snapshot=10 * (i + 1),
        )

    # Direct acceptances (unsorted WR)
    for i in range(4, 12):
        TournamentEntry.objects.create(
            tournament=t,
            player=players[i],
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=100 + i,
        )

    # Qualifiers with some NR
    for i in range(12, 20):
        wr = 200 + i if i % 2 == 0 else None
        TournamentEntry.objects.create(
            tournament=t,
            player=players[i],
            entry_type=EntryType.Q,
            status=EntryStatus.ACTIVE,
            wr_snapshot=wr,
        )

    # Reserves
    for i in range(20, 24):
        wr = 300 + i if i % 2 else None
        TournamentEntry.objects.create(
            tournament=t,
            player=players[i],
            entry_type=EntryType.ALT,
            status=EntryStatus.ACTIVE,
            wr_snapshot=wr,
        )

    prev = preview_recalculate_registration(t)
    current_ids = [r.entry_id for r in prev.current]
    proposed_ids = [r.entry_id for r in prev.proposed]
    assert proposed_ids == current_ids
