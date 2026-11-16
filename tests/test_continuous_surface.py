"""Surface geometry, sampled feedback and mapping integration without hardware."""

import json
import ast
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_integration_experiment as fixture
import test_mapping_reliability as mapping_fixture
from iris.utils.continuous_surface import SurfaceLine, SurfaceMove, build_surface_lines, plan_surface_speed
from iris.gui.motion_video import Frm_MotionController
from iris.utils.autosave_storage import run_info


XY_LIMITS = dict(maximum_speed_mm_s=10., minimum_relative_percent=.001)
Z_LIMITS = dict(minimum_mm=0., maximum_mm=.45, settling_s=.5)


class ProfileTests(unittest.TestCase):
    points = [(0., 0., .1), (.05, 0., .104), (.1, 0., .1),
              (0., .1, .11), (.05, .1, .114), (.1, .1, .11)]

    def test_nonlinear_middle_points_and_reversed_snake_lines(self):
        lines = build_surface_lines(self.points)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[1].start, self.points[-1])
        self.assertAlmostEqual(lines[0].target_z((.025, 0)), .102)
        self.assertAlmostEqual(lines[0].target_z((.05, 0)), .104)
        self.assertAlmostEqual(lines[1].target_z((.025, .1)), .112)
        self.assertEqual(lines[0].target_z((10, 0)), .1)

    def test_y_direction_raster_and_unsorted_source(self):
        points = [(y, x, z) for x, y, z in reversed(self.points)]
        lines = build_surface_lines(points, axis=1, snake=False)
        self.assertLess(lines[1].start[1], lines[1].end[1])
        self.assertAlmostEqual(lines[1].target_z((.1, .05)), .114)

    def test_conflicting_duplicates_and_sparse_lines_are_rejected(self):
        for points in ([(0, 0, .1)], [(0, 0, .1), (0, 0, .2)], [(0, 0, float('nan'))]):
            with self.assertRaises(ValueError):
                build_surface_lines(points)
        self.assertEqual(len(build_surface_lines(self.points + [self.points[0]])[0].points), 3)

    def test_speed_cap_uses_interior_slope_and_preserves_flat_speed(self):
        lines = build_surface_lines(self.points)
        relative = plan_surface_speed(lines, 20., XY_LIMITS, Z_LIMITS, .005)
        self.assertAlmostEqual(relative, .005*.5/(.08*.75)/10*100)
        flat = build_surface_lines([(0, 0, .1), (.1, 0, .1)])
        self.assertEqual(plan_surface_speed(flat, 20., XY_LIMITS, Z_LIMITS, .005), 20.)

    def test_bad_tolerance_travel_and_unreachable_speed_are_rejected(self):
        lines = build_surface_lines(self.points)
        for value in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                plan_surface_speed(lines, 20., XY_LIMITS, Z_LIMITS, value)
        with self.assertRaisesRegex(ValueError, 'travel range'):
            plan_surface_speed(build_surface_lines([(0, 0, .1), (1, 0, .5)]),
                               20., XY_LIMITS, Z_LIMITS, .005)
        with self.assertRaisesRegex(ValueError, 'below the XY stage minimum'):
            plan_surface_speed(lines, 20., dict(XY_LIMITS, minimum_relative_percent=50.), Z_LIMITS, .005)


class ScriptedStage:
    """Advance reported XY on reads so tests need no wall-clock motion model."""
    def __init__(self, points=(0., .025, .05, .075, .1), z=.1):
        self.positions = iter(points)
        self.x = 0.
        self.z = z
        self.end = threading.Event()
        self.targets = []
        self.z_targets = []
        self.stops = 0
        self.running = True

    def move_xy(self, target):
        self.targets.append(target)
        if not self.end.wait(2):
            raise TimeoutError('Test stage stalled')

    def read_xy(self):
        self.x = next(self.positions, self.x)
        if self.x == .1:
            self.end.set()
        return self.x, 0.

    def move_z(self, target):
        self.z_targets.append(target)
        self.z = target

    def stop(self):
        self.stops += 1
        self.end.set()


