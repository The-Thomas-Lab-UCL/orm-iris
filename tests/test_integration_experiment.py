"""Hardware-free experiment checks. Run with unittest discover -s tests."""

import os
import json
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

# IRIS imports read/create config.ini. Isolate those side effects from the lab's
# real configuration and never instantiate controller_app or hardware drivers.
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
os.environ.setdefault('MPLBACKEND', 'Agg')
with tempfile.TemporaryDirectory() as isolated:
    original_directory = Path.cwd()
    try:
        os.chdir(isolated)
        import dill
        import numpy as np
        import pandas as pd
        from iris import DataAnalysisConfigEnum
        from iris.data.measurement_RamanMap import MeaRMap_Unit, MeaRMap_Hub, MeaRMap_Handler
        import iris.gui.hilvl_Raman as raman_gui
        from iris.gui.hilvl_Raman import Frm_HighLvlController_Raman
        from iris.gui.raman import Frm_RamanSpectrometerController
        from iris.gui.motion_video import Frm_MotionController
        from iris.controllers.raman_spectrometer_controller_dummy import SpectrometerController_Dummy
        from iris.utils.experiment_naming import build_integration_map_names
        from iris.utils.integration_experiment import validate_experiment_settings, run_pointwise_experiment
    finally:
        os.chdir(original_directory)


class SimulatedCancel:
    """Record waits without real delays, optionally stop during a chosen wait."""
    def __init__(self, stop_wait=None):
        self.stopped = False
        self.waits = []
        self.stop_wait = stop_wait

    def is_set(self):
        return self.stopped

    def set(self):
        self.stopped = True

    def clear(self):
        self.stopped = False

    def wait(self, seconds):
        self.waits.append(seconds)
        if len(self.waits) == self.stop_wait:
            self.set()
        return self.stopped


class SimulatedSpectrometer:
    def __init__(self):
        self.integration_us = 250000
        self.calls = []
        self.timestamp = 1000
        self.fail_time = None

    def set_integration_time_us(self, value):
        self.integration_us = value
        self.calls.append(value)
        return value

    def get_single_measurement(self):
        if self.integration_us == self.fail_time:
            raise RuntimeError('Simulated spectrometer failure')
        self.timestamp += 1
        return self.timestamp, pd.DataFrame({DataAnalysisConfigEnum.WAVELENGTH_LABEL.value: [500., 600.],
                                            DataAnalysisConfigEnum.INTENSITY_LABEL.value: [10., 20.]}), self.integration_us / 1000


def raman_frame(device):
    frame = SimpleNamespace(_controller=device, _ramanHub=device,
                            _laserpower_mW=10., _laserwavelength_nm=785.)
    frame.acquire_experiment_spectrum = lambda value, **kwargs: Frm_RamanSpectrometerController.acquire_experiment_spectrum(frame, value, **kwargs)
    return frame


class ValidationTests(unittest.TestCase):
    def test_valid_order_and_limits(self):
        self.assertEqual(validate_experiment_settings('500, 100, 100', '2.5', (1000, 1000000, 1000)),
                         ((500., 100., 100.), 2.5))

    def test_invalid_settings(self):
        for times, delay in [('', '0'), ('100,', '0'), ('NaN', '0'), ('0', '0'),
                             ('1001', '0'), ('0.5', '0'), ('1.0005', '0'),
                             ('100', '-1'), ('100', 'inf'), ('100', 'bad')]:
            with self.subTest(times=times, delay=delay), self.assertRaises(ValueError):
                validate_experiment_settings(times, delay, (1000, 1000000, 1000))

    def test_names_and_collisions(self):
        self.assertEqual(build_integration_map_names(' sample ', '100, 100.0, 0.5'),
                         ['sample_100ms', 'sample_100ms_repeat2', 'sample_0.5ms'])
        self.assertEqual(build_integration_map_names('sample', '100', ['SAMPLE_100MS']),
                         ['sample_1_100ms'])
        for name in ('', '../sample', 'sample:', 'sample.'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                build_integration_map_names(name, '100')


class SchedulingTests(unittest.TestCase):
    coordinates = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.)]

    def run_scan(self, cancel, acquire=None, direction='x-direction'):
        self.events = []
        self.saved = []
        self.checkpoints = []
        def measure(value):
            self.events.append(('expose', value))
            return acquire(value) if acquire else value
        return run_pointwise_experiment(
            self.coordinates, (100., 500.), 2000., direction, cancel,
            lambda coordinate: self.events.append(('move', coordinate)), measure,
            lambda *values: self.saved.append(values), lambda text: None,
            lambda: self.checkpoints.append(list(self.saved)))

    def test_point_first_order_and_waits(self):
        cancel = SimulatedCancel()
        self.assertEqual(self.run_scan(cancel), 3)
        self.assertEqual([event[0] for event in self.events], ['move', 'expose', 'expose'] * 3)
        self.assertEqual([item[0] for item in self.saved], [0, 1] * 3)
        self.assertEqual(cancel.waits, [0.75, 2., 0.2, 2., 0.75, 2.])

    def test_y_scan_settling(self):
        cancel = SimulatedCancel()
        self.run_scan(cancel, direction='y-direction')
        self.assertEqual(cancel.waits, [0.75, 2., 0.75, 2., 0.75, 2.])

    def test_stop_during_bleaching(self):
        self.assertEqual(self.run_scan(SimulatedCancel(stop_wait=2)), 0)
        self.assertEqual(self.saved, [])
        self.assertEqual(len(self.events), 1)

    def test_stop_during_exposure_retains_it(self):
        cancel = SimulatedCancel()
        def acquire(value):
            cancel.set()
            return value
        self.assertEqual(self.run_scan(cancel, acquire), 0)
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(len(self.checkpoints[-1]), 1)

    def test_failure_retains_partial_point(self):
        def acquire(value):
            if value == 500:
                raise RuntimeError('device error')
            return value
        with self.assertRaisesRegex(RuntimeError, 'device error'):
            self.run_scan(SimulatedCancel(), acquire)
        self.assertEqual(len(self.checkpoints[-1]), 1)

    def test_pre_cancelled_does_not_move(self):
        cancel = SimulatedCancel()
        cancel.set()
        self.assertEqual(self.run_scan(cancel), 0)
        self.assertEqual(self.events, [])


