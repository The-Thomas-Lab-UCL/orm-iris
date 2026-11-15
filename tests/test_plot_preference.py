"""Raw-only preference is respected by final renders and in-flight plot updates."""
import queue
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_integration_experiment as fixture
import test_single_acquisition as single_fixture
import numpy as np


class PlotPreferenceTests(unittest.TestCase):
    def plotting(self, frame=None, raw_only=True, switch_during_average=False):
        frame = frame or SimpleNamespace()
        state = SimpleNamespace(value=raw_only)
        frame._bool_PlotRawOnly = SimpleNamespace(get=lambda: state.value)
        frame._img_size = (20, 10)
        frame._get_plot_limits = lambda: (None, None, None, None)
        frame._last_plotter_input = {}
        frame._queue_plot_display = queue.Queue()
        frame._plotter = SimpleNamespace(plot_RamanMeasurement=Mock())
        calls = []
        def submit(func, args=(), kwds=None):
            if func == frame._plotter.plot_RamanMeasurement:
                calls.append(kwds.copy())
                image = np.full((kwds['plt_size'][1], kwds['plt_size'][0], 3),
                                1 if kwds['plot_raw'] else 2, dtype=np.uint8)
                def result():
                    if switch_during_average and not kwds['plot_raw']:
                        state.value = True
                    return image
                return SimpleNamespace(get=result)
            return SimpleNamespace(get=lambda: func(*args))
        frame._processor = SimpleNamespace(apply_async=submit)
        for method in ('AnalyseAndPlot_rawlist', 'Plot_rawlist_RM', '_force_update_plot'):
            setattr(frame, method, getattr(fixture.Frm_RamanSpectrometerController, method).__get__(frame))
        return frame, state, calls

    def measurement(self):
        return fixture.raman_frame(fixture.SimulatedSpectrometer()).acquire_experiment_spectrum(100.)[1]

    def test_checked_preference_prevents_combined_final_plot(self):
        frame, _, calls = self.plotting()
        measurement = self.measurement()
        frame.AnalyseAndPlot_rawlist(measurement, measurement.get_raw_list(), 0)
        image = frame._queue_plot_display.get_nowait()
        self.assertEqual(image.shape, (10, 20, 3))
        self.assertTrue(np.all(image == 1))
        self.assertEqual([call['plot_raw'] for call in calls], [True])
        self.assertEqual(frame._last_plotter_input['type'], 'raw')

    def test_unchecked_preference_keeps_combined_display(self):
        frame, _, _ = self.plotting(raw_only=False)
        measurement = self.measurement()
        frame.AnalyseAndPlot_rawlist(measurement, measurement.get_raw_list(), 0)
        image = frame._queue_plot_display.get_nowait()
        self.assertEqual(image.shape, (10, 20, 3))
        self.assertTrue(np.all(image[:5] == 1))
        self.assertTrue(np.all(image[5:] == 2))

    def test_checkbox_change_during_render_discards_average(self):
        frame, _, _ = self.plotting(raw_only=False, switch_during_average=True)
        measurement = self.measurement()
        frame.AnalyseAndPlot_rawlist(measurement, measurement.get_raw_list(), 0)
        self.assertTrue(np.all(frame._queue_plot_display.get_nowait() == 1))
        self.assertTrue(frame._queue_plot_display.empty())

    def test_refresh_uses_current_checkbox_instead_of_previous_plot_type(self):
        frame, state, calls = self.plotting(raw_only=False)
        measurement = self.measurement()
        frame.AnalyseAndPlot_rawlist(measurement, measurement.get_raw_list(), 0)
        frame._queue_plot_display.get_nowait()
        state.value = True
        frame._force_update_plot()
        self.assertTrue(np.all(frame._queue_plot_display.get_nowait() == 1))
        self.assertTrue(calls[-1]['plot_raw'])
        state.value = False
        frame._force_update_plot()
        combined = frame._queue_plot_display.get_nowait()
        self.assertTrue(np.all(combined[5:] == 2))

    def test_actual_acquisition_keeps_raw_display_for_progress_and_completion(self):
        owner = single_fixture.SingleAcquisitionTests()
        frame, _, _ = self.plotting(owner.frame(count=2))
        try:
            worker = frame.perform_single_measurement()
            worker.join(3)
            self.assertFalse(worker.is_alive())
            images = list(frame._queue_plot_display.queue)
            self.assertGreaterEqual(len(images), 2)
            self.assertTrue(all(image.shape == (10, 20, 3) and np.all(image == 1) for image in images))
            self.assertEqual(frame._sgl_measurement.get_metadata()['accumulation'], 2)
        finally:
            owner.doCleanups()


if __name__ == '__main__':
    unittest.main()
