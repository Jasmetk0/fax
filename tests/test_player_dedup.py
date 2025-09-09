import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from msa.admin import PlayerAdmin
from msa.models import (
    Match,
    Player,
    PlayerLicense,
    RankingAdjustment,
    Season,
    Tournament,
    TournamentEntry,
)
from msa.services.player_dedup import find_duplicate_candidates, merge_players


@pytest.mark.django_db
def test_find_duplicate_candidates_suggests_similar_names():
    p1 = Player.objects.create(name="Tomas Novak")
    p2 = Player.objects.create(name="Tomáš Novák")
    Player.objects.create(name="John Doe")
    candidates = find_duplicate_candidates(threshold=0.88)
    pair = next(((a, b, s) for a, b, s in candidates if {a, b} == {p1.id, p2.id}), None)
    assert pair is not None and pair[2] >= 0.88


@pytest.mark.django_db
def test_merge_players_updates_all_references_and_deletes_dup(settings):
    settings.MSA_ADMIN_MODE = True
    master = Player.objects.create(name="Master")
    dup = Player.objects.create(name="Dup")
    other1 = Player.objects.create(name="Other1")
    other2 = Player.objects.create(name="Other2")
    season = Season.objects.create(name="2024")
    PlayerLicense.objects.create(player=master, season=season)
    PlayerLicense.objects.create(player=dup, season=season)
    Tournament.objects.create(id=1, name="T1")
    TournamentEntry.objects.create(tournament_id=1, player=dup)
    Match.objects.create(player_top=dup, player_bottom=other1)
    Match.objects.create(player_top=other2, player_bottom=dup)
    RankingAdjustment.objects.create(player=dup)

    merge_players(master.id, dup.id)

    assert not Player.objects.filter(id=dup.id).exists()
    assert TournamentEntry.objects.filter(player=master).count() == 1
    assert Match.objects.filter(player_top=master).count() == 1
    assert Match.objects.filter(player_bottom=master).count() == 1
    assert PlayerLicense.objects.filter(player=master, season=season).count() == 1
    assert RankingAdjustment.objects.filter(player=master).count() == 1


@pytest.mark.django_db
def test_merge_players_detects_conflict_same_match_side(settings):
    settings.MSA_ADMIN_MODE = True
    a = Player.objects.create(name="A")
    b = Player.objects.create(name="B")
    Match.objects.create(player_top=a, player_bottom=b)
    with pytest.raises(Exception) as exc:
        merge_players(a.id, b.id)
    assert "conflict" in str(exc.value)


@pytest.mark.django_db
def test_admin_action_merges_into_lowest_id(settings):
    settings.MSA_ADMIN_MODE = True
    a = Player.objects.create(id=10, name="A")
    b = Player.objects.create(id=12, name="B")
    c = Player.objects.create(id=15, name="C")
    queryset = Player.objects.filter(id__in=[a.id, b.id, c.id])
    site = AdminSite()
    admin_obj = PlayerAdmin(Player, site)
    request = RequestFactory().get("/")
    request.session = {}
    messages = FallbackStorage(request)
    request._messages = messages

    admin_obj.merge_selected_into_first(request, queryset)

    assert Player.objects.filter(id=a.id).exists()
    assert not Player.objects.filter(id=b.id).exists()
    assert not Player.objects.filter(id=c.id).exists()
