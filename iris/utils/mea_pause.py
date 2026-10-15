"""
Coordination between a running mapping scan and the data hub's save/autosave/offload operations.

A save walks the whole MappingMeasurement_Hub and writes it to a database file. While that happens
the scan must not keep appending spectra to the units being written, so the scan is asked to hold
still until the save is finished. The two live in different modules (and different threads), so the
handshake is kept here, in a neutral place both can import:

    saver side                              scan side
    ----------                              ---------
    gate.request_pause()  ----------------> (scan reaches the end of its current point)
       (blocks until the scan is parked)    gate.checkpoint() parks the scan
    ... write the database ...
    gate.release()        ----------------> checkpoint() returns, the scan carries on

The gate is deliberately permissive: if the scan never reaches a checkpoint within the timeout, the
saver is told so and decides for itself whether to go ahead (an autosave that can never run is worse
than one taken while a scan is mid-point).

Made for: The Thomas Group, Biochemical Engineering Dept., UCL
"""
import threading
import time


class MeasurementPauseGate:
    """
    A re-entrant pause handshake between the saver(s) and a running scan.

    The scan brackets its run with scan_started()/scan_finished() and calls checkpoint() at every
    point it can safely be parked at. A saver brackets its write with request_pause()/release().
    Several savers may hold the pause at once; the scan resumes when the last one releases.
    """

    POLL_INTERVAL_SEC = 0.02    # How often a parked scan re-checks whether it may continue

    def __init__(self):
        self._lock = threading.Lock()
        self._num_pause_requests = 0                    # Re-entrant: the scan runs again at 0
        self._event_pause_requested = threading.Event() # Set while any saver holds the pause
        self._event_scan_parked = threading.Event()     # Set while the scan sits in checkpoint()
        self._event_scan_running = threading.Event()    # Set between scan_started/scan_finished

    # >>> Scan side <<<

    def scan_started(self) -> None:
        """
        Marks the start of a scan. Call it where the scan begins acquiring.
        """
        self._event_scan_running.set()
        self._event_scan_parked.clear()

    def scan_finished(self) -> None:
        """
        Marks the end of a scan. Call it where the scan stops acquiring, including on an error or a
        cancellation, so that a saver waiting on this gate is not left waiting for a dead scan.
        """
        self._event_scan_running.clear()
        self._event_scan_parked.clear()

    def is_scan_running(self) -> bool:
        """
        Returns:
            bool: True while a scan is between scan_started() and scan_finished().
        """
        return self._event_scan_running.is_set()

    def is_pause_requested(self) -> bool:
        """
        Returns:
            bool: True while at least one saver holds the pause.
        """
        return self._event_pause_requested.is_set()

    def checkpoint(self, event_keep_running:threading.Event|None=None) -> float:
        """
        Parks the scan while a save is in progress. Returns immediately when no save is running, so
        this is cheap enough to call at every scan point.

        Args:
            event_keep_running (threading.Event|None): The scan's "still acquiring" flag, if any.
                When given, the scan is released as soon as this is cleared, so cancelling a
                measurement is not held up by an in-progress save.

        Returns:
            float: Seconds spent parked. Feed this to the scan's progress estimator so the pause is
                not mistaken for a slow stage.
        """
        if not self._event_pause_requested.is_set(): return 0.0

        time_start = time.time()
        self._event_scan_parked.set()
        try:
            while self._event_pause_requested.is_set():
                if event_keep_running is not None and not event_keep_running.is_set(): break
                time.sleep(self.POLL_INTERVAL_SEC)
        finally:
            self._event_scan_parked.clear()

        return time.time() - time_start

    # >>> Saver side <<<

    def request_pause(self, timeout_sec:float=120.0) -> bool:
        """
        Asks a running scan to park itself and waits until it has. Always pair it with release().

        Args:
            timeout_sec (float): How long to wait for the scan to reach a checkpoint.

        Returns:
            bool: True if it is safe to write (no scan is running, or the scan is parked). False if
                the scan did not park within the timeout, in which case the pause is still held and
                release() must still be called.
        """
        with self._lock:
            self._num_pause_requests += 1
            self._event_pause_requested.set()

        # Nothing to wait for if no scan is running. Re-checked after the wait below, since the scan
        # may well finish on its own while we are waiting for it to park.
        if not self._event_scan_running.is_set(): return True

        time_deadline = time.time() + max(0.0, timeout_sec)
        while time.time() < time_deadline:
            if self._event_scan_parked.is_set(): return True
            if not self._event_scan_running.is_set(): return True
            time.sleep(self.POLL_INTERVAL_SEC)

        return not self._event_scan_running.is_set() or self._event_scan_parked.is_set()

    def release(self) -> None:
        """
        Releases this saver's claim on the pause. The scan carries on once every claim is released.
        """
        with self._lock:
            self._num_pause_requests = max(0, self._num_pause_requests - 1)
            if self._num_pause_requests == 0: self._event_pause_requested.clear()
