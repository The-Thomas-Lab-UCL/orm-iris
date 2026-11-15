"""Single-acquisition cancellation with simulated exposures and real measurement data."""
import queue
import threading
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from test_integration_experiment import Frm_RamanSpectrometerController, SimulatedSpectrometer
from iris.gui.dataHub_MeaRMap import Frm_DataHub_Mapping
from iris.utils.recovery_journal import recover_mapping_hub, read_recovery
from iris.utils.live_spectrum import LatestSpectrum


class SingleAcquisitionTests(unittest.TestCase):
    def frame(self, count=1000):
        device = SimulatedSpectrometer()
        button = Mock()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        data_hub = SimpleNamespace(require_autosave_folder=lambda: folder.name,
                                   register_recovery_writer=Mock())
        data_hub.start_single_autosave = Frm_DataHub_Mapping.start_single_autosave.__get__(data_hub)
        frame = SimpleNamespace(
            _controller=device, _ramanHub=device, _dataHub=data_hub, integration_time_ms=100.,
            singMea_accumulation=count, contMea_accumulation=2,
            _laserpower_mW=10., _laserwavelength_nm=785., _bg_colour='grey',
            _flg_isrunning=threading.Event(), _single_cancel=threading.Event(),
            _single_measurement_lock=threading.Lock(), _single_busy=False,
            _sgl_measurement=None, _live_spectra=LatestSpectrum(), btn_single_mea=button, btn_continuous_mea=Mock(),
            _sfrm_controls=SimpleNamespace(winfo_children=lambda: [button]),
            _sfrm_data=SimpleNamespace(winfo_children=lambda: []),
            pause_auto_measurement=Mock(), disable_widgets=Mock(),
            _bool_PlotRamanShift=Mock(get=lambda: False), _bool_PlotRawOnly=Mock(get=lambda: True),
            update_label_device_parameters=Mock(), status_update=Mock(),
            Plot_rawlist_RM=Mock(), AnalyseAndPlot_rawlist=Mock(),
            Analyse=Mock(side_effect=lambda measurement, raw_list: measurement.check_uptodate()))
        button.winfo_children.return_value = []
        for method in ('perform_single_measurement', 'perform_single_measurement_manual',
                       '_run_single_acquisition', '_queue_live_spectrum', 'force_stop_measurement',
                       'get_running_status', 'reset_n_enable_widgets'):
            setattr(frame, method, getattr(Frm_RamanSpectrometerController, method).__get__(frame))
        return frame

    def join(self, worker):
        worker.join(3)
        self.assertFalse(worker.is_alive())

    def test_stop_inflight_retains_partial_and_prevents_overlapping_restart(self):
        frame = self.frame()
        entered, finish = threading.Event(), threading.Event()
        original = frame._ramanHub.get_single_measurement
        def exposure():
            entered.set()
            if not finish.wait(2):
                raise TimeoutError('Test exposure timed out')
            return original()
        frame._ramanHub.get_single_measurement = Mock(side_effect=exposure)
        worker = frame.perform_single_measurement()
        self.assertTrue(entered.wait(2))
        frame.btn_single_mea.configure.assert_any_call(
            state='normal', text='STOP acquisition', bg='red', command=frame.force_stop_measurement)
        frame.force_stop_measurement()
        self.assertTrue(frame.get_running_status())
        with self.assertRaisesRegex(RuntimeError, 'already running or stopping'):
            frame.perform_single_measurement()
        finish.set()
        self.join(worker)
        self.assertEqual(frame._ramanHub.get_single_measurement.call_count, 1)
        self.assertEqual(frame._sgl_measurement.get_metadata()['accumulation'], 1)
        writer = frame._dataHub.register_recovery_writer.call_args.args[0]
        self.assertEqual(len(read_recovery(writer.path)), 1)
        recovered = recover_mapping_hub(writer.path)
        unit = recovered.get_MappingUnit(recovered.get_list_MappingUnit_ids()[0])
        self.assertEqual(unit.get_dict_measurement_metadata()['accumulation'], 1)
        self.assertFalse(frame.get_running_status())
        self.assertIn('1 of 1000 exposures retained', frame.status_update.call_args.args[0])
        restored = frame.btn_single_mea.configure.call_args.kwargs
        self.assertEqual(restored['text'], 'Single measurement')
        self.assertEqual(restored['state'], 'normal')
        frame.singMea_accumulation = 2
        self.join(restored['command']())
        self.assertEqual(frame._sgl_measurement.get_metadata()['accumulation'], 2)

    def test_stop_before_first_exposure_keeps_previous_measurement(self):
        frame = self.frame()
        previous = object()
        frame._sgl_measurement = previous
        frame.pause_auto_measurement.side_effect = frame.force_stop_measurement
        frame._ramanHub.get_single_measurement = Mock()
        self.join(frame.perform_single_measurement())
        frame._ramanHub.get_single_measurement.assert_not_called()
        self.assertIs(frame._sgl_measurement, previous)
        frame.Analyse.assert_not_called()
        self.assertFalse(frame._single_measurement_lock.locked())

    def test_manual_cancellation_does_not_return_partial_as_complete(self):
        frame = self.frame()
        original = frame._ramanHub.get_single_measurement
        def exposure():
            frame.force_stop_measurement()
            return original()
        frame._ramanHub.get_single_measurement = exposure
        response = queue.Queue()
        self.join(frame.perform_single_measurement_manual(widget_override=True, queue_response=response))
        self.assertTrue(response.empty())
        self.assertEqual(frame._sgl_measurement.get_metadata()['accumulation'], 1)
        frame.disable_widgets.assert_not_called()

    def test_complete_manual_acquisition_returns_full_measurement(self):
        frame = self.frame(count=3)
        response = queue.Queue()
        self.join(frame.perform_single_measurement_manual(widget_override=True, queue_response=response))
        plot_thread, measurement = response.get_nowait()
        self.assertFalse(plot_thread.is_alive())
        self.assertEqual(measurement.get_metadata()['accumulation'], 3)
        self.assertFalse(frame.get_running_status())

    def test_device_failure_preserves_completed_exposure_and_restores_controls(self):
        frame = self.frame()
        original = frame._ramanHub.get_single_measurement
        frame._ramanHub.get_single_measurement = Mock(side_effect=[original(), RuntimeError('disconnected')])
        self.join(frame.perform_single_measurement())
        self.assertIn('disconnected', frame.status_update.call_args.args[0])
        self.assertEqual(frame._sgl_measurement.get_metadata()['accumulation'], 1)
        self.assertFalse(frame.get_running_status())
        self.assertFalse(frame._single_measurement_lock.locked())

    def test_completed_single_recovers_one_average_with_all_raw_exposures(self):
        frame = self.frame(count=3)
        self.join(frame.perform_single_measurement())
        writer = frame._dataHub.register_recovery_writer.call_args.args[0]
        self.assertEqual(len(read_recovery(writer.path)), 3)
        hub = recover_mapping_hub(writer.path)
        self.assertEqual(len(hub.get_list_MappingUnit_ids()), 1)
        unit = hub.get_MappingUnit(hub.get_list_MappingUnit_ids()[0])
        self.assertEqual(unit.get_numMeasurements(), 1)
        self.assertEqual(unit.get_dict_measurement_metadata()['accumulation'], 3)
        self.assertEqual(len(unit.get_dict_measurements()[unit._label_listmea][0]), 3)
        import pandas as pd
        pd.testing.assert_frame_equal(unit.get_dict_measurements()[unit._label_avemea][0],
                                      frame._sgl_measurement.get_analysed())

    def test_autosave_folder_failure_starts_no_exposure_and_releases_lock(self):
        frame = self.frame(count=3)
        frame._dataHub.start_single_autosave = Mock(side_effect=OSError('Cannot write autosave folder'))
        frame._ramanHub.get_single_measurement = Mock()
        with self.assertRaisesRegex(OSError, 'Cannot write autosave folder'):
            frame.perform_single_measurement()
        frame._ramanHub.get_single_measurement.assert_not_called()
        self.assertFalse(frame.get_running_status())
        self.assertFalse(frame._single_measurement_lock.locked())

    def test_mapping_acquisitions_do_not_create_duplicate_single_autosaves(self):
        frame = self.frame(count=2)
        self.join(frame.perform_single_measurement_manual(widget_override=True, queue_response=queue.Queue()))
        frame._dataHub.register_recovery_writer.assert_not_called()

    def test_autosave_write_failure_keeps_measurement_and_restores_controls(self):
        frame = self.frame(count=2)
        start = frame._dataHub.start_single_autosave
        def failing_writer(settings):
            writer, unit = start(settings)
            writer._commit = Mock(side_effect=OSError('disk full'))
            return writer, unit
        frame._dataHub.start_single_autosave = failing_writer
        self.join(frame.perform_single_measurement())
        self.assertEqual(frame._sgl_measurement.get_metadata()['accumulation'], 2)
        self.assertIn('disk full', frame.status_update.call_args.args[0])
        self.assertFalse(frame.get_running_status())
        self.assertFalse(frame._single_measurement_lock.locked())


if __name__ == '__main__':
    unittest.main()
