from functools import wraps

from django.db import transaction


def atomic(_fn=None):
    """
    Použití:
      @atomic()   # doporučeno (se závorkami)
      @atomic     # funguje taky
    """

    def _decorator(fn):
        @wraps(fn)
        def _wrapped(*args, **kwargs):
            with transaction.atomic():
                return fn(*args, **kwargs)

        return _wrapped

    # @atomic bez závorek
    if callable(_fn):
        return _decorator(_fn)
    # @atomic() se závorkami
    return _decorator


def locked(qs):
    """SELECT FOR UPDATE; na SQLite no-op, na Postgresu skutečný lock."""
    return qs.select_for_update()
