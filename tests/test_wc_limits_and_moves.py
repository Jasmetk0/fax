import pytest
from django.core.exceptions import ValidationError

from msa.models import EntryStatus, EntryType, TournamentEntry
from msa.services.wc import apply_qwc, apply_wc, remove_qwc, remove_wc
from tests.factories import make_category_season, make_player, make_tournament


@pytest.mark.django_db
def test_wc_limits_and_moves():
    cs, _season, _cat = make_category_season(draw_size=8, qualifiers_count=2, qual_rounds=0)
    cs.wc_slots_default = 1
    cs.q_wc_slots_default = 1
    cs.save(update_fields=["wc_slots_default", "q_wc_slots_default"])
    t = make_tournament(cs=cs, qualifiers_count=2)

    players = [make_player(f"P{i}") for i in range(1, 9)]
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.ALT,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )

    # WC above cutline → label only
    above = TournamentEntry.objects.get(tournament=t, player=players[5])  # WR=6
    apply_wc(t, above.id)
    above.refresh_from_db()
    assert above.is_wc is True
    assert above.promoted_by_wc is False
    assert above.entry_type == EntryType.DA
    assert TournamentEntry.objects.filter(tournament=t, promoted_by_wc=True).count() == 0

    # WC below cutline → promotion and last DA demoted
    target = TournamentEntry.objects.get(tournament=t, player=players[7])  # WR=8
    apply_wc(t, target.id)
    target.refresh_from_db()
    assert target.entry_type == EntryType.DA
    assert target.promoted_by_wc is True
    assert target.is_wc is True

    dropped = TournamentEntry.objects.get(tournament=t, player=players[5])  # WR=6
    dropped.refresh_from_db()
    assert dropped.entry_type == EntryType.Q
    assert dropped.is_wc is True  # label preserved if above cutline historically

    other = TournamentEntry.objects.get(tournament=t, player=players[6])  # WR=7
    with pytest.raises(ValidationError) as ex:
        apply_wc(t, other.id)
    assert ex.value.messages[0] == "Nedostatek WC slotů (použito 1/1)."

    # remove_wc: return target to Q and promote best outside (WR7)
    remove_wc(t, target.id)
    target.refresh_from_db()
    assert target.entry_type == EntryType.Q
    assert target.is_wc is False and target.promoted_by_wc is False

    other.refresh_from_db()
    assert other.entry_type == EntryType.DA
    assert other.is_wc is False and other.promoted_by_wc is False


@pytest.mark.django_db
def test_qwc_limits_and_moves():
    cs, _season, _cat = make_category_season(draw_size=8, qualifiers_count=2, qual_rounds=0)
    cs.wc_slots_default = 1
    cs.q_wc_slots_default = 1
    cs.save(update_fields=["wc_slots_default", "q_wc_slots_default"])
    t = make_tournament(cs=cs, qualifiers_count=2)

    p_q1, _p_q2, p_alt1, p_alt2 = [make_player() for _ in range(4)]
    q1 = TournamentEntry.objects.create(
        tournament=t,
        player=p_q1,
        entry_type=EntryType.Q,
        status=EntryStatus.ACTIVE,
        wr_snapshot=10,
    )
    TournamentEntry.objects.create(
        tournament=t,
        player=_p_q2,
        entry_type=EntryType.Q,
        status=EntryStatus.ACTIVE,
        wr_snapshot=20,
    )
    alt1 = TournamentEntry.objects.create(
        tournament=t,
        player=p_alt1,
        entry_type=EntryType.ALT,
        status=EntryStatus.ACTIVE,
        wr_snapshot=30,
    )
    alt2 = TournamentEntry.objects.create(
        tournament=t,
        player=p_alt2,
        entry_type=EntryType.ALT,
        status=EntryStatus.ACTIVE,
        wr_snapshot=40,
    )

    # ALT → QWC promotion
    apply_qwc(t, alt1.id)
    alt1.refresh_from_db()
    assert alt1.entry_type == EntryType.Q
    assert alt1.is_qwc is True and alt1.promoted_by_qwc is True

    # Q → label only
    apply_qwc(t, q1.id)
    q1.refresh_from_db()
    assert q1.entry_type == EntryType.Q
    assert q1.is_qwc is True and q1.promoted_by_qwc is False

    # limit reached
    with pytest.raises(ValidationError) as ex:
        apply_qwc(t, alt2.id)
    assert ex.value.messages[0] == "Nedostatek QWC slotů (použito 1/1)."

    # remove_qwc frees slot
    remove_qwc(t, alt1.id)
    alt1.refresh_from_db()
    assert alt1.entry_type == EntryType.ALT
    assert alt1.is_qwc is False and alt1.promoted_by_qwc is False

    apply_qwc(t, alt2.id)
    alt2.refresh_from_db()
    assert alt2.entry_type == EntryType.Q
    assert alt2.promoted_by_qwc is True and alt2.is_qwc is True
