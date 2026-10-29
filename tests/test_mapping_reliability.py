"""Exercise the actual Tk scan methods with simulated device/UI callbacks."""

import json
import queue
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_integration_experiment import (
    Frm_HighLvlController_Raman, Frm_MotionController, Frm_RamanSpectrometerController, MeaRMap_Unit,
    SimulatedSpectrometer, raman_frame, raman_gui, dill, np,
    SpectrometerController_Dummy,
)
from iris.utils.mapping_waits import wait_for_motion, wait_for_buffer


class WaitTests(unittest.TestCase):
    def test_stationary_stage_times_out(self):
        ticks = iter(range(100))
        worker = Mock(is_alive=lambda: True)
        with self.assertRaisesRegex(TimeoutError, 'stopped changing'):
            wait_for_motion([worker], queue.Queue(), lambda: (0, 0, 0), 3,
                            clock=lambda: next(ticks))

    def test_slow_move_can_exceed_timeout_while_progressing(self):
        ticks = iter(range(100))
        positions = iter((n * 0.002, 0, 0) for n in range(20))
        worker = Mock()
        worker.is_alive.side_effect = [True] * 12 + [False]
        wait_for_motion([worker], queue.Queue(), lambda: next(positions), 3,
                        clock=lambda: next(ticks))
        self.assertEqual(worker.join.call_count, 12)

    def test_worker_error_propagates_even_after_worker_exits(self):
        failures = queue.Queue()
        failures.put(RuntimeError('lost COM port'))
        with self.assertRaisesRegex(RuntimeError, 'lost COM port'):
            wait_for_motion([Mock(is_alive=lambda: False)], failures, lambda: (0, 0, 0), 15)

    def test_buffer_stall_death_and_stop(self):
        buffer = queue.Queue()
        buffer.put('retained')
        with self.assertRaisesRegex(RuntimeError, 'saver stopped'):
            wait_for_buffer(buffer, Mock(is_alive=lambda: False), lambda: True)
        ticks = iter(range(100))
        with self.assertRaisesRegex(TimeoutError, 'no progress'):
            wait_for_buffer(buffer, Mock(is_alive=lambda: True), lambda: True,
                            timeout=2, clock=lambda: next(ticks))
        self.assertFalse(wait_for_buffer(buffer, Mock(), lambda: False))
        self.assertEqual(buffer.get_nowait(), 'retained')


