from functools import wraps

from django.db import transaction

from msa.models import Tournament
from msa.services.tx import locked


def _lock_tournament_row(tournament):
    pk = getattr(tournament, "pk", tournament)
    locked(Tournament.objects.filter(pk=pk)).exists()


def atomic_tournament(fn):
    @wraps(fn)
    def wrapper(tournament, *args, **kwargs):
        with transaction.atomic():
            _lock_tournament_row(tournament)
            return fn(tournament, *args, **kwargs)

    return wrapper


def lock_qs(qs):
    return locked(qs)
