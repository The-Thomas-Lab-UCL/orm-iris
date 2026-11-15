"""Display backpressure must not block acquisition or change stored spectra."""
import queue
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_single_acquisition as single_fixture
import test_integration_experiment as fixture
from iris.utils.live_spectrum import LatestSpectrum


class LiveSpectrumTests(unittest.TestCase):
    def test_mailbox_coalesces_and_limits_submission_to_once_per_second(self):
        clock = SimpleNamespace(value=0.)
        mailbox = LatestSpectrum(clock=lambda: clock.value)
        mailbox.offer('first')
        self.assertEqual(mailbox.take(), 'first')
        mailbox.offer('older')
        mailbox.offer('newest')
        clock.value = .99
        self.assertIsNone(mailbox.take())
        clock.value = 1.
        self.assertEqual(mailbox.take(), 'newest')
        self.assertIsNone(mailbox.take())

    def test_blocked_renderer_does_not_block_measurements_or_return_wrong_data(self):
        owner = single_fixture.SingleAcquisitionTests()
        frame = owner.frame(count=1)
        started, release = threading.Event(), threading.Event()
        def blocked_plot(**kwargs):
            started.set()
            release.wait(3)
        frame.Plot_rawlist_RM.side_effect = blocked_plot
        frame.AnalyseAndPlot_rawlist.side_effect = blocked_plot
        existing_render = threading.Thread(target=blocked_plot)
        existing_render.start()
        self.assertTrue(started.wait(1))
        measurements = []
        try:
            for _ in range(3):
                response = queue.Queue()
                worker = frame.perform_single_measurement_manual(widget_override=True, queue_response=response)
                worker.join(1)
                self.assertFalse(worker.is_alive())
                completion, measurement = response.get_nowait()
                self.assertIs(completion, worker)
                self.assertEqual(measurement.get_metadata()['accumulation'], 1)
                measurements.append(measurement)
                self.assertEqual(worker.acquisition_timing['final_plot_ms'], 0)
            self.assertEqual(len({id(measurement) for measurement in measurements}), 3)
            self.assertEqual(len({measurement.get_latest_timestamp() for measurement in measurements}), 3)
            self.assertIs(frame._live_spectra.take(), measurements[-1])
            frame.Plot_rawlist_RM.assert_not_called()
            frame.AnalyseAndPlot_rawlist.assert_not_called()
        finally:
            release.set()
            existing_render.join(3)
            owner.doCleanups()

    def test_tk_poller_leaves_pending_measurement_until_renderer_finishes(self):
        mailbox = LatestSpectrum()
        mailbox.offer('latest')
        callbacks = []
        frame = SimpleNamespace(_live_spectra=mailbox, _experiment_plot_results=['busy'],
                                after=lambda delay, callback: callbacks.append(callback),
                                display_experiment_spectrum=Mock())
        frame._poll_live_spectra = fixture.Frm_RamanSpectrometerController._poll_live_spectra.__get__(frame)
        frame._poll_live_spectra()
        frame.display_experiment_spectrum.assert_not_called()
        frame._experiment_plot_results = None
        callbacks.pop(0)()
        frame.display_experiment_spectrum.assert_called_once_with('latest', store=False)

    def test_rendering_an_old_frame_does_not_replace_current_single_measurement(self):
        frame, _, _ = fixture.SpectrumDisplayTests().make_display(raw_only=True)
        current = object()
        frame._sgl_measurement = current
        measurement = fixture.SpectrumDisplayTests().measurement(100.)
        frame.display_experiment_spectrum(measurement, store=False)
        self.assertIs(frame._sgl_measurement, current)

    def test_inflight_averaged_plot_is_discarded_when_raw_only_becomes_checked(self):
        frame, results, callbacks = fixture.SpectrumDisplayTests().make_display(raw_only=False)
        frame.display_experiment_spectrum(fixture.SpectrumDisplayTests().measurement(100.))
        for result in results:
            result.ready.return_value = True
        frame._bool_PlotRawOnly = SimpleNamespace(get=lambda: True)
        callbacks.pop(0)()
        self.assertTrue(frame._queue_plot_display.empty())
        self.assertEqual(len(results), 3)  # Two discarded panels, one new raw panel.
        results[-1].ready.return_value = True
        callbacks.pop(0)()
        self.assertEqual(frame._queue_plot_display.get_nowait().shape, (10, 20, 3))


if __name__ == '__main__':
    unittest.main()
