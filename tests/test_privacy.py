from kdyn.recorder import Recorder


def test_recorder_no_plaintext_storage(monkeypatch):
    r = Recorder()
    # Simulate press/release using fake objects with vk
    class K: pass
    k = K(); k.vk = 65  # 'A' but vk only

    r._running.set(); r._paused.clear()

    r._on_press(k)
    r._on_release(k)

    # Ensure only vk and timing fields are present
    assert all(hasattr(h, 'code') and hasattr(h, 'hold_ms') for h in r.holds)
    assert all(hasattr(l, 'latency_ms') for l in r.latencies)
    # No attribute that stores plaintext
    assert not any(hasattr(h, 'char') for h in r.holds)