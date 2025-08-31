import logging

from django.db import transaction

from ..models import Player, RankingEntry, RankingSnapshot

logger = logging.getLogger(__name__)


def create_ranking_snapshot(as_of, *, season=None, user=None) -> RankingSnapshot:
    with transaction.atomic():
        snapshot = RankingSnapshot.objects.create(
            as_of=as_of, created_by=user, updated_by=user
        )
        players = Player.objects.all().order_by("-rtf_current_points", "name")
        entries = [
            RankingEntry(
                snapshot=snapshot,
                player=p,
                rank=i,
                points=p.rtf_current_points or 0,
                created_by=user,
                updated_by=user,
            )
            for i, p in enumerate(players, start=1)
        ]
        RankingEntry.objects.bulk_create(entries)
    logger.info(
        "snapshot.create user=%s as_of=%s entries=%s",
        getattr(user, "id", None),
        as_of,
        len(entries),
    )
    return snapshot
