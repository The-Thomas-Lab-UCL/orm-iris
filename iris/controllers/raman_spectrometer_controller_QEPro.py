"""
A class that allows the control of the QE Pro spectrometer from Ocean Insight.
This implementation is based on the API provided by Ocean Insight.
"""

import os
import sys
from datetime import datetime
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import msvcrt
from multiprocessing import Lock
from typing import Literal
# matplotlib.use('Agg')

from iris.controllers import ControllerSpecificConfigEnum
from iris.utils.general import *
from iris.controllers.class_spectrometer_controller import Class_SpectrometerController

# Import Ocean Direct using the wrapper to handle SDK import issues
from iris.controllers.oceandirect_wrapper import get_oceandirect_classes, create_oceandirect_api

from iris import DataAnalysisConfigEnum

class SpectrometerController_QEPro(Class_SpectrometerController):
    def __init__(self) -> None:
        # Get the Ocean Direct classes from the wrapper
        OceanDirectAPI, OceanDirectError, FeatureID = get_oceandirect_classes()
        
        # Store the classes as instance variables for use in other methods
        self.OceanDirectAPI = OceanDirectAPI
        self.OceanDirectError = OceanDirectError
        self.FeatureID = FeatureID
        
        # Create the API instance with proper path handling
        self.od = create_oceandirect_api()                  # Ocean Direct API
        self.dev_count = self.od.find_usb_devices()         # Device count
        self.dev_ids = self.od.get_device_ids()             # Device IDs (if multiple)
        self.api_info = self.od.get_api_version_numbers()   # API info
        
        self.dev = None         # OD API device class
        self.dev_id = None      # Store the device ID
        self.dev_serial = None  # device serial number
        
        # Aquisition related parameters
        self.integration_time_min = None        # int: Stores the spectrometer's minimum allowable integration time [millisec]
        self.integration_time_max = None        # int: Stores the spectrometer's maximum allowable integration time [millisec]
        self.integration_time_inc = None        # int: Stores the spectrometer's allowable integration time increment [millisec]
        
        # Calibration related parameters
        self.bg_acq_num = 10    # Number of aquisition for the background removal
        self.bg_spec = None     # The background spectrum
        
        
        # Lock for the device communications
        self._lock = Lock()     # Lock for the acquisition process
        
        self._mode:Literal['discreet','continuous'] = ControllerSpecificConfigEnum.OCEANINSIGHT_MODE.value
        if not self._mode in ['discreet','continuous']: self._mode = 'continuous'
        
        # >>> Current implementation is for the 'continuous' mode only. The 'discreet' mode seems to be causing some weird communication slowdowns.
        print(f"\n>>>>> QEPro: Current mode: {self._mode}")
        print(f"Warning: The 'discreet' mode is NOT FULLY IMPLEMENTED yet and might cause some random SLOWDOWNS. If you experience any issues, please switch to the 'continuous' mode.\n")
        print("<<<<<\n")
        
        
        # Measurement related parameters
        if self._mode == 'discreet':
            self._init_timestamp = None # Initial timestamp of the measurement
            self._offset_timestamp = None # Offset timestamp of the measurement
            self._temp_list_mea = []    # Temporary list to transfer measurements from the device
            self._temp_list_ts = []     # Temporary list to transfer timestamps from the device
        
        # Acquisition parameters:
        self._wavelength:list = None
        
        # Start the initialisation process
        self.initialisation()

