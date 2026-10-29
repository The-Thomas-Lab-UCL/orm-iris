"""Power sweeps with simulated laser communication and real Raman storage."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# The existing test fixture isolates IRIS's config imports and opens no hardware.
import test_integration_experiment as integration_fixture
from test_integration_experiment import (
    SimulatedCancel, DummyWidget, raman_gui,
    MeaRMap_Hub, MeaRMap_Unit, MeaRMap_Handler, Frm_HighLvlController_Raman)
from iris.controllers.laser_controller_toptica import IBeamController, IBeamProfile
from iris.gui.laser_status import Frm_IBeamStatus
from iris.utils.power_experiment import validate_power_experiment, run_power_experiment
from iris.utils.experiment_naming import build_power_map_names


class SimulatedLaser:
    def __init__(self):
        self.power_w = .1
        self.commands = []
        self.enabled = True
        self.channel_enabled = True
        self.fail_power_w = None

    def get_device_info(self):
        return SimpleNamespace(serial='laser120', version='test')

    def is_enabled(self):
        return self.enabled

    def is_channel_enabled(self, channel='all'):
        return [self.channel_enabled, False] if channel == 'all' else self.channel_enabled

    def get_output_power(self):
        return self.power_w * .96

    def get_channel_power(self, channel='all'):
        return [self.power_w, 0.]

    def set_channel_power(self, channel, power):
        if power == self.fail_power_w:
            raise RuntimeError('Simulated communication failure')
        self.commands.append(power * 1000)
        self.power_w = power
        return power

    def close(self):
        pass


def laser_controller():
    device = SimulatedLaser()
    controller = IBeamController(lambda connection: device)
    controller.connect(IBeamProfile('120 mW', 'COM4', 120., expected_serial='laser120'))
    return controller, device


class PowerSettingsTests(unittest.TestCase):
    def test_independent_bleach_and_ascending_powers(self):
        controller, _ = laser_controller()
        settings = validate_power_experiment('40,20,20', '50', '15', '250', '10',
                                             (10000, 10000000, 25000), controller.validate_power_mw)
        self.assertEqual(settings['powers_mw'], (20., 20., 40.))
        self.assertEqual(settings['photobleach_power_mw'], 15.)
        self.assertEqual(settings['photobleach_duration_ms'], 250.)
        self.assertEqual(settings['integration_time_ms'], 50.)
        self.assertEqual(build_power_map_names('region', settings['powers_mw']),
                         ['region_20mW', 'region_20mW_repeat2', 'region_40mW'])

    def test_zero_duration_ignores_blank_bleaching_power(self):
        controller, _ = laser_controller()
        settings = validate_power_experiment('20', '50', '', '0', '0',
                                             (10000, 10000000, 25000), controller.validate_power_mw)
        self.assertIsNone(settings['photobleach_power_mw'])

    def test_invalid_settings_write_nothing(self):
        controller, device = laser_controller()
        for powers, integration, bleach_power, duration, settle in (
                ('', '50', '', '0', '10'), ('121', '50', '', '0', '10'),
                ('20', '50,100', '', '0', '10'), ('20', '50', '', '250', '10'),
                ('20', '50', '121', '250', '10'), ('20', '50', '', '-1', '10'),
                ('20', '50', '', '0', 'nan'), ('20', '50', '', '0', '-1')):
            with self.subTest(powers=powers, integration=integration, duration=duration), self.assertRaises(ValueError):
                validate_power_experiment(powers, integration, bleach_power, duration, settle,
                                          (10000, 10000000, 25000), controller.validate_power_mw)
        self.assertEqual(device.commands, [])

    def test_power_names_and_collision(self):
        self.assertEqual(build_power_map_names('region', [-0., 0., .5]),
                         ['region_0mW', 'region_0mW_repeat2', 'region_0.5mW'])
        self.assertEqual(build_power_map_names('region', [20], ['REGION_20MW']), ['region_1_20mW'])

    def test_whole_run_uses_next_free_suffix(self):
        existing = ['region_20mW', 'region_1_40mW', 'REGION_2_20MW_REPEAT2']
        self.assertEqual(build_power_map_names('region', [20, 20, 40], existing),
                         ['region_3_20mW', 'region_3_20mW_repeat2', 'region_3_40mW'])
        self.assertEqual(existing, ['region_20mW', 'region_1_40mW', 'REGION_2_20MW_REPEAT2'])


class PowerSequenceTests(unittest.TestCase):
    def run_scan(self, cancel=None, duration=250., acquire=None):
        controller, self.device = laser_controller()
        self.cancel = cancel or SimulatedCancel()
        self.events = []
        self.saved = []
        self.checkpoints = []
        def exposure(power):
            self.events.append(('exposure', power))
            return acquire(power) if acquire else power
        return run_power_experiment(
            [(0., 0., 0.), (1., 0., 0.)], (20., 40.), 15., duration, 10., 'x-direction', self.cancel,
            lambda coordinate: self.events.append(('move', self.device.power_w)), controller.set_power_mw,
            controller.prepare_power_experiment, exposure,
            lambda *args: self.saved.append(args), lambda text: None,
            lambda: self.checkpoints.append(list(self.saved)))

    def test_bleaches_once_per_point_and_moves_at_zero(self):
        self.assertEqual(self.run_scan(), 2)
        self.assertEqual(self.device.commands, [0., 15., 20., 40., 0.] * 2 + [0.])
        self.assertEqual([event for event in self.events if event[0] == 'move'], [('move', 0.), ('move', 0.)])
        self.assertEqual(self.cancel.waits, [.75, .01, .25, .01, .01, .2, .01, .25, .01, .01])
        self.assertEqual(len(self.saved), 4)

    def test_no_bleaching_does_not_set_bleach_power(self):
        self.run_scan(duration=0.)
        self.assertNotIn(15., self.device.commands)

    def test_stop_during_bleaching_sets_zero_without_acquisition(self):
        self.assertEqual(self.run_scan(SimulatedCancel(stop_wait=3)), 0)
        self.assertEqual(self.saved, [])
        self.assertEqual(self.device.commands, [0., 15., 0.])

    def test_stop_during_exposure_preserves_spectrum(self):
        cancel = SimulatedCancel()
        def acquire(power):
            cancel.set()
            return power
        self.assertEqual(self.run_scan(cancel, acquire=acquire), 0)
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(len(self.checkpoints[-1]), 1)
        self.assertEqual(self.device.commands[-1], 0.)

    def test_acquisition_failure_preserves_previous_data_and_sets_zero(self):
        def acquire(power):
            if power == 40:
                raise RuntimeError('spectrometer error')
            return power
        with self.assertRaisesRegex(RuntimeError, 'spectrometer error'):
            self.run_scan(acquire=acquire)
        self.assertEqual(len(self.checkpoints[-1]), 1)
        self.assertEqual(self.device.commands[-1], 0.)


class PowerUIFlowTests(unittest.TestCase):
    def make_frame(self):
        frame, hub, moves, callbacks, selected = integration_fixture.UIFlowTests().make_frame()
        controller, device = laser_controller()
        panel = SimpleNamespace(controller=controller, _executor=ThreadPoolExecutor(max_workers=1),
                                _future=None, _closing=False, _experiment_reserved=False,
                                _status=SimpleNamespace(set=lambda value: None),
                                _readback=SimpleNamespace(set=lambda value: None),
                                _update_controls=Mock(), refresh=Mock())
        for method in ('reserve_for_experiment', 'execute_for_experiment', 'release_from_experiment',
                       'submit_status_for_monitor'):
            setattr(panel, method, getattr(Frm_IBeamStatus, method).__get__(panel))
        frame._laser_panel = panel
        self.addCleanup(panel._executor.shutdown, wait=True)
        value = lambda text: SimpleNamespace(get=lambda: text)
        frame._str_power_levels_mw = value('40,20')
        frame._str_power_integration_ms = value('50')
        frame._str_power_bleach_mw = value('15')
        frame._str_power_bleach_ms = value('250')
        frame._str_power_settle_ms = value('10')
        frame._str_power_scan_method = value('snake')
        frame._str_power_scan_direction = value('y-direction')
        frame._btn_power_experiment = DummyWidget()
        frame._power_settings = Frm_HighLvlController_Raman._power_settings.__get__(frame)
        return frame, hub, device, callbacks

    def execute_frame(self, frame, callbacks, autosave, kind='laser_power'):
        with patch.object(raman_gui, 'SaveParamsEnum', SimpleNamespace(AUTOSAVE_PATH=SimpleNamespace(value=autosave))), \
                patch.object(raman_gui.messagebox, 'showinfo') as showinfo, \
                patch.object(raman_gui.messagebox, 'showerror') as showerror:
            frame.start_integration_experiment(kind)
            deadline = time.monotonic() + 15
            while frame._experiment_thread is not None and time.monotonic() < deadline:
                pending, callbacks[:] = callbacks[:], []
                for callback in pending:
                    callback()
                time.sleep(.001)
            self.assertIsNone(frame._experiment_thread)
            return showinfo, showerror

    def test_complete_power_run_saves_maps_and_readbacks(self):
        frame, hub, device, callbacks = self.make_frame()
        frame.raman_controller._laserwavelength_nm = 532.  # Profile must override manual metadata.
        with tempfile.TemporaryDirectory() as autosave:
            showinfo, showerror = self.execute_frame(frame, callbacks, autosave)
            showerror.assert_not_called()
            showinfo.assert_called_once()
            self.assertEqual(hub.get_list_MappingUnit_names(), ['region_20mW', 'region_40mW'])
            loaded = MeaRMap_Hub()
            folder = Path(frame._experiment_recovery_dir)
            MeaRMap_Handler().load_MappingMeasurement_pickle(loaded, str(folder / 'maps.pkl'))
            for power in (20, 40):
                unit = loaded.get_MappingUnit(unit_name=f'region_{power}mW')
                self.assertEqual(unit.get_numMeasurements(), 4)
                meta = unit.get_dict_measurement_metadata()
                self.assertEqual(meta['laser_power_milliwatt'], power)
                self.assertEqual(meta['laser_wavelength_nm'], 785.)
                self.assertEqual(meta['integration_time_ms'], 50.)
                self.assertEqual(meta['accumulation'], 1)
            records = [json.loads(line) for line in (folder / 'power_readbacks.jsonl').read_text().splitlines()]
            self.assertEqual([record['requested_power_mw'] for record in records], [20., 40.] * 4)
            self.assertEqual(records[0]['output_readback_before_exposure_mw'], 19.2)
            settings = json.loads((folder / 'settings.json').read_text())
            self.assertEqual(settings['photobleach_power_mw'], 15.)
            self.assertEqual(settings['photobleach_duration_ms'], 250.)
            quality = json.loads((folder / 'laser_quality.json').read_text())
            self.assertEqual(len(quality['spectra']), 8)
            self.assertIsNone(quality['fault'])
        self.assertEqual(device.commands, [0., 15., 20., 40., 0.] * 4 + [0.])
        self.assertFalse(frame._laser_panel._experiment_reserved)
        self.assertEqual(frame.raman_controller.display_experiment_spectrum.call_count, 8)

    def test_integration_run_monitors_without_power_commands(self):
        frame, _, device, callbacks = self.make_frame()
        with tempfile.TemporaryDirectory() as autosave:
            _, showerror = self.execute_frame(frame, callbacks, autosave, kind='integration')
            showerror.assert_not_called()
            folder = Path(frame._experiment_recovery_dir)
            settings = json.loads((folder / 'settings.json').read_text())
            self.assertEqual(settings['laser_monitoring'], 'background')
            quality = json.loads((folder / 'laser_quality.json').read_text())
            self.assertEqual(len(quality['spectra']), 8)
            self.assertIsNone(quality['fault'])
            self.assertTrue((folder / 'laser_monitor.jsonl').exists())
        self.assertEqual(device.commands, [])
        self.assertTrue(device.enabled)
        self.assertFalse(frame._laser_panel._experiment_reserved)

    def test_laser_loss_during_exposure_is_retained_and_flagged(self):
        frame, hub, device, callbacks = self.make_frame()
        frame._experiment_cancel = threading.Event()
        original = frame.raman_controller.acquire_experiment_spectrum
        def acquire(value, **kwargs):
            if value == 500:
                device.enabled = False
                self.assertTrue(frame._experiment_cancel.wait(2))
            return original(value, **kwargs)
        frame.raman_controller.acquire_experiment_spectrum = acquire
        with tempfile.TemporaryDirectory() as autosave:
            _, showerror = self.execute_frame(frame, callbacks, autosave, kind='integration')
            showerror.assert_called_once()
            self.assertIn('Background laser monitor', showerror.call_args.args[1])
            quality = json.loads((Path(frame._experiment_recovery_dir) / 'laser_quality.json').read_text())
            self.assertEqual(len(quality['spectra']), 2)
            self.assertEqual(quality['spectra'][1]['laser_quality'], 'suspect_laser_fault')
            self.assertEqual(hub.get_MappingUnit(unit_name='region_500ms').get_numMeasurements(), 1)
        self.assertFalse(device.enabled)
        self.assertEqual(device.commands, [])

    def test_communication_failure_preserves_partial_map(self):
        frame, _, device, callbacks = self.make_frame()
        device.fail_power_w = .04
        with tempfile.TemporaryDirectory() as autosave:
            _, showerror = self.execute_frame(frame, callbacks, autosave)
            showerror.assert_called_once()
            self.assertIn('Could not verify channel 1 at 0 mW', showerror.call_args.args[1])
            loaded = MeaRMap_Hub()
            MeaRMap_Handler().load_MappingMeasurement_pickle(loaded, str(Path(frame._experiment_recovery_dir) / 'maps.pkl'))
            self.assertEqual(loaded.get_MappingUnit(unit_name='region_20mW').get_numMeasurements(), 1)
        self.assertFalse(frame._laser_panel._experiment_reserved)

    def test_zero_bleach_duration_with_blank_power_completes(self):
        frame, _, device, callbacks = self.make_frame()
        frame._str_power_bleach_ms = SimpleNamespace(get=lambda: '0')
        frame._str_power_bleach_mw = SimpleNamespace(get=lambda: '')
        with tempfile.TemporaryDirectory() as autosave:
            _, showerror = self.execute_frame(frame, callbacks, autosave)
            showerror.assert_not_called()
        self.assertNotIn(15., device.commands)

    def test_emission_off_does_not_enable_or_change_power(self):
        frame, _, device, callbacks = self.make_frame()
        device.enabled = False
        with tempfile.TemporaryDirectory() as autosave:
            _, showerror = self.execute_frame(frame, callbacks, autosave)
            showerror.assert_called_once()
        self.assertFalse(device.enabled)
        self.assertEqual(device.commands, [])

    def test_duplicate_map_name_creates_new_power_run(self):
        frame, hub, device, callbacks = self.make_frame()
        original = MeaRMap_Unit('region_20mW')
        hub.append_mapping_unit(original)
        with tempfile.TemporaryDirectory() as autosave:
            _, showerror = self.execute_frame(frame, callbacks, autosave)
            showerror.assert_not_called()
            settings = json.loads((Path(frame._experiment_recovery_dir) / 'settings.json').read_text())
            self.assertEqual(settings['run_name'], 'region_1')
            self.assertEqual(settings['map_names'], ['region_1_20mW', 'region_1_40mW'])
        self.assertEqual(hub.get_list_MappingUnit_names(), ['region_20mW', 'region_1_20mW', 'region_1_40mW'])
        self.assertIs(hub.get_MappingUnit(unit_name='region_20mW'), original)
        self.assertEqual(original.get_numMeasurements(), 0)
        self.assertEqual(hub.get_MappingUnit(unit_name='region_1_20mW').get_numMeasurements(), 4)
        self.assertFalse(frame._laser_panel._experiment_reserved)


if __name__ == '__main__':
    unittest.main()
