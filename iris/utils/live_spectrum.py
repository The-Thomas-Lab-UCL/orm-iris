"""Bounded display-only mailbox; acquired data is stored through separate paths."""
import threading
import time


class LatestSpectrum:
    def __init__(self, interval_s=1., clock=None):
        self._lock = threading.Lock()
        self._pending = None
        self._next_due = 0.
        self._interval = interval_s
        self._clock = clock or time.monotonic

    def offer(self, measurement):
        with self._lock:
            self._pending = measurement

    def take(self):
        with self._lock:
            now = self._clock()
            if self._pending is None or now < self._next_due:
                return None
            measurement, self._pending = self._pending, None
            self._next_due = now + self._interval
            return measurement
