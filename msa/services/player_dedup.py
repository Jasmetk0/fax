from __future__ import annotations

import difflib
import unicodedata

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from msa.models import Match, Player, PlayerLicense, RankingAdjustment, TournamentEntry
from msa.services.admin_gate import require_admin_mode


def normalize_name(name: str) -> str:
    """lowercase, remove diacritics, collapse whitespace."""
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    name = " ".join(name.split())
    return name.casefold()


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def find_duplicate_candidates(
    threshold: float = 0.88, limit: int = 200
) -> list[tuple[int, int, float]]:
    players = list(Player.objects.order_by("id").values_list("id", "name"))
    results: list[tuple[int, int, float]] = []
    start = max(0, len(players) - limit)
    for idx in range(len(players) - 1, start - 1, -1):
        a_id, a_name = players[idx]
        a_norm = normalize_name(a_name or "")
        for j in range(idx):
            b_id, b_name = players[j]
            score = difflib.SequenceMatcher(None, a_norm, normalize_name(b_name or "")).ratio()
            if score >= threshold:
                results.append((b_id, a_id, score))
    results.sort(key=lambda x: x[2], reverse=True)
    return results


@require_admin_mode
@transaction.atomic
def merge_players(master_id: int, dup_id: int, dry_run: bool = False) -> dict:
    if master_id == dup_id:
        raise ValidationError("master and duplicate must differ")

    players = Player.objects.select_for_update().filter(id__in=[master_id, dup_id])
    if players.count() != 2:
        raise ValidationError("player not found")
    players_map = {p.id: p for p in players}
    master = players_map[master_id]
    dup = players_map[dup_id]

    conflict_q = Match.objects.filter(
        Q(player_top=dup_id, player_bottom__in=[master_id, dup_id])
        | Q(player_bottom=dup_id, player_top__in=[master_id, dup_id])
    )
    if conflict_q.exists():
        raise ValidationError("conflict: same player in a match")

    updated: dict[str, int] = {}

    def _update(qs, key: str, **kwargs) -> None:
        count = qs.count()
        if count:
            updated[key] = count
            if not dry_run:
                qs.update(**kwargs)

    _update(
        TournamentEntry.objects.filter(player=dup),
        "TournamentEntry",
        player=master,
    )
    _update(Match.objects.filter(player_top=dup), "Match.player_top", player_top=master)
    _update(Match.objects.filter(player_bottom=dup), "Match.player_bottom", player_bottom=master)
    _update(Match.objects.filter(winner=dup), "Match.winner", winner=master)
    _update(Match.objects.filter(player1=dup), "Match.player1", player1=master)
    _update(Match.objects.filter(player2=dup), "Match.player2", player2=master)

    licenses_merged = 0
    dup_licenses = PlayerLicense.objects.filter(player=dup)
    for lic in dup_licenses:
        exists = PlayerLicense.objects.filter(player=master, season=lic.season).exists()
        if exists:
            licenses_merged += 1
            if not dry_run:
                lic.delete()
        else:
            if not dry_run:
                lic.player = master
                lic.save(update_fields=["player"])
    adjustments_qs = RankingAdjustment.objects.filter(player=dup)
    adjustments_merged = adjustments_qs.count()
    if not dry_run and adjustments_merged:
        adjustments_qs.update(player=master)

    if not dry_run:
        dup.delete()

    return {
        "updated": updated,
        "licenses_merged": licenses_merged,
        "adjustments_merged": adjustments_merged,
        "deleted_player_id": dup_id,
    }
