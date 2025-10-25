from kdyn.analytics import HoldEvent, LatencyEvent, aggregate, compute_bursts


def test_percentiles_and_bursts():
    holds = [HoldEvent(code=65, hold_ms=v) for v in [100, 90, 110, 95, 105]]
    lats = [LatencyEvent(latency_ms=v) for v in [50, 60, 70, 80, 90, 100]]
    presses = [0, 100, 200, 800, 1000, 1600]  # ms
    bursts, avg = compute_bursts(presses, threshold_ms=700)
    assert bursts == 2
    assert abs(avg - 3.0) < 1e-6  # (3 + 3) / 2

    m = aggregate("sess", "2025-01-01T00:00:00Z", 10, 100, holds, lats, presses)
    assert m.median_hold_ms == 100
    assert m.median_latency_ms == 75.0
    assert 0 < m.p95_latency_ms <= 100
    per_key = {k['code']: k for k in m.per_key}
    assert per_key[65]['count'] == 5
    assert per_key[65]['median_hold'] == 100