from django.db.models import Q

from msa.services._concurrency import atomic_tournament, lock_qs


@atomic_tournament
def replace_slot(tournament, slot, alt_id):
    from msa.models import EntryStatus, TournamentEntry

    alt = lock_qs(TournamentEntry.objects).get(
        pk=alt_id, tournament=tournament, status=EntryStatus.ACTIVE
    )

    incumbent = lock_qs(
        TournamentEntry.objects.filter(tournament=tournament, position=slot).exclude(pk=alt.pk)
    ).first()
    if incumbent:
        TournamentEntry.objects.filter(pk=incumbent.pk).update(position=None)

    updated = (
        TournamentEntry.objects.filter(pk=alt.pk)
        .filter(Q(position__isnull=True) | Q(position=slot))
        .update(position=slot)
    )
    if updated != 1:
        alt.refresh_from_db()
    return alt