# Core functionalities (initialisation, termination)
    def initialisation(self):
        """
        Initializes the Raman spectrometer controller.
        
        This function performs the following tasks:
        1. Prints the API info and the number of devices connected.
        2. Checks if any device is found. If not, it terminates the program.
        3. Checks if more than one device is found. If so, it terminates the program.
        4. Creates a device instance using the first device in the device list.
        5. Retrieves the serial number of the device.
        6. Retrieves the integration time requirements of the device.
        """
        # Print the API info and the devices connected
        print("API Version  : %d.%d.%d " % self.api_info)   # if this doesn't work, try (self.api_info[0],self.api_info[1],self.api_info[2])
        print("Total Device : %d     \n" % self.dev_count)
        
        if self.dev_count == 0:
            print(">> No device found <<")
            self.terminate()
            return
        elif self.dev_count>1:
            print(">> More than 1 device is found <<")
            print("The program has not been designed to handle more than 1 devices and thus will be shut down")
            self.terminate(True)
            return
        
        # Create a device instance by taking the 1st in the device list
        self.dev_id = self.dev_ids[0]
        self.dev = self.od.open_device(self.dev_id)
        self.dev_serial = self.dev.get_serial_number()
        print("First Device : %d       " % self.dev_id)
        print("Serial Number: %s     \n" % self.dev_serial)
        
        # Retrieve the integration time requirements of the device
        self.integration_time_max = self.dev.get_maximum_integration_time()
        self.integration_time_min = self.dev.get_minimum_integration_time()
        self.integration_time_inc = self.dev.get_integration_time_increment()
        
        # Initialise the timestamp
        if self._mode == 'discreet':
            with self._lock:
                int_time = self.dev.get_integration_time()
                min_int_time = self.dev.get_minimum_integration_time()
                self.dev.set_integration_time(min_int_time)
                
                self._init_timestamp = get_timestamp_us_int()
                self._temp_list_mea.clear(); self._temp_list_ts.clear()
                
                # self.dev.Advanced.set_number_of_backtoback_scans(1)
                self.dev.Advanced.acquire_spectra_to_buffer()
                self.dev.Advanced.get_raw_spectrum_with_metadata(self._temp_list_mea, self._temp_list_ts, 1)
                
                self._offset_timestamp = self._temp_list_ts[-1]
                self.dev.set_integration_time(int_time)
        
        if self._mode == 'continuous':
            with self._lock:
                self.dev.Advanced.acquire_spectra_to_buffer()
        
        # Grab the wavelengths of the device
        self._wavelength = self.dev.get_wavelengths()
        
    def terminate(self, error_flag=False):
        """
        To terminate the connections to the Raman spectrometers

        Args:
            error_flag (bool, optional): Can also passes an error message. Defaults to False.
        """
        if error_flag!=False:
            print("\n Error code:")
            print(error_flag)
        
        for i in range(len(self.dev_ids)):
            self.od.close_device(self.dev_ids[i])
        
        print("\n>>>>> Raman controller TERMINATED <<<<<")
        print("Ocean Insight devices disconnected")

    def get_integration_time_limits_us(self):
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
        with self._lock:
            int_time = self.dev.get_integration_time()
        return int_time
    
    def set_integration_time_us(self,integration_time:int):
        """Sets the integration time of the device

        Args:
            integration_time (int): Integration time in [device unit] 
            (microseconds for the QE Pro)

        Returns:
            int: Device integrationt time after set up
        """
        
        print('work here (raman spectrometer controller file)')
        
        if not isinstance(integration_time,int) and not isinstance(integration_time,float):
            raise ValueError("Integration time must be an integer")
        integration_time = int(integration_time)
        
        with self._lock:
            self.dev.set_integration_time(integration_time)
            int_time = self.dev.get_integration_time()
        
        return int_time
    