class MappingTests(unittest.TestCase):
    coordinates = [(0., 0., 0.), (0.1, 0., 0.), (0., 0.1, 0.), (0.1, 0.1, 0.)]

    def frame(self):
        frame = SimpleNamespace(
            measurement_data_2D_unit=MeaRMap_Unit('test_map'),
            flg_isrunning_mapping=True, _flg_meaCancelled=False,
            status_update=Mock(), _dataHub_map=Mock(), _coorHub=Mock(),
            _stageHub=SimpleNamespace(get_coordinates_interpolate=lambda timestamp: (0., 0., 0.)),
            _frm_coorHub_treeview=Mock(), motion_controller=Mock(), raman_controller=Mock(),
        )
        frame.motion_controller.isontarget_gotocoor.return_value = True
        frame.raman_controller.get_integration_time_ms.return_value = 100.
        frame._frm_coorHub_treeview.offload_mappingCoor.return_value = Mock(is_alive=lambda: False)
        for name in ('_check_mapping_saver', '_finish_standard_mapping', '_scan_discreet',
                     '_scan_continuous', 'measurement_autosaver_discreet',
                     'measurement_autosaver_continuous', '_check_standard_mapping_idle'):
            setattr(frame, name, getattr(Frm_HighLvlController_Raman, name).__get__(frame))
        acquisition = raman_frame(SimulatedSpectrometer())

        def acquire(**kwargs):
            result = acquisition.acquire_experiment_spectrum(100.)
            kwargs['queue_response'].put((None, result[1]))
            return Mock(join=Mock())

        frame.raman_controller.perform_single_measurement_manual.side_effect = acquire
        return frame

    def isolated_scan(self, frame, method, coordinates=None):
        # Redirect only the save-path enum; never touch the lab config or hardware.
        with tempfile.TemporaryDirectory() as directory:
            enum = SimpleNamespace(AUTOSAVE_PATH=SimpleNamespace(value=directory))
            with patch.object(raman_gui, 'SaveParamsEnum', enum), patch.object(raman_gui.time, 'sleep'):
                getattr(frame, method)(coordinates or self.coordinates, **(
                    {'mapping_speed_rel': 20} if method == '_scan_continuous' else {}))
            path = Path(frame._mapping_recovery_dir)
            with (path / 'maps.pkl').open('rb') as source:
                hub = dill.load(source)
            return hub.get_MappingUnit(unit_name='test_map'), json.loads(
                (path / 'remaining_coordinates.json').read_text())

    def test_discrete_success_retains_all_spectra(self):
        frame = self.frame()
        recovered, remaining = self.isolated_scan(frame, '_scan_discreet')
        self.assertEqual(recovered.get_numMeasurements(), 4)
        self.assertEqual(remaining, [])
        self.assertFalse(frame._flg_meaCancelled)
        self.assertTrue(all(not worker.is_alive() for worker in frame._standard_mapping_workers))

    def test_discrete_with_actual_dummy_spectrum_generator(self):
        frame = self.frame()
        device = SpectrometerController_Dummy()
        acquisition = raman_frame(device)
        def single():
            spectrum, timestamp, integration_us = device.measure_spectrum()
            return timestamp, spectrum, integration_us / 1000
        acquisition._ramanHub = SimpleNamespace(get_single_measurement=single)
        def acquire(**kwargs):
            _, measurement = acquisition.acquire_experiment_spectrum(1.)
            kwargs['queue_response'].put((None, measurement))
            return Mock(join=Mock())
        frame.raman_controller.perform_single_measurement_manual.side_effect = acquire
        recovered, _ = self.isolated_scan(frame, '_scan_discreet')
        self.assertEqual(recovered.get_numMeasurements(), 4)

    def test_spectrometer_worker_without_result_is_not_saved_as_success(self):
        frame = self.frame()
        frame.raman_controller.perform_single_measurement_manual.side_effect = lambda **kwargs: Mock(join=Mock())
        with tempfile.TemporaryDirectory() as directory:
            enum = SimpleNamespace(AUTOSAVE_PATH=SimpleNamespace(value=directory))
            with patch.object(raman_gui, 'SaveParamsEnum', enum), patch.object(raman_gui.time, 'sleep'):
                with self.assertRaisesRegex(RuntimeError, 'completed spectrum'):
                    frame._scan_discreet(self.coordinates)
            self.assertEqual(frame.measurement_data_2D_unit.get_numMeasurements(), 0)
            remaining = json.loads((Path(frame._mapping_recovery_dir) / 'remaining_coordinates.json').read_text())
            self.assertEqual(remaining[0], list(self.coordinates[0]))
            self.assertFalse(frame._standard_mapping_active)

    def test_discrete_stop_during_exposure_retains_that_spectrum(self):
        frame = self.frame()
        original = frame.raman_controller.perform_single_measurement_manual.side_effect
        def stop(**kwargs):
            result = original(**kwargs)
            frame.flg_isrunning_mapping = False
            return result
        frame.raman_controller.perform_single_measurement_manual.side_effect = stop
        recovered, remaining = self.isolated_scan(frame, '_scan_discreet')
        self.assertEqual(recovered.get_numMeasurements(), 1)
        self.assertEqual(remaining, [list(point) for point in self.coordinates[1:]])
        self.assertTrue(frame._flg_meaCancelled)

    def test_discrete_failed_move_aborts_without_another_exposure(self):
        frame = self.frame()
        frame.motion_controller.go_to_coordinates.side_effect = [None, RuntimeError('stage disconnected')]
        with tempfile.TemporaryDirectory() as directory:
            enum = SimpleNamespace(AUTOSAVE_PATH=SimpleNamespace(value=directory))
            with patch.object(raman_gui, 'SaveParamsEnum', enum), patch.object(raman_gui.time, 'sleep'):
                with self.assertRaisesRegex(RuntimeError, 'stage disconnected'):
                    frame._scan_discreet(self.coordinates)
            remaining = json.loads((Path(frame._mapping_recovery_dir) / 'remaining_coordinates.json').read_text())
            self.assertEqual(remaining[0], list(self.coordinates[1]))
            self.assertEqual(frame.measurement_data_2D_unit.get_numMeasurements(), 1)
            frame.motion_controller.enable_controls.assert_called_once()
            self.assertEqual(frame.raman_controller.perform_single_measurement_manual.call_count, 1)

    def continuous(self, frame, stop_on_move=None, failure_on_move=None):
        results = queue.Queue()
        stopped = threading.Event()
        producer = threading.Thread(target=stopped.wait)
        producer.start()
        acquisition = raman_frame(SimulatedSpectrometer())
        calls = []
        def move(*args, **kwargs):
            calls.append(args)
            if len(calls) == failure_on_move:
                raise RuntimeError('stage disconnected')
            results.put(acquisition.acquire_experiment_spectrum(100.))
            if len(calls) == stop_on_move:
                frame.flg_isrunning_mapping = False
        frame.motion_controller.go_to_coordinates.side_effect = move
        frame.raman_controller.perform_ContinuousMeasurement_trigger.return_value = (
            producer, results, Mock(), Mock(), Mock(), stopped.set)
        self.addCleanup(stopped.set)
        return producer

    def test_continuous_stop_restarts_partial_line_at_its_start(self):
        frame = self.frame()
        producer = self.continuous(frame, stop_on_move=2)
        recovered, remaining = self.isolated_scan(frame, '_scan_continuous')
        self.assertFalse(producer.is_alive())
        self.assertGreater(recovered.get_numMeasurements(), 0)
        self.assertEqual(remaining, [list(point) for point in self.coordinates])
        frame.motion_controller.enable_controls.assert_called_once()

    def test_continuous_completion_drains_all_results(self):
        frame = self.frame()
        self.continuous(frame)
        recovered, remaining = self.isolated_scan(frame, '_scan_continuous')
        self.assertEqual(recovered.get_numMeasurements(), 4)
        self.assertEqual(remaining, [])
        self.assertFalse(frame._flg_meaCancelled)

    def test_continuous_failure_restores_original_speed(self):
        frame = self.frame()
        frame.motion_controller.calculate_vel_relative.return_value = 20
        frame.motion_controller.get_VelocityParameters.return_value = (53., 27.)
        frame._convertCoor_byScanOptions = lambda coordinates, **kwargs: coordinates
        frame._scramble_mapping_coordinates = lambda coordinates, mode: coordinates
        frame._scan_continuous = Mock(side_effect=RuntimeError('scan failed'))
        with self.assertRaisesRegex(RuntimeError, 'scan failed'):
            Frm_HighLvlController_Raman._perform_continuousMapping(
                frame, Mock(), self.coordinates, 0.1, 'map')
        frame.motion_controller.set_vel_relative.assert_called_once_with(vel_xy=53., vel_z=27.)

    def test_pending_stage_command_does_not_mask_scan_error_or_restore_speed(self):
        frame = self.frame()
        frame.motion_controller.calculate_vel_relative.return_value = 20
        frame.motion_controller.get_VelocityParameters.return_value = (53., 27.)
        frame.motion_controller._check_mapping_motion_idle.side_effect = RuntimeError('still running')
        frame._convertCoor_byScanOptions = lambda coordinates, **kwargs: coordinates
        frame._scramble_mapping_coordinates = lambda coordinates, mode: coordinates
        frame._scan_continuous = Mock(side_effect=TimeoutError('stage stalled'))
        with self.assertRaisesRegex(TimeoutError, 'stage stalled'):
            Frm_HighLvlController_Raman._perform_continuousMapping(
                frame, Mock(), self.coordinates, 0.1, 'map')
        frame.motion_controller.set_vel_relative.assert_not_called()

    def test_last_continuous_worker_error_is_not_reported_as_completion(self):
        frame = self.frame()
        self.continuous(frame)
        values = frame.raman_controller.perform_ContinuousMeasurement_trigger.return_value
        def stop():
            failures = frame.raman_controller.perform_ContinuousMeasurement_trigger.call_args.kwargs['failure_queue']
            failures.put(RuntimeError('spectrometer disconnected'))
            values[-1]()
        frame.raman_controller.perform_ContinuousMeasurement_trigger.return_value = (*values[:-1], stop)
        with tempfile.TemporaryDirectory() as directory:
            enum = SimpleNamespace(AUTOSAVE_PATH=SimpleNamespace(value=directory))
            with patch.object(raman_gui, 'SaveParamsEnum', enum):
                with self.assertRaisesRegex(RuntimeError, 'spectrometer disconnected'):
                    frame._scan_continuous(self.coordinates, 20)
            self.assertTrue(frame._flg_meaCancelled)
            self.assertEqual(frame.measurement_data_2D_unit.get_numMeasurements(), 4)

    def test_actual_continuous_worker_transports_failure_and_cleans_up(self):
        frame = SimpleNamespace(
            _ramanHub=Mock(), _flg_isrunning=threading.Event(),
            pause_auto_measurement=Mock(), reset_n_enable_widgets=Mock(), status_update=Mock())
        frame._ramanHub.isrunning_auto_measurement.side_effect = RuntimeError('SDK error')
        failures = queue.Queue()
        worker = Frm_RamanSpectrometerController._perform_ContinuousMeasurement_trigger(
            frame, queue.Queue(), queue.Queue(), failures)
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(str(failures.get_nowait()), 'SDK error')
        frame.pause_auto_measurement.assert_called_once()
        frame.reset_n_enable_widgets.assert_called_once()
        self.assertFalse(frame._flg_isrunning.is_set())

    def test_new_scan_rejected_while_old_saver_or_cleanup_runs(self):
        frame = self.frame()
        frame._standard_mapping_workers = [Mock(is_alive=lambda: True)]
        with self.assertRaisesRegex(RuntimeError, 'still running'):
            frame._check_standard_mapping_idle()
        frame._standard_mapping_workers = []
        frame._standard_mapping_active = True
        with self.assertRaisesRegex(RuntimeError, 'cleanup is still running'):
            frame._check_standard_mapping_idle()

    def test_continuous_move_error_stops_producer_and_drains_completed_data(self):
        frame = self.frame()
        producer = self.continuous(frame, failure_on_move=2)
        with tempfile.TemporaryDirectory() as directory:
            enum = SimpleNamespace(AUTOSAVE_PATH=SimpleNamespace(value=directory))
            with patch.object(raman_gui, 'SaveParamsEnum', enum):
                with self.assertRaisesRegex(RuntimeError, 'stage disconnected'):
                    frame._scan_continuous(self.coordinates, 20)
            self.assertTrue((Path(frame._mapping_recovery_dir) / 'maps.pkl').exists())
        self.assertFalse(producer.is_alive())
        self.assertEqual(frame.measurement_data_2D_unit.get_numMeasurements(), 1)
        self.assertTrue(all(not worker.is_alive() for worker in frame._standard_mapping_workers))

    def test_saver_failure_preserves_unprocessed_results_and_reports_failure(self):
        frame = self.frame()
        frame.measurement_data_2D_unit.append_ramanmeasurement_data = Mock(side_effect=RuntimeError('bad data'))
        with tempfile.TemporaryDirectory() as directory:
            enum = SimpleNamespace(AUTOSAVE_PATH=SimpleNamespace(value=directory))
            with patch.object(raman_gui, 'SaveParamsEnum', enum), patch.object(raman_gui.time, 'sleep'):
                with self.assertRaisesRegex(RuntimeError, 'saver failed'):
                    frame._scan_discreet(self.coordinates)
            self.assertTrue((Path(frame._mapping_recovery_dir) / 'pending_results.pkl').exists())


