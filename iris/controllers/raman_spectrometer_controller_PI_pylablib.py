"""A class that allows the control of the Princeton Instruments Raman spectrometer.

Technical notes:
Because the PIXIS100 is very slow at capturing single frames,
the acquisition mode is set to 'sequence' and the acquisition
is performed continuously from the creation of the object.
Even with this, as far as I know, the capture rate is still
limited to 10Hz.

Acknowledgement:
pylablib for the library that provides the interface to the spectrometer.

Made on: 04 March 2024
By: Kevin Uning, The Thomas Group, Biochemical Engineering Dept., UCL
In collaboration with: The Bergholt Lab, King's College London
"""
import os
import sys
import time
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
# if not __name__ == '__main__': matplotlib.use('Agg')

import pylablib as pll
from pylablib.devices import PrincetonInstruments as pic

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))
    

from iris.utils.general import *
from iris.controllers.class_spectrometer_controller import Class_SpectrometerController

from iris import DataAnalysisConfigEnum
from iris.controllers import ControllerSpecificConfigEnum


# # Add the directory containing the oceandirect module to the Python path
# module_dir = os.path.abspath(ControllerSpecificConfigEnum.OCEANINSIGHT_API_DIRPATH.value)
# sys.path.append(module_dir)

pll.par["devices/dlls/picam"] = r"C:\Program Files\Princeton Instruments\PICam\Runtime"

def test():
    print(pic.list_cameras())
    with pic.PicamCamera() as cam:
        # All available attributes
        print(cam.get_all_attributes())

    # >> Test setting and getting attributes (exposure time) <<
        print('Exposure Time: {}'.format(cam.get_attribute_value("Exposure Time")))
        cam.set_attribute_value("Exposure Time", 10)  # set the exposure time to 10 ms
        print('Exposure Time: {}'.format(cam.get_attribute_value("Exposure Time")))
        cam.set_attribute_value("Exposure Time", 20)
        print('Exposure Time: {}'.format(cam.get_attribute_value("Exposure Time")))
        
        # Frame rate settings
        print('Frame Rate Calculation: {}'.format(cam.get_attribute_value("Frame Rate Calculation")))

        # Get the time resolution parameters for the timing
        ts_res = cam.get_attribute_value("Time Stamp Resolution")
        print("Time Stamp Bit Depth: {}".format(cam.get_attribute_value("Time Stamp Bit Depth")))
        print("Time Stamp Resolution: {}".format(ts_res))
        print("Time Stamps: {}".format(cam.get_attribute_value("Time Stamps")))

    # >> Test reading a Raman spectrum <<
        cam.start_acquisition()
        time.sleep(2)
        result = cam.read_newest_image(return_info=True)
        cam.stop_acquisition()
        info = result[1]
        spectrum_raw = result[0]

        # Add timestamps into the info request
        cam.enable_metadata(enable=True)
        print('ismetadataenabled: {}'.format(cam.is_metadata_enabled()))
        print(cam.get_acquisition_parameters())
        print(cam.get_acquisition_parameters())

        list_time = [time.time()]
        list_acq = []
        def acquisition_snap(list_time:list, list_acq:list):
            print('Acquisition mode: snap')
            i=0
            cam.setup_acquisition(mode='snap',nframes=1)
            while i<5:
                i+=1
                result=cam.snap(timeout=5,return_info=True)
                spectrum_raw = result[0]

                # print(result[1])
                ts_start_ms = result[1].timestamp_start
                ts_end_ms = result[1].timestamp_end
                # print('Acquisition duration: {}'.format(ts_end_ms-ts_start_ms))
                print('Acquisition timestamp_start [ms]: {}'.format(ts_start_ms/ts_res*1000))
                list_acq.append((ts_end_ms-ts_start_ms)/ts_res)

                list_time.append(time.time())
            return list_time, list_acq

        def acquisition_grab(list_time:list, list_acq:list):
            print('Acquisition mode: grab')
            cam.setup_acquisition(mode='sequence')
            cam.start_acquisition()
            i=0
            while i<5:
                i+=1
                result=cam.grab(nframes=1,frame_timeout=5,return_info=True)
                spectrum_raw = result[0][-1]

                # print(result[1][-1])
                ts_start_ms = result[1][-1].timestamp_start
                ts_end_ms = result[1][-1].timestamp_end
                # print('Acquisition duration: {}'.format(ts_end_ms-ts_start_ms))
                print('Acquisition timestamp_start [ms]: {}'.format(ts_start_ms/ts_res*1000))
                list_acq.append((ts_end_ms-ts_start_ms)/ts_res)
                list_time.append(time.time())
            cam.stop_acquisition()
            return list_time, list_acq
        
        def acquisition_read(list_time:list, list_acq:list):
            print('Acquisition mode: read')
            cam.setup_acquisition(mode='sequence')
            cam.start_acquisition()
            cam.wait_for_frame()
            i=0
            list_time_read = []
            while i<5:
                i+=1
                cam.wait_for_frame()
                time1 = time.time()
                result = cam.read_oldest_image(return_info=True)
                spectrum_raw = result[0]
                list_time_read.append(time.time()-time1)

                # print(result[1][-1])
                ts_start_ms = result[1].timestamp_start
                ts_end_ms = result[1].timestamp_end
                # print('Acquisition duration: {}'.format(ts_end_ms-ts_start_ms))
                print('Acquisition timestamp_start [ms]: {}'.format(ts_start_ms/ts_res*1000))
                list_acq.append((ts_end_ms-ts_start_ms)/ts_res)

                list_time.append(time.time())
            cam.stop_acquisition()

            print('Average read time: {}'.format(np.mean(list_time_read)*1000))

            return list_time, list_acq

        list_time,list_acq=acquisition_snap(list_time,list_acq)
        list_time,list_acq=acquisition_grab(list_time,list_acq)
        list_time,list_acq=acquisition_read(list_time,list_acq)
        # Calculate the average measurement time
        list_time_diff = np.diff(list_time)
        print('Average measurement time: {}'.format(np.mean(list_time_diff)*1000))
        print('Average acquisition time: {}'.format(np.mean(list_acq)*1000))

        spectrum_raw_np = np.array(spectrum_raw)
        plt.imshow(spectrum_raw_np, cmap='hot')
        plt.show()
        
        spectrum:np.ndarray = np.mean(spectrum_raw_np, axis=0)
        print('Spectrum length: {}'.format(len(spectrum)))
        print('Spectrum shape: {}'.format(spectrum.shape))
        plt.plot(spectrum)
        plt.show()

