"""Real Tk layout checks without importing the instrument/configuration stack."""

import ast
from pathlib import Path
import queue
import threading
import math
import time
import tkinter as tk
from tkinter import ttk
from typing import Callable, Literal
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


class Coordinates:
    def __init__(self, name, points):
        self.mappingUnit_name = name
        self.mapping_coordinates = points


class Hub(list):
    def add_observer(self, callback):
        pass


def all_widgets(parent):
    return [child for widget in parent.winfo_children()
            for child in [widget, *all_widgets(widget)]]


namespace = dict(tk=tk, ttk=ttk, Callable=Callable, Literal=Literal, queue=queue,
                 threading=threading, math=math, messagebox=Mock(),
                 messagebox_request_input=Mock(), thread_assign=lambda f: f,
                 get_all_widgets=all_widgets, Frm_MotionController=object,
                 Frm_DataHub_Mapping=object, Frm_DataHub_Image=object,
                 Frm_DataHub_ImgCal=object, List_MeaCoor_Hub=Hub,
                 MeaCoor_mm=Coordinates)


def load_class(path, name):
    source = ROOT / path
    tree = ast.parse(source.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace[name]


namespace['MapMod1'] = load_class('iris/gui/submodules/meaCoor_modifier/every_z.py', 'EveryZ')
load_class('iris/gui/submodules/scrollable_frame.py', 'ScrollableFrame')
namespace['Map1'] = load_class(
    'iris/gui/submodules/meaCoor_generator/rectangle_endToEnd.py', 'Rect_EndToEnd')
namespace['Map2'] = load_class(
    'iris/gui/submodules/meaCoor_generator/rectangle_aroundCentre.py', 'Rect_AroundCentre')
namespace['ZScan1'] = load_class(
    'iris/gui/submodules/meaCoor_generator/line_zScan.py', 'ZScanMethod_linear')
for name in ('Map3', 'Map4', 'Map5', 'Map6', 'MapMod2', 'MapMod3', 'MapMod4', 'MapMod5'):
    namespace[name] = namespace['Map1']
load_class('iris/gui/hilvl_coorGen.py', 'Frm_Treeview_MappingCoordinates')
load_class('iris/gui/hilvl_coorGen.py', 'sFrm_CoorModifier')
Generator = load_class('iris/gui/hilvl_coorGen.py', 'Frm_CoorGenerator')


class CoordinateLayoutTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry('1000x900')
        self.hub = Hub([Coordinates('flat', [(0, 0, .1), (1, 0, .1), (0, 1, .1)])])
        self.motion = Mock()
        self.motion.check_coordinates.return_value = True
        self.frame = Generator(self.root, self.hub, self.motion, Mock(), Mock(), Mock())
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.notebook = self.frame._notebook
        self.editor = self.frame._sfrm_mapping_coorMod._current_map_method
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_generator_controls_fit_after_narrow_z_editor_and_resize(self):
        self.root.geometry('920x1000')
        self.root.update()
        expected_height = self.notebook.winfo_height()
        self.notebook.select(self.frame._modifier_page)
        self.root.geometry('750x650')
        self.root.update()
        self.editor._combo_mapUnit.set('flat')
        self.editor._run_modify_z_coordinates()
        self.wait_move()
        self.notebook.select(self.frame._generator_page)
        self.frame._combo_mappingmethods.set('2. Around center')
        self.frame.show_frm_mapping_method()
        self.root.geometry('920x1000')
        self.root.update()
        self.assertEqual(self.notebook.winfo_height(), expected_height)
        button = self.frame._btn_generate_mappingCoor_zscan
        bottom = button.winfo_rooty() + button.winfo_height()
        self.assertLessEqual(bottom, self.root.winfo_rooty() + self.root.winfo_height())

    def wait_move(self):
        deadline = time.monotonic() + 2
        while self.editor._moving and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.005)
        self.assertFalse(self.editor._moving)

    def test_narrow_editor_scrolls_and_wide_editor_shrinks_again(self):
        self.notebook.select(self.frame._modifier_page)
        self.root.geometry('750x650')
        self.root.update()
        page = self.frame._modifier_page
        self.assertEqual(self.editor._surface_layout, 'below')
        self.assertLess(page.canvas.yview()[1], 1.)
        # Scroll the bottom of the plot into the visible viewport.
        page.canvas.yview_moveto(1.)
        self.root.update()
        plot = self.editor._surface_frame
        self.assertLessEqual(plot.winfo_rooty() + plot.winfo_height(),
                             page.canvas.winfo_rooty() + page.canvas.winfo_height())
        narrow_height = page.content.winfo_height()
        self.root.geometry('1350x1000')
        self.root.update()
        self.assertEqual(self.editor._surface_layout, 'side')
        self.assertLess(page.content.winfo_height(), narrow_height)
        self.assertEqual(page.canvas.yview(), (0., 1.))
        self.assertGreater(self.editor._surface_frame.winfo_x(),
                           self.editor._frm_controls.winfo_x())

    def test_switching_tabs_keeps_pending_edits_and_does_not_move_stage(self):
        self.notebook.select(self.frame._modifier_page)
        self.editor._combo_mapUnit.set('flat')
        self.editor._run_modify_z_coordinates()
        self.wait_move()
        self.editor._entry_newZCoor.delete(0, tk.END)
        self.editor._entry_newZCoor.insert(0, '105.25')
        moves = self.motion.go_to_coordinates.call_count
        for _ in range(3):
            self.root.geometry('750x650')
            self.notebook.select(self.frame._generator_page)
            self.root.update()
            self.root.geometry('1350x1000')
            self.notebook.select(self.frame._modifier_page)
            self.root.update()
        self.assertIs(self.frame._sfrm_mapping_coorMod._current_map_method, self.editor)
        self.assertTrue(self.editor._editing)
        self.assertEqual(self.editor._entry_newZCoor.get(), '105.25')
        self.assertEqual(self.motion.go_to_coordinates.call_count, moves)
        geometry = self.root.winfo_geometry()
        for message in ('x=1 y=2 z=3', 'x=123456789.123456 y=987654321.987654 z=123456.123456' * 4, ''):
            self.editor._surface_toolbar.set_message(message)
            self.root.update()
            self.assertEqual(self.root.winfo_geometry(), geometry)


if __name__ == '__main__':
    unittest.main()
