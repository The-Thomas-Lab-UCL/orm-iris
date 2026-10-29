"""Background laser observations; acquisition never waits for a monitor read."""

from dataclasses import asdict
import json
from pathlib import Path
import threading
import time


class BackgroundLaserMonitor:
    def __init__(self, submit_read, baseline, cancel, directory, power_sweep=False, interval_s=.5):
        self._submit_read = submit_read
        self._baseline = baseline
        self._cancel = cancel
        self._directory = Path(directory)
        self._power_sweep = power_sweep
        self._interval = interval_s
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._finalized = False
        self._pending = None
        self._generation = 0
        self._stable = not power_sweep
        self._expected_power = None
        self._fault = None
        self._samples = []
        self._exposures = []
        self._unwritten_exposures = []

    @property
    def fault(self):
        with self._lock:
            return self._fault

    def start(self):
        self._thread = threading.Thread(target=self._run, name='laser-monitor', daemon=True)
        self._thread.start()

    def transition(self):
        """Exclude deliberate power switching from stability checks."""
        with self._lock:
            self._generation += 1
            self._stable = False
            pending = self._pending
        if pending is not None:
            pending.cancel()  # Cancel queued work only; never interrupt serial I/O.

    def stable_at(self, power):
        with self._lock:
            self._expected_power = power
            self._stable = True

    def acquire(self, operation):
        """Record the software acquisition window without a serial query or wait."""
        start = time.monotonic()
        start_us = time.time_ns() // 1000
        result = operation()
        entry = dict(timestamp=result[0], acquisition_call_start_s=start,
                     acquisition_call_end_s=time.monotonic(), acquisition_call_start_us=start_us,
                     acquisition_call_end_us=time.time_ns() // 1000)
        with self._lock:
            self._exposures.append(entry)
            self._unwritten_exposures.append(entry)
        return result

    def _problem(self, status, stable, expected_power):
        if not status.enabled:
            return 'Laser emission reported OFF.'
        if not stable:
            return None
        if self._power_sweep:
            if not status.channel_enabled or not status.channel_enabled[0]:
                return 'Laser channel 1 reported OFF.'
            if not status.channel_setpoints_mw or abs(status.channel_setpoints_mw[0] - expected_power) > .00051:
                return 'Laser channel 1 setpoint changed.'
            light_expected = expected_power > 0
        else:
            if (status.channel_enabled != self._baseline.channel_enabled or
                    status.channel_setpoints_mw != self._baseline.channel_setpoints_mw):
                return 'Laser channel settings changed during the integration-time experiment.'
            light_expected = any(enabled and power > 0 for enabled, power in
                                 zip(status.channel_enabled, status.channel_setpoints_mw))
            if not light_expected:
                return 'No enabled laser channel has a positive power setpoint.'
        if light_expected and status.output_mw <= 0:
            return 'Laser output readback is zero while illumination is expected.'
        return None

    def _set_fault(self, reason):
        with self._lock:
            if self._fault is None:
                self._fault = reason
        self._cancel.set()

    def _write(self, record):
        with (self._directory / 'laser_monitor.jsonl').open('a', encoding='utf-8') as output:
            output.write(json.dumps(record) + '\n')

    def _flush_exposures(self):
        with self._lock:
            entries, self._unwritten_exposures = self._unwritten_exposures, []
        for entry in entries:
            self._write(dict(kind='acquisition_window', **entry))

    def _run(self):
        next_read = time.monotonic()
        request = None
        try:
            while not self._stop.is_set():
                self._flush_exposures()
                with self._lock:
                    pending = self._pending
                    generation, stable, power = self._generation, self._stable, self._expected_power
                if pending is not None and pending.done():
                    if not pending.cancelled():
                        sample = dict(kind='status', query_start_s=request[0], query_end_s=time.monotonic(),
                                      observed_at_us=time.time_ns() // 1000)
                        try:
                            status = pending.result()  # Only consume a finished Future.
                            with self._lock:
                                same_phase = request[1] == self._generation
                                sample.update(status=asdict(status), stable=same_phase and request[2])
                                sample['problem'] = self._problem(status, sample['stable'], request[3])
                        except Exception as error:
                            sample.update(problem=f'Laser status read failed: {error}', stable=False)
                        with self._lock:
                            self._samples.append(sample)
                        self._write(sample)
                        if sample['problem']:
                            self._set_fault(sample['problem'])
                            break
                    with self._lock:
                        self._pending = None
                    next_read = time.monotonic() + self._interval
                elif pending is None and stable and time.monotonic() >= next_read:
                    request = (time.monotonic(), generation, stable, power)
                    future = self._submit_read()
                    with self._lock:
                        self._pending = future
                    if future is None:
                        next_read = time.monotonic() + self._interval
                self._stop.wait(.02)
        except Exception as error:
            self._set_fault(f'Laser monitoring failed: {error}')
        finally:
            try:
                self._flush_exposures()
            except Exception as error:
                self._set_fault(f'Laser monitor log could not be saved: {error}')

    def stop(self):
        if self._finalized:
            return
        self._stop.set()
        with self._lock:
            pending = self._pending
        if pending is not None:
            pending.cancel()
        if self._thread is not None:
            self._thread.join()  # Does not wait for an unfinished serial Future.
        self._flush_exposures()
        with self._lock:
            samples, exposures = list(self._samples), list(self._exposures)
        quality = []
        for entry in exposures:
            overlapping = [sample for sample in samples if
                           sample['query_start_s'] <= entry['acquisition_call_end_s'] and
                           sample['query_end_s'] >= entry['acquisition_call_start_s']]
            if any(sample['problem'] for sample in overlapping):
                flag = 'suspect_laser_fault'
            elif any(sample.get('stable') and
                     entry['acquisition_call_start_s'] <= sample['query_start_s'] and
                     sample['query_end_s'] <= entry['acquisition_call_end_s'] for sample in overlapping):
                flag = 'background_sample_ok'
            else:
                flag = 'not_observed_during_exposure'
            quality.append(dict(entry, laser_quality=flag))
        with (self._directory / 'laser_quality.json').open('w', encoding='utf-8') as output:
            json.dump(dict(mode='background; not strict before/after verification',
                           fault=self.fault, pending_read_at_end=pending is not None and not pending.done(),
                           spectra=quality), output, indent=2)
        self._finalized = True
