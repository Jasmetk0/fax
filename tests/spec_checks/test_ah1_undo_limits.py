from msa.services.planning_undo import _limits


def test_default_limits():
    count, size = _limits()
    assert count == 300
    assert size == 8 * 1024 * 1024
