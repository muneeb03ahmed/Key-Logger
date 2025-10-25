from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
import statistics

@dataclass
class HoldEvent:
    code: int
    hold_ms: float

@dataclass
class LatencyEvent:
    latency_ms: float

@dataclass
class Metrics:
    session_id: str
    started_at: str
    duration_secs: int
    events: int
    holds_count: int
    latency_count: int
    median_hold_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    bursts: int
    avg_burst_len: float
    per_key: List[Dict]


def _percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    data_sorted = sorted(data)
    k = (len(data_sorted) - 1) * p
    f = int(k)
    c = min(f + 1, len(data_sorted) - 1)
    if f == c:
        return float(data_sorted[int(k)])
    d0 = data_sorted[f] * (c - k)
    d1 = data_sorted[c] * (k - f)
    return float(d0 + d1)


def compute_bursts(timestamps_ms: List[float], threshold_ms: float = 700.0) -> Tuple[int, float]:
    """
    timestamps_ms: press timestamps (ms) sorted ascending.
    Returns: (burst_count, avg_burst_len)
    """
    if not timestamps_ms:
        return 0, 0.0
    bursts = []
    current_len = 1
    for i in range(1, len(timestamps_ms)):
        if timestamps_ms[i] - timestamps_ms[i - 1] < threshold_ms:
            current_len += 1
        else:
            bursts.append(current_len)
            current_len = 1
    bursts.append(current_len)
    return len(bursts), (sum(bursts) / len(bursts)) if bursts else 0.0


def aggregate(session_id: str, started_at: str, duration_secs: int,
              total_events: int, holds: List[HoldEvent], latencies: List[LatencyEvent],
              press_timestamps_ms: List[float]) -> Metrics:
    hold_vals = [h.hold_ms for h in holds]
    lat_vals = [l.latency_ms for l in latencies]

    median_hold = statistics.median(hold_vals) if hold_vals else 0.0
    median_latency = statistics.median(lat_vals) if lat_vals else 0.0
    p95_latency = _percentile(lat_vals, 0.95) if lat_vals else 0.0

    # Per-key stats
    per_key_map: Dict[int, List[float]] = {}
    for h in holds:
        per_key_map.setdefault(h.code, []).append(h.hold_ms)
    per_key = []
    for code, vals in sorted(per_key_map.items()):
        per_key.append({
            "code": int(code),
            "count": int(len(vals)),
            "median_hold": float(statistics.median(vals)),
            "p95_hold": float(_percentile(vals, 0.95)),
        })

    bursts_count, avg_burst_len = compute_bursts(press_timestamps_ms)

    return Metrics(
        session_id=session_id,
        started_at=started_at,
        duration_secs=int(duration_secs),
        events=int(total_events),
        holds_count=int(len(holds)),
        latency_count=int(len(latencies)),
        median_hold_ms=float(median_hold),
        median_latency_ms=float(median_latency),
        p95_latency_ms=float(p95_latency),
        bursts=int(bursts_count),
        avg_burst_len=float(avg_burst_len),
        per_key=per_key,
    )