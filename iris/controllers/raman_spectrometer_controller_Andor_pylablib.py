"""A class that allows the control of the Andor spectrometers.

Technical notes:
This script is based on the Andor CCD iVac 316 though, the it should 
be applicable to most of Andor's other spectrometers with minimal to
no adjustments (aside from the advance features).

Acknowledgement:
pylablib for the library that provides the interface to the spectrometer.
"""
import os
import sys
import time
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
# if not __name__ == '__main__': matplotlib.use('Agg')

from multiprocessing import Lock

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))
    

from iris.utils.general import *
from iris.controllers.class_spectrometer_controller import Class_SpectrometerController

from iris import DataAnalysisConfigEnum
from iris.controllers import ControllerSpecificConfigEnum

# Pylablib import setup
import pylablib as pll
# Add the path to the Andor SDK2 DLLs
pll.par["devices/dlls/andor_sdk2"] = ControllerSpecificConfigEnum.ANDOR_ATMCD64D_DLL_PATH.value
pll.par['devices/dlls/andor_shamrock'] = ControllerSpecificConfigEnum.ANDOR_ATSPECTROGRAPH_DLL_PATH.value

from pylablib.devices import Andor
from pylablib.devices.interface.camera import TFrameInfo

# To STAY in the file
DEFAULT_TEMRINATION_TEMPERATURE = 0.0

def test(spec: Andor.AndorSDK2Camera):
    # > 2. Cooler test
    temp = spec.get_temperature()
    print(f"Temperature: {temp}, type: {type(temp)}")
    spec.set_temperature(temp,enable_cooler=False)
    try: print(f'Cooler status: {spec.cooler_status}')
    except Exception as e: print('2. Cooler test ERROR: {e}')
    print("Test 2. Cooler: OK")
    
    try:
        # > 3. Acquisition setup test (single mode)
        # spec.set_acquisition_mode(mode='single')
        print('3.1. Acquisition mode: single')
        spec.setup_shutter(mode='auto')
        print('3.2. Shutter mode: auto')
        spec.set_trigger_mode(mode='int')    # function 'SetTriggerMode' raised error 20095(DRV_INVALID_TRIGGER_MODE) for 'software' trigger mode
        print(f'3.3. Trigger mode: {spec.get_trigger_mode()}')      # maybe it doesn't have the software trigger mode (?)
        spec.set_exposure(200e-3) # Sets the exposure time of the spectrometer in [sec], set to 100ms
        print(f'3.4. Exposure time: {spec.get_exposure()*1000} [ms]')
        print("Test 3. Acquisition setup (single mode): OK")
        
        spec.set_acquisition_mode('cont')
        # spec.setup_kinetic_mode()
        print(f'3.5. Acquisition mode: {spec.get_acquisition_mode()}')
        print(f'3.5. Acquisition parameters {spec.get_acquisition_parameters()}')
        
    except Exception as e: print(f'3. Acquisition setup ERROR: {e}')
    
    try:
        # > Start acquisition
        spec.start_acquisition()
    except Exception as e: print(f'Start acquisition ERROR: {e}')
    
    try:
        spec.wait_for_frame()
        img = spec.read_newest_image(return_info=False)
    except Exception as e: print(f'4. Acquisition test ERROR: {e}')
    try: print(f"4.4. Image shape: {img.shape}, type: {type(img)}")
    except Exception as e: print(f"4.4. Image: {e}")
    
    print(f"4.4. Image: {img}")
    try: plt.imshow(img); plt.show()
    except Exception as e: print(f"4.5. Plotting: {e}")
    
    # > 5. Metadata test
    # acquire_single()
    # res = spec.grab(1,frame_timeout=1,return_info=False)
    res = spec.read_newest_image(return_info=True)
    print(f"5.1. Type of the result: {type(res)}")
    try: print(f"5.1. Type_img: {type(res[0])}, type_info: {type(res[1])}")
    except Exception as e: print(f"5.1. Metadata test (print result elements): {e}")
    try: print(f"5.2. Result: {res}")
    except Exception as e: print(f"5.2. Metadata test (print result): {e}")
    try: print(f'5.3. Metadata: {res[1]}')
    except Exception as e: print(f'5.3. Metadata print ERROR: {e}')
    try:print(f'5.4. Frame info fields: {spec.get_frame_info_fields()}')
    except Exception as e: print(f'5.4. Frame info get ERROR: {e}')
    
    # > Stop acquisition
    try: spec.stop_acquisition()
    except Exception as e: print(f'Stop acquisition ERROR: {e}')
    
    # > 6. Spectrometer termination test
    spec.set_cooler(False)
    print("6.1. Cooler: OFF")
    print(f'6.1. Temperature: {spec.get_temperature()}')
    print("Test 6. Spectrometer termination: OK")
    
    
