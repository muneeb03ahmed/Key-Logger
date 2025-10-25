from kdyn.analytics import HoldEvent, LatencyEvent, aggregate
from kdyn.reports import write_json, write_html
import json


def test_report_schema_and_html(tmp_path):
    holds = [HoldEvent(code=65, hold_ms=100.0)]
    lats = [LatencyEvent(latency_ms=50.0)]
    presses = [0, 500]
    m = aggregate("sess123", "2025-01-01T00:00:00Z", 12, 2, holds, lats, presses)
    jpath = tmp_path / "reports"  # override folder by monkeypatching path if needed

    # Temporarily switch REPORTS_DIR via monkeypatch-like approach
    from kdyn import reports as rep
    old = rep.REPORTS_DIR
    rep.REPORTS_DIR = tmp_path
    try:
        jp = write_json(m)
        hp = write_html(m)
    finally:
        rep.REPORTS_DIR = old

    data = json.loads(jp.read_text())
    for key in [
        "session_id","started_at","duration_secs","events","holds_count","latency_count",
        "median_hold_ms","median_latency_ms","p95_latency_ms","bursts","avg_burst_len","per_key"]:
        assert key in data

    assert hp.exists()
    assert "<html" in hp.read_text().lower()