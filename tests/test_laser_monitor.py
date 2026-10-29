"""Background checks never wait on serial I/O in the acquisition caller."""

from concurrent.futures import Future
from dataclasses import replace
import json
from pathlib import Path
import queue
import tempfile
import threading
import time
import unittest

import test_integration_experiment as integration_fixture  # Isolated config imports.
from iris.controllers.laser_controller_toptica import IBeamStatus
from iris.utils.laser_monitor import BackgroundLaserMonitor


class BackgroundMonitorTests(unittest.TestCase):
    baseline = IBeamStatus('test', '1', True, 95., (100., 0.), (True, False))

    def make_monitor(self, power_sweep=False, interval=.01):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        requests = queue.Queue()
        cancel = threading.Event()
        def submit():
            future = Future()
            # Model already-running serial reads: cancel cannot abort them.
            future.set_running_or_notify_cancel()
            requests.put(future)
            return future
        monitor = BackgroundLaserMonitor(submit, self.baseline, cancel, directory.name,
                                         power_sweep=power_sweep, interval_s=interval)
        self.addCleanup(monitor.stop)
        return monitor, requests, cancel, Path(directory.name)

    def wait_until(self, condition):
        deadline = time.monotonic() + 2
        while not condition() and time.monotonic() < deadline:
            time.sleep(.002)
        self.assertTrue(condition())

    def test_pending_read_does_not_delay_exposures_or_monitor_stop(self):
        monitor, requests, _, directory = self.make_monitor()
        monitor.start()
        pending = requests.get(timeout=2)
        completed = threading.Event()
        def acquire():
            for index in range(10):
                self.assertEqual(monitor.acquire(lambda: (index, 'spectrum')), (index, 'spectrum'))
            completed.set()
        worker = threading.Thread(target=acquire)
        worker.start()
        self.assertTrue(completed.wait(1))  # Serial read is deliberately still unfinished.
        worker.join()
        stopped = threading.Event()
        stopper = threading.Thread(target=lambda: (monitor.stop(), stopped.set()))
        stopper.start()
        self.assertTrue(stopped.wait(1))
        stopper.join()
        self.assertFalse(pending.done())
        self.assertTrue(requests.empty())  # At most one outstanding serial read.
        quality = json.loads((directory / 'laser_quality.json').read_text())
        self.assertTrue(quality['pending_read_at_end'])
        self.assertEqual(len(quality['spectra']), 10)
        self.assertEqual({entry['laser_quality'] for entry in quality['spectra']},
                         {'not_observed_during_exposure'})

    def test_good_background_sample_is_attributed_to_exposure(self):
        monitor, requests, cancel, directory = self.make_monitor()
        monitor.start()
        first = requests.get(timeout=2)
        first.set_result(self.baseline)
        self.wait_until(lambda: len(monitor._samples) == 1)
        started, release = threading.Event(), threading.Event()
        def exposure():
            started.set()
            release.wait(2)
            return 42, 'spectrum'
        worker = threading.Thread(target=lambda: monitor.acquire(exposure))
        worker.start()
        self.assertTrue(started.wait(1))
        second = requests.get(timeout=2)
        second.set_result(self.baseline)
        self.wait_until(lambda: len(monitor._samples) >= 2)
        release.set()
        worker.join(2)
        monitor.stop()
        self.assertFalse(cancel.is_set())
        quality = json.loads((directory / 'laser_quality.json').read_text())
        self.assertEqual(quality['spectra'][0]['laser_quality'], 'background_sample_ok')

    def test_emission_failure_keeps_and_flags_in_progress_spectrum(self):
        monitor, requests, cancel, directory = self.make_monitor()
        monitor.start()
        pending = requests.get(timeout=2)
        started, release = threading.Event(), threading.Event()
        results = []
        def exposure():
            started.set()
            release.wait(2)
            return 77, 'retained spectrum'
        worker = threading.Thread(target=lambda: results.append(monitor.acquire(exposure)))
        worker.start()
        self.assertTrue(started.wait(1))
        pending.set_result(replace(self.baseline, enabled=False, output_mw=0.))
        self.assertTrue(cancel.wait(2))
        release.set()
        worker.join(2)
        monitor.stop()
        self.assertEqual(results, [(77, 'retained spectrum')])
        self.assertIn('OFF', monitor.fault)
        quality = json.loads((directory / 'laser_quality.json').read_text())
        self.assertEqual(quality['spectra'][0]['laser_quality'], 'suspect_laser_fault')

    def test_deliberate_power_transition_is_not_reported_as_failure(self):
        monitor, requests, cancel, _ = self.make_monitor(power_sweep=True)
        monitor.stable_at(0.)
        monitor.start()
        pending = requests.get(timeout=2)
        monitor.transition()
        monitor.stable_at(20.)
        pending.set_result(replace(self.baseline, channel_setpoints_mw=(0., 0.), output_mw=0.))
        self.wait_until(lambda: bool(monitor._samples))
        monitor.stop()
        self.assertFalse(cancel.is_set())
        self.assertIsNone(monitor.fault)
        self.assertFalse(monitor._samples[0]['stable'])

    def test_background_serial_failure_requests_stop(self):
        monitor, requests, cancel, _ = self.make_monitor()
        monitor.start()
        requests.get(timeout=2).set_exception(TimeoutError('serial timeout'))
        self.assertTrue(cancel.wait(2))
        monitor.stop()
        self.assertIn('serial timeout', monitor.fault)

    def test_zero_output_and_changed_channel_settings_are_detected(self):
        for status in (replace(self.baseline, output_mw=0.),
                       replace(self.baseline, channel_enabled=(False, False)),
                       replace(self.baseline, channel_setpoints_mw=(20., 0.))):
            with self.subTest(status=status):
                monitor, requests, cancel, _ = self.make_monitor()
                monitor.start()
                requests.get(timeout=2).set_result(status)
                self.assertTrue(cancel.wait(2))
                monitor.stop()
                self.assertIsNotNone(monitor.fault)


if __name__ == '__main__':
    unittest.main()
