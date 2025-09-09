from django.test import override_settings

from msa.services.calendar_sync import day_order_description, is_enabled


class Dummy:
    def __init__(self, id, rn, st, sb):
        self.id = id
        self.round_name = rn
        self.slot_top = st
        self.slot_bottom = sb


def test_disabled_by_default(settings):
    assert not is_enabled()


@override_settings(MSA_CALENDAR_SYNC_ENABLED=True)
def test_builds_numbered_day_order_description():
    matches = [
        Dummy(1, "R1", 1, 2),
        Dummy(2, "R1", 3, 4),
        Dummy(3, "QF", 1, 4),
    ]
    desc = day_order_description(matches)
    assert desc.splitlines() == [
        "1. R1 [1 vs 2]",
        "2. R1 [3 vs 4]",
        "3. QF [1 vs 4]",
    ]
    assert is_enabled()