def initialization() -> Andor.AndorSDK2Camera:
    print(Andor.list_shamrock_spectrographs())
    # > 1. Connect to the spectrometer
    spec = Andor.AndorSDK2Camera()
    print("Test 1. Connection: OK")
    return spec
    
def termination(spec: Andor.AndorSDK2Camera):
    # !!! IMPORTANT NOTE !!!
    # Always close the spectrometer to release the resources!
    # Otherwise, it will need an os restart (i.e., to restart the PC)
    # to be able to use the spectrometer again.
    spec.close()
    
    
    
    
    
    
    

class SectrometerController_AndorSDK2(Class_SpectrometerController):
    def __init__(self,monitor_temp:bool=False) -> None:
        # > Devices <
        self._dev:Andor.AndorSDK2Camera = None
        
        # > Operational parameters
        self._ope_temperature_degC = None   # Temperature of the device in degrees Celsius
        self._enable_cooler = True          # Enable the cooler functionality
        self._flg_monitor_temp = monitor_temp
        
        # > Locks <
        self._lock = Lock()     # Lock for the acquisition process
        self._flg_monitortemp_isrunning = threading.Event()
        
        # > Device parameters <
        self.integration_time_min = 1000    # Minimum device integration time in [microsec]
        self.integration_time_max = 1e10    # Maximum device integration time in [microsec]
        self.integration_time_inc = 10      # Integration time increment in [microsec]
        
        # Internal parameters
        self._integration_time_devUnit = 0.0    # Integration time (stored in the object, NOT the unit) in the device's unit
        
        # Start the initialisation process
        self.initialisation()
        
        print('NOT YET IMPLEMENTED: ROI AND BINNING')

