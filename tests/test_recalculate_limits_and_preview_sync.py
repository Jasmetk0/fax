import pytest
from django.core.exceptions import ValidationError

from msa.models import EntryStatus, EntryType, TournamentEntry
from msa.services.recalculate import (
    confirm_recalculate_registration,
    preview_recalculate_registration,
)
from tests.factories import make_category_season, make_player, make_tournament


@pytest.mark.django_db
def test_confirm_blocks_with_combined_limit_messages():
    cs, _season, _cat = make_category_season(draw_size=16, qualifiers_count=2, qual_rounds=1)
    cs.wc_slots_default = 0
    cs.q_wc_slots_default = 0
    cs.save(update_fields=["wc_slots_default", "q_wc_slots_default"])
    t = make_tournament(cs=cs, qualifiers_count=2)

    players = [make_player(f"P{i}") for i in range(1, 21)]
    entries = []
    for i, p in enumerate(players, start=1):
        entries.append(
            TournamentEntry.objects.create(
                tournament=t,
                player=p,
                entry_type=EntryType.ALT,
                status=EntryStatus.ACTIVE,
                wr_snapshot=i,
            )
        )

    e_wc = entries[10]
    e_wc.entry_type = EntryType.DA
    e_wc.is_wc = True
    e_wc.promoted_by_wc = True
    e_wc.save(update_fields=["entry_type", "is_wc", "promoted_by_wc"])

    e_qwc = entries[15]
    e_qwc.entry_type = EntryType.Q
    e_qwc.is_qwc = True
    e_qwc.promoted_by_qwc = True
    e_qwc.save(update_fields=["entry_type", "is_qwc", "promoted_by_qwc"])

    prev = preview_recalculate_registration(t)
    assert prev.counters["WC_used"] == 1 and prev.counters["WC_limit"] == 0
    assert prev.counters["QWC_used"] == 1 and prev.counters["QWC_limit"] == 0

    with pytest.raises(ValidationError) as ex:
        confirm_recalculate_registration(t, prev)
    msg = ex.value.messages[0]
    assert "WC limit exceeded:" in msg and "QWC limit exceeded:" in msg


@pytest.mark.django_db
def test_confirm_warns_when_entries_changed():
    cs, _season, _cat = make_category_season(draw_size=8, qualifiers_count=0, qual_rounds=0)
    t = make_tournament(cs=cs)

    players = [make_player(f"P{i}") for i in range(3)]
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.ALT,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )

    prev = preview_recalculate_registration(t)

    extra = make_player("X")
    TournamentEntry.objects.create(
        tournament=t,
        player=extra,
        entry_type=EntryType.ALT,
        status=EntryStatus.ACTIVE,
        wr_snapshot=99,
    )

    with pytest.raises(ValidationError) as ex:
        confirm_recalculate_registration(t, prev)
    assert (
        ex.value.messages[0]
        == "Preview neodpovídá aktuálním registracím (změnily se položky). Vygeneruj znovu."
    )