# Spectrometer acquisition control
    def _acquisitionDelay(self, delay_value):
        """
        Sets the acquisition delay of the spectrometer.
        This may also be referred to as the trigger delay.
        In any event, it is the time between some event (such as a request for data, or an external trigger pulse) and when data acquisition begins.

        Q. Why is it needed?
        Sometimes we want to delay the acquisition so that the 
        
        Args:
            delay_value (int): The acquisition delay to be set [us]
        """
        #device.set_acquisition_delay(120)
        #print("acquisitionDelay(device): set acqDelay 120")
        device = self.dev
        
        acqDelay    = device.get_acquisition_delay()
        acqDelayInc = device.get_acquisition_delay_increment()
        acqDelayMin = device.get_acquisition_delay_minimum()
        acqDelayMax = device.get_acquisition_delay_maximum()

        print("acquisitionDelay(device): acqDelay     =  %d " % acqDelay)
        print("acquisitionDelay(device): acqDelayInc  =  %d " % acqDelayInc)
        print("acquisitionDelay(device): acqDelayMin  =  %d " % acqDelayMin)
        print("acquisitionDelay(device): acqDelayMax  =  %d " % acqDelayMax)
        print("")

        # Now to set the delay value
        with self._lock:
            self.dev.set_acquisition_delay(delay_value)
            print("acquisitionDelay(device): set acqDelay =  %d " % delay_value)

            # Print the new delay value to check
            acqDelay = self.dev.get_acquisition_delay()
        print("acquisitionDelay(device): get acqDelay(expected %d)  =  %d " % (delay_value,acqDelay))
        print("")
    
    def _set_analyser_boxcar(self, scanToAve, boxcarWidth):
        """
        A function to smoothen the read spectrum using the boxcar method.
        Basically, it takes the points around it and averages them out.
        It also takes several acquisition data and averages them too, hence the name boxcar.

        Args:
            scanToAve (int): the number of scan acquisition to be averaged out
            boxcarWidth (int): the number of neighboring data points to be averaged out
        """
        
        # Set the device to set up as the device of this current class instance
        device = self.dev
        try:
            value = device.get_scans_to_average() #Gets the number of spectra to average.
            print("scanToAverageBoxcar(): cur scans_to_average        =  %d" % value)

            value = device.get_integration_time() #Returns the current integration time on the device in microseconds.
            print("scanToAverageBoxcar(): current integrationTimeUs   =  %dus" % value)

            minAveIntTime = device.get_minimum_averaging_integration_time()
            # This function returns the smallest integration time setting, in microseconds, that is valid for the spectrometer.
            # NOTE: some devices that make use of onboard functionality to perform averaging have a different, larger, minimum integration time
            # for acquisition when averaging is enabled. Refer to the documentation for your spectrometer to see if this is the case. The 
            # minimum integration time when averaging is enabled can be determined using odapi_get_minimum_averaging_integration_time_micros.
            print("scanToAverageBoxcar(): minAverageIntegrationTimeUs =  %d" % minAveIntTime)
            print("")
        except self.OceanDirectError as err:
            [errorCode, errorMsg] = err.get_error_details()
            print("scanToAverageBoxcar(): set/get / %d = %s" % (errorCode, errorMsg))

        try:
            # Sets the number of spectra to average.
            print("scanToAverageBoxcar(): set_scans_to_average        =  %d" % scanToAve)
            device.set_scans_to_average(scanToAve)
        except self.OceanDirectError as err:
            [errorCode, errorMsg] = err.get_error_details()
            print("scanToAverageBoxcar(): ERROR with code/scanToAverage, %d = %s ************" % (errorCode, scanToAve))

        try:
            # Print to check the new value
            value = device.get_scans_to_average()
            print("scanToAverageBoxcar(): get_scans_to_average        =  %d" % value)

        except self.OceanDirectError as err:
            [errorCode, errorMsg] = err.get_error_details()
            print("scanToAverageBoxcar(device): set/get / %d = %s" % (errorCode, errorMsg))

        try:
            # Sets the boxcar width to average the spectral data.
            device.set_boxcar_width(boxcarWidth)
            print("scanToAverageBoxcar(): set_boxcar_width            =  %d" % boxcarWidth)

            # Print to check the boxcar width we just set
            value = device.get_boxcar_width()
            print("scanToAverageBoxcar(): get_boxcar_width            =  %d" % value)

        except self.OceanDirectError as err:
            [errorCode, errorMsg] = err.get_error_details()
            print("scanToAverageBoxcar(): set/get / %d = %s" % (errorCode, errorMsg))
        print("")
        
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
            if self._mode == 'continuous':
                timestamp = get_timestamp_us_int()
                intensity_raw = self.dev.get_formatted_spectrum()
                timestamp = int((timestamp + get_timestamp_us_int())/2)
            
            if self._mode == 'discreet':
                # new method:
                adv = self.dev.Advanced
                adv.abort_acquisition()
                adv.clear_data_buffer()
                
                self._temp_list_mea.clear()
                self._temp_list_ts.clear()
                
                adv.acquire_spectra_to_buffer()
                adv.get_raw_spectrum_with_metadata(self._temp_list_mea, self._temp_list_ts, 1)
                
                adv.abort_acquisition()
                adv.clear_data_buffer()
                
                intensity_raw = self._temp_list_mea[-1]
                timestamp = self._temp_list_ts[-1] + self._init_timestamp - self._offset_timestamp
                
            wavelength = self._wavelength
            integration_time = self.dev.get_integration_time()
        
        # Convert ctypes LP_c_double objects to Python floats
        # The Ocean Direct API returns ctypes objects that need to be converted
        try:
            # For continuous mode: intensity_raw is a ctypes array
            # For discrete mode: intensity_raw is a ctypes POINTER(c_double)
            if hasattr(intensity_raw, '_length_'):
                # It's a ctypes array, convert each element
                intensity = [float(intensity_raw[i]) for i in range(len(intensity_raw))]
            else:
                # It's a ctypes pointer, convert each element by indexing
                # Get the length from wavelength array since they should match
                intensity = [float(intensity_raw[i]) for i in range(len(wavelength))]
        except (TypeError, AttributeError):
            # Fallback: if intensity_raw is already a list of floats, use as-is
            intensity = intensity_raw
        
        spectra = pd.DataFrame({
            DataAnalysisConfigEnum.WAVELENGTH_LABEL.value: wavelength,
            DataAnalysisConfigEnum.INTENSITY_LABEL.value: intensity,
        })
        return (spectra, timestamp, integration_time)
    
    def self_test_get_spec_formatted(self):
        """
        Q. Honestly, I don't really understand what this does.
        """
        device = self.dev
        sn = self.dev_serial
        try:
            #100ms
            device.set_integration_time(100000)

            print("Reading spectra for dev s/n = %s" % sn, flush=True)
            for i in range(10):
                spectra = device.get_formatted_spectrum()
                print("spectra[100]: %d, %d, %d, %d" % (spectra[100], spectra[101], spectra[102], spectra[103]), flush=True)
        except self.OceanDirectError as err:
            [errorCode, errorMsg] = err.get_error_details()
            print("get_spec_formatted(device): exception / %d = %s" % (errorCode, errorMsg))
            

        """
        To set up an external light source
        """
        device = self.dev
        periodInc = 0
        try:
            periodInc = device.Advanced.get_continuous_strobe_period_increment()
            print("continuousStrobe(device): period increment =  %d " % periodInc)
        except self.OceanDirectError as err:
            [errorCode, errorMsg] = err.get_error_details()
            print("continuousStrobe(device): get_continuous_strobe_period_increment() %d = %s" % (errorCode, errorMsg))

        strobePeriod = device.Advanced.get_continuous_strobe_period()
        print("continuousStrobe(device): get strobePeriod =  %d " % strobePeriod)

        strobeEnable = device.Advanced.get_continuous_strobe_enable()
        print("continuousStrobe(device): get strobeEnable =  %s " % strobeEnable)

        values = [False, True]
        for enable in values:
            device.Advanced.set_continuous_strobe_enable(False)
            print("continuousStrobe(device): get strobeEnable =  %s " % enable)
            strobeEnable = device.Advanced.get_continuous_strobe_enable()
            print("continuousStrobe(device): set strobeEnable =  %s " % enable)
            print("")

        try:
            periodMin = device.Advanced.get_continuous_strobe_period_minimum()
            print("continuousStrobe(device): periodMin          =  %d " % periodMin)
        except self.OceanDirectError as err:
            [errorCode, errorMsg] = err.get_error_details()
            print("continuousStrobe(device): get_continuous_strobe_period_minimum() %d = %s" % (errorCode, errorMsg))

        try:
            periodMax = device.Advanced.get_continuous_strobe_period_maximum()
            print("continuousStrobe(device): periodMax          =  %d " % periodMax)
        except self.OceanDirectError as err:
            [errorCode, errorMsg] = err.get_error_details()
            print("continuousStrobe(device): get_continuous_strobe_period_maximum() %d = %s" % (errorCode, errorMsg))



        strobePeriodList = [1200, 1505, 800, 453]
        for period in strobePeriodList:
            if (periodInc > 1) and ((period % periodInc) != 0):
                print("continuousStrobe(device): set strobePeriod =  %d  ====> ********* expecting EXCEPTION!" % period)

            try:
                device.Advanced.set_continuous_strobe_period(period)
                print("continuousStrobe(device): set strobePeriod =  %d " % period)
            except self.OceanDirectError as err:
                [errorCode, errorMsg] = err.get_error_details()
                print("continuousStrobe(device): set_continuous_strobe_period() %d = %s" % (errorCode, errorMsg))

            try:
                period = device.Advanced.get_continuous_strobe_period()
                print("continuousStrobe(device): get strobePeriod =  %d " % period)
            except self.OceanDirectError as err:
                [errorCode, errorMsg] = err.get_error_details()
                print("continuousStrobe(device): get_continuous_strobe_period() %d = %s" % (errorCode, errorMsg))
            print("")

        try:
            strobeWidth = 216
            device.Advanced.set_continuous_strobe_width(strobeWidth)
            print("continuousStrobe(device): set strobeWidth    =  %d " % strobeWidth)

            strobeWidth = device.Advanced.get_continuous_strobe_width()
            print("continuousStrobe(device): get strobeWidth    =  %d " % strobeWidth)
        except self.OceanDirectError as err:
            [errorCode, errorMsg] = err.get_error_details()
            print("continuousStrobe(device): %d = %s" % (errorCode, errorMsg))

        print("")
    