class FeedbackTests(unittest.TestCase):
    profile = SurfaceLine(((0., 0., .1), (.05, 0., .104), (.1, 0., .1)), 0)

    def move(self, stage, **kwargs):
        move = SurfaceMove(self.profile, stage.move_xy, stage.read_xy, stage.move_z,
                           lambda: stage.z, stage.stop, lambda: stage.running, .005,
                           poll_s=.001, **kwargs)
        move.start()
        for worker in move.workers:
            worker.join(3)
        self.assertTrue(all(not worker.is_alive() for worker in move.workers))
        return move

    def test_tracks_reported_position_and_nonflat_interior(self):
        stage = ScriptedStage()
        move = self.move(stage)
        self.assertTrue(move.failures.empty())
        self.assertEqual(stage.targets, [(.1, 0.)])
        self.assertTrue(any(abs(z-.104) < 1e-10 for z in stage.z_targets))
        self.assertAlmostEqual(stage.z, .1)
        self.assertTrue(move.report['complete'])
        self.assertLessEqual(move.report['maximum_observed_error_um'], 5.)

    def test_stop_holds_current_z_without_jumping_to_end(self):
        stage = ScriptedStage()
        original = stage.move_z
        def stop_after_update(target):
            original(target)
            stage.running = False
        stage.move_z = stop_after_update
        move = self.move(stage)
        self.assertFalse(move.report['complete'])
        self.assertEqual(len(stage.z_targets), 1)
        self.assertAlmostEqual(stage.z, .102)
        self.assertGreaterEqual(stage.stops, 1)

    def test_excessive_focus_error_stops_xy_and_reports_failure(self):
        stage = ScriptedStage()
        original = stage.move_z
        def drift(target):
            original(target)
            stage.z -= .02
        stage.move_z = drift
        move = self.move(stage)
        self.assertIn('exceeds', str(move.failures.get_nowait()))
        self.assertFalse(move.report['complete'])
        self.assertGreater(stage.stops, 0)

    def test_initial_focus_error_prevents_any_movement(self):
        stage = ScriptedStage(z=.12)
        with self.assertRaisesRegex(RuntimeError, 'exceeds'):
            self.move(stage)
        self.assertEqual(stage.targets, [])
        self.assertEqual(stage.z_targets, [])

    def test_z_driver_error_stops_xy_without_marking_complete(self):
        stage = ScriptedStage()
        stage.move_z = Mock(side_effect=RuntimeError('lost piezo connection'))
        move = self.move(stage)
        self.assertIn('lost piezo', str(move.failures.get_nowait()))
        self.assertFalse(move.report['complete'])
        self.assertGreater(stage.stops, 0)

    def test_motion_wrapper_keeps_timed_out_workers_guarded(self):
        stage = ScriptedStage()
        block = threading.Event()
        entered = threading.Event()
        original = stage.move_z
        def blocked(target):
            entered.set()
            block.wait(2)
            original(target)
        frame = SimpleNamespace(
            ctrl_xy=SimpleNamespace(move_direct=stage.move_xy, get_coordinates=stage.read_xy, stop_move=stage.stop),
            ctrl_z=SimpleNamespace(move_direct=blocked, get_coordinates=lambda: stage.z),
            _flg_ontarget_gotocoor=threading.Event())
        frame._check_mapping_motion_idle = lambda: Frm_MotionController._check_mapping_motion_idle(frame)
        def timeout(*args):
            self.assertTrue(entered.wait(1))
            raise TimeoutError('stalled')
        try:
            with patch('iris.gui.motion_video.wait_for_motion', side_effect=timeout):
                with self.assertRaises(TimeoutError):
                    Frm_MotionController.follow_surface_line(frame, self.profile, .005, lambda: True, {})
            with self.assertRaisesRegex(RuntimeError, 'still running'):
                frame._check_mapping_motion_idle()
        finally:
            block.set()
            stage.end.set()
            for worker in frame._mapping_move_threads:
                worker.join(3)
        frame._check_mapping_motion_idle()
        self.assertFalse(frame._flg_ontarget_gotocoor.is_set())


