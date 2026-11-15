"""Exercise the Z editor with real Tk widgets and a simulated motion controller."""
import ast
import math
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import unittest
from unittest.mock import Mock
from typing import Literal

SOURCE = Path(__file__).resolve().parents[1] / 'iris/gui/submodules/meaCoor_modifier/every_z.py'


class Coordinates:
    def __init__(self, mappingUnit_name, mapping_coordinates):
        self.mappingUnit_name = mappingUnit_name
        self.mapping_coordinates = mapping_coordinates


class Hub(list):
    def add_observer(self, observer):
        pass


def widgets(parent):
    return [child for widget in parent.winfo_children()
            for child in [widget, *widgets(widget)]]


tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'EveryZ')
messages = Mock()
request_name = Mock(return_value='edited')
namespace = dict(tk=tk, ttk=ttk, Literal=Literal, threading=threading, queue=queue,
                 math=math, Frm_MotionController=object, List_MeaCoor_Hub=Hub,
                 MeaCoor_mm=Coordinates, get_all_widgets=widgets, messagebox=messages,
                 messagebox_request_input=request_name)
exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), namespace)
EveryZ = namespace['EveryZ']


class ZEditorTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        messages.reset_mock()
        request_name.reset_mock(return_value=True)
        request_name.return_value = 'edited'
        self.original = [(0., 0., .00123456789), (1., 2., .002), (2., 3., .003)]
        self.hub = Hub([Coordinates('source', self.original.copy())])
        self.motion = Mock()
        self.motion.check_coordinates.return_value = True
        self.frame = EveryZ(self.root, self.hub, self.motion)
        self.frame._combo_mapUnit.set('source')
        self.frame._run_modify_z_coordinates()
        self.wait_move()

    def tearDown(self):
        self.root.destroy()

    def wait_move(self):
        deadline = time.monotonic() + 2
        while self.frame._moving and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.005)
        self.assertFalse(self.frame._moving)

    def enter(self, text):
        self.frame._entry_newZCoor.delete(0, tk.END)
        self.frame._entry_newZCoor.insert(0, text)

    def test_back_forward_dropdown_reedit_and_save(self):
        self.assertEqual(self.frame._btn_back['state'], 'disabled')
        self.assertEqual(self.frame._str_previousZCoor.get(), 'N/A')
        self.enter('4.25')
        self.frame._btn_forward.invoke()
        self.wait_move()
        self.assertEqual(float(self.frame._str_previousZCoor.get()), 4.25)
        self.frame._btn_back.invoke()
        self.wait_move()
        self.assertEqual(self.frame._str_previousZCoor.get(), 'N/A')
        self.assertEqual(float(self.frame._entry_newZCoor.get()), 4.25)
        self.enter('5.75')
        self.frame._combo_point.current(2)
        self.frame._select_point()
        self.wait_move()
        self.assertEqual(float(self.frame._str_previousZCoor.get()), 2.)
        self.assertEqual(self.frame._btn_forward['state'], 'disabled')
        self.frame._btn_commit_modification.invoke()
        self.assertEqual(self.frame._btn_save['state'], 'normal')
        self.assertTrue(self.frame._editing)  # Last point stays editable.
        self.frame._btn_save.invoke()
        self.assertFalse(self.frame._editing)
        self.assertEqual(self.frame._str_previousZCoor.get(), 'N/A')
        self.assertEqual(self.hub[1].mapping_coordinates[0], (0., 0., .00575))
        self.assertEqual(self.hub[0].mapping_coordinates, self.original)
        self.motion.go_to_coordinates.assert_called_with(coor_x_mm=2., coor_y_mm=3., coor_z_mm=.003)

    def test_invalid_input_stays_at_current_point(self):
        for text in ('bad', 'nan', 'inf'):
            self.enter(text)
            self.frame._combo_point.current(2)
            self.frame._select_point()
            self.assertEqual(self.frame._point_index, 0)
            self.assertEqual(self.frame._combo_point.current(), 0)
        self.motion.check_coordinates.return_value = False
        self.enter('42')
        self.frame._commit_modification()
        self.assertEqual(self.frame._reviewed, set())
        self.assertEqual(self.motion.go_to_coordinates.call_count, 1)

    def test_precision_cancel_and_restart(self):
        self.frame._navigate_point(1)
        self.wait_move()
        self.assertEqual(self.frame._point_index, 1)
        self.assertAlmostEqual(self.frame._coordinates[0][2], self.original[0][2], places=14)
        self.frame._cancel_modification()
        self.assertEqual(len(self.hub), 1)
        self.frame._run_modify_z_coordinates()
        self.wait_move()
        self.assertEqual(self.frame._point_index, 0)
        self.assertEqual(self.frame._reviewed, set())

    def test_move_failure_ends_session(self):
        self.motion.go_to_coordinates.side_effect = RuntimeError('disconnected')
        self.frame._navigate_point(1)
        self.wait_move()
        self.assertFalse(self.frame._editing)
        self.assertEqual(len(self.hub), 1)
        messages.showerror.assert_called_with('Stage movement failed', 'disconnected')

    def test_cannot_save_until_all_points_reviewed(self):
        self.frame._save_modifications()
        self.assertEqual(len(self.hub), 1)
        request_name.assert_not_called()

    def test_surface_preview_commit_and_rotation(self):
        self.frame._show_surface_plot()
        ax = self.frame._surface_ax
        self.assertIsNot(self.frame._surface_triangles, False)
        ax.view_init(elev=17, azim=29)
        self.enter('25')
        self.frame._update_surface_plot()
        self.assertIn('Preview', ax.get_title())
        self.assertEqual(float(ax.collections[-1]._offsets3d[2][0]), 25.)
        self.assertEqual(self.frame._coordinates[0], self.original[0])
        self.assertEqual((ax.elev, ax.azim), (17, 29))
        self.frame._commit_modification()
        self.wait_move()
        self.assertEqual(self.frame._coordinates[0][2], .025)
        self.assertIn('1/3 reviewed', ax.get_title())
        self.enter('nan')
        self.frame._update_surface_plot()
        self.assertIn('Invalid Z input', ax.get_title())
        self.frame._cancel_modification()
        self.assertIn('Start modifying', ax.get_title())

    def test_stage_view_orientation_and_reset(self):
        from mpl_toolkits.mplot3d import proj3d

        ax = self.frame._surface_ax
        self.assertEqual((ax.elev, ax.azim, ax.roll), (30, -90, 0))
        projection = ax.get_proj()
        center = proj3d.proj_transform(1., 1.5, 2., projection)
        right = proj3d.proj_transform(1.5, 1.5, 2., projection)
        towards = proj3d.proj_transform(1., 1., 2., projection)
        increasing_z = proj3d.proj_transform(1., 1.5, 2.5, projection)
        self.assertGreater(right[0], center[0])
        self.assertLess(towards[1], center[1])
        self.assertLess(increasing_z[1], center[1])
        self.assertTrue(ax.zaxis_inverted())
        coordinates = self.frame._coordinates.copy()
        moves = self.motion.go_to_coordinates.call_count
        ax.view_init(elev=12, azim=45, roll=15)
        self.frame._update_surface_plot()
        self.assertEqual((ax.elev, ax.azim, ax.roll), (12, 45, 15))
        self.assertTrue(ax.zaxis_inverted())
        self.frame._btn_surface_reset.invoke()
        self.assertEqual((ax.elev, ax.azim, ax.roll), (30, -90, 0))
        self.assertTrue(ax.zaxis_inverted())
        self.assertEqual(self.frame._coordinates, coordinates)
        self.assertEqual(self.motion.go_to_coordinates.call_count, moves)

    def test_surface_handles_sparse_collinear_and_duplicate_points(self):
        self.frame._show_surface_plot()
        for points in ([(0., 0., 0.)], [(0., 0., 0.), (1., 1., .001)],
                       [(0., 0., 0.), (1., 1., .001), (2., 2., .002)],
                       [(0., 0., 0.), (0., 0., .001), (1., 1., .002)]):
            self.frame._coordinates = points
            self.frame._surface_triangles = None
            self.frame._update_surface_plot()
            self.assertIn('Points only', self.frame._surface_ax.get_title())
        self.frame._surface_canvas.draw()

    def test_embedded_surface_toggle_and_final_save_keeps_plot(self):
        self.frame._show_surface_plot()
        canvas = self.frame._surface_canvas
        self.frame._btn_surface.invoke()
        self.assertFalse(self.frame._surface_visible)
        self.frame._btn_surface.invoke()
        self.assertTrue(self.frame._surface_visible)
        self.assertIs(self.frame._surface_canvas, canvas)
        self.assertEqual(self.frame._surface_canvas.get_tk_widget().master, self.frame._surface_frame)
        self.assertFalse(any(isinstance(w, tk.Toplevel) for w in self.frame.winfo_children()))
        for _ in range(3):
            self.frame._commit_modification()
            self.wait_move()
        self.frame._save_modifications()
        self.assertIn('3/3 reviewed', self.frame._surface_ax.get_title())
        self.assertNotIn('Selected', self.frame._surface_ax.get_legend_handles_labels()[1])

    def test_embedded_surface_reflows_when_editor_is_resized(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.root.geometry('1350x850')
        self.root.deiconify()
        self.root.update()
        self.assertEqual(self.frame._surface_layout, 'side')
        self.assertGreater(self.frame._surface_frame.winfo_x(), self.frame._frm_controls.winfo_x())
        self.root.geometry('850x1000')
        self.root.update()
        self.assertEqual(self.frame._surface_layout, 'below')
        self.assertGreaterEqual(self.frame._surface_frame.winfo_y(),
                                self.frame._frm_controls.winfo_height())
        self.frame._btn_surface.invoke()
        self.root.update()
        self.assertFalse(self.frame._surface_frame.winfo_ismapped())
        self.enter('8.5')
        self.frame._commit_modification()
        self.wait_move()
        self.frame._btn_surface.invoke()
        self.root.update()
        self.assertTrue(self.frame._surface_frame.winfo_ismapped())
        self.assertIn('1/3 reviewed', self.frame._surface_ax.get_title())

    def test_flat_file_remains_flat_without_rounding_preview_or_navigation_edits(self):
        self.frame._cancel_modification()
        z = .1234567890123456
        source = [(0., 0., z), (1., 0., z), (0., 1., z), (1., 1., z)]
        self.frame._dict_mapUnit['flat'] = Coordinates('flat', source.copy())
        self.frame._combo_mapUnit.set('flat')
        self.frame._run_modify_z_coordinates()
        self.wait_move()
        ax = self.frame._surface_ax
        self.assertNotIn('Preview', ax.get_title())
        for artist in ax.collections:
            if hasattr(artist, '_offsets3d'):
                self.assertTrue(all(value == z*1000 for value in artist._offsets3d[2]))
        self.assertGreaterEqual(abs(ax.get_zlim()[1]-ax.get_zlim()[0]), 1.)
        self.frame._navigate_point(1)
        self.wait_move()
        self.assertEqual(self.frame._coordinates, source)
        self.assertNotIn('Preview', ax.get_title())

    def test_hover_coordinate_messages_do_not_resize_editor_or_switch_layout(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.root.geometry('1350x850')
        self.root.deiconify()
        self.root.update()
        before = (self.root.winfo_geometry(), self.frame.winfo_reqwidth(), self.frame._surface_layout)
        for message in ('x=0, y=0, z=0', 'x=123456789.123456 y=987654321.987654 z=123456.123456' * 4, ''):
            self.frame._surface_toolbar.set_message(message)
            self.root.update()
            self.assertEqual((self.root.winfo_geometry(), self.frame.winfo_reqwidth(),
                              self.frame._surface_layout), before)


if __name__ == '__main__':
    unittest.main()
