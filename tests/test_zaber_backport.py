"""Test the upstream Zaber reliability backport without opening a serial port."""

import contextlib
import io
import pickle
import threading
import unittest
from unittest.mock import Mock

import test_integration_experiment as integration_fixture  # Isolate IRIS config imports.

try:
    import zaber_motion as zm
    from zaber_motion.dto.exceptions import CommandFailedExceptionData
    from iris.controllers.xy_stage_controller_zaber import XYController_Zaber
except ImportError as error:
    raise unittest.SkipTest(f'Optional Zaber dependency unavailable: {error}')


def sdk_error():
    details = CommandFailedExceptionData(command='move abs 1', response_data='BADDATA',
                                        reply_flag='RJ', status='IDLE', warning_flag='--',
                                        device_address=1, axis_number=1, id=0)
    return zm.CommandFailedException('Simulated command rejection', details)


class ZaberBackportTests(unittest.TestCase):
    def setUp(self):
        # Bypass __init__: its normal purpose is to connect/home real hardware.
        self.controller = XYController_Zaber.__new__(XYController_Zaber)
        stage = self.controller
        stage.motorx = Mock(spec=['home', 'move_absolute', 'move_velocity', 'move_relative',
                                 'stop', 'wait_until_idle'])
        stage.motory = Mock(spec=['home', 'move_absolute', 'move_velocity', 'move_relative',
                                 'stop', 'wait_until_idle'])
        stage._lock = threading.Lock()
        stage.motorx_state = stage.motory_state = 0
        stage.motorx_vel_mms, stage.motory_vel_mms = 1.25, 2.5
        stage.unit_len = zm.Units.LENGTH_MILLIMETRES
        stage.unit_vel = zm.Units.VELOCITY_MILLIMETRES_PER_SECOND
        stage._flipxy = stage._invertx = stage._inverty = False
        stage.dict_ctrl_remap = {key: key for key in ('xfwd', 'xrev', 'yfwd', 'yrev')}
        stage._jog_step_mm = .025

    def assert_idle_and_unlocked(self):
        self.assertEqual((self.controller.motorx_state, self.controller.motory_state), (0, 0))
        self.assertTrue(self.controller._lock.acquire(blocking=False))
        self.controller._lock.release()

    def invoke(self, name, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return getattr(self.controller, name)(*args)

    def test_absolute_move_keeps_coordinates_speeds_and_waits(self):
        self.invoke('move_direct', (1., 2.))
        self.controller.motorx.move_absolute.assert_called_once_with(
            1., unit=self.controller.unit_len, velocity=1.25,
            velocity_unit=self.controller.unit_vel, wait_until_idle=False)
        self.controller.motory.move_absolute.assert_called_once_with(
            2., unit=self.controller.unit_len, velocity=2.5,
            velocity_unit=self.controller.unit_vel, wait_until_idle=False)
        self.controller.motorx.wait_until_idle.assert_called_once()
        self.controller.motory.wait_until_idle.assert_called_once()
        self.assert_idle_and_unlocked()

    def test_absolute_move_preserves_axis_remapping(self):
        self.controller._invertx = True
        self.controller._flipxy = True
        self.invoke('move_direct', (1., 2.))
        self.assertEqual(self.controller.motorx.move_absolute.call_args.args, (2.,))
        self.assertEqual(self.controller.motory.move_absolute.call_args.args, (-1.,))

    def test_sdk_move_failure_is_portable_and_allows_next_request(self):
        original = sdk_error()
        self.controller.motorx.move_absolute.side_effect = [original, None]
        with self.assertRaises(RuntimeError) as caught:
            self.invoke('move_direct', (1., 2.))
        self.assertIs(type(caught.exception), RuntimeError)
        roundtrip = pickle.loads(pickle.dumps(caught.exception))
        self.assertEqual(str(roundtrip), str(original))
        self.assert_idle_and_unlocked()
        self.invoke('move_direct', (3., 4.))
        self.assertEqual(self.controller.motorx.move_absolute.call_count, 2)
        self.assert_idle_and_unlocked()

    def test_failures_during_move_or_wait_clear_flags(self):
        for axis_name, operation in (('motorx', 'move_absolute'), ('motory', 'move_absolute'),
                                     ('motorx', 'wait_until_idle'), ('motory', 'wait_until_idle')):
            with self.subTest(axis=axis_name, operation=operation):
                self.setUp()
                getattr(getattr(self.controller, axis_name), operation).side_effect = sdk_error()
                with self.assertRaises(RuntimeError):
                    self.invoke('move_direct', (1., 2.))
                self.assert_idle_and_unlocked()

    def test_bad_coordinate_input_does_not_mark_motors_running(self):
        with self.assertRaises(ValueError):
            self.invoke('move_direct', (1., 2., 3.))
        self.assert_idle_and_unlocked()

    def test_homing_failure_clears_flags_and_unlocks(self):
        for axis_name, operation in (('motorx', 'home'), ('motory', 'home'),
                                     ('motorx', 'wait_until_idle'), ('motory', 'wait_until_idle')):
            with self.subTest(axis=axis_name, operation=operation):
                self.setUp()
                getattr(getattr(self.controller, axis_name), operation).side_effect = sdk_error()
                with self.assertRaises(RuntimeError):
                    self.invoke('homing_n_coor_calibration')
                self.assert_idle_and_unlocked()

    def test_successful_continuous_move_stays_busy_until_stop(self):
        self.invoke('move_continuous', 'xfwd')
        self.assertEqual((self.controller.motorx_state, self.controller.motory_state), (1, 0))
        self.controller.motorx.move_velocity.assert_called_once_with(1.25, unit=self.controller.unit_vel)
        self.invoke('stop_move')
        self.controller.motorx.stop.assert_called_once_with(wait_until_idle=False)
        self.controller.motory.stop.assert_called_once_with(wait_until_idle=False)
        self.assert_idle_and_unlocked()

    def test_continuous_failure_and_stop_failure_clear_flags(self):
        self.controller.motory.move_velocity.side_effect = sdk_error()
        with self.assertRaises(RuntimeError):
            self.invoke('move_continuous', 'yrev')
        self.assert_idle_and_unlocked()
        self.controller.motorx_state = self.controller.motory_state = 1
        self.controller.motorx.stop.side_effect = sdk_error()
        with self.assertRaises(RuntimeError):
            self.invoke('stop_move')
        self.assert_idle_and_unlocked()

    def test_jog_failure_clears_flags(self):
        self.controller.motorx.move_relative.side_effect = sdk_error()
        with self.assertRaises(RuntimeError):
            self.invoke('move_jog', 'xrev')
        self.assert_idle_and_unlocked()

    def test_unexpected_finite_move_error_still_cleans_up(self):
        self.controller.motorx.move_absolute.side_effect = ValueError('invalid stage request')
        with self.assertRaisesRegex(ValueError, 'invalid stage request'):
            self.invoke('move_direct', (1., 2.))
        self.assert_idle_and_unlocked()

    def test_busy_stage_rejects_additional_movement_commands(self):
        for operation, args in (('move_direct', ((1., 2.),)), ('move_jog', ('xfwd',)),
                                 ('move_continuous', ('yfwd',)), ('homing_n_coor_calibration', ())):
            with self.subTest(operation=operation):
                self.setUp()
                self.controller.motorx_state = 1
                self.invoke(operation, *args)
                self.assertEqual(self.controller.motorx.method_calls, [])
                self.assertEqual(self.controller.motory.method_calls, [])


if __name__ == '__main__':
    unittest.main()
