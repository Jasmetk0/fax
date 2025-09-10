# tests/test_wc_qwc.py
import pytest

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Player,
    Season,
    Tournament,
    TournamentEntry,
    TournamentState,
)
from msa.services.wc import apply_qwc, apply_wc, remove_qwc, remove_wc, set_q_wc_slots, set_wc_slots


@pytest.mark.django_db
def test_wc_above_cutline_is_label_only_does_not_consume():
    # MD32, qualifiers=4 → D = 28
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=32, wc_slots_default=2)
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T",
        slug="t",
        state=TournamentState.REG,
        qualifiers_count=4,
    )

    # 40 registrací: 1..40 (1 nejlepší). DA/Q/ALT neřešíme, rozhoduje WR.
    players = [Player.objects.create(name=f"P{i}") for i in range(1, 41)]
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.ALT,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )

    # hráč s WR=10 je nad čarou D=28 → jen label, bez čerpání
    eid = TournamentEntry.objects.get(tournament=t, player=players[9]).id
    apply_wc(t, eid)
    te = TournamentEntry.objects.get(pk=eid)
    assert te.is_wc is True and te.promoted_by_wc is False and te.entry_type == EntryType.DA

    # snížení wc_slots pod využití jde (0), protože nikdo nebyl povýšen
    set_wc_slots(t, 0)


@pytest.mark.django_db
def test_wc_below_cutline_promotes_and_demotes_last_DA_and_respects_limit():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=32, wc_slots_default=1)
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T",
        slug="t",
        state=TournamentState.REG,
        qualifiers_count=4,
    )

    players = [Player.objects.create(name=f"P{i}") for i in range(1, 41)]
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.ALT,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )

    # WR=30 je POD čarou (D=28) → povýší do DA, spotřebuje 1 slot
    below = TournamentEntry.objects.get(tournament=t, player=players[29])
    apply_wc(t, below.id)
    below.refresh_from_db()
    assert below.entry_type == EntryType.DA and below.promoted_by_wc is True and below.is_wc is True

    # druhý pokus POD čarou musí selhat (slots=1 využit)
    below2 = TournamentEntry.objects.get(tournament=t, player=players[30])
    with pytest.raises(Exception):
        apply_wc(t, below2.id)

    # odeber WC z prvního → vrátí ho do Q a do DA povýší nejlepšího mimo čáru
    remove_wc(t, below.id)
    below.refresh_from_db()
    assert (
        below.entry_type == EntryType.Q and below.is_wc is False and below.promoted_by_wc is False
    )


@pytest.mark.django_db
def test_qwc_promotes_alt_to_q_and_respects_limit_label_only_in_q():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=32, q_wc_slots_default=1)
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T",
        slug="t",
        state=TournamentState.REG,
        qualifiers_count=4,
    )

    P = [Player.objects.create(name=f"P{i}") for i in range(1, 10)]
    # 6 hráčů ALT, 2 hráči už Q
    for i, p in enumerate(P[:6], start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.ALT,
            status=EntryStatus.ACTIVE,
            wr_snapshot=50 + i,
        )
    q1 = TournamentEntry.objects.create(
        tournament=t, player=P[6], entry_type=EntryType.Q, status=EntryStatus.ACTIVE, wr_snapshot=10
    )
    q2 = TournamentEntry.objects.create(
        tournament=t, player=P[7], entry_type=EntryType.Q, status=EntryStatus.ACTIVE, wr_snapshot=12
    )

    # ALT → Q pomocí QWC (spotřebuje slot)
    alt = TournamentEntry.objects.filter(tournament=t, entry_type=EntryType.ALT).first()
    apply_qwc(t, alt.id)
    alt.refresh_from_db()
    assert alt.entry_type == EntryType.Q and alt.is_qwc is True and alt.promoted_by_qwc is True

    # Q → jen label, bez čerpání
    apply_qwc(t, q1.id)
    q1.refresh_from_db()
    assert q1.entry_type == EntryType.Q and q1.is_qwc is True and q1.promoted_by_qwc is False

    # druhý ALT → QWC by měl selhat (limit 1)
    alt2 = TournamentEntry.objects.filter(tournament=t, entry_type=EntryType.ALT).first()
    with pytest.raises(Exception):
        apply_qwc(t, alt2.id)

    # snížení limitu pod využití failne
    with pytest.raises(Exception):
        set_q_wc_slots(t, 0)

    # odeber QWC z povýšeného → vrátí do ALT; pak lze slot znovu použít
    remove_qwc(t, alt.id)
    alt.refresh_from_db()
    assert alt.entry_type == EntryType.ALT and alt.is_qwc is False and alt.promoted_by_qwc is False
    # teď lze aplikovat na jiného
    apply_qwc(t, alt2.id)
    alt2.refresh_from_db()
    assert alt2.entry_type == EntryType.Q and alt2.promoted_by_qwc is True
