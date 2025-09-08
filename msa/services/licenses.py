# msa/services/licenses.py
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from django.core.exceptions import ValidationError

from msa.models import (
    EntryStatus,
    Player,
    PlayerLicense,
    Tournament,
    TournamentEntry,
)


@dataclass(frozen=True)
class MissingLicense:
    player_id: int
    player_name: str | None


def _active_entries(t: Tournament) -> Iterable[TournamentEntry]:
    return TournamentEntry.objects.filter(tournament=t, status=EntryStatus.ACTIVE).select_related(
        "player"
    )


def _has_license(player_id: int, season_id: int | None) -> bool:
    if not season_id:
        # Bez sezóny neaplikujeme licenční gate (MVP tolerantní chování).
        return True
    return PlayerLicense.objects.filter(player_id=player_id, season_id=season_id).exists()


def missing_licenses(t: Tournament) -> list[MissingLicense]:
    """
    Vrátí seznam hráčů (ACTIVE entries), kteří NEMAJÍ platnou licenci pro sezonu turnaje.
    Pokud tournament.season je NULL, vrací prázdný seznam (gate se neaplikuje).
    """
    if not t.season_id:
        return []
    out: list[MissingLicense] = []
    for te in _active_entries(t):
        pid = te.player_id
        if not pid:
            continue
        if not _has_license(pid, t.season_id):
            out.append(MissingLicense(player_id=pid, player_name=getattr(te.player, "name", None)))
    # deduplikace na hráče (může mít víc entries ve výjimečných stavech)
    uniq = {}
    for m in out:
        uniq[m.player_id] = m
    return list(uniq.values())


def assert_all_licensed_or_raise(t: Tournament) -> None:
    """
    Pokud jakýkoli ACTIVE hráč v turnaji nemá licenci pro sezonu turnaje,
    zvedne ValidationError se čitelnou zprávou (pro inline UI akci “přiřadit licenci”).
    """
    missing = missing_licenses(t)
    if not missing:
        return
    names = ", ".join((m.player_name or f"#{m.player_id}") for m in missing)
    raise ValidationError(
        f"Licenční kontrola selhala: {len(missing)} hráč(ů) bez licence pro sezónu {getattr(t.season, 'name', '?')}: {names}."
    )


def grant_license_for_tournament_season(t: Tournament, player_id: int) -> PlayerLicense:
    """
    Rychlá inline akce: vytvoří licenci hráči pro sezónu turnaje (idempotentně).
    Pokud t.season není nastaven, vyhodí ValidationError.
    """
    if not t.season_id:
        raise ValidationError("Turnaj nemá přiřazenou sezónu; nelze udělit licenci.")
    p = Player.objects.filter(pk=player_id).first()
    if not p:
        raise ValidationError("Hráč neexistuje.")
    lic, _ = PlayerLicense.objects.get_or_create(player_id=player_id, season_id=t.season_id)
    return lic
