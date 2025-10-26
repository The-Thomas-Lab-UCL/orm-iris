"""
Class definition for the Raman spectrometer controller and a guide to writing one for the IRIS
"""

import os
import sys
import pandas as pd
import numpy as np
from multiprocessing import Lock

from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
# matplotlib.use('Agg')

import wasatch as ws

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))

from iris.controllers import ControllerSpecificConfigEnum
from iris.controllers.class_spectrometer_controller import Class_SpectrometerController

from iris.utils.general import *

from iris import DataAnalysisConfigEnum


# def test():
#     import sys
#     from wasatch.WasatchBus    import WasatchBus
#     from wasatch.WasatchDevice import WasatchDevice

#     bus = WasatchBus()
#     if not bus.device_ids:        
#         print("no spectrometers found")
#         sys.exit(1)

#     device_id = bus.device_ids[0]
#     print("found %s" % device_id)

#     device = WasatchDevice(device_id)
#     if not device.connect():
#         print("connection failed")
#         sys.exit(1)

#     print("connected to %s %s with %d pixels from (%.2f, %.2f)" % (
#         device.settings.eeprom.model,
#         device.settings.eeprom.serial_number,
#         device.settings.pixels(),
#         device.settings.wavelengths[0],
#         device.settings.wavelengths[-1]))
    
#     print("setting integration time")
#     device.hardware.set_integration_time_ms(10)
#     # or: device.change_setting("integration_time_ms", 10)

#     print("reading spectrum")
#     spectrum = device.hardware.get_line().data.spectrum
#     # or: spectrum = device.acquire_data().spectrum

#     for pixel in range(device.settings.pixels()):
#         print("%8.2f %8.2f" % (device.settings.wavelengths[pixel], spectrum[pixel]))

#     print("done")

LASER_ENABLE = ControllerSpecificConfigEnum.WASATCH_LASER_ENABLE.value
LASER_POWER_MW = ControllerSpecificConfigEnum.WASATCH_LASER_POWER_MW.value

class SpectrometerController_WasatchEnlighten(Class_SpectrometerController):
    def __init__(self) -> None:
        from wasatch.WasatchBus import WasatchBus
        from wasatch.WasatchDevice import WasatchDevice
        
        bus = WasatchBus()
        if not bus.device_ids:
            raise RuntimeError("No Wasatch Enlighten spectrometers found")
        
        dev_id = bus.device_ids[0]
        print("-"*20)
        print(f"Connected to Wasatch Enlighten spectrometer with Device ID: {dev_id}")
        
        self.device = WasatchDevice(dev_id)
        
        # Device internal parameters
        self._integration_time_us = 100000
        
        self._lock = Lock()     # Lock for the acquisition process
        
        self._identifier = None
        # Start the initialisation process
        self.initialisation()
        
    def get_identifier(self) -> str:
        """
        Returns the identifier of the spectrometer.

        Returns:
            str: The identifier of the spectrometer
        """
        if self._identifier is None: self._identifier = self._get_hardware_identifier()
        return self._identifier
        
    def _get_hardware_identifier(self) -> str:
        """
        Returns the hardware identifier of the spectrometer.

        Returns:
            str: The hardware identifier of the spectrometer
        """
        model = self.device.settings.eeprom.model
        serial_number = self.device.settings.eeprom.serial_number
        return f"WasatchEnlighten_{model}_S/N:{serial_number}"
        
# Core functionalities (initialisation, termination)
    def initialisation(self) -> None:
        """
        Initializes the Raman spectrometer controller.
        """
        self.device.connect()
        self._identifier = self._get_hardware_identifier()
        self._list_pixels = self.device.settings.pixels()
        
        self._wavelengths = np.asarray(self.device.settings.wavelengths)
        self._wavelengths = self._wavelengths.astype(float).tolist()
        
        self.device.hardware.set_integration_time_ms(100)  # Set a default integration time of 100 ms
        
        if LASER_ENABLE:
            self.device.hardware.set_laser_enable(True)
            self.device.hardware.set_laser_power_mW(LASER_POWER_MW)

    def terminate(self) -> None:
        """
        To terminate the connections to the Raman spectrometers
        """
        if LASER_ENABLE:
            self.device.hardware.set_laser_enable(False)
        self.device.disconnect()
    
        print("\n>>>>> Raman controller TERMINATED <<<<<")
    
    def get_integration_time_us(self) -> int:
        """
        Get the integration time of the device

        Returns:
            int: Integration time in [device unit] (microseconds for the QE Pro)
        """
        # with self._lock:
        #     int_time = self.device.hardware.get_integration_time_ms()
        #     int_time = int(int_time * 1000)  # Convert milliseconds to microseconds
        
        self._integration_time_us
        
        # print(f'Received a get_integration_time_us call, returning {self._integration_time_us/1e3} ms')
        
        return self._integration_time_us
    
    def get_integration_time_limits_us(self):
        """
        Get the integration time limits of the device

        Returns:
            tuple: A tuple containing the minimum, maximum, and increment of the integration time in [us]
        """
        return (10, 1e9, 1)
    
    def set_integration_time_us(self,integration_time:int) -> int:
        """Sets the integration time of the device

        Args:
            integration_time (int): Integration time in [device unit] 
            (microseconds for the QE Pro)

        Returns:
            int: Device integrationt time after set up in microseconds
        """
        
        # print(f'Received a set_integration_time_us call with integration_time={integration_time/1e3} ms')
        
        if not isinstance(integration_time,int) and not isinstance(integration_time,float):
            raise ValueError("Integration time must be an integer")
        integration_time = int(integration_time)
        
        with self._lock:
            self.device.hardware.set_integration_time_ms(integration_time/1e3)
            self._integration_time_us = integration_time

        return self._integration_time_us

    def measure_spectrum(self) -> tuple[pd.DataFrame, int, int]:
        """ 
        A function to measure the spectrum of the Raman spectrometer.
        
        Returns:
            tuple[pd.DataFrame, int, int]: A tuple containing the following:
                - pandas.DataFrame: A DataFrame containing the measured spectrum with the wavelength and
                    intensity columns, from the config file. (as a global constant)
                - int: The timestamp of the measurement in integer format (microseconds).
                - int: The integration time used for the measurement in microseconds.
        """
        with self._lock:
            intensity = np.asarray(self.device.hardware.get_line().data.spectrum)
            intensity = intensity.astype(float).tolist()
            
            timestamp = get_timestamp_us_int()
            integration_time = self._integration_time_us if self._integration_time_us is not None else self.get_integration_time_us()
        
        spectra = pd.DataFrame({
            DataAnalysisConfigEnum.WAVELENGTH_LABEL.value: self._wavelengths,
            DataAnalysisConfigEnum.INTENSITY_LABEL.value: intensity,
        })
        return (spectra, timestamp, integration_time)
    
# Set of commands for testing/automation
    def self_test(self):
        # <<<<< Insert the self-test commands here
        pass

if __name__ == '__main__':
    r_spec = SpectrometerController_WasatchEnlighten()
    r_spec.self_test()
    
    spectra = r_spec.measure_spectrum()[0]
    r_spec.terminate()

    spectra.to_csv('spectra_dummy.csv',index=False)
    
    # Plotting using the DataFrame
    import matplotlib.pyplot as plt
    plt.plot(spectra['Wavelength [nm]'], spectra['Intensity [a.u.]'])
    plt.show()
    