# Core functionalities (initialisation, termination)
    def initialisation(self) -> None:
        """
        Initializes the Raman spectrometer controller.
        """
        self._dev = Andor.AndorSDK2Camera()
        print(f'>>>>> CONNECTED TO {self._dev.get_device_info()} <<<<<')
        
        # > Monitor temperature if requested
        if self._flg_monitor_temp: self.monitor_temperature()
        
        # > Initialise the cooler
        self._enable_cooler = True
        try: temp = float(ControllerSpecificConfigEnum.ANDOR_OPERATIONAL_TEMPERATURE.value)
        except: temp = self._dev.get_temperature(); self._enable_cooler = False
        self._dev.set_temperature(temp,enable_cooler=self._enable_cooler)
        print(f'Cooler enabled: {self._enable_cooler}, temperature: {temp}degC')
        
        if self._enable_cooler: self._wait_temperature(temp,cooling=True)
        
        # > Initialise the acquisition mode
        self._dev.setup_shutter(mode='auto')
        self._dev.set_trigger_mode(mode='int')
        self._dev.set_acquisition_mode('cont')
        # self._dev.set_acquisition_mode('single')
        print(f'Acquisition parameters: {self._dev.get_acquisition_parameters()}')
        
        # > Set the ROI and binning
        try: self._set_ROI_binning()
        except Exception as e: print(f'ROI and binning ERROR: {e}')
        finally: print(f'ROI and binning: {self._dev.get_roi()}')
            
        
    def terminate(self) -> None:
        """
        To terminate the connections to the Raman spectrometers
        """
        # Stop the auto measurement
        # if self._dev.acquisition_in_progress(): self._dev.stop_acquisition()
        
        # Turn off the cooler
        try: temp = float(ControllerSpecificConfigEnum.ANDOR_TERMINATION_TEMPERATURE.value)
        except: temp = DEFAULT_TEMRINATION_TEMPERATURE
        if not self._enable_cooler: temp = self._dev.get_temperature()
        
        self._dev.set_temperature(temperature=temp, enable_cooler=False)
        if self._dev.is_cooler_on(): self._dev.set_cooler(False)
        
        print(f'Termination temperature: {temp}')
        
        if self._enable_cooler: self._wait_temperature(temp,cooling=False)
        print(f'Device back to termination temp')
        
        self._dev.close()
        print("\n>>>>> Raman controller TERMINATED <<<<<")
    
    def _set_ROI_binning(self) -> None:
        """
        Set the region of interest (ROI) of the device
        """
        # > ROI and binning
        # row: horizontal (h), col: vertical (v)
        hlim,vlim = self._dev.get_roi_limits()
        hmin, hmax, hpstep, hsstep, hmaxbin = hlim
        hbin = min(hmaxbin,ControllerSpecificConfigEnum.ANDOR_ROI_BIN_ROW.value,
                   (ControllerSpecificConfigEnum.ANDOR_ROI_ROW_MAX.value-ControllerSpecificConfigEnum.ANDOR_ROI_ROW_MIN.value))
        hstart = max(hmin,ControllerSpecificConfigEnum.ANDOR_ROI_BIN_ROW.value)
        hend = min(hmax,ControllerSpecificConfigEnum.ANDOR_ROI_ROW_MAX.value)
        
        vmin, vmax, vpstep, vsstep, vmaxbin = vlim
        vbin = min(vmaxbin,ControllerSpecificConfigEnum.ANDOR_ROI_BIN_COL.value,
                     (ControllerSpecificConfigEnum.ANDOR_ROI_COL_MAX.value-ControllerSpecificConfigEnum.ANDOR_ROI_COL_MIN.value))
        vstart = max(vmin,ControllerSpecificConfigEnum.ANDOR_ROI_BIN_COL.value)
        vend = min(vmax,ControllerSpecificConfigEnum.ANDOR_ROI_COL_MAX.value)
        
        self._dev.set_roi(
            hstart=hstart,
            hend=hend,
            vstart=vstart,
            vend=vend,
            hbin=hbin,
            vbin=vbin
        )
    
    def get_integration_time_limits_us(self) -> tuple[int,int,int]:
        """
        Get the integration time limits of the device
        
        Returns:
            tuple: A tuple containing the minimum, maximum, and increment of the integration time in [device unit] (microseconds for the QE Pro)
        """
        return (self.integration_time_min, self.integration_time_max, self.integration_time_inc)
    
    def get_integration_time_us(self) -> int:
        """
        Get the integration time of the device
        
        Returns:
            int: Integration time in microseconds
        """
        with self._lock:
            if self._dev.acquisition_in_progress(): self._dev.stop_acquisition()
            self._integration_time_devUnit = self._dev.get_exposure()
            
        int_time_us = self._integration_time_devUnit*1e6
        return int_time_us
    
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
            if self._dev.acquisition_in_progress(): self._dev.stop_acquisition()
            self._dev.set_exposure(integration_time*1e-6)
        int_time = self.get_integration_time_us()
        print(int_time)
        
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
            if not self._dev.acquisition_in_progress(): self._dev.start_acquisition()
        
        # img:np.ndarray = self._dev.snap(timeout=self._integration_time_devUnit)
        # self._dev.wait_for_frame()
        # img:np.ndarray = self._dev.read_newest_image(return_info=False)
        # img = self._dev.grab(1)
        time1 = time.time()
        with self._lock:
            self._dev.wait_for_frame("lastwait")    # Pretty slow, at around 390millisec waiting time
            img:np.ndarray = self._dev.read_newest_image()
            
        # print(img)
        # print(f'image shape: {img.shape}')
        # plt.imshow(img)
        # plt.show()
        
        timestamp = get_timestamp_us_int()
        # print(f'reading time: {(time.time()-time1)*1e3} millisec')
        # self._dev.stop_acquisition()
        # print(img)
        list_intensity = np.mean(img,axis=0)
        list_wavelength = list(range(len(list_intensity)+1,1,-1))
        
        list_wavelength = [float(wavelength) for wavelength in list_wavelength]
        list_intensity = [float(intensity) for intensity in list_intensity]
        
        integration_time = self.get_integration_time_us()
        
        spectra = pd.DataFrame({
            DataAnalysisConfigEnum.WAVELENGTH_LABEL.value: list_wavelength,
            DataAnalysisConfigEnum.INTENSITY_LABEL.value: list_intensity,
        })
        return (spectra, timestamp, integration_time)
    
    def _wait_temperature(self,target_temperature:float,cooling:bool):
        """
        Waits for the device temperature to reach the target temperature

        Args:
            target_temperature (float): The target temperature
            cooling (bool): If True, will return when the device temperature is lower than the target
                temperature. If False, return when the device temperature is above than the target.
        """
        while True:
            try:
                with self._lock: dev_temp = self._dev.get_temperature()
                if cooling and dev_temp <= (target_temperature + 1): break
                elif not cooling and dev_temp >= (target_temperature - 1): break
                time.sleep(1)
                print(f'Camera temperature: {dev_temp} degC, target temperature: {target_temperature}')
            except Exception as e:
                print(f'Error in _wait_temperature: {e}')
        
        print('Target temperature reached')
        
    
    @thread_assign
    def monitor_temperature(self):
        self._flg_monitortemp_isrunning.set()
        try:
            while self._flg_monitortemp_isrunning.is_set():
                with self._lock:
                    temp = self._dev.get_temperature()
                print(f'Spectrometer temperature: {temp}')
                time.sleep(1)
        except: pass
    
