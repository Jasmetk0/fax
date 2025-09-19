import pytest
from django.urls import reverse

from msa.models import (
    Category,
    CategorySeason,
    Country,
    EntryType,
    Match,
    Phase,
    Player,
    PlayerLicense,
    Season,
    SeedingSource,
    Snapshot,
    Tour,
    Tournament,
    TournamentEntry,
    TournamentState,
)
from tests.woorld_helpers import woorld_date


@pytest.fixture
@pytest.mark.django_db
def sample_tournament():
    season = Season.objects.create(
        name="2025/01",
        start_date=woorld_date(2025, 1, 1),
        end_date=woorld_date(2025, 12, 1),
        best_n=16,
    )
    tour = Tour.objects.create(name="World Tour", rank=1, code="WT")
    category = Category.objects.create(name="Diamond 1000", tour=tour, rank=1)
    cs = CategorySeason.objects.create(
        category=category,
        season=season,
        draw_size=16,
        qual_rounds=2,
        wc_slots_default=2,
        q_wc_slots_default=1,
    )
    tournament = Tournament.objects.create(
        season=season,
        category=category,
        category_season=cs,
        name="Test Open",
        slug="test-open",
        start_date=woorld_date(2025, 2, 1),
        end_date=woorld_date(2025, 2, 7),
        draw_size=16,
        qualifiers_count=4,
        q_best_of=3,
        md_best_of=5,
        wc_slots=2,
        q_wc_slots=1,
        third_place_enabled=True,
        calendar_sync_enabled=True,
        scoring_md={"R16": 120, "Winner": 1000},
        scoring_qual_win={"Q2": 50, "Q1": 25},
        seeding_source=SeedingSource.SNAPSHOT,
        snapshot_label="Initial snapshot",
        seeding_monday=woorld_date(2025, 1, 1),
        rng_seed_active=42,
        state=TournamentState.MD,
    )

    country = Country.objects.create(iso3="CZE", name="Czechia")
    players = [
        Player.objects.create(name=f"Player {idx:02d}", country=country) for idx in range(1, 21)
    ]
    placeholder_player = Player.objects.create(name="Winner K1", country=country)

    for idx, player in enumerate(players):
        if idx == 11:  # one DA without license
            continue
        PlayerLicense.objects.create(player=player, season=season)

    # Seeds
    seed_positions = [1, 16, 8, 9]
    for idx, pos in enumerate(seed_positions):
        TournamentEntry.objects.create(
            tournament=tournament,
            player=players[idx],
            entry_type=EntryType.DA,
            seed=idx + 1,
            wr_snapshot=idx + 5,
            position=pos,
        )

    # Direct acceptances (including a WC and cutline)
    da_positions = [2, 15, 7, 10, 3, 14, 6, 11]
    for offset, pos in enumerate(da_positions):
        player = players[4 + offset]
        entry_kwargs = {
            "tournament": tournament,
            "player": player,
            "position": pos,
            "wr_snapshot": 30 + offset,
        }
        if offset == 0:
            entry_kwargs.update({"entry_type": EntryType.WC, "is_wc": True})
        else:
            entry_kwargs["entry_type"] = EntryType.DA
        TournamentEntry.objects.create(**entry_kwargs)

    # Qualification entries
    for offset, player in enumerate(players[12:16]):
        entry_type = EntryType.Q if offset else EntryType.QWC
        TournamentEntry.objects.create(
            tournament=tournament,
            player=player,
            entry_type=entry_type,
            wr_snapshot=100 + offset,
            is_qwc=entry_type == EntryType.QWC,
        )

    TournamentEntry.objects.create(
        tournament=tournament,
        player=placeholder_player,
        entry_type=EntryType.Q,
        position=13,
    )

    # Reserve entries
    TournamentEntry.objects.create(
        tournament=tournament,
        player=players[16],
        entry_type=EntryType.ALT,
        wr_snapshot=200,
    )
    TournamentEntry.objects.create(
        tournament=tournament,
        player=players[17],
        entry_type=EntryType.LL,
        wr_snapshot=210,
    )

    Snapshot.objects.create(
        tournament=tournament,
        type=Snapshot.SnapshotType.CONFIRM_MD,
        payload={"rng_seed": str(tournament.rng_seed_active)},
    )

    Match.objects.create(
        tournament=tournament,
        phase=Phase.MD,
        round_name="R16",
        slot_top=1,
        slot_bottom=2,
        player_top=players[0],
        player_bottom=players[4],
        state="LIVE",
        score={"sets": [{"a": 6, "b": 4, "status": "in_progress"}], "meta": {"status": "live"}},
    )

    return tournament


@pytest.mark.django_db
def test_tournaments_index_ssr(client, sample_tournament):
    response = client.get("/msa/tournaments/")
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-testid="tournament-card"' in html
    assert 'data-total="1"' in html
    assert 'name="season"' in html
    assert sample_tournament.name in html


@pytest.mark.django_db
def test_tournament_overview_page(client, sample_tournament):
    url = reverse("msa:tournament_info", args=[sample_tournament.id])
    response = client.get(url)
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-testid="tournament-overview"' in html
    assert "Tournament summary" in html
    assert sample_tournament.snapshot_label in html
    assert str(sample_tournament.rng_seed_active) in html


@pytest.mark.django_db
def test_tournament_players_page(client, sample_tournament):
    url = reverse("msa:tournament_players", args=[sample_tournament.id])
    response = client.get(url)
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-testid="players-table"' in html
    assert "Seeds (4)" in html
    assert "Direct acceptance" in html
    assert "Qualification (" in html
    assert "Reserve / alternates" in html
    assert 'data-separator="cutline"' in html
    assert "License missing" in html


@pytest.mark.django_db
def test_tournament_draws_page_and_apis(client, sample_tournament):
    detail_url = reverse("msa:tournament_draws", args=[sample_tournament.id])
    response = client.get(detail_url)
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-testid="qualification-section"' in html
    assert 'data-testid="maindraw-section"' in html

    entries_url = reverse("msa-tournament-entries-api", args=[sample_tournament.id])
    entries_data = client.get(entries_url).json()
    assert entries_data["summary"]["S"] == 4
    assert entries_data["summary"]["D"] == 12
    assert "seeds" in entries_data["blocks"]
    assert "da" in entries_data["blocks"]
    assert entries_data["blocks"]["da"][0]["wc_label"] is True

    qual_url = reverse("msa-tournament-qualification-api", args=[sample_tournament.id])
    qual_data = client.get(qual_url).json()
    assert qual_data["K"] == 4
    assert qual_data["R"] == 2
    assert len(qual_data["brackets"]) == 4

    md_url = reverse("msa-tournament-maindraw-api", args=[sample_tournament.id])
    md_data = client.get(md_url).json()
    assert md_data["template_size"] == 16
    assert "seed_bands" in md_data
    assert len(md_data["slots"]) == 16

    history_url = reverse("msa-tournament-history-api", args=[sample_tournament.id])
    history_data = client.get(history_url).json()
    assert len(history_data["snapshots"]) >= 1
    assert history_data["snapshots"][0]["type"] == Snapshot.SnapshotType.CONFIRM_MD


@pytest.mark.django_db
def test_live_badge_counts_live_matches(client, sample_tournament):
    response = client.get("/msa/status/live-badge")
    assert response.status_code == 200
    payload = response.content.decode()
    assert "● 1" in payload
    assert "hidden" not in payload
