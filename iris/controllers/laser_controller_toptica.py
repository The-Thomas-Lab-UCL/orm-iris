"""iBeam smart status and explicit channel 1 power control."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math


@dataclass(frozen=True)
class IBeamProfile:
    name: str
    port: str
    max_power_mw: float
    wavelength_nm: float = 785.0
    expected_serial: str = ''


@dataclass(frozen=True)
class IBeamStatus:
    serial: str
    firmware: str
    enabled: bool
    output_mw: float
    channel_setpoints_mw: tuple[float, ...]
    channel_enabled: tuple[bool, ...] = ()


class IBeamController:
    """Serialize calls from one worker; never enable or disable emission.

    pylablib initializes serial communication (including disabling command echo)
    but does not change laser output when opening a connection. Its power API
    uses watts; all values exposed here use mW.
    """

    def __init__(self, device_factory=None):
        self._factory = device_factory
        self._device = None
        self.profile = None
        self._last_status = None

    @property
    def connected(self):
        return self._device is not None

    @property
    def last_status(self):
        return self._last_status

    @property
    def power_control_available(self):
        return bool(self.connected and self.profile.expected_serial and self._last_status
                    and self._last_status.serial == self.profile.expected_serial)

    def validate_power_mw(self, power_mw):
        if not self.power_control_available:
            raise ValueError('Power control requires a connected laser with a matching configured serial number.')
        try:
            value = Decimal(str(power_mw))
        except InvalidOperation:
            raise ValueError('Enter a numeric power in mW.') from None
        if not value.is_finite() or not 0 <= value <= Decimal(str(self.profile.max_power_mw)):
            raise ValueError(f'Power must be between 0 and {self.profile.max_power_mw:g} mW.')
        if value * 1000 != (value * 1000).to_integral_value():
            raise ValueError('Power supports at most three decimal places in mW.')
        return 0.0 if value == 0 else float(value)

    def set_power_mw(self, power_mw):
        """Set channel 1 only, verifying identity and the returned setpoint.

        Other enabled channels must have zero setpoints. Disabled channels can
        retain their presets. Emission and channel enable states never change.
        A failed command is not retried by this wrapper or automatically undone.
        """
        requested = self.validate_power_mw(power_mw)
        before = self.read_status()  # Recheck identity immediately before writing.
        self._check_channel_1_layout(before)
        try:
            actual = self._mw(self._device.set_channel_power(1, requested / 1000))
            after = self.read_status()
            self._check_channel_1_layout(after)
            if (not after.channel_setpoints_mw or
                    not math.isclose(actual, requested, rel_tol=0, abs_tol=0.00051) or
                    not math.isclose(after.channel_setpoints_mw[0], requested, rel_tol=0, abs_tol=0.00051)):
                raise RuntimeError('The laser did not confirm the requested channel 1 setpoint.')
            return after
        except Exception as error:
            self.close()
            raise RuntimeError(f'Power update could not be verified; the output may have changed. {error}') from error

    def prepare_power_experiment(self):
        """Read and validate the emission/channel state without turning anything on."""
        status = self.read_status()
        if not self.power_control_available:
            raise ValueError('The laser serial must match its configured power profile.')
        self._check_channel_1_layout(status)
        if not status.enabled or not status.channel_enabled[0]:
            raise ValueError('Enable laser emission and channel 1 in the iBeam application before the experiment.')
        return status

    @staticmethod
    def _check_channel_1_layout(status):
        if (not status.channel_setpoints_mw or
                len(status.channel_setpoints_mw) != len(status.channel_enabled)):
            raise ValueError('Channel power and enable states could not be verified. Refresh laser status.')
        active = [f'channel {index} is ON at {power:g} mW'
                  for index, (power, enabled) in enumerate(
                      zip(status.channel_setpoints_mw, status.channel_enabled), 1)
                  if index > 1 and enabled and power != 0]
        if active:
            raise ValueError('Channel 1-only control is blocked: ' + '; '.join(active) +
                             '. In the iBeam application, turn those channels OFF or set their power to 0 mW.')

    def connect(self, profile, baudrate=115200):
        if self.connected:
            raise RuntimeError('Disconnect before selecting another laser.')
        if not profile.port.strip():
            raise ValueError('Enter the laser COM port.')
        if self._factory is None:
            try:
                from pylablib.devices.Toptica import TopticaIBeam
            except ImportError as error:
                raise RuntimeError('Install laser support with: python -m pip install -e ".[toptica]"') from error
            factory = TopticaIBeam
        else:
            factory = self._factory
        self._device = factory((profile.port.strip(), int(baudrate)))
        self.profile = profile
        return self.read_status()

    @staticmethod
    def _mw(watts):
        value = float(watts) * 1000
        if not math.isfinite(value) or value < 0:
            raise ValueError('The laser returned an invalid power readback.')
        return value

    def read_status(self):
        if not self.connected:
            raise RuntimeError('Connect to the laser first.')
        try:
            info = self._device.get_device_info()
            if self.profile.expected_serial and str(info.serial) != self.profile.expected_serial:
                raise ValueError('The laser serial number does not match the selected profile.')
            return self._read_operating_status(str(info.serial), str(info.version))
        except Exception:
            self.close()
            raise

    def read_monitor_status(self):
        """Read operating state using cached identity to reduce serial traffic.

        Run on the same serial executor as power commands. Power changes still
        use read_status() to verify device identity immediately before writing.
        """
        if not self.connected or self._last_status is None:
            raise RuntimeError('Laser connection unavailable for background monitoring.')
        try:
            return self._read_operating_status(self._last_status.serial, self._last_status.firmware)
        except Exception:
            self.close()
            raise

    def _read_operating_status(self, serial, firmware):
        powers = tuple(self._mw(value) for value in self._device.get_channel_power(channel='all'))
        channel_enabled = tuple(self._device.is_channel_enabled(channel='all'))
        if (not powers or len(powers) != len(channel_enabled) or
                not all(isinstance(value, bool) for value in channel_enabled)):
            raise ValueError('The laser returned incomplete channel enable states.')
        status = IBeamStatus(serial=serial, firmware=firmware,
                            enabled=bool(self._device.is_enabled()),
                            output_mw=self._mw(self._device.get_output_power()),
                            channel_setpoints_mw=powers, channel_enabled=channel_enabled)
        self._last_status = status
        return status

    def close(self):
        device, self._device = self._device, None
        self.profile = None
        self._last_status = None
        if device is not None:
            device.close()
