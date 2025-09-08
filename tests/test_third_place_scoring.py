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
from msa.services.scoring import compute_md_points

THIRD = 200
FOURTH = 120
SFPTS = 90


def _mk_base(draw=16):
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=draw, md_seeds_count=4)
    # scoring tabulka s Third/Fourth + SF
    cs.scoring_md = {"Winner": 1000, "RunnerUp": 600, "SF": SFPTS, "Third": THIRD, "Fourth": FOURTH}
    cs.save(update_fields=["scoring_md"])
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T",
        slug="t",
        state=TournamentState.MD,
        third_place_enabled=True,
    )
    return s, c, cs, t


@pytest.mark.django_db
def test_third_place_points_override_sf_when_played():
    _, _, cs, t = _mk_base()
    # dva hráči – semifinalisté (v testu si SF jen nasimulujeme body přes SF zápasy)
    A = Player.objects.create(name="A")
    B = Player.objects.create(name="B")
    TournamentEntry.objects.create(
        tournament=t, player=A, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=t, player=B, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )

    # SF: A i B prohráli své SF – získají SF body
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=Player.objects.create(name="X"),
        best_of=5,
        win_by_two=True,
        winner_id=None,  # SF porážka A: výsledek nastavíme dalším voláním
        state=MatchState.DONE,
    )
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=3,
        slot_bottom=4,
        player_top=B,
        player_bottom=Player.objects.create(name="Y"),
        best_of=5,
        win_by_two=True,
        winner_id=None,  # SF porážka B: výsledek nastavíme dalším voláním
        state=MatchState.DONE,
    )

    # označ explicitní vítěze v SF (A i B prohráli svá SF)
    sf1 = Match.objects.filter(
        tournament=t, phase=Phase.MD, round_name="SF", slot_top=1, slot_bottom=2
    ).first()
    sf2 = Match.objects.filter(
        tournament=t, phase=Phase.MD, round_name="SF", slot_top=3, slot_bottom=4
    ).first()
    sf1.winner_id = sf1.player_bottom_id
    sf2.winner_id = sf2.player_bottom_id
    sf1.save(update_fields=["winner"])
    sf2.save(update_fields=["winner"])

    # 3P je DOHRANÝ → A vyhrál, B prohrál
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="3P",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        winner_id=A.id,
        state=MatchState.DONE,
    )

    pts = compute_md_points(t, only_completed_rounds=False)
    assert pts.get(A.id, 0) == cs.scoring_md["Third"]
    assert pts.get(B.id, 0) == cs.scoring_md["Fourth"]


@pytest.mark.django_db
def test_no_third_place_match_or_not_done_keeps_sf_points():
    _, _, cs, t = _mk_base()
    A = Player.objects.create(name="A")
    B = Player.objects.create(name="B")
    TournamentEntry.objects.create(
        tournament=t, player=A, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=t, player=B, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )

    # SF prohry – základ pro SF body
    X = Player.objects.create(name="X")
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=X,
        best_of=5,
        win_by_two=True,
        winner_id=X.id,
        state=MatchState.DONE,
    )
    Y = Player.objects.create(name="Y")
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=3,
        slot_bottom=4,
        player_top=B,
        player_bottom=Y,
        best_of=5,
        win_by_two=True,
        winner_id=Y.id,
        state=MatchState.DONE,
    )

    # 3P buď neexistuje, nebo je jen PENDING:
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="3P",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        state=MatchState.PENDING,  # nehotovo => SF body zůstanou
    )

    pts = compute_md_points(t, only_completed_rounds=False)
    assert pts.get(A.id, 0) == SFPTS
    assert pts.get(B.id, 0) == SFPTS


@pytest.mark.django_db
def test_third_place_ignored_when_flag_off():
    # stejné prostředí, ale third_place_enabled=False
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="WT")
    cs = CategorySeason.objects.create(category=c, season=s, draw_size=16, md_seeds_count=4)
    cs.scoring_md = {
        "Winner": 1000,
        "RunnerUp": 600,
        "SF": SFPTS,
        "Third": THIRD,
        "Fourth": FOURTH,
    }
    cs.save(update_fields=["scoring_md"])
    t = Tournament.objects.create(
        season=s,
        category=c,
        category_season=cs,
        name="T2",
        slug="t2",
        state=TournamentState.MD,
        third_place_enabled=False,
    )
    A = Player.objects.create(name="A2")
    B = Player.objects.create(name="B2")
    TournamentEntry.objects.create(
        tournament=t, player=A, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    TournamentEntry.objects.create(
        tournament=t, player=B, entry_type=EntryType.DA, status=EntryStatus.ACTIVE
    )
    x = Player.objects.create(name="X2")
    y = Player.objects.create(name="Y2")
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=x,
        best_of=5,
        win_by_two=True,
        winner_id=x.id,
        state=MatchState.DONE,
    )
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="SF",
        slot_top=3,
        slot_bottom=4,
        player_top=B,
        player_bottom=y,
        best_of=5,
        win_by_two=True,
        winner_id=y.id,
        state=MatchState.DONE,
    )
    # existuje hotový 3P (A porazil B), ale flag je OFF → ignorovat a ponechat SF body
    Match.objects.create(
        tournament=t,
        phase=Phase.MD,
        round_name="3P",
        slot_top=1,
        slot_bottom=2,
        player_top=A,
        player_bottom=B,
        best_of=5,
        win_by_two=True,
        winner_id=A.id,
        state=MatchState.DONE,
    )
    pts = compute_md_points(t, only_completed_rounds=False)
    assert pts.get(A.id, 0) == SFPTS
    assert pts.get(B.id, 0) == SFPTS
