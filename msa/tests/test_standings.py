# tests/test_standings.py
from datetime import date, timedelta

import pytest

from msa.models import (
    Category,
    CategorySeason,
    EntryStatus,
    EntryType,
    Match,
    MatchState,
    Phase,
    Player,
    Season,
    Tournament,
    TournamentEntry,
    TournamentState,
)
from msa.services.scoring import compute_tournament_points
from msa.services.standings import _monday_of, rolling_standings, rtf_standings, season_standings


def _mk_tournament(season, category, name, end_date_str, scoring_md=None):
    cs = CategorySeason.objects.filter(category=category, season=season).first()
    if not cs:
        cs = CategorySeason.objects.create(
            category=category, season=season, draw_size=16, md_seeds_count=4
        )
        if scoring_md:
            cs.scoring_md = scoring_md
            cs.save(update_fields=["scoring_md"])
    t = Tournament.objects.create(
        season=season,
        category=category,
        category_season=cs,
        name=name,
        slug=name.lower(),
        state=TournamentState.MD,
        end_date=end_date_str,
    )
    return t


@pytest.mark.django_db
def test_season_best_n_counts_top_results_only():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31", best_N=1)
    cat = Category.objects.create(name="World Tour")
    scoring = {"Winner": 100, "RunnerUp": 60, "SF": 36, "QF": 18, "R16": 9}

    # dva turnaje v sezóně, stejná kategorie
    t1 = _mk_tournament(s, cat, "T1", "2025-03-10", scoring_md=scoring)
    t2 = _mk_tournament(s, cat, "T2", "2025-05-20", scoring_md=scoring)

    # hráč A vyhraje T1 (100), v T2 jen QF (18)
    A = Player.objects.create(name="A")
    B = Player.objects.create(name="B")
    TournamentEntry.objects.create(
        tournament=t1, player=A, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=t1, player=B, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=t2, player=A, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=t2, player=B, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )

    # T1 finále: A winner
    Match.objects.create(
        tournament=t1,
        phase=Phase.MD,
        round_name="R2",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        winner=A,
        state=MatchState.DONE,
    )
    # T2 QF: porážka A v QF (R8)
    Match.objects.create(
        tournament=t2,
        phase=Phase.MD,
        round_name="QF",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        winner=B,
        state=MatchState.DONE,
    )

    rows = season_standings(s)
    rowA = next(r for r in rows if r.player_id == A.id)
    assert rowA.total == 100  # best_N=1 → bere jen 100
    assert rowA.counted == [100] and rowA.dropped == [18]


@pytest.mark.django_db
def test_rolling_activation_and_expiry_61_weeks():
    # dvě sezóny (kvůli best_N fallbacku), ale počítáme podle datumu
    s1 = Season.objects.create(
        name="2025", start_date="2025-01-01", end_date="2025-12-31", best_N=2
    )
    s2 = Season.objects.create(
        name="2026", start_date="2026-01-01", end_date="2026-12-31", best_N=2
    )
    cat = Category.objects.create(name="WT")
    scoring = {"Winner": 100, "RunnerUp": 60, "SF": 36, "QF": 18, "R16": 9, "R32": 5}

    # T končí ve čtvrtek 2025-02-06 → aktivace pondělí 2025-02-10
    t = _mk_tournament(s1, cat, "OpenA", "2025-02-06", scoring_md=scoring)
    A = Player.objects.create(name="A")
    B = Player.objects.create(name="B")
    TournamentEntry.objects.create(
        tournament=t, player=A, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=t, player=B, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="R2",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        winner=A,
        state=MatchState.DONE,
    )

    # snapshot 2025-02-03 (pondělí před aktivací) → 0 bodů
    r0 = rolling_standings("2025-02-03")
    assert all(row.total == 0 for row in r0) or len(r0) == 0

    # snapshot 2025-02-10 (aktivace) → A má 100
    r1 = rolling_standings("2025-02-10")
    rowA = next((r for r in r1 if r.player_id == A.id), None)
    assert rowA and rowA.total == 100

    # snapshot 61 týdnů po aktivaci už turnaj nepatří do okna
    r61 = rolling_standings(date(2026, 4, 13))  # 2025-02-10 + 61 týdnů = 2026-04-13
    rowA61 = next((r for r in r61 if r.player_id == A.id), None)
    assert (rowA61 is None) or (rowA61.total == 0)


@pytest.mark.django_db
def test_rtf_pins_auto_top_winners():
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31", best_N=2)
    catP = Category.objects.create(name="WT Platinum")
    catS = Category.objects.create(name="WT Silver")
    scoring = {"Winner": 100, "RunnerUp": 60, "SF": 36, "QF": 18, "R16": 9}

    tP = _mk_tournament(s, catP, "Platinum", "2025-03-15", scoring_md=scoring)
    tS = _mk_tournament(s, catS, "Silver", "2025-05-01", scoring_md=scoring)

    A = Player.objects.create(name="A")
    B = Player.objects.create(name="B")
    C = Player.objects.create(name="C")
    # Platinum: A vítěz
    TournamentEntry.objects.create(
        tournament=tP, player=A, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=tP, player=B, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    Match.objects.create(
        tournament=tP,
        phase=Phase.MD,
        round_name="R2",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        winner=A,
        state=MatchState.DONE,
    )
    # Silver: C vítěz
    TournamentEntry.objects.create(
        tournament=tS, player=C, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=tS, player=B, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    Match.objects.create(
        tournament=tS,
        phase=Phase.MD,
        round_name="R2",
        slot_top=1,
        slot_bottom=2,
        player_top=C,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        winner=C,
        state=MatchState.DONE,
    )

    rows = rtf_standings(s, auto_top_categories=["WT Platinum", "WT Silver"])
    # první dva řádky jsou pinned vítězové ve stejném pořadí kategorií
    assert len(rows) >= 2
    assert rows[0].pinned_category == "WT Platinum" and rows[0].player_id == A.id
    assert rows[1].pinned_category == "WT Silver" and rows[1].player_id == C.id
