"""
A class that allows the control of the QE Pro spectrometer from Ocean Insight.
This implementation is based on the API provided by Ocean Insight.

Inspiration: Ocean Insight Inc. example code
Made on: 04 March 2024
For: The Thomas Group, Biochemical Engineering Dept., UCL
By: Kevin Uning
"""

import os
import sys
import time
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
matplotlib.use('Agg')

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))
    

from iris.utils.general import *

from iris.controllers.class_spectrometer_controller import Class_SpectrometerController

class SpectrometerController_Dummy(Class_SpectrometerController):
    def __init__(self, **kwargs) -> None:
        # self.od = OceanDirectAPI()                          # Ocean Direct API
        # self.dev_count = self.od.find_usb_devices()         # Device count
        # self.dev_ids = self.od.get_device_ids()             # Device IDs (if multiple)
        # self.api_info = self.od.get_api_version_numbers()   # API info
        
        self.dev = dummy_spectrometer()         # OD API device class
        self.dev_id = None      # Store the device ID
        self.dev_serial = None  # device serial number
        
        # Aquisition related parameters
        self.integration_time_us = 500e3        # int: Stores the spectrometer's integration time [microsec]
        self.integration_time_min = 10        # int: Stores the spectrometer's minimum allowable integration time [millisec]
        self.integration_time_max = 10000        # int: Stores the spectrometer's maximum allowable integration time [millisec]
        self.integration_time_inc = 25        # int: Stores the spectrometer's allowable integration time increment [millisec]
        
        # Calibration related parameters
        self.bg_acq_num = 10    # Number of aquisition for the background removal
        self.bg_spec = None     # The background spectrum
        
        # Start the initialisation process
        print("\n>>>>> DUMMY Raman controller is used <<<<<")
        self.initialisation()
        
    def get_identifier(self) -> str:
        return "Dummy Spectrometer Controller"
        
# Core functionalities (initialisation, termination)
    def initialisation(self):
        pass
        
    def terminate(self, error_flag=False):
        """
        To terminate the connections to the Raman spectrometers

        Args:
            error_flag (bool, optional): Can also passes an error message. Defaults to False.
        """
        if error_flag!=False:
            print("\n Error code:")
            print(error_flag)
        
        print("\n>>>>> Raman controller TERMINATED <<<<<")
        print("Ocean Insight devices disconnected")

