"""Check startup callbacks without importing the hardware/configuration stack."""

import ast
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


def isolated_class(path, name, methods, base=object):
    # App imports read/write the lab configuration. Compile the actual method
    # bodies in isolation so these regressions can run without lab hardware.
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    node = next(node for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == name)
    node.bases = [ast.Name(id='Base', ctx=ast.Load())]
    node.body = [method for method in node.body
                 if isinstance(method, ast.FunctionDef) and method.name in methods]
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    namespace = {'Base': base}
    exec(compile(module, str(ROOT / path), 'exec'), namespace)
    return namespace[name]


Calibration = isolated_class(
    'iris/calibration/calibration_generator.py', 'Frm_SpectrometerCalibrationGenerator',
    {'_analyse_intensity_calibration_params'})
TimestampFrame = isolated_class(
    'iris/gui/timestamp_coorshift.py', 'sFrm_xyCoorTimestampShift',
    {'_auto_update', 'destroy'}, tk.Frame)


class IntensityLoadingTests(unittest.TestCase):
    def frame(self, pixels=(), measured=(), reference=()):
        frame = SimpleNamespace(
            _cal_params=dict(intensity_list_pixel_idx=list(pixels),
                             intensity_list_measured=list(measured),
                             intensity_list_reference=list(reference),
                             intensity_poly_coeffs=(0, 1)),
            _calculate_transferFunc_int_cubic=Mock(return_value=((1, 2, 3, 4), [])),
            _plot_int_transfer_func=Mock(),
            _ax_int_raw=Mock(), _ax_int_cal=Mock(), _canvas_int=Mock())
        return frame

    def test_empty_saved_points_preserve_coefficients_and_clear_stale_plot(self):
        frame = self.frame()
        Calibration._analyse_intensity_calibration_params(frame, False)
        self.assertEqual(frame._cal_params['intensity_poly_coeffs'], (0, 1))
        frame._calculate_transferFunc_int_cubic.assert_not_called()
        frame._plot_int_transfer_func.assert_not_called()
        frame._ax_int_raw.cla.assert_called_once()
        frame._ax_int_cal.cla.assert_called_once()
        frame._canvas_int.draw.assert_called_once()

    def test_saved_fit_with_one_point_does_not_refit(self):
        frame = self.frame([10], [2], [6])
        Calibration._analyse_intensity_calibration_params(frame, False)
        frame._calculate_transferFunc_int_cubic.assert_not_called()
        self.assertEqual(frame._cal_params['intensity_poly_coeffs'], (0, 1))
        frame._plot_int_transfer_func.assert_called_once_with([10], [2], [6], [(10, 3)])

    def test_new_fit_requires_four_points(self):
        for pixels in ([], [1, 2, 3]):
            frame = self.frame(pixels, pixels, pixels)
            with self.assertRaisesRegex(ValueError, 'at least four'):
                Calibration._analyse_intensity_calibration_params(frame)
            frame._calculate_transferFunc_int_cubic.assert_not_called()

    def test_mismatched_points_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'matching lengths'):
            Calibration._analyse_intensity_calibration_params(self.frame([1], [], []), False)

    def test_new_fit_stores_calculated_coefficients(self):
        frame = self.frame([1, 2, 3, 4], [2, 2, 2, 2], [4, 4, 4, 4])
        Calibration._analyse_intensity_calibration_params(frame)
        frame._calculate_transferFunc_int_cubic.assert_called_once()
        self.assertEqual(frame._cal_params['intensity_poly_coeffs'], (1, 2, 3, 4))


class TimestampUpdateTests(unittest.TestCase):
    def test_refresh_updates_values_and_schedules_next_callback(self):
        frame = SimpleNamespace(_dataHub=Mock(), _combo_sourceUnitName=Mock(),
                                after=Mock(return_value='next'), _auto_update=Mock())
        frame._dataHub.get_MappingHub.return_value.get_dict_nameToID.return_value = {'map': 'id'}
        TimestampFrame._auto_update(frame)
        frame._combo_sourceUnitName.configure.assert_called_once_with(values=['map'])
        frame.after.assert_called_once_with(500, frame._auto_update)
        self.assertEqual(frame._dict_nameToID, {'map': 'id'})
        self.assertEqual(frame._update_after_id, 'next')

    def test_destroy_cancels_pending_callback(self):
        base = type('FrameStub', (), {'destroy': lambda self: None})
        frame_type = isolated_class('iris/gui/timestamp_coorshift.py',
                                    'sFrm_xyCoorTimestampShift', {'destroy'}, base)
        frame = frame_type()
        frame._update_after_id = 'pending'
        frame.after_cancel = Mock()
        frame.destroy()
        frame.after_cancel.assert_called_once_with('pending')
        self.assertIsNone(frame._update_after_id)
        frame.destroy()
        frame.after_cancel.assert_called_once()

    def test_real_tk_refresh_repeats_and_is_cancelled_on_destroy(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f'Tk is unavailable: {exc}')
        root.withdraw()
        try:
            frame = TimestampFrame(root)
            frame._dataHub = Mock()
            frame._dataHub.get_MappingHub.return_value.get_dict_nameToID.return_value = {'map': 'id'}
            frame._combo_sourceUnitName = ttk.Combobox(frame)
            frame._update_after_id = frame.after_idle(frame._auto_update)
            root.update()
            self.assertEqual(frame._combo_sourceUnitName['values'], ('map',))
            self.assertEqual(frame._dict_nameToID, {'map': 'id'})
            pending = frame._update_after_id
            self.assertIn(pending, root.tk.call('after', 'info'))
            frame.destroy()
            self.assertNotIn(pending, root.tk.call('after', 'info'))
            root.update()
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
