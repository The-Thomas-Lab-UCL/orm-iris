"""Recovery durability, DB export compatibility, and background writer isolation."""
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from test_integration_experiment import (
    MeaRMap_Unit, MeaRMap_Hub, MeaRMap_Handler, SimulatedSpectrometer,
    raman_frame, raman_gui,
)
import test_integration_experiment as experiment_fixture
from iris.utils.recovery_journal import RecoveryWriter, recover_mapping_hub, read_recovery


class RecoveryTests(unittest.TestCase):
    def measurement(self):
        return raman_frame(SimulatedSpectrometer()).acquire_experiment_spectrum(100.)[1]

    def submit(self, writer, timestamp=1, unit=None):
        measurement = self.measurement()
        unit = unit or MeaRMap_Unit('sample')
        unit.append_ramanmeasurement_data(timestamp, (1., 2., 3.), measurement)
        writer.submit(unit, timestamp, (1., 2., 3.), measurement)
        return unit, measurement

    def until(self, condition):
        deadline = time.monotonic() + 3
        while not condition() and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertTrue(condition())

    def test_twenty_second_default_final_flush_and_detached_spectra(self):
        with tempfile.TemporaryDirectory() as folder:
            writer = RecoveryWriter(folder)
            self.assertEqual(writer.interval_s, 20)
            unit, measurement = self.submit(writer)
            measurement.get_raw_list()[0].iloc[0, 1] = 999
            self.assertEqual(writer.status()['committed'], 0)
            writer.close()
            records = read_recovery(writer.path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['coordinate'], (1., 2., 3.))
            self.assertNotEqual(records[0]['raw'][0].iloc[0, 1], 999)
            self.assertEqual(writer.status()['committed'], 1)
            with self.assertRaisesRegex(RuntimeError, 'already closed'):
                self.submit(writer, 2, unit)

    def test_single_exposures_recover_before_the_accumulation_finishes(self):
        with tempfile.TemporaryDirectory() as folder:
            writer = RecoveryWriter(folder, settings={'acquisition_kind': 'single'}, interval_s=.03)
            unit = MeaRMap_Unit('single_test')
            measurement = self.measurement()
            try:
                writer.submit_single_exposure(unit, 1, measurement.get_raw_list()[0], measurement.get_metadata())
                self.until(lambda: writer.status()['committed'] == 1)
                partial = recover_mapping_hub(writer.path).get_MappingUnit(unit_name='single_test')
                self.assertEqual(partial.get_dict_measurement_metadata()['accumulation'], 1)
                writer.submit_single_exposure(unit, 2, measurement.get_raw_list()[0], measurement.get_metadata())
                writer.submit_single_exposure(unit, 3, measurement.get_raw_list()[0], measurement.get_metadata())
            finally:
                writer.close()
            recovered = recover_mapping_hub(writer.path).get_MappingUnit(unit_name='single_test')
            self.assertEqual(recovered.get_numMeasurements(), 1)
            self.assertEqual(recovered.get_dict_measurement_metadata()['accumulation'], 3)

    def test_timer_commits_new_rows_only(self):
        with tempfile.TemporaryDirectory() as folder:
            writer = RecoveryWriter(folder, interval_s=.03)
            try:
                unit, _ = self.submit(writer)
                self.until(lambda: writer.status()['committed'] == 1)
                self.submit(writer, 2, unit)
                self.until(lambda: writer.status()['committed'] == 2)
            finally:
                writer.close()
            self.assertEqual([r['timestamp'] for r in read_recovery(writer.path)], [1, 2])

    def test_blocked_disk_does_not_block_enqueue_and_overflow_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            writer = RecoveryWriter(folder, interval_s=.01, max_pending=1)
            entered, release = threading.Event(), threading.Event()
            original = writer._commit
            def blocked(connection, records):
                if records:
                    entered.set()
                    release.wait(3)
                original(connection, records)
            writer._commit = blocked
            try:
                unit, _ = self.submit(writer)
                self.assertTrue(entered.wait(2))
                # This submission must return while the disk writer is blocked.
                self.submit(writer, 2, unit)
                with self.assertRaisesRegex(RuntimeError, 'cannot keep up'):
                    self.submit(writer, 3, unit)
            finally:
                release.set()
                writer.close()
            self.assertEqual(len(read_recovery(writer.path)), 2)

    def test_disk_failure_is_visible_and_prevents_further_saves(self):
        with tempfile.TemporaryDirectory() as folder:
            writer = RecoveryWriter(folder)
            self.submit(writer)
            writer._commit = Mock(side_effect=sqlite3.OperationalError('disk full'))
            with self.assertRaisesRegex(RuntimeError, 'disk full'):
                writer.close()
            self.assertEqual(writer.status()['committed'], 0)
            self.assertIn('disk full', writer.status()['error'])
            self.assertEqual(read_recovery(writer.path), [])

    def test_sqlite_capacity_limit_preserves_the_last_committed_batch(self):
        # Exercise real SQLITE_FULL behavior without filling the physical drive.
        with tempfile.TemporaryDirectory() as folder:
            writer = RecoveryWriter(folder, interval_s=.03)
            unit, _ = self.submit(writer)
            self.until(lambda: writer.status()['committed'] == 1)
            original = writer._commit
            def limited(connection, records):
                if records:
                    pages = connection.execute('PRAGMA page_count').fetchone()[0]
                    connection.execute(f'PRAGMA max_page_count={pages}')
                original(connection, records)
            writer._commit = limited
            import pandas as pd
            measurement = self.measurement()
            large_spectrum = pd.concat([measurement.get_raw_list()[0]] * 2048, ignore_index=True)
            measurement.reconstruct(2, measurement.get_metadata(), large_spectrum, [large_spectrum])
            writer.submit(unit, 2, (1., 2., 3.), measurement)
            with self.assertRaisesRegex(RuntimeError, 'database or disk is full'):
                writer.close()
            self.assertEqual(writer.status()['committed'], 1)
            self.assertEqual([record['timestamp'] for record in read_recovery(writer.path)], [1])

    def test_recovered_maps_export_and_reload_with_existing_db_handler(self):
        with tempfile.TemporaryDirectory() as folder:
            writer = RecoveryWriter(folder)
            unit, original = self.submit(writer)
            self.submit(writer, 2, unit)
            writer.close()
            recovered = recover_mapping_hub(writer.path)
            handler = MeaRMap_Handler()
            export = handler.save_MappingHub_database(recovered, folder, 'existing_format')
            export.join(5)
            self.assertFalse(export.is_alive())
            loaded = MeaRMap_Hub()
            handler.load_MappingMeasurementHub_database(loaded, str(Path(folder) / 'existing_format.db'), flg_readraw=True)
            result = loaded.get_MappingUnit(unit_name='sample')
            self.assertEqual(result.get_numMeasurements(), 2)
            self.assertEqual(result.get_dict_measurement_metadata(), original.get_metadata())
            self.assertEqual(result.get_dict_measurements()[result._label_x], [1., 1.])
            import pandas as pd
            pd.testing.assert_frame_equal(
                result.get_dict_measurements()[result._label_avemea][0].reset_index(drop=True),
                original.get_analysed().reset_index(drop=True))
            self.assertEqual(len(result.get_dict_measurements()[result._label_listmea][0]), 1)

    def test_forced_process_exit_keeps_committed_rows_only(self):
        helper = Path(__file__).resolve().parents[1] / 'iris/utils/recovery_journal.py'
        script = '''
import importlib.util, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]).resolve().parents[2]))
from types import SimpleNamespace
import pandas as pd
spec = importlib.util.spec_from_file_location('journal', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
writer = module.RecoveryWriter(sys.argv[2], interval_s=.05)
df = pd.DataFrame({'wavelength': [500.], 'intensity': [10.]})
unit = SimpleNamespace(get_unit_id=lambda:'unit', get_unit_name=lambda:'sample', get_dict_unit_metadata=lambda:{})
mea = SimpleNamespace(get_metadata=lambda:{}, get_raw_list=lambda:[df], get_analysed=lambda:df)
writer.submit(unit,1,(0,0,0),mea)
while writer.status()['committed'] < 1: time.sleep(.005)
writer.interval_s = 3600
# Let the next timer expire with no new data so its new interval applies.
time.sleep(.1)
writer.submit(unit,2,(0,0,0),mea)
print(writer.path, flush=True)
while True: time.sleep(1)
'''
        with tempfile.TemporaryDirectory() as folder:
            process = subprocess.Popen([sys.executable, '-c', script, str(helper), folder],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=folder)
            try:
                path = process.stdout.readline().strip()
                self.assertTrue(path, process.stderr.read() if process.poll() is not None else '')
            finally:
                process.kill()
                process.wait(5)
                process.stdout.close()
                process.stderr.close()
            self.assertEqual([r['timestamp'] for r in read_recovery(path)], [1])
            with closing(sqlite3.connect(path)) as connection:
                self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone(), ('ok',))

    def test_unavailable_autosave_folder_starts_no_experiment_or_hardware(self):
        frame, hub, moves, callbacks, _ = experiment_fixture.UIFlowTests().make_frame()
        frame._dataHub_map.require_autosave_folder = Mock(side_effect=OSError('Autosave folder is not writable'))
        with patch.object(raman_gui.messagebox, 'showerror') as message:
            frame.start_integration_experiment()
        self.assertIsNone(frame._experiment_thread)
        self.assertEqual(moves, [])
        self.assertEqual(hub.get_list_MappingUnit_names(), [])
        self.assertEqual(callbacks, [])
        message.assert_called_once()


