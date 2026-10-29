"""No hardware access: test iBeam identity checks, status and manual power."""

from dataclasses import FrozenInstanceError, replace
import math
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
os.environ.setdefault('MPLBACKEND', 'Agg')
with tempfile.TemporaryDirectory() as isolated:
    original_directory = Path.cwd()
    try:
        os.chdir(isolated)
        from iris.controllers.laser_controller_toptica import IBeamProfile, IBeamController
        from iris.gui.laser_status import load_ibeam_profiles, Frm_IBeamStatus
    finally:
        os.chdir(original_directory)


class ReadOnlyLaserTests(unittest.TestCase):
    def setUp(self):
        self.device = Mock(spec=['get_device_info', 'is_enabled', 'get_output_power',
                                 'get_channel_power', 'is_channel_enabled', 'set_channel_power', 'close'])
        self.device.get_device_info.return_value = SimpleNamespace(serial='12345', version='1.0')
        self.device.is_enabled.return_value = True
        self.device.get_output_power.return_value = 0.095
        self.device.get_channel_power.return_value = [0.100, 0.0005]
        self.device.is_channel_enabled.return_value = [True, False]
        self.factory = Mock(return_value=self.device)
        self.controller = IBeamController(self.factory)
        self.profile = IBeamProfile('120 mW laser', 'COM4', 120.)

    def test_initialization_opens_nothing(self):
        self.assertFalse(self.controller.connected)
        self.factory.assert_not_called()
        self.controller.close()
        self.device.close.assert_not_called()

    def test_connection_reads_without_output_commands(self):
        status = self.controller.connect(self.profile)
        self.factory.assert_called_once_with(('COM4', 115200))
        self.assertEqual(status.serial, '12345')
        self.assertTrue(status.enabled)
        self.assertAlmostEqual(status.output_mw, 95.)
        self.assertEqual(status.channel_setpoints_mw, (100., 0.5))
        self.assertEqual(status.channel_enabled, (True, False))
        self.assertEqual([call[0] for call in self.device.method_calls],
                         ['get_device_info', 'get_channel_power', 'is_channel_enabled', 'is_enabled', 'get_output_power'])
        self.controller.close()
        self.assertFalse(self.controller.connected)
        self.device.close.assert_called_once()

    def test_switch_requires_disconnect(self):
        self.controller.connect(self.profile)
        with self.assertRaisesRegex(RuntimeError, 'Disconnect'):
            self.controller.connect(replace(self.profile, max_power_mw=250.))
        self.factory.assert_called_once()

    def test_read_failure_releases_port(self):
        self.device.get_output_power.side_effect = TimeoutError('read timeout')
        with self.assertRaisesRegex(TimeoutError, 'read timeout'):
            self.controller.connect(self.profile)
        self.assertFalse(self.controller.connected)
        self.device.close.assert_called_once()

    def test_wrong_serial_releases_port_before_power_read(self):
        with self.assertRaisesRegex(ValueError, 'serial number'):
            self.controller.connect(replace(self.profile, expected_serial='different'))
        self.device.get_output_power.assert_not_called()
        self.device.close.assert_called_once()

    def test_invalid_readbacks_are_rejected(self):
        for value in (math.nan, math.inf, -0.1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.controller._mw(value)

    def test_profiles_have_distinct_ratings_and_configurable_ports(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.ini'
            profiles, baudrate = load_ibeam_profiles(str(config))
            low, high = profiles.values()
            self.assertEqual((low.max_power_mw, high.max_power_mw), (120, 250))
            self.assertEqual((low.port, high.port), ('COM4', 'COM4'))
            self.assertEqual((low.wavelength_nm, high.wavelength_nm), (785., 785.))
            self.assertEqual(baudrate, 115200)
            with self.assertRaises(FrozenInstanceError):
                low.max_power_mw = 250
            content = config.read_text().replace('port_250mw = "COM4"', 'port_250mw = "COM5"')
            config.write_text(content)
            updated, _ = load_ibeam_profiles(str(config))
            self.assertEqual(list(updated.values())[1].port, 'COM5')

    def enable_power_control(self):
        self.profile = replace(self.profile, expected_serial='12345')
        self.device.get_channel_power.return_value = [0.100, 0.]
        def set_channel(channel, watts):
            self.assertEqual(channel, 1)
            self.device.get_channel_power.return_value = [watts] + self.device.get_channel_power.return_value[1:]
            return watts
        self.device.set_channel_power.side_effect = set_channel
        self.controller.connect(self.profile)

    def test_power_change_converts_to_watts_and_verifies_setpoint(self):
        self.enable_power_control()
        status = self.controller.set_power_mw('80.125')
        self.device.set_channel_power.assert_called_once_with(1, 0.080125)
        self.assertEqual(status.channel_setpoints_mw, (80.125, 0.))
        self.assertEqual(status.output_mw, 95.)  # Output readback may differ from setpoint.
        self.assertTrue(status.enabled)  # No enable/disable API is available in the fake.

    def test_invalid_power_never_writes(self):
        self.enable_power_control()
        for value in ('bad', 'NaN', 'Infinity', '-1', '120.001', '0.0001'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.controller.set_power_mw(value)
        self.device.set_channel_power.assert_not_called()

    def test_boundaries_and_250mw_profile_limit(self):
        self.enable_power_control()
        for value in (0, 120):
            self.controller.set_power_mw(value)
        self.controller.close()
        self.device.get_device_info.return_value = SimpleNamespace(serial='250serial', version='1')
        self.controller.connect(IBeamProfile('250 mW', 'COM4', 250., expected_serial='250serial'))
        self.controller.set_power_mw(250)
        with self.assertRaises(ValueError):
            self.controller.set_power_mw(250.001)

    def test_unbound_250mw_profile_cannot_write(self):
        self.controller.connect(IBeamProfile('250 mW', 'COM4', 250.))
        self.assertFalse(self.controller.power_control_available)
        with self.assertRaisesRegex(ValueError, 'serial number'):
            self.controller.set_power_mw(200)
        self.device.set_channel_power.assert_not_called()

    def test_identity_is_checked_again_before_write(self):
        self.enable_power_control()
        self.device.get_device_info.return_value = SimpleNamespace(serial='different', version='1')
        with self.assertRaises(ValueError):
            self.controller.set_power_mw(80)
        self.device.set_channel_power.assert_not_called()
        self.assertFalse(self.controller.connected)

    def test_other_channels_prevent_power_change(self):
        self.enable_power_control()
        self.device.get_channel_power.return_value = [0.1, 0.01]
        self.device.is_channel_enabled.return_value = [True, True]
        with self.assertRaisesRegex(ValueError, 'channel 2 is ON at 10 mW'):
            self.controller.set_power_mw(80)
        self.device.set_channel_power.assert_not_called()

    def test_disabled_channel_preset_does_not_block_or_get_overwritten(self):
        self.enable_power_control()
        self.device.get_channel_power.return_value = [.1, .06]
        status = self.controller.set_power_mw(80)
        self.assertEqual(status.channel_setpoints_mw, (80., 60.))
        self.assertEqual(status.channel_enabled, (True, False))
        self.device.set_channel_power.assert_called_once_with(1, .08)
        self.assertTrue(self.controller.connected)
        self.controller.prepare_power_experiment()

    def test_other_enabled_channel_at_zero_is_allowed(self):
        self.enable_power_control()
        self.device.is_channel_enabled.return_value = [True, True]
        self.controller.set_power_mw(80)
        self.device.set_channel_power.assert_called_once_with(1, .08)

    def test_incomplete_channel_enable_readback_closes_without_writing(self):
        self.enable_power_control()
        self.device.is_channel_enabled.return_value = [True]
        with self.assertRaisesRegex(ValueError, 'incomplete channel enable'):
            self.controller.set_power_mw(80)
        self.device.set_channel_power.assert_not_called()
        self.assertFalse(self.controller.connected)

    def test_failed_write_or_mismatch_disconnects_and_reports_uncertainty(self):
        for failure in ('timeout', 'mismatch'):
            with self.subTest(failure=failure):
                self.setUp()
                self.enable_power_control()
                if failure == 'timeout':
                    self.device.set_channel_power.side_effect = TimeoutError('no reply')
                else:
                    self.device.set_channel_power.side_effect = lambda channel, watts: 0.099
                with self.assertRaisesRegex(RuntimeError, 'may have changed'):
                    self.controller.set_power_mw(80)
                self.assertFalse(self.controller.connected)
                self.device.set_channel_power.assert_called_once()

    def test_duplicate_serial_profiles_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.ini'
            load_ibeam_profiles(str(config))
            text = config.read_text().replace('serial_120mw = ""', 'serial_120mw = "same"')
            config.write_text(text.replace('serial_250mw = ""', 'serial_250mw = "same"'))
            with self.assertRaisesRegex(ValueError, 'different laser serial'):
                load_ibeam_profiles(str(config))


class Value:
    def __init__(self, value=''):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class LaserUIStateTests(unittest.TestCase):
    def test_blocked_power_change_keeps_current_readback(self):
        status = SimpleNamespace(serial='12345', firmware='1', enabled=True, output_mw=100.,
                                 channel_setpoints_mw=(100., 20.), channel_enabled=(True, True))
        future = Mock()
        future.done.return_value = True
        future.result.side_effect = ValueError('channel 2 is ON at 20 mW')
        frame = SimpleNamespace(_closing=False, _future=future, _operation='power',
                                controller=SimpleNamespace(connected=True, last_status=status),
                                _status=Value(), _readback=Value(), _power_busy_changed=Mock(),
                                _update_controls=Mock())
        frame._render_laser_readback = Frm_IBeamStatus._render_laser_readback.__get__(frame)
        Frm_IBeamStatus._poll(frame)
        self.assertIn('no power command sent', frame._status.get())
        self.assertIn('Channel 2: ON, setpoint 20 mW', frame._readback.get())
        self.assertNotIn('COM port', frame._readback.get())

    def test_readback_distinguishes_disabled_presets(self):
        frame = SimpleNamespace(_readback=Value())
        status = SimpleNamespace(serial='12345', firmware='1', enabled=True, output_mw=80.,
                                 channel_setpoints_mw=(80., 60.), channel_enabled=(True, False))
        Frm_IBeamStatus._render_laser_readback(frame, status)
        self.assertIn('Channel 2: OFF, setpoint 60 mW', frame._readback.get())

    def test_reserved_experiment_blocks_manual_serial_commands(self):
        frame = SimpleNamespace(_closing=False, _future=None, _experiment_reserved=True)
        operation = Mock()
        Frm_IBeamStatus._submit(frame, operation, 'Read')
        operation.assert_not_called()

    def test_cannot_reserve_during_pending_manual_operation(self):
        frame = SimpleNamespace(_closing=False, _future=Mock(), _experiment_reserved=False)
        with self.assertRaises(ValueError):
            Frm_IBeamStatus.reserve_for_experiment(frame)

    def test_profile_and_port_are_locked_while_connected(self):
        frame = SimpleNamespace(_future=None, controller=SimpleNamespace(connected=True, power_control_available=False),
                                _power_note=Value())
        for name in ('_profile_selector', '_port_entry', '_connect', '_refresh', '_disconnect', '_power_entry', '_apply_power'):
            setattr(frame, name, Mock())
        Frm_IBeamStatus._update_controls(frame)
        frame._profile_selector.configure.assert_called_with(state='disabled')
        frame._port_entry.configure.assert_called_with(state='disabled')
        frame._disconnect.configure.assert_called_with(state='normal')
        frame.controller.connected = False
        Frm_IBeamStatus._update_controls(frame)
        frame._profile_selector.configure.assert_called_with(state='readonly')
        frame._connect.configure.assert_called_with(state='normal')

    def test_manual_power_disabled_without_verified_serial(self):
        frame = SimpleNamespace(_future=None, controller=SimpleNamespace(connected=True, power_control_available=False),
                                _power_note=Value())
        for name in ('_profile_selector', '_port_entry', '_connect', '_refresh', '_disconnect', '_power_entry', '_apply_power'):
            setattr(frame, name, Mock())
        Frm_IBeamStatus._update_controls(frame)
        frame._apply_power.configure.assert_called_with(state='disabled')
        frame.controller.power_control_available = True
        frame.controller.profile = IBeamProfile('120mW', 'COM4', 120.)
        Frm_IBeamStatus._update_controls(frame)
        frame._apply_power.configure.assert_called_with(state='normal')

    def test_acquisition_blocks_power_changes(self):
        frame = SimpleNamespace(_future=None, _closing=False, _acquisition_busy=lambda: True,
                                _status=Value(), _submit=Mock())
        Frm_IBeamStatus.apply_power(frame)
        frame._submit.assert_not_called()
        self.assertIn('Stop the acquisition', frame._status.get())

    def test_connection_error_clears_old_readback(self):
        future = Mock()
        future.done.return_value = True
        future.result.side_effect = RuntimeError('port busy')
        frame = SimpleNamespace(_closing=False, _future=future, _status=Value(),
                                _readback=Value('Old reading'), _update_controls=Mock())
        Frm_IBeamStatus._poll(frame)
        self.assertIn('port busy', frame._status.get())
        self.assertIn('No current readback', frame._readback.get())
        self.assertIsNone(frame._future)
        frame._update_controls.assert_called_once()


if __name__ == '__main__':
    unittest.main()
