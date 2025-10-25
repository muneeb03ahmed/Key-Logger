from __future__ import annotations
import threading
import time
from typing import Optional, List, Dict
from pynput import keyboard
import logging
from .analytics import HoldEvent, LatencyEvent

logger = logging.getLogger(__name__)

# IMPORTANT: Do not log plaintext. We only store anonymized key codes and timings.

class Recorder:
    def __init__(self, max_duration_sec: int = 120, idle_timeout_sec: int = 10):
        self.max_duration_sec = max_duration_sec
        self.idle_timeout_sec = idle_timeout_sec

        self._listener: Optional[keyboard.Listener] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._paused = threading.Event()
        self._paused.set()  # start paused until Start() called

        self.started_at_iso: Optional[str] = None
        self.start_ts: Optional[float] = None
        self.last_event_ts: Optional[float] = None

        self.total_events = 0
        self.holds: List[HoldEvent] = []
        self.latencies: List[LatencyEvent] = []
        self._press_times: Dict[int, float] = {}
        self._press_timestamps_ms: List[float] = []

    @property
    def press_timestamps_ms(self) -> List[float]:
        return list(self._press_timestamps_ms)

    def _vk_of(self, key) -> Optional[int]:
        try:
            if hasattr(key, 'vk') and key.vk is not None:
                return int(key.vk)
            if hasattr(key, 'value') and hasattr(key.value, 'vk'):
                return int(key.value.vk)
        except Exception:
            return None
        return None

    def _on_press(self, key):
        if not self._running.is_set() or self._paused.is_set():
            return
        now = time.time()
        vk = self._vk_of(key)
        if vk is None:
            return
        self.total_events += 1
        self._press_times[vk] = now
        self._press_timestamps_ms.append(now * 1000.0)
        if self.last_event_ts is not None:
            self.latencies.append(LatencyEvent(latency_ms=(now - self.last_event_ts) * 1000.0))
        self.last_event_ts = now

    def _on_release(self, key):
        if not self._running.is_set() or self._paused.is_set():
            return
        now = time.time()
        vk = self._vk_of(key)
        if vk is None:
            return
        t0 = self._press_times.pop(vk, None)
        if t0 is not None:
            hold_ms = (now - t0) * 1000.0
            self.holds.append(HoldEvent(code=vk, hold_ms=hold_ms))
        self.last_event_ts = now

    def _run(self):
        logger.info("Recorder thread started")
        with keyboard.Listener(on_press=self._on_press, on_release=self._on_release) as listener:
            self._listener = listener
            while self._running.is_set():
                if self.start_ts and self.max_duration_sec > 0:
                    if time.time() - self.start_ts >= self.max_duration_sec:
                        logger.info("Max duration reached; stopping")
                        self.stop()
                        break
                if self.last_event_ts and self.idle_timeout_sec > 0 and not self._paused.is_set():
                    if time.time() - self.last_event_ts >= self.idle_timeout_sec:
                        logger.info("Idle timeout reached; auto-pausing")
                        self.pause()
                time.sleep(0.05)
        logger.info("Recorder thread exiting")

    def start(self, started_at_iso: str):
        if self._running.is_set():
            return
        self.reset(clear_data=False)
        self.started_at_iso = started_at_iso
        self.start_ts = time.time()
        self._running.set()
        self._paused.clear()
        self._thread = threading.Thread(target=self._run, name="KDynRecorder", daemon=True)
        self._thread.start()

    def pause(self):
        self._paused.set()

    def resume(self):
        if self._running.is_set():
            self._paused.clear()
            self.last_event_ts = time.time()

    def stop(self):
        self._paused.set()
        self._running.clear()
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
        self._listener = None

    def reset(self, clear_data: bool = True):
        self.stop()
        if clear_data:
            self.total_events = 0
            self.holds.clear()
            self.latencies.clear()
            self._press_times.clear()
            self._press_timestamps_ms.clear()
            self.started_at_iso = None
            self.start_ts = None
            self.last_event_ts = None

    def duration_secs(self) -> int:
        if not self.start_ts:
            return 0
        return int(time.time() - self.start_ts)