class StorageAndWorkerTests(unittest.TestCase):
    def test_one_exposure_and_independent_metadata(self):
        device = SimulatedSpectrometer()
        frame = raman_frame(device)
        units = [MeaRMap_Unit(name) for name in build_integration_map_names('sample', '100,500')]
        for coordinate in [(0., 0., 0.), (1., 0., 0.)]:
            for time_ms, unit in zip((100., 500.), units):
                timestamp, measurement = frame.acquire_experiment_spectrum(time_ms)
                unit.append_ramanmeasurement_data(timestamp, coordinate, measurement)
        self.assertEqual(device.calls, [100000, 500000] * 2)
        for time_ms, unit in zip((100., 500.), units):
            self.assertEqual(unit.get_numMeasurements(), 2)
            self.assertEqual(unit.get_dict_measurement_metadata()['integration_time_ms'], time_ms)
            self.assertEqual(unit.get_dict_measurement_metadata()['accumulation'], 1)

    def test_device_rounding_rejected(self):
        device = SimulatedSpectrometer()
        device.set_integration_time_us = lambda value: value + 1000
        with self.assertRaises(ValueError):
            raman_frame(device).acquire_experiment_spectrum(100.)

    def run_worker(self, failure=False, stop_on_first=False):
        device = SimulatedSpectrometer()
        if failure:
            device.fail_time = 500000
        raman = raman_frame(device)
        auto_calls = []
        raman.pause_auto_measurement = lambda: auto_calls.append('pause')
        raman.resume_auto_measurement = lambda: auto_calls.append('resume')
        with tempfile.TemporaryDirectory() as recovery_dir:
            cancel = SimulatedCancel()
            frame = SimpleNamespace(raman_controller=raman, _experiment_events=queue.Queue(),
                                    _experiment_cancel=cancel, _experiment_recovery_dir=recovery_dir,
                                    motion_controller=SimpleNamespace(move_for_experiment=lambda coordinate: None))
            units = [MeaRMap_Unit('sample_100ms'), MeaRMap_Unit('sample_500ms')]
            plan = dict(coordinates=[(0., 0., 0.), (1., 0., 0.)], integration_times_ms=(100., 500.),
                        photobleach_delay_ms=0., scan_direction='x-direction')
            worker = threading.Thread(target=Frm_HighLvlController_Raman._run_integration_experiment,
                                      args=(frame, plan, units, 250000, True))
            worker.start()
            finished = None
            try:
                while finished is None:
                    kind, payload = frame._experiment_events.get(timeout=10)
                    if kind == 'measurement':
                        unit, coordinate, result, reply = payload
                        timestamp, measurement = result
                        try:
                            unit.append_ramanmeasurement_data(timestamp, coordinate, measurement)
                            if stop_on_first:
                                cancel.set()
                        except Exception as error:
                            reply.put(error)
                        else:
                            reply.put(None)
                    elif kind == 'finished':
                        finished = payload
            finally:
                worker.join(timeout=10)
            self.assertFalse(worker.is_alive())
            self.assertEqual(device.integration_us, 250000)
            self.assertEqual(auto_calls, ['pause', 'resume'])
            with open(Path(recovery_dir) / 'maps.pkl', 'rb') as source:
                recovered = dill.load(source)
            return finished, recovered

    def test_worker_recovery_roundtrip(self):
        finished, recovered = self.run_worker()
        self.assertEqual(finished, (2, 2, None))
        for name, value in [('sample_100ms', 100.), ('sample_500ms', 500.)]:
            unit = recovered.get_MappingUnit(unit_name=name)
            self.assertEqual(unit.get_numMeasurements(), 2)
            self.assertEqual(unit.get_dict_measurement_metadata()['integration_time_ms'], value)

    def test_worker_failure_and_stop_recovery(self):
        for failure, stop in [(True, False), (False, True)]:
            with self.subTest(failure=failure, stop=stop):
                finished, recovered = self.run_worker(failure, stop)
                self.assertEqual(finished[:2], (0, 2))
                self.assertEqual(bool(finished[2]), failure)
                self.assertEqual(recovered.get_MappingUnit(unit_name='sample_100ms').get_numMeasurements(), 1)
                self.assertEqual(recovered.get_list_MappingUnit_names(), ['sample_100ms'])

    def test_motion_driver_failure_propagates(self):
        def fail(coordinate):
            raise RuntimeError('stage disconnected')
        motion = SimpleNamespace(ctrl_xy=SimpleNamespace(move_direct=fail),
                                 ctrl_z=SimpleNamespace(move_direct=lambda coordinate: None))
        with self.assertRaisesRegex(RuntimeError, 'stage disconnected'):
            motion._check_mapping_motion_idle = lambda: Frm_MotionController._check_mapping_motion_idle(motion)
            Frm_MotionController.move_for_experiment(motion, (0., 0., 0.))


