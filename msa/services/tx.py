from functools import wraps

from django.db import connections, transaction


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
    """SELECT FOR UPDATE; na SQLite fallback na no-op, na Postgresu skutečný lock."""
    try:
        conn = connections[qs.db]
        if getattr(conn.features, "has_select_for_update", False):
            return qs.select_for_update()
    except Exception:
        pass
    return qs
