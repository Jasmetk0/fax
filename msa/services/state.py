import logging
from django.db import transaction
from django.db.models import Q

from ..models import Tournament

logger = logging.getLogger(__name__)


def update_tournament_state(tournament, user=None):
    """Update tournament.state to LIVE or COMPLETE if conditions met."""

    with transaction.atomic():
        t = Tournament.objects.select_for_update().get(pk=tournament.pk)
        matches = t.matches.all()
        new_state = t.state
        if matches.exists():
            all_winners = not matches.filter(winner__isnull=True).exists()
            any_live = matches.filter(
                Q(winner__isnull=False)
                | Q(live_status__in=["live", "finished", "result"])
            ).exists()
            if all_winners:
                new_state = Tournament.State.COMPLETE
            elif any_live:
                new_state = Tournament.State.LIVE
        if new_state != t.state:
            t.state = new_state
            if user:
                t.updated_by = user
                t.save(update_fields=["state", "updated_by"])
            else:
                t.save(update_fields=["state"])
            return True
    return False