class AutosaveUITests(unittest.TestCase):
    def test_provisional_folder_survives_restart_and_recovery_adds_distinct_maps(self):
        import tkinter as tk
        from types import SimpleNamespace
        from iris.gui import dataHub_MeaRMap as ui

        root = tk.Tk()
        root.withdraw()
        with tempfile.TemporaryDirectory() as folder:
            try:
                params = SimpleNamespace(DEFAULT_SAVE_PATH=SimpleNamespace(value=folder))
                with patch.object(ui, 'SaveParamsEnum', params):
                    frame = ui.Frm_DataHub_Mapping(root, autosave=True)
                provisional = Path(folder) / 'provisional'
                with patch.object(ui, 'PROVISIONAL_AUTOSAVE_FOLDER', provisional), \
                     patch.object(ui.filedialog, 'askdirectory', return_value='') as chooser:
                    self.assertEqual(frame.require_autosave_folder(), str(provisional))
                    chooser.assert_not_called()
                    writer = RecoveryWriter(frame.require_autosave_folder())
                    RecoveryTests().submit(writer)
                    writer.close()
                    # A fresh app session resolves the same folder without relying on cwd.
                    frame._autosave_path = None
                    self.assertEqual(frame.require_autosave_folder(), str(provisional))
                    self.assertEqual(len(read_recovery(writer.path)), 1)
                    frame.choose_autosave_folder()  # Cancelling keeps the working default.
                    self.assertEqual(frame._autosave_path, str(provisional))
                with patch.object(ui.filedialog, 'askdirectory', return_value=folder):
                    frame.choose_autosave_folder()
                    self.assertEqual(frame.require_autosave_folder(), str(Path(folder).resolve()))
                writer = RecoveryWriter(folder)
                RecoveryTests().submit(writer)
                frame.register_recovery_writer(writer)
                writer.close()
                frame.after_cancel(frame._recovery_poll)
                frame._recovery_poll = None
                frame._poll_recovery_status()
                self.assertIn('1/1 spectra committed', frame._str_autosave_status.get())
                with patch.object(ui.filedialog, 'askopenfilename', return_value=str(writer.path)), \
                     patch.object(ui.messagebox, 'showinfo'), patch.object(ui.messagebox, 'showerror') as error:
                    frame.recover_autosaved_maps()
                    frame.recover_autosaved_maps()
                    error.assert_not_called()
                self.assertEqual(frame._MappingHub.get_list_MappingUnit_names(),
                                 ['sample_recovered', 'sample_recovered_2'])
            finally:
                # Tk Variables must be released on the GUI thread, including
                # when a later test starts a background database export.
                if 'frame' in locals():
                    frame._str_search = None
                    frame._bool_save_raw_MappingUnit_ext = None
                    frame._str_autosave_path = None
                    frame._str_autosave_status = None
                root.destroy()
                import gc
                gc.collect()


if __name__ == '__main__':
    unittest.main()
