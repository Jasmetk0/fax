from contextlib import contextmanager

from django.db import transaction


@contextmanager
def atomic():
    """
    Jednotné místo pro atomic bloky (snadno se později zpřísní nastavení).
    """
    with transaction.atomic():
        yield


def locked(qs):
    """
    SELECT FOR UPDATE; na SQLite no-op, na Postgresu skutečný lock.
    """
    return qs.select_for_update()
