"""Owned-temp-folder tests for storage warnings and manual recovery deletion."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_integration_experiment as fixture
from iris.utils.autosave_storage import (
    GIB, RunLease, disk_capacity, list_recovery_runs, delete_recovery_run, run_info,
)
from iris.utils.recovery_journal import RecoveryWriter


class AutosaveStorageTests(unittest.TestCase):
    def make_run(self, root, name='mapping_recovery_test'):
        path = Path(root) / name
        path.mkdir()
        (path / 'settings.json').write_text('{}')
        (path / 'maps.pkl').write_bytes(b'recovery copy')
        return path

    def test_only_selected_recovery_run_is_deleted(self):
        with tempfile.TemporaryDirectory() as root:
            chosen = self.make_run(root)
            other = self.make_run(root, 'single_acquisition_other')
            exported = Path(root) / 'saved_dataset.db'
            exported.write_bytes(b'final export')
            before = list_recovery_runs(root)
            self.assertEqual(len(before), 2)
            self.assertTrue(all(row['deletable'] for row in before))
            removed = delete_recovery_run(root, chosen.name)
            self.assertGreater(removed, 0)
            self.assertFalse(chosen.exists())
            self.assertTrue(other.exists())
            self.assertEqual(exported.read_bytes(), b'final export')

    def test_exports_inside_run_protect_the_entire_folder(self):
        with tempfile.TemporaryDirectory() as root:
            run = self.make_run(root)
            export = run / 'saved_dataset.db'
            export.write_bytes(b'final export')
            self.assertFalse(list_recovery_runs(root)[0]['deletable'])
            with self.assertRaisesRegex(ValueError, 'exports or other files'):
                delete_recovery_run(root, run.name)
            self.assertEqual(export.read_bytes(), b'final export')
            self.assertTrue((run / 'maps.pkl').exists())

    def test_active_run_is_protected_through_post_scan_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            run = self.make_run(root)
            writer = RecoveryWriter(run)
            try:
                self.assertTrue(run_info(root, run.name)['active'])
                with self.assertRaises(OSError):
                    delete_recovery_run(root, run.name)
                writer.close(release_run=False)
                self.assertFalse(writer.thread.is_alive())
                self.assertTrue(run_info(root, run.name)['active'])
                writer.close()  # A second close must not release the finalizer's lock.
                self.assertTrue(writer.run_active)
                with self.assertRaises(OSError):
                    delete_recovery_run(root, run.name)
            finally:
                writer.release_run()
            self.assertFalse(run_info(root, run.name)['active'])
            delete_recovery_run(root, run.name)
            self.assertFalse(run.exists())

    def test_paths_cannot_escape_the_selected_folder(self):
        with tempfile.TemporaryDirectory() as root:
            run = self.make_run(root)
            for name in ('..', '../mapping_recovery_outside', str(run.resolve()), 'data out'):
                with self.assertRaises(ValueError):
                    delete_recovery_run(root, name)
            self.assertTrue((run / 'maps.pkl').exists())

    def test_nested_or_linked_content_is_never_traversed(self):
        with tempfile.TemporaryDirectory() as root:
            run = self.make_run(root)
            nested = run / 'exported_data'
            nested.mkdir()
            (nested / 'spectra.parquet').write_bytes(b'export')
            with self.assertRaises(ValueError):
                delete_recovery_run(root, run.name)
            self.assertEqual((nested / 'spectra.parquet').read_bytes(), b'export')
            outside = Path(root) / 'outside'
            outside.mkdir()
            (outside / 'maps.pkl').write_bytes(b'keep')
            linked = Path(root) / 'mapping_recovery_linked'
            try:
                linked.symlink_to(outside, target_is_directory=True)
            except OSError:
                return  # Junction/symlink creation can be unavailable on Windows.
            with self.assertRaises(ValueError):
                delete_recovery_run(root, linked.name)
            self.assertEqual((outside / 'maps.pkl').read_bytes(), b'keep')

    def test_low_space_thresholds_use_actual_target_drive(self):
        from collections import namedtuple
        Usage = namedtuple('Usage', 'total used free')
        with tempfile.TemporaryDirectory() as root:
            for total, free, low in ((100*GIB, 9*GIB, True), (1000*GIB, 40*GIB, True),
                                     (100*GIB, 30*GIB, False)):
                with patch('iris.utils.autosave_storage.shutil.disk_usage', return_value=Usage(total, total-free, free)):
                    self.assertEqual(disk_capacity(root)['low_space'], low)

    def test_other_process_run_is_protected_and_crash_releases_lock(self):
        repo = Path(__file__).resolve().parents[1]
        script = '''
import sys
sys.path.insert(0,sys.argv[1])
from iris.utils.recovery_journal import RecoveryWriter
writer=RecoveryWriter(sys.argv[2])
print('ready',flush=True)
sys.stdin.readline()
'''
        with tempfile.TemporaryDirectory() as root:
            run = self.make_run(root)
            process = subprocess.Popen([sys.executable, '-c', script, str(repo), str(run)], cwd=root,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertEqual(process.stdout.readline().strip(), 'ready')
                self.assertTrue(run_info(root, run.name)['active'])
                with self.assertRaises(OSError):
                    delete_recovery_run(root, run.name)
            finally:
                process.kill()
                process.wait(5)
                for stream in (process.stdin, process.stdout, process.stderr):
                    stream.close()
            self.assertFalse(run_info(root, run.name)['active'])
            delete_recovery_run(root, run.name)
            self.assertFalse(run.exists())

class AutosaveStorageUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from types import SimpleNamespace
        from iris.gui import dataHub_MeaRMap as ui
        self.ui = ui
        self.root = tk.Tk()
        self.root.withdraw()
        self.directory = tempfile.TemporaryDirectory()
        params = SimpleNamespace(DEFAULT_SAVE_PATH=SimpleNamespace(value=self.directory.name))
        with patch.object(ui, 'SaveParamsEnum', params):
            self.frame = ui.Frm_DataHub_Mapping(self.root, autosave=True)
        self.frame._autosave_path = self.directory.name

    def tearDown(self):
        for writer in self.frame._recovery_writers:
            writer.close()
            writer.release_run()
        for name in ('_str_search', '_bool_save_raw_MappingUnit_ext', '_str_autosave_path',
                     '_str_autosave_status', '_str_disk_space'):
            setattr(self.frame, name, None)
        self.root.destroy()
        import gc
        gc.collect()
        self.directory.cleanup()

    def wait_for_dialog(self, dialog):
        import time
        deadline = time.monotonic() + 5
        while dialog._busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.005)
        self.assertFalse(dialog._busy)

    def test_cleanup_requires_confirmation_and_keeps_active_and_exported_files(self):
        from iris.gui import autosave_cleanup as ui
        helper = AutosaveStorageTests()
        chosen = helper.make_run(self.directory.name)
        other = helper.make_run(self.directory.name, 'single_acquisition_other')
        active = helper.make_run(self.directory.name, 'mapping_recovery_active')
        exported = Path(self.directory.name) / 'final.db'
        exported.write_bytes(b'export')
        writer = RecoveryWriter(active)
        self.frame._recovery_writers.append(writer)
        self.frame.open_autosave_cleanup()
        dialog = self.frame._cleanup_window
        self.wait_for_dialog(dialog)
        keys = {run['name']: key for key, run in dialog._runs.items()}
        self.assertIn('free', dialog._space.get())
        dialog._tree.selection_set(keys[chosen.name])
        with patch.object(ui.messagebox, 'askyesno', return_value=False):
            dialog.delete_selected()
        self.assertTrue(chosen.exists())
        with patch.object(ui.messagebox, 'askyesno', return_value=True), \
             patch.object(ui.messagebox, 'showerror') as errors:
            dialog.delete_selected()
            self.wait_for_dialog(dialog)
            errors.assert_not_called()
        self.assertFalse(chosen.exists())
        self.assertTrue(other.exists())
        self.assertTrue(active.exists())
        self.assertEqual(exported.read_bytes(), b'export')
        active_key = next(key for key, run in dialog._runs.items() if run['name'] == active.name)
        dialog._tree.selection_set(active_key)
        dialog._selection_changed()
        self.assertEqual(dialog._delete_button['state'], 'disabled')
        with patch.object(ui.messagebox, 'askyesno') as confirm:
            dialog.delete_selected()
            confirm.assert_not_called()
        dialog.destroy()

    def test_low_space_preflight_warning_is_once_per_folder(self):
        capacity = dict(free_bytes=2*GIB, total_bytes=100*GIB, low_space=True)
        with patch.object(self.ui, 'disk_capacity', return_value=capacity), \
             patch.object(self.ui.messagebox, 'showwarning') as warning:
            self.frame.require_autosave_folder()
            self.frame.require_autosave_folder()
            warning.assert_called_once()
            self.assertIn('2.0 GiB', self.frame._str_disk_space.get())

    def test_background_capacity_warning_appears_in_status(self):
        run = AutosaveStorageTests().make_run(self.directory.name)
        capacity = dict(free_bytes=2*GIB, total_bytes=100*GIB, low_space=True)
        with patch('iris.utils.recovery_journal.disk_capacity', return_value=capacity):
            writer = RecoveryWriter(run)
        self.frame.register_recovery_writer(writer)
        self.frame.after_cancel(self.frame._recovery_poll)
        self.frame._recovery_poll = None
        self.frame._poll_recovery_status()
        self.assertIn('LOW DISK SPACE', self.frame._str_autosave_status.get())
        self.assertEqual(self.frame._lbl_autosave_status['fg'], 'red')


if __name__ == '__main__':
    unittest.main()