class SpectrumDisplayTests(unittest.TestCase):
    def make_display(self, raw_only=False):
        callbacks = []
        results = []
        def submit(function, kwds):
            result = Mock()
            result.ready.return_value = False
            result.get.return_value = np.zeros((10, 20, 3), dtype=np.uint8)
            results.append(result)
            return result
        frame = SimpleNamespace(
            _bool_PlotRawOnly=SimpleNamespace(get=lambda: raw_only),
            _bool_PlotRamanShift=SimpleNamespace(get=lambda: True),
            _img_size=(400, 400), _get_plot_limits=lambda: (None, None, None, None),
            _plotter=SimpleNamespace(plot_RamanMeasurement=Mock()),
            _processor=SimpleNamespace(apply_async=Mock(side_effect=submit)),
            _queue_plot_display=queue.Queue(), after=lambda delay, callback: callbacks.append(callback))
        for name in ('display_experiment_spectrum', '_start_experiment_spectrum_plot',
                     '_poll_experiment_spectrum_plot'):
            setattr(frame, name, getattr(Frm_RamanSpectrometerController, name).__get__(frame))
        return frame, results, callbacks

    def measurement(self, time_ms):
        return raman_frame(SimulatedSpectrometer()).acquire_experiment_spectrum(time_ms)[1]

    def test_raw_and_combined_display(self):
        for raw_only in (True, False):
            with self.subTest(raw_only=raw_only):
                frame, results, callbacks = self.make_display(raw_only)
                frame.display_experiment_spectrum(self.measurement(100.))
                self.assertEqual(len(results), 1 if raw_only else 2)
                self.assertTrue(frame._queue_plot_display.empty())
                for result in results:
                    result.ready.return_value = True
                callbacks.pop(0)()
                image = frame._queue_plot_display.get_nowait()
                self.assertEqual(image.shape, (10 if raw_only else 20, 20, 3))
                options = frame._processor.apply_async.call_args_list[0].kwargs['kwds']
                self.assertIn('100 ms', options['title'])
                self.assertTrue(options['flg_plot_ramanshift'])
                self.assertEqual(frame._last_plotter_input['type'], 'raw' if raw_only else 'avg')

    def test_slow_plotter_keeps_latest_pending_spectrum(self):
        frame, results, callbacks = self.make_display(raw_only=True)
        frame.display_experiment_spectrum(self.measurement(100.))
        frame.display_experiment_spectrum(self.measurement(500.))
        frame.display_experiment_spectrum(self.measurement(1000.))
        self.assertEqual(len(results), 1)
        callbacks.pop(0)()  # Incomplete rendering does not block the Tk thread.
        self.assertTrue(frame._queue_plot_display.empty())
        results[0].ready.return_value = True
        callbacks.pop(0)()
        self.assertEqual(len(results), 2)
        self.assertIn('1000 ms', frame._processor.apply_async.call_args.kwargs['kwds']['title'])
        results[1].ready.return_value = True
        callbacks.pop(0)()
        self.assertIsNone(frame._experiment_plot_results)
        self.assertEqual(frame._queue_plot_display.qsize(), 2)

    def test_render_failure_is_reported_and_clears_pending_work(self):
        frame, results, callbacks = self.make_display(raw_only=True)
        frame.display_experiment_spectrum(self.measurement(100.))
        results[0].ready.return_value = True
        results[0].get.side_effect = RuntimeError('plot failed')
        with patch('builtins.print') as report:
            callbacks.pop(0)()
        report.assert_called_once()
        self.assertIsNone(frame._experiment_plot_results)


