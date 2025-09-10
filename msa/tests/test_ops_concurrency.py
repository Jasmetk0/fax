import threading

import pytest
from django.db import close_old_connections

from msa.models import Player, Tournament, TournamentEntry
from msa.services.ops import replace_slot


@pytest.mark.django_db
def test_replace_slot_concurrent():
    t = Tournament.objects.create(name="T", slug="t", draw_size=16)
    players = [Player.objects.create(name=f"P{i}", country="XX") for i in range(20)]

    md_entries = []
    for i in range(16):
        md_entries.append(
            TournamentEntry.objects.create(
                tournament=t,
                player=players[i],
                status="ACTIVE",
                entry_type="DA",
                position=i,
            )
        )
    prev = md_entries[5]

    alt = TournamentEntry.objects.create(
        tournament=t,
        player=players[16],
        status="ACTIVE",
        entry_type="ALT",
        position=None,
    )

    SLOT = 5

    def run():
        close_old_connections()
        try:
            replace_slot(t, SLOT, alt.pk)
        except Exception:  # pragma: no cover - concurrency errors tolerated
            pass

    th1 = threading.Thread(target=run)
    th2 = threading.Thread(target=run)
    th1.start()
    th2.start()
    th1.join()
    th2.join()

    alt.refresh_from_db()
    assert alt.position == SLOT

    active_on_slot = TournamentEntry.objects.filter(tournament=t, position=SLOT, status="ACTIVE")
    assert active_on_slot.count() == 1
    assert active_on_slot.first().pk == alt.pk

    total_on_slot = TournamentEntry.objects.filter(tournament=t, position=SLOT)
    assert total_on_slot.count() == 1

    prev.refresh_from_db()
    assert not (prev.status == "ACTIVE" and prev.position == SLOT)


@pytest.mark.django_db
def test_replace_slot_idempotent_when_alt_already_on_slot():
    t = Tournament.objects.create(name="T2", slug="t2", draw_size=16)
    p1 = Player.objects.create(name="A")
    p2 = Player.objects.create(name="B")
    incumbent = TournamentEntry.objects.create(
        tournament=t,
        player=p1,
        status="ACTIVE",
        entry_type="DA",
        position=3,
    )
    alt = TournamentEntry.objects.create(
        tournament=t,
        player=p2,
        status="ACTIVE",
        entry_type="ALT",
        position=None,
    )
    replace_slot(t, 3, alt.pk)
    replace_slot(t, 3, alt.pk)
    alt.refresh_from_db()
    incumbent.refresh_from_db()
    assert alt.position == 3
    assert incumbent.position is None
    assert TournamentEntry.objects.filter(tournament=t, position=3).count() == 1
