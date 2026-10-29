"""Bounded progress waits for the legacy mapping UI; no device or Tk imports."""

import math
import queue
import time


def wait_for_motion(threads, failures, position, timeout, *, clock=time.monotonic):
    """Propagate worker errors and time out only when telemetry stops changing.

    Mirrors upstream 26a8fa4's progress-based stall timeout. A timeout does not
    terminate a driver call; the caller must keep its outstanding workers guarded.
    """
    last = tuple(position())
    last_progress = clock()
    while True:
        try:
            raise failures.get_nowait()
        except queue.Empty:
            pass
        if not any(thread.is_alive() for thread in threads):
            # Workers publish errors before exiting.
            try:
                raise failures.get_nowait()
            except queue.Empty:
                return
        current = tuple(position())
        if not all(math.isfinite(value) for value in current):
            raise RuntimeError('Stage reported invalid coordinates.')
        if any(abs(a - b) > 0.001 for a, b in zip(last, current)):
            last_progress = clock()
            last = current
        if clock() - last_progress >= timeout:
            raise TimeoutError(f'Stage position stopped changing for {timeout:g} seconds. '
                               'No further scan moves will be issued.')
        for thread in threads:
            thread.join(timeout=0.05)


def wait_for_buffer(buffer, consumer, running, *, timeout=15.0, clock=time.monotonic):
    """Wait for a backed-up saver without silently restarting or losing its queue."""
    previous = buffer.qsize()
    last_progress = clock()
    while not buffer.empty():
        if not running():
            return False
        if not consumer.is_alive():
            raise RuntimeError('Mapping data saver stopped before its buffer was drained.')
        size = buffer.qsize()
        if size < previous:
            last_progress = clock()
            previous = size
        if clock() - last_progress >= timeout:
            raise TimeoutError('Mapping data saver made no progress; stopping the scan with partial data retained.')
        consumer.join(timeout=0.05)
    return True
