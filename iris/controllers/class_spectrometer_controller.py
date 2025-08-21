"""
Class definition for the Raman spectrometer controller and a guide to writing one for the IRIS
"""

import os
import sys
import pandas as pd
from multiprocessing import Lock

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))
    

from iris.utils.general import *

class Class_SpectrometerController():
    def __init__(self) -> None:
        # <<<<< Insert the device initialisation commands here (connection, parameters, etc.)
        
        self._lock = Lock()     # Lock for the acquisition process
        
        # Start the initialisation process
        self.initialisation()

# Core functionalities (initialisation, termination)
    def initialisation(self) -> None:
        """
        Initializes the Raman spectrometer controller.
        """
        # <<<<< Insert the initialisation commands here
        pass
        
        
    def terminate(self) -> None:
        """
        To terminate the connections to the Raman spectrometers
        """
        # <<<<< Insert the termination commands here
        pass
    
        print("\n>>>>> Raman controller TERMINATED <<<<<")
    
    def get_integration_time_us(self) -> int:
        """
        Get the integration time of the device

        Returns:
            int: Integration time in [device unit] (microseconds for the QE Pro)
        """
        with self._lock:
            # <<<<< Insert the command to get the integration time here
            int_time = 100
            pass
        
        return int_time
    
    def set_integration_time_us(self,integration_time:int) -> int:
        """Sets the integration time of the device

        Args:
            integration_time (int): Integration time in [device unit] 
            (microseconds for the QE Pro)

        Returns:
            int: Device integrationt time after set up in microseconds
        """
        
        print('work here (raman spectrometer controller file)')
        
        if not isinstance(integration_time,int) and not isinstance(integration_time,float):
            raise ValueError("Integration time must be an integer")
        integration_time = int(integration_time)
        
        with self._lock:
            # <<<<< Insert the command to set the integration time here
            pass
            int_time = self.get_integration_time_us()
        
        return int_time
        
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
            # <<<<< Insert the command to measure the spectrum here
            intensity = []
            wavelength = []
            pass
            
            timestamp = get_timestamp_us_int()
            integration_time = self.get_integration_time_us()
        
        spectra = pd.DataFrame({
            DataAnalysisConfigEnum.WAVELENGTH_LABEL.value: wavelength,
            DataAnalysisConfigEnum.INTENSITY_LABEL.value: intensity,
        })
        return (spectra, timestamp, integration_time)
    
# Set of commands for testing/automation
    def self_test(self):
        # <<<<< Insert the self-test commands here
        pass

if __name__ == '__main__':
    r_spec = raman_spectrometer_controller()
    r_spec.self_test()
    
    spectra = r_spec.measure_spectrum()[0]
    r_spec.terminate()

    spectra.to_csv('spectra_dummy.csv',index=False)
    
    # Plotting using the DataFrame
    import matplotlib.pyplot as plt
    plt.plot(spectra['Wavelength [nm]'], spectra['Intensity [a.u.]'])
    plt.show()
    