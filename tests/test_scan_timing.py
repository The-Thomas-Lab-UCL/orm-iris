"""Known-duration timing checks and actual acquisition/streamer integration."""
import csv
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_integration_experiment as fixture
import test_single_acquisition as single_fixture
from iris.multiprocessing.dataStreamer_Raman import DataStreamer_Raman
from iris.utils.scan_timing import StageTimer, write_scan_timing


class ScanTimingTests(unittest.TestCase):
    def test_stage_partitions_use_monotonic_elapsed_time(self):
        ticks = iter([10., 10.1, 10.3, 10.31])
        timer = StageTimer(clock=lambda: next(ticks))
        timer.mark('motion_ms')
        timer.mark('settling_ms')
        data = timer.finish()
        self.assertAlmostEqual(data['motion_ms'], 100.)
        self.assertAlmostEqual(data['settling_ms'], 200.)
        self.assertAlmostEqual(data['unclassified_ms'], 10.)
        self.assertAlmostEqual(data['total_ms'], 310.)

    def test_report_excludes_partial_points_and_keeps_nested_times_separate(self):
        records = [dict(index=1, complete=True, total_ms=1000., expected_integration_ms=100.,
                        acquisition_ms=700., acquisition_final_plot_ms=500., overhead_ms=900.),
                   dict(index=2, complete=True, total_ms=1200., expected_integration_ms=100.,
                        acquisition_ms=900., acquisition_final_plot_ms=700., overhead_ms=1100.),
                   dict(index=3, complete=False, total_ms=20.)]
        with tempfile.TemporaryDirectory() as folder:
            path = write_scan_timing(folder, records)
            report = json.loads((Path(folder) / 'scan_timing.json').read_text())
            self.assertEqual(report['completed_points'], 2)
            self.assertEqual(report['summary']['total_ms']['mean_ms'], 1100.)
            self.assertEqual(report['summary']['acquisition_final_plot_ms']['mean_ms'], 600.)
            self.assertIn('do not add twice', path.read_text())
            with (Path(folder) / 'scan_timing.csv').open(newline='') as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[-1]['complete'], 'False')

    def test_actual_worker_separates_device_calibration_analysis_and_plotting(self):
        owner = single_fixture.SingleAcquisitionTests()
        frame = owner.frame(count=1)
        value = SimpleNamespace(seconds=0.)
        spectrum = fixture.SimulatedSpectrometer().get_single_measurement()[1]
        def device_exposure():
            value.seconds += .1
            return spectrum, 1000, 100000
        def calibrated():
            value.seconds += .03
            return spectrum
        hub = SimpleNamespace(_flg_pause_measurement=threading.Event(),
                              _controller=SimpleNamespace(measure_spectrum=device_exposure),
                              _lock_meaCal_pipe=threading.Lock(),
                              _pipe_cal_mea_front=SimpleNamespace(send=Mock(), recv=calibrated))
        hub._flg_pause_measurement.set()
        hub.get_single_measurement = DataStreamer_Raman.get_single_measurement.__get__(hub)
        frame._ramanHub = hub
        def analyse(measurement, raw_list):
            value.seconds += .02
            measurement.check_uptodate()
        def plot(**kwargs):
            value.seconds += .04
        frame.Analyse.side_effect = analyse
        frame.AnalyseAndPlot_rawlist.side_effect = plot
        try:
            with patch.object(fixture.raman_gui.time, 'perf_counter', lambda: value.seconds):
                worker = frame.perform_single_measurement_manual(widget_override=True)
                worker.join(3)
            self.assertFalse(worker.is_alive())
            data = worker.acquisition_timing
            self.assertAlmostEqual(data['device_call_ms'], 100.)
            self.assertAlmostEqual(data['calibration_ms'], 30.)
            self.assertAlmostEqual(data['fetch_ms'], 130.)
            self.assertAlmostEqual(data['final_analysis_ms'], 20.)
            self.assertAlmostEqual(data['final_plot_ms'], 0.)
            frame.AnalyseAndPlot_rawlist.assert_not_called()
            self.assertIs(frame._live_spectra.take(), frame._sgl_measurement)
            self.assertAlmostEqual(data['expected_integration_ms'], 100.)
            self.assertAlmostEqual(data['total_ms'], 150.)
        finally:
            owner.doCleanups()


if __name__ == '__main__':
    unittest.main()
