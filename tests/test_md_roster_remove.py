import pytest
from django.core.exceptions import ValidationError

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
    Schedule,
    Season,
    Tournament,
    TournamentEntry,
)
from msa.services.md_confirm import confirm_main_draw
from msa.services.md_embed import r1_name_for_md
from msa.services.md_roster import ensure_vacancies_filled, remove_player_from_md
from msa.services.results import set_result


@pytest.mark.django_db
def test_remove_blocks_when_r1_has_result():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="M1", slug="m1")

    players = [Player.objects.create(name=f"P{i}") for i in range(16)]
    for i, p in enumerate(players):
        PlayerLicense.objects.create(player=p, season=s)
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )

    confirm_main_draw(t, rng_seed=1)
    r1 = r1_name_for_md(t)
    m = Match.objects.filter(tournament=t, phase=Phase.MD, round_name=r1).first()
    assert m is not None
    slot = m.slot_top
    set_result(m.id, mode="WIN_ONLY", winner="top")

    with pytest.raises(ValidationError):
        remove_player_from_md(t, slot)


@pytest.mark.django_db
def test_remove_vacates_and_fills_with_ll_then_alt():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="M2", slug="m2")

    players = [Player.objects.create(name=f"P{i}") for i in range(16)]
    for i, p in enumerate(players):
        PlayerLicense.objects.create(player=p, season=s)
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )

    confirm_main_draw(t, rng_seed=2)
    r1 = r1_name_for_md(t)
    m = Match.objects.filter(tournament=t, phase=Phase.MD, round_name=r1).first()
    assert m is not None
    slot = m.slot_top

    ll_player = Player.objects.create(name="LL")
    PlayerLicense.objects.create(player=ll_player, season=s)
    ll_entry = TournamentEntry.objects.create(
        tournament=t,
        player=ll_player,
        entry_type=EntryType.LL,
        status=EntryStatus.ACTIVE,
        position=None,
    )

    alt_player = Player.objects.create(name="ALT")
    PlayerLicense.objects.create(player=alt_player, season=s)
    alt_entry = TournamentEntry.objects.create(
        tournament=t,
        player=alt_player,
        entry_type=EntryType.ALT,
        status=EntryStatus.ACTIVE,
        position=None,
    )

    Schedule.objects.create(tournament=t, match=m, play_date="2025-01-01", order=1)

    eid = remove_player_from_md(t, slot)
    assert eid == ll_entry.id
    ll_entry.refresh_from_db()
    assert ll_entry.position == slot
    m.refresh_from_db()
    assert m.player_top_id == ll_entry.player_id
    assert m.state == MatchState.PENDING
    assert m.winner_id is None
    assert m.score == {}
    assert not Schedule.objects.filter(match=m).exists()

    ll_entry.position = None
    ll_entry.status = EntryStatus.WITHDRAWN
    ll_entry.save(update_fields=["position", "status"])

    eid = remove_player_from_md(t, slot)
    assert eid == alt_entry.id
    alt_entry.refresh_from_db()
    assert alt_entry.position == slot
    m.refresh_from_db()
    assert m.player_top_id == alt_entry.player_id
    assert m.state == MatchState.PENDING
    assert m.winner_id is None
    assert m.score == {}
    assert not Schedule.objects.filter(match=m).exists()


@pytest.mark.django_db
def test_ensure_vacancies_filled_after_ll_promotion():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="M3", slug="m3")

    players = [Player.objects.create(name=f"P{i}") for i in range(16)]
    for i, p in enumerate(players):
        PlayerLicense.objects.create(player=p, season=s)
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )

    confirm_main_draw(t, rng_seed=3)
    r1 = r1_name_for_md(t)
    m = Match.objects.filter(tournament=t, phase=Phase.MD, round_name=r1).first()
    assert m is not None
    slot = m.slot_top

    res = remove_player_from_md(t, slot)
    assert res is None
    m.refresh_from_db()
    assert m.player_top_id is None

    new_ll_player = Player.objects.create(name="LL2")
    PlayerLicense.objects.create(player=new_ll_player, season=s)
    ll_entry = TournamentEntry.objects.create(
        tournament=t,
        player=new_ll_player,
        entry_type=EntryType.LL,
        status=EntryStatus.ACTIVE,
        position=None,
    )

    filled = ensure_vacancies_filled(t)
    assert filled == 1
    ll_entry.refresh_from_db()
    assert ll_entry.position == slot
    m.refresh_from_db()
    assert m.player_top_id == ll_entry.player_id
    assert m.state == MatchState.PENDING
    assert m.winner_id is None
    assert m.score == {}
