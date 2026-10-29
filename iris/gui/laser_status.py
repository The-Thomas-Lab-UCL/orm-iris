"""Status and manual channel 1 power control for the lab's two iBeam lasers."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import tkinter as tk
from tkinter import ttk

from iris.controllers.laser_controller_toptica import IBeamProfile, IBeamController
from iris.utils.general import read_update_config_file_section


def load_ibeam_profiles(config_file='config.ini'):
    defaults = dict(port_120mw='COM4', port_250mw='COM4', baudrate=115200,
                    serial_120mw='', serial_250mw='')
    comments = dict(port_120mw='COM port for the 785 nm / 120 mW laser',
                    port_250mw='COM port for the 785 nm / 250 mW laser',
                    baudrate='Serial baud rate; default 115200',
                    serial_120mw='Expected serial for the 120 mW laser; required for power control',
                    serial_250mw='Expected serial for the 250 mW laser; required for power control')
    settings = read_update_config_file_section(
        defaults, comments, 'LASER - TOPTICA IBEAM', config_file=config_file)
    profiles = [IBeamProfile(f'iBeam 785 nm - {power} mW', settings[f'port_{power}mw'],
                            power, expected_serial=settings[f'serial_{power}mw'].strip())
                for power in (120, 250)]
    serials = [profile.expected_serial for profile in profiles if profile.expected_serial]
    if len(serials) != len(set(serials)):
        raise ValueError('The 120 mW and 250 mW profiles must have different laser serial numbers.')
    return {profile.name: profile for profile in profiles}, settings['baudrate']


class Frm_IBeamStatus(tk.Frame):
    def __init__(self, parent, acquisition_busy=None, power_busy_changed=None):
        super().__init__(parent)
        self._profiles, self._baudrate = load_ibeam_profiles()
        self.controller = IBeamController()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='ibeam-status')
        self._future = None
        self._closing = False
        self._experiment_reserved = False
        self._acquisition_busy = acquisition_busy or (lambda: False)
        self._power_busy_changed = power_busy_changed or (lambda busy: None)
        self._profile_name = tk.StringVar(master=self, value=next(iter(self._profiles)))
        self._port = tk.StringVar(master=self)
        self._rating = tk.StringVar(master=self)
        self._status = tk.StringVar(master=self, value='Disconnected')
        self._readback = tk.StringVar(master=self, value='No laser readback yet.')
        self._power_mw = tk.StringVar(master=self, value='')
        self._power_note = tk.StringVar(master=self)

        tk.Label(self, text='TOPTICA iBeam smart 785 S hp', anchor='w').grid(
            row=0, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        tk.Label(self, text='Laser profile:').grid(row=1, column=0, sticky='w', padx=5)
        self._profile_selector = ttk.Combobox(
            self, textvariable=self._profile_name, values=list(self._profiles), state='readonly', width=30)
        self._profile_selector.grid(row=1, column=1, columnspan=2, sticky='ew', padx=5, pady=5)
        self._profile_selector.bind('<<ComboboxSelected>>', self._select_profile)
        tk.Label(self, text='COM port:').grid(row=2, column=0, sticky='w', padx=5)
        self._port_entry = tk.Entry(self, textvariable=self._port)
        self._port_entry.grid(row=2, column=1, columnspan=2, sticky='ew', padx=5, pady=5)
        tk.Label(self, textvariable=self._rating, anchor='w').grid(
            row=3, column=0, columnspan=3, sticky='w', padx=5)
        self._connect = tk.Button(self, text='Connect', command=self.connect)
        self._refresh = tk.Button(self, text='Refresh status', command=self.refresh)
        self._disconnect = tk.Button(self, text='Disconnect', command=self.disconnect)
        for column, button in enumerate((self._connect, self._refresh, self._disconnect)):
            button.grid(row=4, column=column, sticky='ew', padx=5, pady=5)
        tk.Label(self, textvariable=self._status, anchor='w', justify='left', wraplength=420).grid(
            row=5, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        tk.Label(self, textvariable=self._readback, anchor='w', justify='left', wraplength=420).grid(
            row=6, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        tk.Label(self, text='Close the iBeam application before connecting here.\n'
                           'Connect and Disconnect leave laser output unchanged.\n'
                           'Power readback is at the laser, not at the tissue.',
                 anchor='w', justify='left', wraplength=420).grid(
            row=7, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        tk.Label(self, text='Channel 1 power [mW]:').grid(row=8, column=0, sticky='w', padx=5)
        self._power_entry = tk.Entry(self, textvariable=self._power_mw)
        self._power_entry.grid(row=8, column=1, sticky='ew', padx=5, pady=5)
        self._apply_power = tk.Button(self, text='Apply power', command=self.apply_power)
        self._apply_power.grid(row=8, column=2, sticky='ew', padx=5, pady=5)
        tk.Label(self, textvariable=self._power_note, anchor='w', justify='left', wraplength=420).grid(
            row=9, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        self.grid_columnconfigure(1, weight=1)
        self._select_profile()
        self._update_controls()

    def _select_profile(self, *_):
        profile = self._profiles[self._profile_name.get()]
        self._port.set(profile.port)
        self._rating.set(f'Configured rating: {profile.wavelength_nm:g} nm, '
                         f'maximum {profile.max_power_mw:g} mW')

    def _update_controls(self):
        busy = self._future is not None or getattr(self, '_experiment_reserved', False)
        connected = self.controller.connected
        self._profile_selector.configure(state='disabled' if busy or connected else 'readonly')
        self._port_entry.configure(state='disabled' if busy or connected else 'normal')
        self._connect.configure(state='disabled' if busy or connected else 'normal')
        for button in (self._refresh, self._disconnect):
            button.configure(state='normal' if connected and not busy else 'disabled')
        writable = self.controller.power_control_available and not busy
        for widget in (self._power_entry, self._apply_power):
            widget.configure(state='normal' if writable else 'disabled')
        self._power_note.set(
            f'Channel 1 range: 0-{self.controller.profile.max_power_mw:g} mW. '
            'Apply changes power immediately if emission is ON.' if self.controller.power_control_available else
            'Power control requires a connection with a matching serial number in config.ini.')

    def _submit(self, operation, message, kind='read'):
        if self._closing or self._future is not None or getattr(self, '_experiment_reserved', False):
            return
        self._status.set(message)
        self._operation = kind
        if kind == 'power':
            self._power_busy_changed(True)
        try:
            self._future = self._executor.submit(operation)
        except Exception:
            if kind == 'power':
                self._power_busy_changed(False)
            raise
        self._update_controls()
        self.after(50, self._poll)

    def connect(self):
        profile = replace(self._profiles[self._profile_name.get()], port=self._port.get().strip())
        self._submit(lambda: self.controller.connect(profile, self._baudrate), 'Connecting...', 'connect')

    def reserve_for_experiment(self, require_power_control=True):
        """Called on Tk thread; reserve the serial executor for acquisition."""
        if self._closing or self._future is not None or self._experiment_reserved:
            raise ValueError('Wait for the current laser operation to finish.')
        if not self.controller.connected:
            raise ValueError('Connect the laser in the Laser tab first.')
        if require_power_control and not self.controller.power_control_available:
            raise ValueError('Connect a serial-verified laser in the Laser tab first.')
        self._experiment_reserved = True
        self._status.set('Laser connection reserved for mapping experiment.')
        self._update_controls()

    def execute_for_experiment(self, operation):
        """Worker-only call: use the same serial worker as manual laser controls."""
        if not self._experiment_reserved or self._closing:
            raise RuntimeError('The laser is not reserved for this experiment.')
        return self._executor.submit(operation).result()

    def submit_status_for_monitor(self):
        """Submit one asynchronous read without waiting in the acquisition loop."""
        if not self._experiment_reserved or self._closing:
            raise RuntimeError('Laser connection unavailable for monitoring.')
        return self._executor.submit(self.controller.read_monitor_status)

    def release_from_experiment(self):
        """Called on Tk thread after the acquisition worker has finished."""
        self._experiment_reserved = False
        self._update_controls()
        if self.controller.connected and not self._closing:
            self.refresh()
        else:
            self._status.set('Power experiment finished; laser connection unavailable.')
            self._readback.set('No current readback. Check laser output using the iBeam application.')

    def apply_power(self):
        if self._future is not None or self._closing:
            return
        if self._acquisition_busy():
            self._status.set('Stop the acquisition before changing laser power.')
            return
        try:
            requested = self.controller.validate_power_mw(self._power_mw.get())
        except ValueError as error:
            self._status.set(str(error))
            return
        self._submit(lambda: self.controller.set_power_mw(requested),
                     f'Applying {requested:g} mW to channel 1...', 'power')

    def refresh(self):
        self._submit(self.controller.read_status, 'Reading laser status...')

    def disconnect(self):
        self._submit(self.controller.close, 'Disconnecting...')

    def _render_laser_readback(self, result):
        channels = []
        for index, value in enumerate(result.channel_setpoints_mw):
            state = ('ON' if result.channel_enabled[index] else 'OFF') if index < len(result.channel_enabled) else 'UNKNOWN'
            channels.append(f'Channel {index + 1}: {state}, setpoint {value:g} mW')
        self._readback.set(f'Serial: {result.serial}\nFirmware: {result.firmware}\n'
                           f'Emission reported: {"ON" if result.enabled else "OFF"}\n'
                           f'Output readback: {result.output_mw:g} mW\n' + '\n'.join(channels))

    def _poll(self):
        if self._closing:
            return
        if not self._future.done():
            self.after(50, self._poll)
            return
        try:
            result = self._future.result()
            if result is None:
                self._status.set('Disconnected; laser output was not changed.')
                self._readback.set('No current readback.')
            else:
                mode = 'serial verified' if self.controller.power_control_available else 'read only'
                prefix = 'Power setpoint verified. ' if self._operation == 'power' else ''
                self._status.set(f'{prefix}Connected on {self.controller.profile.port} ({mode})')
                if self._operation in ('connect', 'power') and result.channel_setpoints_mw:
                    self._power_mw.set(f'{result.channel_setpoints_mw[0]:g}')
                self._render_laser_readback(result)
        except Exception as error:
            controller = getattr(self, 'controller', None)
            last = controller.last_status if controller is not None and controller.connected else None
            if last is not None:
                self._render_laser_readback(last)
                if isinstance(error, ValueError):
                    self._status.set(f'Power change blocked; no power command sent. {error}')
                else:
                    self._status.set(f'Laser operation failed; connection retained. {error}')
            else:
                self._status.set(f'Laser operation failed: {error}')
                self._readback.set('No current readback. Check the COM port and close the iBeam application.')
        finally:
            self._future = None
            if getattr(self, '_operation', None) == 'power':
                self._power_busy_changed(False)
            self._update_controls()

    def terminate(self):
        if self._closing:
            return
        self._closing = True
        # Queue close after any active operation; disconnect leaves output unchanged.
        close = self._executor.submit(self.controller.close)
        try:
            close.result()
        finally:
            self._executor.shutdown(wait=True)
