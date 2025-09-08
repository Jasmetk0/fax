import pytest
from django.core.exceptions import ValidationError
from django.db.models import Q

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Match,
    MatchState,
    Phase,
    Player,
    PlayerLicense,
    Season,
    Tournament,
    TournamentEntry,
    TournamentState,
)
from msa.services.qual_confirm import confirm_qualification
from msa.services.qual_replace import remove_and_replace_in_qualification


def _mk_base(K=1, R=2, pool=8):
    # size = 2^R na větev
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(
        category=c, season=s, draw_size=16, qualifiers_count=K, qual_rounds=R
    )
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.QUAL
    )
    # vytvoř hráče: dost pro Q + pár ALT
    players = [Player.objects.create(name=f"P{i}") for i in range(pool)]
    for p in players:
        PlayerLicense.objects.create(player=p, season=s)
    # první K*2^R hráčů jako Q (včetně seed tierů si vyřeší confirm)
    need_q = K * (2**R)
    for i in range(need_q):
        TournamentEntry.objects.create(
            tournament=t,
            player=players[i],
            entry_type=EntryType.Q,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )
    return t, players


@pytest.mark.django_db
def test_remove_and_replace_fills_same_slot_seed_anchor_preserved():
    t, _ = _mk_base(K=1, R=2, pool=8)  # size=4
    confirm_qualification(t, rng_seed=123)
    # globální slot 1 = base(0) + local 1 — seed kotva ve větvi (TOP)
    slot = 1
    # přidáme ALT kandidáta
    alt_player = Player.objects.create(name="ALT1")
    alt = TournamentEntry.objects.create(
        tournament=t,
        player=alt_player,
        entry_type=EntryType.ALT,
        status=EntryStatus.ACTIVE,
        wr_snapshot=50,
    )

    res = remove_and_replace_in_qualification(t, slot)
    assert res.slot == slot
    assert res.replacement_entry_id == alt.id

    m = Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name="Q4", slot_top=slot).first()
    assert m is not None
    assert m.player_top_id == alt_player.id
    assert m.state == MatchState.PENDING
    assert m.winner_id is None


@pytest.mark.django_db
def test_remove_and_replace_blocks_when_result_exists():
    t, _ = _mk_base(K=1, R=2, pool=8)
    confirm_qualification(t, rng_seed=1)
    slot = 1
    m = Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name="Q4", slot_top=slot).first()
    # uložíme výsledek, aby se blokovalo
    m.player_top_id = (
        Player.objects.create(name="A").id if m.player_top_id is None else m.player_top_id
    )
    m.player_bottom_id = (
        Player.objects.create(name="B").id if m.player_bottom_id is None else m.player_bottom_id
    )
    m.winner_id = m.player_top_id
    m.state = MatchState.DONE
    m.save()

    with pytest.raises(ValidationError):
        remove_and_replace_in_qualification(t, slot)


@pytest.mark.django_db
def test_remove_and_replace_uses_best_wr_alt():
    t, _ = _mk_base(K=1, R=2, pool=8)
    confirm_qualification(t, rng_seed=1)
    slot = 2  # jakýkoli R1 slot ve stejné větvi

    # dva ALT – vybere se lepší WR (menší číslo), NR až za něj
    a1 = Player.objects.create(name="ALT1")
    a2 = Player.objects.create(name="ALT2")
    te_good = TournamentEntry.objects.create(
        tournament=t, player=a1, entry_type=EntryType.ALT, status=EntryStatus.ACTIVE, wr_snapshot=10
    )
    TournamentEntry.objects.create(
        tournament=t,
        player=a2,
        entry_type=EntryType.ALT,
        status=EntryStatus.ACTIVE,
        wr_snapshot=None,
    )

    res = remove_and_replace_in_qualification(t, slot)
    assert res.replacement_entry_id == te_good.id

    m = (
        Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name="Q4")
        .filter(Q(slot_top=slot) | Q(slot_bottom=slot))
        .first()
    )
    assert m is not None
    assert res.replacement_player_id in (m.player_top_id, m.player_bottom_id)