class MotionTests(unittest.TestCase):
    def test_stage_worker_error_does_not_set_target_flag(self):
        frame = SimpleNamespace(
            ctrl_xy=SimpleNamespace(move_direct=Mock(side_effect=RuntimeError('driver error'))),
            ctrl_z=SimpleNamespace(move_direct=Mock()), _current_coor=np.zeros(3),
            _flg_ontarget_gotocoor=threading.Event(), status_update=Mock(),
            disable_controls=Mock(), enable_controls=Mock())
        frame._check_mapping_motion_idle = lambda: Frm_MotionController._check_mapping_motion_idle(frame)
        with self.assertRaisesRegex(RuntimeError, 'driver error'):
            Frm_MotionController.go_to_coordinates(frame, 0., 0., 0.)
        for worker in frame._mapping_move_threads:
            worker.join()
        self.assertFalse(frame._flg_ontarget_gotocoor.is_set())
        frame.enable_controls.assert_called_once()

    def test_outstanding_move_rejects_new_mapping_and_experiment_moves(self):
        frame = SimpleNamespace(_mapping_move_threads=[Mock(is_alive=lambda: True)])
        with self.assertRaisesRegex(RuntimeError, 'still running'):
            Frm_MotionController._check_mapping_motion_idle(frame)

    def test_timed_out_move_remains_guarded_until_driver_returns(self):
        released = threading.Event()
        frame = SimpleNamespace(
            ctrl_xy=SimpleNamespace(move_direct=lambda target: released.wait()),
            ctrl_z=SimpleNamespace(move_direct=lambda target: None), _current_coor=np.zeros(3),
            _flg_ontarget_gotocoor=threading.Event(), status_update=Mock(),
            disable_controls=Mock(), enable_controls=Mock())
        frame._check_mapping_motion_idle = lambda: Frm_MotionController._check_mapping_motion_idle(frame)
        try:
            with patch('iris.gui.motion_video.wait_for_motion', side_effect=TimeoutError('stalled')):
                with self.assertRaisesRegex(TimeoutError, 'stalled'):
                    Frm_MotionController.go_to_coordinates(frame, 1., 0., 0., override_controls=True)
            with self.assertRaisesRegex(RuntimeError, 'still running'):
                Frm_MotionController.move_for_experiment(frame, (0., 0., 0.))
            self.assertFalse(frame._flg_ontarget_gotocoor.is_set())
        finally:
            released.set()
            for worker in frame._mapping_move_threads:
                worker.join()
        frame._check_mapping_motion_idle()


if __name__ == '__main__':
    unittest.main()
