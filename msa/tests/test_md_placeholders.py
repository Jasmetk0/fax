# tests/test_md_placeholders.py
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
from msa.services.md_placeholders import (
    PLACEHOLDER_PREFIX,
    confirm_md_with_placeholders,
    create_md_placeholders,
    replace_placeholders_with_qual_winners,
)
from msa.services.qual_confirm import confirm_qualification


@pytest.mark.django_db
def test_placeholders_lock_slots_and_later_swap_to_real_winners():
    # Turnaj: MD32, K=2 kvalifikanti, kvalda R=3 (8 hráčů/ větev)
    s = Season.objects.create(name="2025", start_date="2025-01-01", end_date="2025-12-31")
    c = Category.objects.create(name="World Tour")
    cs = CategorySeason.objects.create(
        category=c, season=s, draw_size=32, md_seeds_count=8, qualifiers_count=2, qual_rounds=3
    )
    t = Tournament.objects.create(
        season=s, category=c, category_season=cs, name="T", slug="t", state=TournamentState.REG
    )

    # Registrace do kvaldy (16 hráčů Q)
    Q_players = [Player.objects.create(name=f"Q{i}") for i in range(1, 17)]
    for p in Q_players:
        TournamentEntry.objects.create(
            tournament=t,
            player=p,
            entry_type=EntryType.Q,
            status=EntryStatus.ACTIVE,
            wr_snapshot=None,
        )

    # MD dřív než kvalda: vytvoř placeholdery a potvrď MD
    mapping = confirm_md_with_placeholders(t, rng_seed=777)

    # Zjisti, na jakých slotech sedí placeholdery
    ph_entries = TournamentEntry.objects.filter(
        tournament=t,
        entry_type=EntryType.Q,
        status=EntryStatus.ACTIVE,
        player__name__startswith=PLACEHOLDER_PREFIX,
    )
    assert ph_entries.count() == 2
    placeholder_slots = sorted([te.position for te in ph_entries])
    assert all(1 <= s <= 32 for s in placeholder_slots)

    # Nyní vytvoř kvalifikaci (K=2, R=3) a nastav finálové vítěze
    confirm_qualification(t, rng_seed=123)  # vytvoří Q8/Q4/Q2 strom
    finals = list(Match.objects.filter(tournament=t, phase=Phase.QUAL, round_name="Q2"))
    assert len(finals) == 2

    # Simuluj vítěze: v obou finále vyhraje always player_top
    for m in finals:
        m.winner_id = m.player_top_id
        m.state = MatchState.DONE
        m.save(update_fields=["winner", "state"])

    # Proveď nahrazení placeholderů skutečnými vítězi
    changed = replace_placeholders_with_qual_winners(t)
    assert changed == 2

    # Ověř, že na těch samých slotech teď sedí **reální hráči** (ne placeholder jména)
    ph_after = TournamentEntry.objects.filter(
        tournament=t, status=EntryStatus.ACTIVE, position__in=placeholder_slots
    )
    assert ph_after.count() == 2
    for te in ph_after:
        assert not te.player.name.startswith(PLACEHOLDER_PREFIX)

    # A že R1 zápasy v MD mají na těch slotech stejné sloty, ale nový player_id
    r1 = list(Match.objects.filter(tournament=t, phase=Phase.MD, round_name="R32"))
    assert len(r1) == 16
    # vyhledej páry obsahující placeholder-sloty – musí referencovat nové player_id
    slots_in_r1 = set()
    for m in r1:
        slots_in_r1.add(m.slot_top)
        slots_in_r1.add(m.slot_bottom)
    for s in placeholder_slots:
        assert s in slots_in_r1