# Spectrometer acquisition control
    def acquisitionDelay(self, delay_value):
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
        
        acqDelay    = 5
        acqDelayInc = 1
        acqDelayMin = 0
        acqDelayMax = 1000

        print("acquisitionDelay(device): acqDelay     =  %d " % acqDelay)
        print("acquisitionDelay(device): acqDelayInc  =  %d " % acqDelayInc)
        print("acquisitionDelay(device): acqDelayMin  =  %d " % acqDelayMin)
        print("acquisitionDelay(device): acqDelayMax  =  %d " % acqDelayMax)
        print("")

        # Now to set the delay value
        print("acquisitionDelay(device): set acqDelay =  %d " % delay_value)

        # Print the new delay value to check
        acqDelay = delay_value
        print("acquisitionDelay(device): get acqDelay(expected %d)  =  %d " % (delay_value,acqDelay))
        print("")
    
    def set_analyser_boxcar(self, scanToAve, boxcarWidth):
        """
        A function to smoothen the read spectrum using the boxcar method.
        Basically, it takes the points around it and averages them out.
        It also takes several acquisition data and averages them too, hence the name boxcar.

        Args:
            scanToAve (int): the number of scan acquisition to be averaged out
            boxcarWidth (int): the number of neighboring data points to be averaged out
        """
        
        print("Assume that things has been set properly")
        
    # def get_spec(self):
    #     device = self.dev
        
    #     print("Integration time: %d" %(device.get_integration_time()))
        
    #     intensity = device.get_formatted_spectrum()
    #     wavelength = device.get_wavelengths()
    #     timestamp = [datetime.now()] * len(intensity)
        
    #     spectra = pd.DataFrame({
    #     'Wavelength [nm]': wavelength,
    #     'Intensity [a.u.]': intensity,
    #     'Timestamp [yyyy-mm-dd hh:mm:ss.microsec]': timestamp
    #     })
        
    #     return spectra
    
    def measure_spectrum(self) -> tuple[pd.DataFrame,int,int]:
        """
        Performs a single spectrum measurement using the spectrometer
        
        Returns:
            tuple[pd.DataFrame,int,int]: The measured spectrum, timestamp, and integration time
            
        Note:
            - The measured spectrum is a DataFrame with the (wavelength and intensity) columns set in the config file.
            - The timestamp is in the integer format [us].
        """
        def dummy_raman_spectrum(x, num_peaks=5):
            # Dummy raman spectrum fixed parameters
            list_A = [0.7,0.4,0.55,1.0,0.5]
            list_x0 = [800, 950, 1200, 1600, 1800]
            list_sigma = [10, 20, 30, 40, 50]
            spectrum = np.zeros_like(x)
            for i in range(num_peaks):
                # A = np.random.uniform(0.1, 1.0)  # Intensity
                # x0 = np.random.uniform(300, 2000)  # Wavenumber
                # sigma = np.random.uniform(5, 50)  # Width
                A = list_A[i%len(list_A)]
                x0 = list_x0[i%len(list_x0)]
                sigma = list_sigma[i%len(list_sigma)]
                
                spectrum += A * np.exp(-0.5 * ((x - x0) / sigma) ** 2)
            return spectrum

        time1_sec = get_timestamp_us_int()/1e6
        
        x_range = np.linspace(800, 2000, 1000)
        raman_spectrum = dummy_raman_spectrum(x_range)
        
        wavelength = x_range
        intensity = raman_spectrum * 100
        
        def add_uniform_noise(data, low=-1.0, high=1.0):
            noise = np.random.uniform(low, high, data.shape)
            return data + noise
        
        noisy_intensity = add_uniform_noise(intensity,low=-5,high=5)
        timestamp = get_timestamp_us_int()
        spectra = pd.DataFrame({
        'Wavelength [nm]': wavelength,
        'Intensity [a.u.]': noisy_intensity,
        })
        
        integration_time_sec = self.integration_time_us/1e6
        time2_sec = get_timestamp_us_int()/1e6
        
        # Sleep for the remaining time
        if (time2_sec-time1_sec) < integration_time_sec:
            time.sleep(integration_time_sec - (time2_sec-time1_sec))
        # time3_sec = get_timestamp_us_int()/1e6
        # print ('Integration time: ',integration_time_sec)
        # print('Time taken: ',time3_sec-time1_sec)
        
        return (spectra,timestamp,self.integration_time_us)
    
    def get_integration_time_us(self):
        """
        Returns the integration time of the device in [microsec]

        Returns:
            int: Integration time in [microsec]
        """
        return self.integration_time_us
    
    def get_integration_time_limits_us(self):
        """
        Returns the minimum, maximum, and increment of the integration time of the device

        Returns:
            tuple: (min, max, increment) of the integration time in [microsec]
        """
        return (self.integration_time_min, self.integration_time_max, self.integration_time_inc)
    
    def set_integration_time_us(self,integration_time):
        """
        Sets the integration time of the device

        Args:
            integration_time (int): Integration time in [millisec]

        Returns:
            int: Device integrationt time after set up
        """
        self.integration_time_us = integration_time
        return self.integration_time_us
        
# <<<<< Implementations: requires additional checks on the min, max, and increment of the integration time
        
        # sets the integration time of the device
        try: # try to set
            print('integration time set to {}'.format(integration_time))
            print(type(integration_time))
        except: # if failure reports it
            print('integration time could not be set:')
            print('error message here')
        
        # reads the actual device integration time
        device_integration_time = integration_time
        
        return device_integration_time
        
class dummy_spectrometer():
    def __init__(self) -> None:
        self.integration_time_us = 10*1000 # 10 ms
    
    def get_integration_time(self):
        return self.integration_time_us
    
    def set_integration_time(self,int_time):
        self.integration_time_us = int_time

if __name__ == '__main__':
    r_spec = SpectrometerController_Dummy()
    r_spec.set_integration_time_us(250e3)
    
    print(r_spec.get_integration_time_us())
    
    spectra = r_spec.measure_spectrum()[0]
    # r_spec.termination()

    # spectra.to_csv('spectra_dummy.csv',index=False)
    
    # Plotting using the DataFrame
    plt.plot(spectra['Wavelength [nm]'], spectra['Intensity [a.u.]'])
    plt.show()
    