class DummyWidget:
    def __init__(self, **values):
        self.values = values

    def cget(self, key):
        return self.values.get(key, 'normal')

    def configure(self, **values):
        self.values.update(values)


class UIFlowTests(unittest.TestCase):
    def make_frame(self):
        device = SpectrometerController_Dummy()
        raman = raman_frame(device)
        # Use the repository's actual dummy spectrum generator in this flow.
        def single_measurement():
            spectrum, timestamp, int_us = device.measure_spectrum()
            return timestamp, spectrum, int_us / 1000
        raman._ramanHub = SimpleNamespace(get_single_measurement=single_measurement)
        raman._flg_isrunning = threading.Event()
        raman.get_running_status = raman._flg_isrunning.is_set
        raman.get_experiment_integration_limits_us = device.get_integration_time_limits_us
        raman.pause_auto_measurement = lambda: None
        raman.resume_auto_measurement = lambda: None
        raman.display_experiment_spectrum = Mock()
        values = lambda value: SimpleNamespace(get=lambda: value)
        hub = MeaRMap_Hub()
        coordinates = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.), (1., 1., 0.)]
        selected = [SimpleNamespace(mappingUnit_name='region', mapping_coordinates=coordinates)]
        moves = []
        callbacks = []
        frame = SimpleNamespace(
            _experiment_thread=None, _experiment_cancel=SimulatedCancel(),
            _list_shortcut_widgets=[], _btn_perform_discreetMapping_multi=DummyWidget(text='Run'),
            _btn_perform_continuousMapping_multi=DummyWidget(text='Run'),
            _btn_experiment_discreet_mapping=DummyWidget(),
            _frm_coorHub_treeview=SimpleNamespace(get_selected_mappingCoor=lambda **kwargs: selected),
            _str_experiment_integration_times_ms=values('100,500'),
            _str_experiment_photobleach_delay_ms=values('250'),
            _str_experiment_scanMethod=values('snake'), _str_experiment_scanDir=values('y-direction'),
            _dataHub_map=SimpleNamespace(get_MappingHub=lambda: hub, update_tree=lambda: None),
            raman_controller=raman, _ramanHub=SimpleNamespace(isrunning_auto_measurement=lambda: False),
            motion_controller=SimpleNamespace(move_for_experiment=lambda coor: moves.append(coor)),
            statbar=DummyWidget(), bg_colour='grey', after=lambda delay, callback: callbacks.append(callback),
            _lock_experiment_controls=lambda: None)
        for name in ('start_integration_experiment', 'stop_integration_experiment', '_get_experiment_map_names',
                     '_convertCoor_byScanOptions', '_run_integration_experiment',
                     '_poll_integration_experiment', '_restore_experiment_controls'):
            setattr(frame, name, getattr(Frm_HighLvlController_Raman, name).__get__(frame))
        return frame, hub, moves, callbacks, selected

    def test_start_poll_finish_with_actual_dummy_spectra(self):
        frame, hub, moves, callbacks, _ = self.make_frame()
        original_us = frame.raman_controller._controller.get_integration_time_us()
        with tempfile.TemporaryDirectory() as autosave, \
                patch.object(raman_gui, 'SaveParamsEnum', SimpleNamespace(AUTOSAVE_PATH=SimpleNamespace(value=autosave))), \
                patch.object(raman_gui.messagebox, 'showinfo') as showinfo, \
                patch.object(raman_gui.messagebox, 'showerror') as showerror:
            frame.start_integration_experiment()
            deadline = time.monotonic() + 15
            while frame._experiment_thread is not None and time.monotonic() < deadline:
                pending, callbacks[:] = callbacks[:], []
                for callback in pending:
                    callback()
                time.sleep(0.001)
            self.assertIsNone(frame._experiment_thread)
            showerror.assert_not_called()
            showinfo.assert_called_once()
            self.assertEqual(moves, [(0., 0., 0.), (0., 1., 0.), (1., 1., 0.), (1., 0., 0.)])
            self.assertEqual(frame.raman_controller._controller.get_integration_time_us(), original_us)
            self.assertFalse(frame.raman_controller.get_running_status())
            self.assertFalse(frame.motion_controller._integration_experiment_running)
            self.assertEqual(frame._btn_experiment_discreet_mapping.cget('state'), 'normal')
            self.assertEqual(hub.get_list_MappingUnit_names(), ['region_100ms', 'region_500ms'])
            self.assertEqual(frame.raman_controller.display_experiment_spectrum.call_count, 8)
            self.assertEqual(frame._experiment_cancel.waits, [0.75, 0.25, 0.2, 0.25, 0.75, 0.25, 0.2, 0.25])
            settings = json.loads((Path(frame._experiment_recovery_dir) / 'settings.json').read_text())
            self.assertEqual(settings['photobleach_delay_ms'], 250.)
            self.assertEqual(settings['coordinate_set'], 'region')
            self.assertEqual(settings['map_names'], ['region_100ms', 'region_500ms'])
            self.assertNotIn('experiment_name', settings)
            self.assertNotIn('photobleach_delay_s', settings)
            recovery_path = Path(frame._experiment_recovery_dir) / 'maps.pkl'
            loaded = MeaRMap_Hub()
            MeaRMap_Handler().load_MappingMeasurement_pickle(loaded, str(recovery_path))
            for name in hub.get_list_MappingUnit_names():
                self.assertEqual(hub.get_MappingUnit(unit_name=name).get_numMeasurements(), 4)
                self.assertEqual(loaded.get_MappingUnit(unit_name=name).get_numMeasurements(), 4)

    def test_names_follow_current_coordinate_selection(self):
        frame, _, _, _, selected = self.make_frame()
        self.assertEqual(frame._get_experiment_map_names(), ['region_100ms', 'region_500ms'])
        selected[0].mappingUnit_name = 'tissue_02'
        self.assertEqual(frame._get_experiment_map_names(), ['tissue_02_100ms', 'tissue_02_500ms'])
        selected.clear()
        with self.assertRaisesRegex(ValueError, 'Select exactly one'):
            frame._get_experiment_map_names()

    def test_coordinate_name_collision_creates_numbered_run(self):
        frame, hub, moves, callbacks, _ = self.make_frame()
        original = MeaRMap_Unit('region_100ms')
        hub.append_mapping_unit(original)
        with tempfile.TemporaryDirectory() as autosave, \
                patch.object(raman_gui, 'SaveParamsEnum', SimpleNamespace(AUTOSAVE_PATH=SimpleNamespace(value=autosave))), \
                patch.object(raman_gui.messagebox, 'showinfo'), \
                patch.object(raman_gui.messagebox, 'showerror') as showerror:
            frame.start_integration_experiment()
            deadline = time.monotonic() + 15
            while frame._experiment_thread is not None and time.monotonic() < deadline:
                pending, callbacks[:] = callbacks[:], []
                for callback in pending:
                    callback()
                time.sleep(.001)
            showerror.assert_not_called()
            settings = json.loads((Path(frame._experiment_recovery_dir) / 'settings.json').read_text())
            self.assertEqual(settings['coordinate_set'], 'region')
            self.assertEqual(settings['run_name'], 'region_1')
        self.assertIsNone(frame._experiment_thread)
        self.assertEqual(hub.get_list_MappingUnit_names(), ['region_100ms', 'region_1_100ms', 'region_1_500ms'])
        self.assertIs(hub.get_MappingUnit(unit_name='region_100ms'), original)
        self.assertEqual(original.get_numMeasurements(), 0)
        self.assertEqual(hub.get_MappingUnit(unit_name='region_1_100ms').get_numMeasurements(), 4)

    def test_invalid_selection_starts_no_worker_or_map(self):
        frame, hub, moves, callbacks, selected = self.make_frame()
        selected.clear()
        with patch.object(raman_gui.messagebox, 'showerror') as showerror:
            frame.start_integration_experiment()
        showerror.assert_called_once()
        self.assertIsNone(frame._experiment_thread)
        self.assertEqual(hub.get_list_MappingUnit_names(), [])
        self.assertEqual(moves, [])
        self.assertEqual(callbacks, [])


if __name__ == '__main__':
    unittest.main()