class SpectrometerController_PI(Class_SpectrometerController):
    def __init__(self) -> None:
        self._dev:pic.PicamCamera = None

        # Device related parameters
        self._timeRes_Hz:float = None       # 'Time Resolution' for time metadata conversion to [sec]
        self._timestamp_init_us:int = None  # Initial timestamp for the device. Starts when the capture starts
        
        # Aquisition related parameters
        ## NOTE: these parameters were not defined by the device and thus,
        ## are set arbitrarily. They may need to be adjusted.
        self.integration_time_min = 10          # int: Stores the spectrometer's minimum allowable integration time [millisec]
        self.integration_time_max = 3600*1000   # int: Stores the spectrometer's maximum allowable integration time [millisec]
        self.integration_time_inc = 1           # int: Stores the spectrometer's allowable integration time increment [millisec]
        
        # Start the initialisation process
        self._identifier = None
        self.initialisation()
        
    def get_identifier(self) -> str:
        """
        Returns the identifier of the spectrometer.

        Returns:
            str: The identifier of the spectrometer
        """
        if self._identifier is None:
            self._identifier = self._get_hardware_identifier()
        return self._identifier
    
    def _get_hardware_identifier(self) -> str:
        """
        Returns the hardware identifier of the spectrometer.

        Returns:
            str: The hardware identifier of the spectrometer
        """
        return f"Princeton Instrument_{self._dev.get_device_info()}"
    
