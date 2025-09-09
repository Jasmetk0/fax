import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import override_settings

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Match,
    Phase,
    Player,
    PlayerLicense,
    Season,
    Tournament,
    TournamentEntry,
    TournamentState,
)
from msa.services.licenses import grant_license_for_tournament_season
from msa.services.md_confirm import confirm_main_draw
from msa.services.planning import insert_match, list_day_order
from msa.services.results import set_result
from msa.services.wc import apply_qwc


def expect_admin_block(callable, *args, **kwargs):
    with pytest.raises(Exception) as e:
        callable(*args, **kwargs)
    msg = str(e.value).lower()
    assert isinstance(e.value, (ValidationError, PermissionDenied, Exception))
    assert ("admin" in msg) or ("mode" in msg) or ("not allowed" in msg)


@pytest.mark.django_db
def test_admin_off_blocks_confirm_main_draw():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="T", slug="t")

    players = [Player.objects.create(name=f"P{i}") for i in range(16)]
    for i, p in enumerate(players, start=1):
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.DA,
            status=EntryStatus.ACTIVE,
            wr_snapshot=i,
        )
        PlayerLicense.objects.create(player=p, season=s)

    with override_settings(MSA_ADMIN_MODE=False):
        before = Match.objects.filter(tournament=t, phase=Phase.MD).count()
        expect_admin_block(confirm_main_draw, t, rng_seed=1)
        after = Match.objects.filter(tournament=t, phase=Phase.MD).count()
        assert after == before

    with override_settings(MSA_ADMIN_MODE=True):
        mapping = confirm_main_draw(t, rng_seed=1)
    assert Match.objects.filter(tournament=t, phase=Phase.MD).count() > 0
    assert len(mapping) == cs.draw_size


@pytest.mark.django_db
def test_admin_off_blocks_insert_match():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T2", slug="t2", state=TournamentState.MD
    )

    P = [Player.objects.create(name=f"P{i}") for i in range(1, 5)]
    m1 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=16,
        player_top=P[0],
        player_bottom=P[1],
    )
    m2 = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=2,
        slot_bottom=15,
        player_top=P[2],
        player_bottom=P[3],
    )

    with override_settings(MSA_ADMIN_MODE=True):
        insert_match(t, m1.id, "2025-08-01", 1)
    before_items = list_day_order(t, "2025-08-01")
    assert [x.match_id for x in before_items] == [m1.id]
    assert [x.order for x in before_items] == [1]

    with override_settings(MSA_ADMIN_MODE=False):
        expect_admin_block(insert_match, t, m2.id, "2025-08-01", 1)
    after_items = list_day_order(t, "2025-08-01")
    assert [x.match_id for x in after_items] == [m1.id]
    assert [x.order for x in after_items] == [1]

    with override_settings(MSA_ADMIN_MODE=True):
        insert_match(t, m2.id, "2025-08-01", 1)
    items = list_day_order(t, "2025-08-01")
    assert [x.match_id for x in items] == [m2.id, m1.id]
    assert [x.order for x in items] == [1, 2]


@pytest.mark.django_db
def test_admin_off_blocks_set_result():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T3", slug="t3", state=TournamentState.MD
    )

    p1 = Player.objects.create(name="A")
    p2 = Player.objects.create(name="B")
    m = Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=2,
        player_top=p1,
        player_bottom=p2,
    )

    with override_settings(MSA_ADMIN_MODE=False):
        expect_admin_block(set_result, m.id, mode="WIN_ONLY", winner="top")
    m.refresh_from_db()
    assert m.winner is None
    assert m.needs_review is False

    with override_settings(MSA_ADMIN_MODE=True):
        set_result(m.id, mode="WIN_ONLY", winner="top")
    m.refresh_from_db()
    assert m.winner == p1
    assert m.needs_review is False


@pytest.mark.django_db
def test_admin_off_blocks_grant_license():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    t = Tournament.objects.create(season=s, category=c, category_season=cs, name="T4", slug="t4")

    p = Player.objects.create(name="P")

    with override_settings(MSA_ADMIN_MODE=False):
        before = PlayerLicense.objects.count()
        expect_admin_block(grant_license_for_tournament_season, t, p.id)
        after = PlayerLicense.objects.count()
        assert after == before

    with override_settings(MSA_ADMIN_MODE=True):
        grant_license_for_tournament_season(t, p.id)
    assert PlayerLicense.objects.filter(player=p, season=s).count() == 1


@pytest.mark.django_db
def test_admin_off_blocks_apply_qwc():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(
        category=c, season=s, draw_size=16, qualifiers_count=4, q_wc_slots_default=1
    )
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T5", slug="t5", state=TournamentState.REG
    )

    p = Player.objects.create(name="ALT")
    te = TournamentEntry.objects.create(
        tournament=t,
        player=p,
        entry_type=EntryType.ALT,
        status=EntryStatus.ACTIVE,
        wr_snapshot=100,
    )

    with override_settings(MSA_ADMIN_MODE=False):
        expect_admin_block(apply_qwc, t, te.id)
    te.refresh_from_db()
    assert te.entry_type == EntryType.ALT
    assert te.is_qwc is False
    assert te.promoted_by_qwc is False

    with override_settings(MSA_ADMIN_MODE=True):
        apply_qwc(t, te.id)
    te.refresh_from_db()
    assert te.entry_type == EntryType.Q
    assert te.is_qwc is True
    assert te.promoted_by_qwc is True
