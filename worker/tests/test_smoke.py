from lectern_worker.main import backoff_seconds


def test_backoff_grows_then_caps():
    waits = [backoff_seconds(a) for a in range(10)]
    assert waits[0] == 1.0
    assert waits == sorted(waits)
    assert waits[-1] == 60.0


def test_backoff_respects_custom_cap():
    assert backoff_seconds(20, base=2.0, cap=15.0) == 15.0