class MappingSurfaceTests(unittest.TestCase):
    def frame(self):
        helper = mapping_fixture.MappingTests()
        self.addCleanup(helper.doCleanups)
        frame = helper.frame()
        frame._bool_continuous_surface = SimpleNamespace(get=lambda: True)
        frame._str_surface_tolerance_um = SimpleNamespace(get=lambda: '5')
        frame._str_scanDir = SimpleNamespace(get=lambda: fixture.raman_gui.Enum_ScanDir.XDIR.value)
        frame._str_scanMethod = SimpleNamespace(get=lambda: fixture.raman_gui.Enum_ScanMthd.SNAKE.value)
        frame._scramble_mapping_coordinates = lambda coordinates, mode: coordinates
        frame.motion_controller.calculate_vel_relative.return_value = 20.
        frame.motion_controller.ctrl_xy.get_surface_following_limits.return_value = XY_LIMITS
        frame.motion_controller.ctrl_z.get_surface_following_limits.return_value = Z_LIMITS
        return helper, frame

    def run_scan(self, stop=False):
        helper, frame = self.frame()
        helper.continuous(frame, stop_on_move=2 if stop else None)
        def follow(profile, tolerance, running, report):
            frame.motion_controller.go_to_coordinates(*profile.end)
            report.update(complete=not stop, maximum_observed_error_um=2.)
        frame.motion_controller.follow_surface_line.side_effect = follow
        with tempfile.TemporaryDirectory() as directory:
            enum = SimpleNamespace(AUTOSAVE_PATH=SimpleNamespace(value=directory))
            with patch.object(fixture.raman_gui, 'SaveParamsEnum', enum):
                fixture.Frm_HighLvlController_Raman._perform_continuousMapping(
                    frame, Mock(), ProfileTests.points, .1, 'surface')
            recovery = Path(frame._mapping_recovery_dir)
            settings = json.loads((recovery / 'settings.json').read_text())
            report = json.loads((recovery / 'z_surface_tracking.json').read_text())
            remaining = json.loads((recovery / 'remaining_coordinates.json').read_text())
            info = run_info(directory, recovery.name)
            self.assertFalse(info.get('protected'))
            self.assertEqual(settings['z_surface_following']['tolerance_um'], 5.)
            self.assertEqual(frame._stage_speeds, [53., 27.])
            return frame, report, remaining

    def test_enabled_mode_uses_full_profiles_and_saves_quality_report(self):
        frame, report, remaining = self.run_scan()
        self.assertEqual(frame.motion_controller.follow_surface_line.call_count, 2)
        self.assertEqual(len(frame.motion_controller.follow_surface_line.call_args.args[0].points), 3)
        self.assertEqual(len(report['lines']), 2)
        self.assertTrue(all(line['complete'] for line in report['lines']))
        self.assertEqual(remaining, [])

    def test_stop_preserves_interior_z_points_for_resuming(self):
        frame, report, remaining = self.run_scan(stop=True)
        self.assertTrue(frame._flg_meaCancelled)
        self.assertEqual(len(remaining), 6)
        self.assertIn(list(ProfileTests.points[1]), remaining)
        self.assertFalse(report['lines'][0]['complete'])

    def test_out_of_range_profile_is_rejected_before_acquisition_or_motion(self):
        _, frame = self.frame()
        with self.assertRaisesRegex(ValueError, 'travel range'):
            fixture.Frm_HighLvlController_Raman._perform_continuousMapping(
                frame, Mock(), [(0, 0, .1), (.1, 0, .6)], .1, 'invalid')
        frame.motion_controller.go_to_coordinates.assert_not_called()
        frame.raman_controller.perform_ContinuousMeasurement_trigger.assert_not_called()


class ControllerLimitTests(unittest.TestCase):
    def method(self, filename, name):
        path = Path(__file__).resolve().parents[1] / 'iris/controllers' / filename
        tree = ast.parse(path.read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
        method = next(node for node in cls.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'get_surface_following_limits')
        namespace = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        return namespace['get_surface_following_limits']

    def test_piezo_limits_convert_device_micrometres_to_map_millimetres(self):
        read = self.method('z_stage_controller_pfm450.py', 'ZController_PFM450')
        channel = SimpleNamespace(GetMaxTravel=lambda: 450.)
        limits = read(SimpleNamespace(_min_travel=0., _channel=channel))
        self.assertEqual(limits, Z_LIMITS)

    def test_xy_limit_caps_both_axes_and_preserves_minimum(self):
        read = self.method('xy_stage_controller_zaber.py', 'XYController_Zaber')
        limits = read(SimpleNamespace(motorx_maxvel_mms=10., motory_maxvel_mms=20., _min_vel_mmS=.0001))
        self.assertEqual(limits, dict(maximum_speed_mm_s=20., minimum_relative_percent=.001))


if __name__ == '__main__':
    unittest.main()
