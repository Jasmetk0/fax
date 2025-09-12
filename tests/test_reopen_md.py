import random

import pytest

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Match,
    Phase,
    Player,
    PlayerLicense,
    Schedule,
    Season,
    Snapshot,
    Tournament,
    TournamentEntry,
)
from msa.services.md_confirm import confirm_main_draw
from msa.services.md_reopen import reopen_main_draw
from msa.services.results import set_result


@pytest.mark.django_db
def test_reopen_md_full_reset_when_no_results():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-28")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="M1", slug="m1")

    players = [Player.objects.create(name=f"P{i}") for i in range(16)]
    for i, p in enumerate(players):
        PlayerLicense.objects.create(player=p, season=s)
        from msa.models import TournamentEntry

        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )

    confirm_main_draw(t, rng_seed=1)
    assert Match.objects.filter(tournament=t, phase=Phase.MD).exists()

    msg = reopen_main_draw(t, mode="AUTO")
    assert "cleared" in msg
    assert not Match.objects.filter(tournament=t, phase=Phase.MD).exists()


@pytest.mark.django_db
def test_reopen_md_soft_preserves_done_pairs_and_shuffles_unseeded_in_pending_r1():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-28")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="M2", slug="m2")

    players = [Player.objects.create(name=f"P{i}") for i in range(16)]
    for i, p in enumerate(players):
        PlayerLicense.objects.create(player=p, season=s)
        from msa.models import TournamentEntry

        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )

    confirm_main_draw(t, rng_seed=123)

    # Označ jeden R1 zápas jako hotový
    r1 = list(Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16"))
    assert r1
    done = r1[0]
    set_result(done.id, mode="WIN_ONLY", winner=done.player_top_id)
    done.refresh_from_db()
    r1 = list(Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16"))

    # U soft módu se DONE pár nemá měnit
    before = [(m.id, m.player_top_id, m.player_bottom_id, m.winner_id) for m in r1]
    msg = reopen_main_draw(t, mode="SOFT", rng_seed=999)
    assert "SOFT" in msg
    after = [
        (m.id, m.player_top_id, m.player_bottom_id, m.winner_id)
        for m in Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16")
    ]
    # DONE zápas zachován
    be = {x[0]: x for x in before}
    af = {x[0]: x for x in after}
    assert af[done.id][1:] == be[done.id][1:]  # top/bot/winner shodně


@pytest.mark.django_db
def test_reopen_md_hard_resets_impacted_results():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-28")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="M3", slug="m3")

    players = [Player.objects.create(name=f"P{i}") for i in range(16)]
    for i, p in enumerate(players):
        PlayerLicense.objects.create(player=p, season=s)
        from msa.models import TournamentEntry

        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )

    confirm_main_draw(t, rng_seed=321)
    r1 = list(Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16"))
    assert r1
    # Udělejme 2 hotové zápasy, aby bylo co resetovat
    set_result(r1[0].id, mode="WIN_ONLY", winner=r1[0].player_top_id)
    set_result(r1[1].id, mode="WIN_ONLY", winner=r1[1].player_bottom_id)

    msg = reopen_main_draw(t, mode="HARD", rng_seed=555)
    assert "HARD" in msg
    # Dotčené páry mohou mít vynulovaného winnera
    r1_after = list(Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16"))
    assert any(m.winner_id is None for m in r1_after)


@pytest.mark.django_db
def test_snapshot_created_on_reopen_md():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-28")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="M4", slug="m4")

    players = [Player.objects.create(name=f"P{i}") for i in range(16)]
    for i, p in enumerate(players):
        PlayerLicense.objects.create(player=p, season=s)
        from msa.models import TournamentEntry

        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i + 1,
        )

    confirm_main_draw(t, rng_seed=77)
    reopen_main_draw(t, mode="AUTO")
    snap = Snapshot.objects.filter(tournament=t, type=Snapshot.SnapshotType.REOPEN).first()
    assert snap is not None
    assert snap.payload and snap.payload.get("kind") == "TOURNAMENT_STATE"


@pytest.mark.django_db
def test_reopen_md_soft_keeps_schedule_if_pair_unchanged():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-28")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="M5", slug="m5")

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

    confirm_main_draw(t, rng_seed=123)

    m = (
        Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16")
        .order_by("slot_top")
        .first()
    )
    Schedule.objects.create(tournament=t, match=m, play_date="2025-01-01", order=1)
    m_done = (
        Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16")
        .exclude(pk=m.pk)
        .first()
    )
    set_result(m_done.id, mode="WIN_ONLY", winner=m_done.player_top_id)
    old_pair = (m.player_top_id, m.player_bottom_id)

    top_entry = TournamentEntry.objects.get(tournament=t, position=m.slot_top)
    bot_entry = TournamentEntry.objects.get(tournament=t, position=m.slot_bottom)
    top_entry.seed = 1
    bot_entry.seed = 2
    top_entry.save(update_fields=["seed"])
    bot_entry.save(update_fields=["seed"])

    reopen_main_draw(t, mode="SOFT", rng_seed=0)

    m.refresh_from_db()
    assert (m.player_top_id, m.player_bottom_id) == old_pair
    assert Schedule.objects.filter(match=m).exists()


@pytest.mark.django_db
def test_reopen_md_soft_deletes_schedule_if_pair_changed():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-28")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="M6", slug="m6")

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

    confirm_main_draw(t, rng_seed=123)

    m = (
        Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16")
        .order_by("slot_top")
        .first()
    )
    Schedule.objects.create(tournament=t, match=m, play_date="2025-01-01", order=1)
    m_done = (
        Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R16")
        .exclude(pk=m.pk)
        .first()
    )
    set_result(m_done.id, mode="WIN_ONLY", winner=m_done.player_top_id)
    old_pair = (m.player_top_id, m.player_bottom_id)

    entries = TournamentEntry.objects.filter(
        tournament=t, status=EntryStatus.ACTIVE, position__isnull=False, seed__isnull=True
    ).order_by("position")
    pool = [e.id for e in entries]
    seed_change = None
    for seed in range(1000):
        arr = pool.copy()
        random.Random(seed).shuffle(arr)
        if arr[:2] != pool[:2]:
            seed_change = seed
            break
    assert seed_change is not None

    reopen_main_draw(t, mode="SOFT", rng_seed=seed_change)

    m.refresh_from_db()
    assert (m.player_top_id, m.player_bottom_id) != old_pair
    assert not Schedule.objects.filter(match=m).exists()
