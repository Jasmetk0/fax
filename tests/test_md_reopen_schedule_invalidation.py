import pytest
from django.conf import settings

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
from msa.services.md_reopen import reopen_main_draw
from msa.services.results import set_result


@pytest.mark.django_db
def test_reopen_soft_keeps_schedule_without_pair_change():
    settings.MSA_ADMIN_MODE = True

    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-28")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=4, md_seeds_count=1)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="TA", slug="ta")

    players = [Player.objects.create(name=f"P{i}") for i in range(4)]
    for i, p in enumerate(players, start=1):
        PlayerLicense.objects.create(player=p, season=s)
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            position=i,
            seed=1 if i == 1 else None,
        )

    m_keep = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R4",
        slot_top=1,
        slot_bottom=2,
        player_top=players[0],
        player_bottom=players[1],
        state=MatchState.PENDING,
    )
    m_done = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R4",
        slot_top=3,
        slot_bottom=4,
        player_top=players[2],
        player_bottom=players[3],
        state=MatchState.PENDING,
    )
    Schedule.objects.create(tournament=t, match=m_keep, play_date="2025-06-01", order=2)
    set_result(m_done.id, mode="WIN_ONLY", winner=m_done.player_top_id)
    old_pair = (m_keep.player_top_id, m_keep.player_bottom_id)

    reopen_main_draw(t, mode="SOFT", rng_seed=42)

    m_keep.refresh_from_db()
    assert (m_keep.player_top_id, m_keep.player_bottom_id) == old_pair
    assert Schedule.objects.filter(match=m_keep).exists()


@pytest.mark.django_db
def test_reopen_soft_deletes_schedule_when_pair_changed():
    settings.MSA_ADMIN_MODE = True

    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-28")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=4, md_seeds_count=1)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="TB", slug="tb")

    players = [Player.objects.create(name=f"Q{i}") for i in range(4)]
    for i, p in enumerate(players, start=1):
        PlayerLicense.objects.create(player=p, season=s)
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            position=i,
            seed=1 if i == 1 else None,
        )

    # mutable matches without results
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R4",
        slot_top=1,
        slot_bottom=2,
        player_top=players[0],
        player_bottom=players[1],
        state=MatchState.PENDING,
    )
    m_target = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R4",
        slot_top=3,
        slot_bottom=4,
        player_top=players[2],
        player_bottom=players[3],
        state=MatchState.PENDING,
    )
    Schedule.objects.create(tournament=t, match=m_target, play_date="2025-06-01", order=2)

    # add extra match with result to avoid full reset
    extra = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R4",
        slot_top=5,
        slot_bottom=6,
        player_top=players[0],
        player_bottom=players[0],
        state=MatchState.PENDING,
    )
    set_result(extra.id, mode="WIN_ONLY", winner=players[0].id)

    old_pair = (m_target.player_top_id, m_target.player_bottom_id)

    reopen_main_draw(t, mode="SOFT", rng_seed=42)

    m_target.refresh_from_db()
    assert (m_target.player_top_id, m_target.player_bottom_id) != old_pair
    assert not Schedule.objects.filter(match=m_target).exists()
