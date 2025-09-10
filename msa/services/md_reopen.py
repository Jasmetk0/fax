from __future__ import annotations

from types import SimpleNamespace

from django.core.exceptions import ValidationError

from msa.models import (
    EntryStatus,
    Match,
    MatchState,
    Phase,
    Schedule,
    Snapshot,
    Tournament,
    TournamentEntry,
)
from msa.services.admin_gate import require_admin_mode
from msa.services.archiver import archive
from msa.services.md_embed import r1_name_for_md
from msa.services.randoms import rng_for, seeded_shuffle
from msa.services.tx import atomic, locked


@require_admin_mode
@atomic()
def reopen_main_draw(t: Tournament, mode: str = "AUTO", rng_seed: int | None = None) -> str:
    """Reopen main draw according to mode.

    - No MD results → delete all MD matches (full reset to edit phase).
    - Results present:
        * SOFT  → shuffle unseeded players in unfinished R1 matches, keep finished pairs.
        * HARD  → hard re-seeding of unseeded players and reset any R1 results.
        * CANCEL→ no-op.
    - AUTO    → if no results, full reset; otherwise behaves like SOFT.
    """
    md_qs = Match.objects.filter(tournament=t, phase=Phase.MD)
    md_matches = list(locked(md_qs))
    any_result = any((m.winner_id is not None) or (m.state == MatchState.DONE) for m in md_matches)

    if not any_result:
        md_qs.delete()
        archive(
            t,
            type=Snapshot.SnapshotType.REOPEN,
            label="reopen_md_no_results",
            extra={"mode": "FULL"},
        )
        return "REOPEN: cleared all MD matches (no results present)"

    if mode.upper() == "CANCEL":
        return "REOPEN: canceled"

    if mode.upper() == "AUTO":
        mode = "SOFT"

    # Správné R1 i pro embed (např. 24→R32)
    r1_name = r1_name_for_md(t)
    r1_matches = [m for m in md_matches if m.round_name == r1_name]

    if mode.upper() in {"SOFT", "HARD"}:
        # collect mutable (unfinished) slots
        mutable_slots: list[int] = []
        for m in r1_matches:
            if (m.winner_id is None) and (m.state != MatchState.DONE):
                mutable_slots.extend([m.slot_top, m.slot_bottom])

        entries_qs = locked(
            TournamentEntry.objects.filter(
                tournament=t, status=EntryStatus.ACTIVE, position__isnull=False
            )
        )
        slot_to_entry = {int(te.position): te for te in entries_qs}

        # gather unseeded entries in mutable slots
        mutable_unseeded_slots: list[int] = []
        pool_entry_ids: list[int] = []
        for slot in sorted(mutable_slots):
            te = slot_to_entry.get(slot)
            if not te or te.seed is not None:
                continue
            mutable_unseeded_slots.append(slot)
            pool_entry_ids.append(te.id)

        if len(pool_entry_ids) > 1:
            rng_source = SimpleNamespace(rng_seed_active=rng_seed) if rng_seed is not None else t
            rng = rng_for(rng_source)
            shuffled = seeded_shuffle(pool_entry_ids, rng)

            # free positions to avoid unique constraint and then assign shuffled positions
            TournamentEntry.objects.filter(pk__in=pool_entry_ids).update(position=None)
            for slot, eid in zip(sorted(mutable_unseeded_slots), shuffled, strict=False):
                TournamentEntry.objects.filter(pk=eid).update(position=slot)

        # update matches
        for m in r1_matches:
            has_result = (m.winner_id is not None) or (m.state == MatchState.DONE)
            if mode.upper() == "SOFT" and has_result:
                # keep finished pairs intact
                continue

            # Před úpravou si schovej původní dvojici
            old_pair = (m.player_top_id, m.player_bottom_id)

            top = TournamentEntry.objects.filter(
                tournament=t, status=EntryStatus.ACTIVE, position=m.slot_top
            ).first()
            bot = TournamentEntry.objects.filter(
                tournament=t, status=EntryStatus.ACTIVE, position=m.slot_bottom
            ).first()
            if top:
                m.player_top_id = top.player_id
            if bot:
                m.player_bottom_id = bot.player_id
            if mode.upper() == "HARD":
                m.winner_id = None
                m.state = MatchState.PENDING
            m.save(update_fields=["player_top", "player_bottom", "winner", "state"])

            # Pokud se dvojice ZMĚNILA, plán už nemusí sedět → smaž Schedule
            new_pair = (m.player_top_id, m.player_bottom_id)
            if new_pair != old_pair:
                Schedule.objects.filter(match=m).delete()

        # If an explicit rng_seed was used, persist it for auditability
        if rng_seed is not None and getattr(t, "rng_seed_active", None) != rng_seed:
            t.rng_seed_active = rng_seed
            t.save(update_fields=["rng_seed_active"])
        label = "reopen_md_soft" if mode.upper() == "SOFT" else "reopen_md_hard"
        archive(t, type=Snapshot.SnapshotType.REOPEN, label=label, extra={"mode": mode.upper()})
        msg = (
            "REOPEN: applied SOFT re-seeding for unseeded R1 only"
            if mode.upper() == "SOFT"
            else "REOPEN: applied HARD re-seeding for unseeded (impacted results reset)"
        )
        return msg

    raise ValidationError("mode must be one of: AUTO | SOFT | HARD | CANCEL")