# Set of commands for testing/automation
    def self_test(self):
        if not __name__ == '__main__': raise ValueError('This function is only for testing purposes within the file and should not be called externally')
        
        int_time_ms = 100
        print(f'1. Integration time set test: {int_time_ms} ms')
        self.set_integration_time_us(int_time_ms*1e3)
        print(f'1. Integration time get test: {self.get_integration_time_us()} ms')
        int_time_ms = 50
        print(f'1.2. Integration time set test: {int_time_ms} ms')
        self.set_integration_time_us(int_time_ms*1e3)
        print(f'1.2. Integration time get test: {self.get_integration_time_us()} ms')
        
        print('2. Acquisition test')
        # <<<<< Insert the self-test commands here
        import matplotlib.pyplot as plt
        matplotlib.use('TkAgg')
        
        res = self.measure_spectrum()
        spectra,ts,int_time = res
        print(spectra)
        print('^^^^^^^^^^^^ Spectra ^^^^^^^^^^^^\n')
        print(f'Timestamp: {ts}, Integration time: {int_time}')
        plt.plot(spectra[DataAnalysisConfigEnum.WAVELENGTH_LABEL.value],spectra[DataAnalysisConfigEnum.INTENSITY_LABEL.value])
        plt.show()
        
        matplotlib.use('Agg')
    
if __name__ == '__main__':
    dev = SectrometerController_AndorSDK2(monitor_temp=True)
    dev.self_test()
    dev.terminate()
    
    # try:
    #     print('setting integration time')
    #     dev.set_integration_time_us(100e3)
    #     print('Measuring spectrum')
    #     time1 = time.time()
    #     for i in range(20):
    #         res = dev.measure_spectrum()
    #         time2 = time.time()
    #         print(f'time taken: {(time2-time1)*1e3}millisec')
    #         time1 = time2
    #     # print(res)
    #     print('done')
    # except Exception as e: print(e)
    # dev.terminate()
    # spec = initialization()
    # test(spec)
    # termination(spec)