# Core functionalities (initialisation, termination)
    def initialisation(self):
        if isinstance(self._dev,pic.PicamCamera): self.terminate()
        self._dev = pic.PicamCamera()
        print("----- Connected to: {} -----".format(self._dev.get_device_info()))

        # Enable metadata for the timestamp and 
        ## start the acquisition immediately
        self._dev.enable_metadata(enable=True)
        self._dev.setup_acquisition(mode='sequence')
        self._dev.start_acquisition()
        self._timestamp_init_us = get_timestamp_us_int()
        
        # Wait for the first frame to be captured
        self._timeRes_Hz = self._dev.get_attribute_value("Time Stamp Resolution")
        self._dev.wait_for_frame()
        
    def terminate(self, error_flag=False):
        """
        To terminate the connections to the Raman spectrometers
        
        Args:
            error_flag (bool, optional): Can also passes an error message. Defaults to False.
        """
        if error_flag!=False: print("\n Error code:",error_flag)
        
        self._dev.stop_acquisition()
        self._dev.close()

        print("\n>>>>> Raman controller TERMINATED <<<<<")

    def get_integration_time_limits_us(self) -> tuple[int,int,int]:
        """
        Get the integration time limits of the device
        
        Returns:
            tuple: A tuple containing the minimum, maximum, and increment of the integration time in [device unit] (microseconds for the QE Pro)
        """
        return (self.integration_time_min, self.integration_time_max, self.integration_time_inc)
    
    def get_integration_time_us(self):
        """
        Get the integration time of the device
        
        Returns:
            int: Integration time in [device unit] (microseconds for the QE Pro)
        """
        int_time_ms = self._dev.get_attribute_value("Exposure Time")
        return int_time_ms*1000
    
    def _restart_acquisition(self):
        """
        Restarts the acquisition process. This allows for new settings/parameters
        to be applied to the device.
        """
        self._dev.stop_acquisition()
        self._dev.start_acquisition()
        self._timestamp_init_us = get_timestamp_us_int()
        self._dev.wait_for_frame()

    def set_integration_time_us(self,integration_time:int) -> int:
        """
        Sets the integration time of the device
        
        Args:
            integration_time (int): Integration time in [device unit] 
            (microseconds for the QE Pro)
        
        Returns:
            int: Device integrationt time after set up [us]
        """
        assert isinstance(integration_time,int), "Integration time must be an integer"
        int_time_ms = int(integration_time/1000)
        
        self._dev.set_attribute_value("Exposure Time", int_time_ms)
        self._restart_acquisition()
        return self._dev.get_attribute_value("Exposure Time")*1000
        
    def measure_spectrum(self) -> tuple[pd.DataFrame, int, int]:
        """
        Measures the spectrum of the Raman spectrometer.
        
        Returns:
            pandas.DataFrame: A DataFrame containing the measured spectrum with the following columns:
            - 'Wavelength [pixel]': The wavelength values in nanometers.
            - 'Intensity [a.u.]': The intensity values in arbitrary units.
            int: The timestamp of the measurement in integer format (microseconds).
            int: The integration time used for the measurement in microseconds.
        """
        # list_time = [] ### <<<
        
        # list_time.append(time.time()) ### <<<
        while True:
            self._dev.wait_for_frame(since='lastread')
            # list_time.append(time.time()) ### <<<
            result = self._dev.read_newest_image(return_info=True)
            if result is not None: break
            else: print('No data captured. Reinitalising the connection...'); self.initialisation()
        img,info = result[0],result[1]
        
        # # list_time.append(time.time()) ### <<< 
        
        img = np.array(img)[74:80,:]
        # img = np.array(img)
        list_intensity = np.mean(img,axis=0)
        list_wavelength = list(range(1, len(list_intensity) + 1))
        
        # plt.imshow(img)
        # plt.set_cmap('gray')
        # plt.colorbar()
        
        # plt.show()
        
        # arr1 = np.array(img)[:,300]
        # plt.plot(arr1)
        # plt.grid()
        # plt.minorticks_on()
        # plt.tick_params(axis='both',which='both',direction='in',top=True,right=True)
        
        # plt.show()
        
        # list_time.append(time.time()) ### <<<
        list_wavelength = [float(wavelength) for wavelength in list_wavelength]
        list_intensity = [float(intensity) for intensity in list_intensity]
        
        # list_time.append(time.time()) ### <<<
        timestamp_us_int = int(info.timestamp_start/self._timeRes_Hz*10**6 + self._timestamp_init_us)
        integration_time = self.get_integration_time_us()
        
        # list_time.append(time.time()) ### <<<
        spectra = pd.DataFrame({
            DataAnalysisConfigEnum.WAVELENGTH_LABEL.value: list_wavelength,
            DataAnalysisConfigEnum.INTENSITY_LABEL.value: list_intensity,
        })
        
        # list_time.append(time.time()) ### <<<
        # for i in range(1,len(list_time)):
        #     print('Time {}: {}ms'.format(i,(list_time[i]-list_time[i-1])*1000))
        
        return (spectra, timestamp_us_int, integration_time)
    
# Set of commands for testing/automation
    def self_test(self):
        print("----- Self-test for the Raman spectrometer -----")
        print("--- Test integration time ---")
        print("Integration time limits [us]: {}".format(self.get_integration_time_limits_us()))
        print("Setting integration time to 5ms")
        self.set_integration_time_us(5000)
        print("Current integration time [us]: {}".format(self.get_integration_time_us()))
        new_int_value_us = 1000000
        self.set_integration_time_us(new_int_value_us)
        print("Setting integration time to {}ms [~{}Hz]".format(new_int_value_us/1000,10**6/new_int_value_us))
        print("Current integration time [us]: {}".format(self.get_integration_time_us()))
        
        print('\n--- Test acquisition ---')
        print("Measuring spectrum")
        
        import threading as th
        from typing import Callable
        
        def offafter5sec(callback:Callable):
            time.sleep(2)
            callback()
        
        flg = th.Event()
        th.Thread(target=offafter5sec,args=(flg.set,)).start()
        
        # plt.ion()  # Turn on interactive mode 
        # fig = plt.figure()  # Create a figure
        # ax = fig.add_subplot(111)  # Create a subplot

        while not flg.is_set():
            time1 = time.time()
            result = self.measure_spectrum()
            print("Timestamp: {}".format(convert_timestamp_us_int_to_str(result[1])))
            print("Integration time [ms]: {}".format(result[2]/1000))
            print("Spectrum shape: {}".format(result[0].shape))

            # Clear the previous plot
            # ax.clear()  

            # # Plot the new data
            # ax.plot(result[0][WAVELENGTH_LABEL], result[0][INTENSITY_LABEL])
            # ax.set_title("Measured spectrum")
            # ax.set_xlabel(WAVELENGTH_LABEL)
            # ax.set_ylabel(INTENSITY_LABEL)

            # # Update the plot
            # fig.canvas.draw()
            # fig.canvas.flush_events()

            time2 = time.time()
            print("Measurement duration: {}ms".format((time2 - time1)*1000))
            
        # plt.ioff()  # Turn off interactive mode
        # plt.show()  # Keep the plot window open at the end
        
        print("----- Self-test completed -----")

def test_device():
    raman = SpectrometerController_PI()
    raman.self_test()
    raman.terminate()

if __name__ == '__main__':
    test()
    # test_device()
    pass