# Set of commands for testing/automation
    def self_test(self):
        self._acquisitionDelay(400)
        self._set_analyser_boxcar(scanToAve= 2, boxcarWidth= 0)
        self.self_test_get_spec_formatted()
        
        #Reset the analyser
        self._set_analyser_boxcar(scanToAve= 1, boxcarWidth= 0)
        
# def fiber_coupling():
#     """
#     A function to help with the fiber coupling of the spectrometer.
    
#     """
#     import matplotlib
#     import matplotlib.pyplot as plt
    
#     matplotlib.use('TkAgg')
#     import msvcrt
    
#     spec = SpectrometerController_QEPro()
#     spec.set_integration_time_us(500e3) # 500ms
    
#     list_intensity = []
    
#     print("Press 'q' to quit the program")
#     while True:
#         if msvcrt.kbhit():
#             key = msvcrt.getch()
#             if key == b'q':
#                 break
        
        
#         intensity = spec.dev.get_formatted_spectrum()
#         sum_intensity = sum(intensity)
        
#         if len(list_intensity) > 100:
#             list_intensity.pop(0)
            
#         list_intensity.append(sum_intensity)
        
#         plt.clf()
#         plt.plot(list_intensity, color='r')
#         plt.scatter([i for i in range(len(list_intensity))], list_intensity, color='b')
#         plt.title("Fiber coupling")
#         plt.xlabel("Time point [a.u.]")
#         plt.ylabel("Sum of intensity (all pixels) [a.u.]")
#         plt.show(block=False)
#         plt.draw()
#         plt.pause(0.1)
        
#     spec.terminate()
#     plt.close()
#     print("Fiber coupling terminated")
        
if __name__ == '__main__':
    r_spec = SpectrometerController_QEPro()
    # r_spec.self_test()
    
    res = r_spec.measure_spectrum()
    r_spec.terminate()
    
    print(res)
    
    # fiber_coupling()
