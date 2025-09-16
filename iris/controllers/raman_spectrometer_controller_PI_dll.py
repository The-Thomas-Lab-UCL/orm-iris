"""A class that allows the control of the Princeton Instruments Raman spectrometer.

Technical notes:
Because the PIXIS100 is very slow at capturing single frames,
the acquisition mode is set to 'sequence' and the acquisition
is performed continuously from the creation of the object.
Even with this, as far as I know, the capture rate is still
limited to 10Hz.

Acknowledgement:
Massive thanks to pylablib for the library that provides the interface to the spectrometer.
The dll was written in for C, which we weren't experienced with. Pylablib has provided the
necessary interface to the dll in Python.
"""
import os
import sys
import time
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import multiprocessing as mp
# if not __name__ == '__main__': matplotlib.use('Agg')

import pylablib as pll
from pylablib.devices.PrincetonInstruments.picam_lib import PicamLib
from pylablib.core.utils import ctypes_wrap
from pylablib.devices.PrincetonInstruments.picam_defs import *  # enum definitions

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))
    

from iris.utils.general import *
from iris.controllers.class_spectrometer_controller import Class_SpectrometerController

from iris import DataAnalysisConfigEnum
from iris.controllers import ControllerSpecificConfigEnum as CSEnum

# # Add the directory containing the oceandirect module to the Python path
# module_dir = os.path.abspath(ControllerSpecificConfigEnum.OCEANINSIGHT_API_DIRPATH.value)
# sys.path.append(module_dir)

# >>>>> Pylablib setup <<<<<
pll.par["devices/dlls/picam"] = r"C:\Program Files\Princeton Instruments\PICam\Runtime"
wrapper = ctypes_wrap.CFunctionWrapper(default_rvals="pointer")

# Initialise the library using Pylablib's PicamLib. It already has all the nice wrapper, structs, etc. so
# we don't have to do it ourselves.
pll.par["devices/dlls/picam"] = r"C:\Program Files\Princeton Instruments\PICam\Runtime"
pylablib_picamlib = PicamLib()
pylablib_picamlib.initlib()

picamlib = pylablib_picamlib.lib   # Get the ctypes library object for the PICam library

# NOTE: In addition to containing the DLL, the picamlib from pylablib also contains
# the restype, argtypes, and other definitions for the functions in the library.
# We'll be using these as is for the wrapper function, also obtained from pylablib.
# The only difference here is that we'll be wrapping the functions ourselves instead
# of using the already available wrapped functions in the pycamlib from pylablib.
# This allows us to handle the return values of the functions in a more flexible way.
# (and also because not all PIXIS functions are available in the picamlib from pylablib)

# > Library related
func_Picam_IsLibraryInitialized=wrapper(picamlib.Picam_IsLibraryInitialized)
func_Picam_InitializeLibrary=wrapper(picamlib.Picam_InitializeLibrary)
func_Picam_UninitializeLibrary=wrapper(picamlib.Picam_UninitializeLibrary)

# > Camera related
func_Picam_GetAvailableCameraIDs = wrapper(picamlib.Picam_GetAvailableCameraIDs)
func_Picam_DestroyCameraIDs = wrapper(picamlib.Picam_DestroyCameraIDs, rvals=[])
func_Picam_OpenCamera=wrapper(picamlib.Picam_OpenCamera, rvals=["camera"])
func_Picam_CloseCamera=wrapper(picamlib.Picam_CloseCamera)

# > ROI related
func_Picam_GetParameterRoisDefaultValue=wrapper(picamlib.Picam_GetParameterRoisDefaultValue)
func_Picam_GetParameterRoisValue = wrapper(picamlib.Picam_GetParameterRoisValue)
func_Picam_CanSetParameterRoisValue=wrapper(picamlib.Picam_CanSetParameterRoisValue, rvals=["settable"])
func_Picam_SetParameterRoisValue=wrapper(picamlib.Picam_SetParameterRoisValue, rvals=[])
func_Picam_DestroyRois=wrapper(picamlib.Picam_DestroyRois, rvals=[])

# > Acquisition related
func_Picam_Acquire=wrapper(picamlib.Picam_Acquire,rconv={"available": CPicamAvailableData.tup_struct}, rvals=["available", "errors"])

# > General functions
func_Picam_GetParameterIntegerValue=wrapper(picamlib.Picam_GetParameterIntegerValue)
func_Picam_SetParameterIntegerValue = wrapper(picamlib.Picam_SetParameterIntegerValue)
func_Picam_GetParameterLargeIntegerValue = wrapper(picamlib.Picam_GetParameterLargeIntegerValue)
func_Picam_GetParameterFloatingPointValue=wrapper(picamlib.Picam_GetParameterFloatingPointValue)
func_Picam_SetParameterFloatingPointValue=wrapper(picamlib.Picam_SetParameterFloatingPointValue)
func_Picam_GetParameterValueType = wrapper(picamlib.Picam_GetParameterValueType)
func_Picam_CommitParameters=wrapper(picamlib.Picam_CommitParameters)

class SpectrometerController_PI(Class_SpectrometerController):
    def __init__(self) -> None:
        self._cameraId = None       # Camera ID to initiate a connection
        self._cameraHandle = None   # Camera handle to control the camera
        
        # ROI related parameters
        self._roi_row = (CSEnum.PIXIS_ROI_ROW_MIN.value, CSEnum.PIXIS_ROI_ROW_MAX.value)
        self._roi_col = (CSEnum.PIXIS_ROI_COL_MIN.value, CSEnum.PIXIS_ROI_COL_MAX.value)
        self._roi_bin = (CSEnum.PIXIS_ROI_BIN_ROW.value, CSEnum.PIXIS_ROI_BIN_COL.value)
        
        self._roi_size = None       # Size of the ROI (width, height)
        self._roi_binning = None    # Binning of the ROI
        self._roi_num_pixels = None # Number of read pixels in the ROI
        
        # > Retrieve the other parameters
        # Get the pixel bit depth
        self._roi_pixel_bit_depth = None    # Bit depth of the pixels in the ROI
        
        self._image_data_size = None        # Size of the image data
        self._timestamp_data_size = None    # Size of the timestamp data
        self._frame_data_size = None        # Size of the frame data (image data + timestamp data) 
                                            # assuming 1 frame per readout and assuming that timestmap is enabled
        
        # Timestamp related parameters
        # Device related parameters
        self._timeRes_Hz:float = None               # 'Time Resolution' for time metadata conversion to [sec]
        
        self._integration_time_local_us:int = None  # Integration time in [us] stored in the object (NOT the device)
        
        # Aquisition related parameters
        ## NOTE: these parameters were not defined by the device and thus,
        ## are set arbitrarily. They may need to be adjusted.
        self.integration_time_min = 10          # int: Stores the spectrometer's minimum allowable integration time [millisec]
        self.integration_time_max = 3600*1000   # int: Stores the spectrometer's maximum allowable integration time [millisec]
        self.integration_time_inc = 1           # int: Stores the spectrometer's allowable integration time increment [millisec]
        
        # Lock for communication with the device
        self._lock = mp.Lock()
        
        # Start the initialisation process
        self.initialisation()

# Core functionalities (initialisation, termination)
    def initialisation(self):
        # > Get the camera handle and initialise the connection
        with self._lock:
            # Check if the library is initialised
            if not func_Picam_IsLibraryInitialized():
                func_Picam_InitializeLibrary()
            
            self._cameraId = self._get_cameraId()
            self._cameraHandle = func_Picam_OpenCamera(self._cameraId)
        
            # > Set the timestamp parameters
            # Enable the timestamp metadata
            func_Picam_SetParameterIntegerValue(self._cameraHandle, PicamParameter.PicamParameter_TimeStamps, PicamTimeStampsMask.PicamTimeStampsMask_ExposureStarted)
            func_Picam_CommitParameters(self._cameraHandle)
            
            # Check if the timestamp is enabled
            maskval = func_Picam_GetParameterIntegerValue(self._cameraHandle, PicamParameter.PicamParameter_TimeStamps)
            if maskval!=PicamTimeStampsMask.PicamTimeStampsMask_ExposureStarted:
                raise ValueError("Timestamps not enabled")
            
            # Get the timestamp resolution and bit depth
            self._timeRes_Hz = func_Picam_GetParameterLargeIntegerValue(self._cameraHandle, PicamParameter.PicamParameter_TimeStampResolution)
            self._timestamp_bit_depth = func_Picam_GetParameterIntegerValue(self._cameraHandle, PicamParameter.PicamParameter_TimeStampBitDepth)
        
        # > Set the ROI parameters
        self._set_ROI(row=self._roi_row, col=self._roi_col, bin_row=self._roi_bin[0])
        
        # > Set the default integration time
        self.set_integration_time_us(100e3)
        
        # > Check the acquisition result
        # Check if the acquisition was successful
        self.measure_spectrum()
        
    def terminate(self, error_flag=False):
        """
        To terminate the connections to the Raman spectrometers
        
        Args:
            error_flag (bool, optional): Can also passes an error message. Defaults to False.
        """
        if error_flag!=False: print("\n Error code:",error_flag)
        func_Picam_CloseCamera(self._cameraHandle)
        
        picamlib.Picam_UninitializeLibrary()
        
        self._cameraHandle = None
        self._cameraId = None

        print("\n>>>>> Raman controller TERMINATED <<<<<")
    
    def _get_cameraId(self) -> PicamCameraID:
        """
        Gets the available camera IDs.

        Returns:
            PicamCameraID: The camera ID of the connected camera.
            
        Raises:
            Exception: If no camera is detected or multiple cameras are detected.
        """
        camera_ids,camera_no = func_Picam_GetAvailableCameraIDs()
        
        for i in range(camera_no):
            camera_id:PicamCameraID = camera_ids[i]
            print('Detected camera no:',i)
            print(f"  Model: {camera_id.model}")
            print(f"  Computer Interface: {camera_id.computer_interface}")
            print(f"  Sensor Name: {camera_id.sensor_name.decode('utf-8')}")  # Decode to string
            print(f"  Serial Number: {camera_id.serial_number.decode('utf-8')}") # Decode to string
            print()
                
        if camera_no==0:
            # print('No camera detected')
            # return None
            raise Exception('No camera detected')
        
        func_Picam_DestroyCameraIDs(camera_ids)
        
        if camera_no==1:
            return camera_ids[0]
        else:
            # print('Multiple cameras detected. Please select the camera to be used.')
            # camera_id = camera_ids[int(input('Enter the camera number: '))]
            # return camera_id
            raise Exception('Multiple cameras detected. Please select the camera to be used.')
        
    def _set_ROI(self, row:tuple[str,str]=('',''), col:tuple[str,str]=('',''),
                 bin_row:str=''):
        """
        Sets the Region of Interest (ROI) for the camera as well as the binning.

        Args:
            row (tuple[float,float]|tuple[str,str], optional): The range of rows to be used for the ROI (min, max).
                if ('',''), the default ROI will be used. Defaults to ('','').
            col (tuple[float,float]|tuple[str,str], optional): The range of columns to be used for the ROI (min, max).
                if ('',''), the default ROI will be used. Defaults to ('','').
            bin_row (int|str, optional): The number of rows to bin, if larger than the ROI size,
                the min of the two will be chosen. If '', the default binning will be used. Defaults to ''.
                'min' will choose the minimum possible binning, 'max' will choose the maximum possible binning.
        """
        camera_handle = self._cameraHandle
        
        with self._lock:
            # Get the default ROI information
            ptr_picamRoisDefault:PicamRois = func_Picam_GetParameterRoisDefaultValue(camera_handle, PicamParameter.PicamParameter_Rois)
        picamRoiDefault = ptr_picamRoisDefault.contents.roi_array[0]  # Get the first ROI
        func_Picam_DestroyRois(ptr_picamRoisDefault)
        
        # print("Default ROI:")
        # print("  x:", picamRoiDefault.x)
        # print("  width:", picamRoiDefault.width)
        # print("  x_binning:", picamRoiDefault.x_binning)
        # print("  y:", picamRoiDefault.y)
        # print("  height:", picamRoiDefault.height)
        # print("  y_binning:", picamRoiDefault.y_binning)
        
        # > Convert the input values to the correct format
        row_min = int(float(row[0])) if row[0] else 0
        row_max = int(float(row[1])) if row[1] else picamRoiDefault.height
        col_min = int(float(col[0])) if col[0] else 0
        col_max = int(float(col[1])) if col[1] else picamRoiDefault.width
        if bin_row=='min': bin_row = 1
        elif bin_row=='max': bin_row = int(picamRoiDefault.height)
        else: bin_row = int(float(bin_row)) if bin_row else None
        
        # Get the ROI information (assuming a single ROI for now)
        with self._lock:
            ptr_picamRois:PicamRois = func_Picam_GetParameterRoisValue(camera_handle, PicamParameter.PicamParameter_Rois)
        picamRoi = ptr_picamRois.contents.roi_array[0]  # Get the first ROI
        
        # print("Current ROI:")
        # print("  x:", picamRoi.x)
        # print("  width:", picamRoi.width)
        # print("  x_binning:", picamRoi.x_binning)
        # print("  y:", picamRoi.y)
        # print("  height:", picamRoi.height)
        # print("  y_binning:", picamRoi.y_binning)
        
        row = (row_min, row_max)
        col = (col_min, col_max)
        bin_row = min(bin_row, row[1]-row[0]) if bin_row else picamRoiDefault.y_binning
        
        new_roi = picamRoi
        new_roi.x = ctypes.c_int(col[0]) if col else picamRoiDefault.x
        new_roi.width = ctypes.c_int(col[1]-col[0]) if col else picamRoiDefault.width
        new_roi.y = ctypes.c_int(row[0]) if row else picamRoiDefault.y
        new_roi.height = ctypes.c_int(row[1]-row[0]) if row else picamRoiDefault.height
        new_roi.y_binning = ctypes.c_int(bin_row) if bin_row else picamRoiDefault.y_binning
        
        with self._lock:
            # Check if the ROI can be set
            settable = func_Picam_CanSetParameterRoisValue(camera_handle, PicamParameter.PicamParameter_Rois, ptr_picamRois)
            print("ROI settable:", settable)
            
            # Set the ROI
            if not settable: func_Picam_DestroyRois(ptr_picamRois); raise ValueError("ROI cannot be set.")
            func_Picam_SetParameterRoisValue(camera_handle, PicamParameter.PicamParameter_Rois, ptr_picamRois)
            func_Picam_CommitParameters(camera_handle)
            func_Picam_DestroyRois(ptr_picamRois)
            
            # Get the ROI information again
            ptr_picamRois:PicamRois = func_Picam_GetParameterRoisValue(camera_handle, PicamParameter.PicamParameter_Rois)
        picamRoi = ptr_picamRois.contents.roi_array[0]  # Get the first ROI
        func_Picam_DestroyRois(ptr_picamRois)
        
        print("Set ROI:")
        print("  x:", picamRoi.x)
        print("  width:", picamRoi.width)
        print("  x_binning:", picamRoi.x_binning)
        print("  y:", picamRoi.y)
        print("  height:", picamRoi.height)
        print("  y_binning:", picamRoi.y_binning)
        
        self._roi_size = (picamRoi.width//picamRoi.x_binning, picamRoi.height//picamRoi.y_binning)  # width, height of the ROI
        self._roi_binning = (picamRoi.x_binning, picamRoi.y_binning)
        self._roi_num_pixels = self._roi_size[0] * self._roi_size[1]
        
        # > Retrieve the other parameters
        # Get the pixel bit depth
        with self._lock:
            self._roi_pixel_bit_depth = func_Picam_GetParameterIntegerValue(camera_handle, PicamParameter.PicamParameter_PixelBitDepth)
        
        self._image_data_size = (self._roi_num_pixels * self._roi_pixel_bit_depth // 8)
        self._timestamp_data_size = (self._timestamp_bit_depth + 7) // 8
        self._frame_data_size = self._image_data_size + self._timestamp_data_size
        
        # > Ensure that the ROI is set correctly
        # Get the ROI information (assuming a single ROI for now)        
        with self._lock:
            ptr_picamRois:PicamRois = func_Picam_GetParameterRoisValue(camera_handle, PicamParameter.PicamParameter_Rois)
        picamRois = ptr_picamRois.contents
        num_rois = picamRois.roi_count
        if num_rois == 0: raise ValueError("No ROI found.")
        if num_rois > 1: raise ValueError("Multiple ROIs found. Only one ROI is supported.")
        
        return

    def get_integration_time_limits_us(self) -> tuple[int,int,int]:
        """
        Get the integration time limits of the device
        
        Returns:
            tuple: A tuple containing the minimum, maximum, and increment of the integration time in [device unit] (microseconds for the QE Pro)
        """
        return (self.integration_time_min, self.integration_time_max, self.integration_time_inc)
    
    def get_integration_time_us(self, fromdev:bool=True) -> int:
        """
        Get the integration time of the device
        
        Args:
            fromdev (bool, optional): If True, the integration time will be retrieved from the device.
                Defaults to True.
        
        Returns:
            int: Integration time in [device unit] (microseconds for the QE Pro)
        """
        # Get the new integration time
        if fromdev:
            camera_handle = self._cameraHandle
            with self._lock:
                int_time_ms = func_Picam_GetParameterFloatingPointValue(camera_handle, PicamParameter.PicamParameter_ExposureTime)
            self._integration_time_local_us = int(int_time_ms*1000)
        else:
            int_time_ms = self._integration_time_local_us/1000
        return int_time_ms*1000
    
    def set_integration_time_us(self,integration_time_us:int) -> int:
        """
        Sets the integration time of the device
        
        Args:
            integration_time (int): Integration time in [device unit] 
            (microseconds for the QE Pro)
        
        Returns:
            int: Device integrationt time after set up [us]
        """
        assert isinstance(integration_time_us,int), "Integration time must be an integer"
        int_time_ms = int(integration_time_us/1000)
        
        with self._lock:
            camera_handle = self._cameraHandle
            func_Picam_SetParameterFloatingPointValue(camera_handle, PicamParameter.PicamParameter_ExposureTime, int_time_ms)
            func_Picam_CommitParameters(camera_handle)
        
        # Use the get function to ensure that the integration time is set correctly
        # And to update the locally stored integration time
        return self.get_integration_time_us()
        
    def _get_bit_depth(self,depth:int) -> np.dtype:
        """
        Get the numpy data type based on the bit depth
        
        Args:
            depth (int): The bit depth of the data
        """    
        if depth == 16:
            return np.uint16
        elif depth == 32:
            return np.uint32
        elif depth == 64:
            return np.uint64
        else:
            raise ValueError("Unsupported timestamp bit depth")
        
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
        
        """
        Acquires an image from the camera.
        
        Args:
            picamlib: The ctypes library object for the PICam library from pylablib.
            camera_handle: The camera handle obtained from Picam_OpenCamera.
            timeout (int): The timeout in milliseconds for the acquisition.
            
        Returns:
            np.ndarray: The acquired image data.
        """
        camera_handle = self._cameraHandle
        
        # Acquire an image
        readout_count = 1  # Number of readouts
        readout_time_out = -1  # Infinite timeout

        # Call the wrapped function
        init_timestamp = get_timestamp_us_int()
        with self._lock:
            available, errors = func_Picam_Acquire(camera_handle, readout_count, readout_time_out)
        
        # Get the image data
        ptr_image_data:CPicamAvailableData = available.initial_readout
        
        # Get the readout stride
        with self._lock:
            readout_stride = func_Picam_GetParameterIntegerValue(camera_handle, PicamParameter.PicamParameter_ReadoutStride)
        # print("Readout stride:", readout_stride)
        
        # Get the ROI information (assuming a single ROI for now)
        with self._lock:
            ptr_picamRois:PicamRois = func_Picam_GetParameterRoisValue(camera_handle, PicamParameter.PicamParameter_Rois)
        picamRois = ptr_picamRois.contents
        num_rois = picamRois.roi_count
        if num_rois == 0: raise ValueError("No ROI found.")
        if num_rois > 1: raise ValueError("Multiple ROIs found. Only one ROI is supported.")
        
        if self._frame_data_size != readout_stride: raise ValueError("Readout stride does not match the expected frame data size.\
            Likely an issue with either, there are multiple readouts, additional masks used, or the frame data size calculation\
            is incorrect.")
        
        # > Extract the image data <
        # Create a buffer for the readout data
        readout_buffer = ctypes.create_string_buffer(self._image_data_size)
        ctypes.memmove(readout_buffer, ptr_image_data, self._image_data_size) # Copy the readout data from the initial readout pointer to the buffer
        
        # Convert the buffer to a numpy array based on the pixel bit depth
        image_data:np.ndarray = np.frombuffer(readout_buffer, dtype=self._get_bit_depth(self._roi_pixel_bit_depth))
        
        # Reshape the image data
        image_data = image_data.reshape((self._roi_size[1], self._roi_size[0])) # Reshape to height x width
        # print("Image data shape:", image_data.shape)
        
        # > Extract the timestamp data <
        # Create a buffer for the timestamp data
        timestamp_buffer = ctypes.create_string_buffer(self._timestamp_data_size)
        ctypes.memmove(timestamp_buffer, ptr_image_data + self._image_data_size, self._timestamp_data_size) # Copy the timestamp data from the initial readout pointer to the buffer
        
        # Convert the buffer to a numpy array
        timestamp_resolution = self._timeRes_Hz
        timestamp_data = int(np.frombuffer(timestamp_buffer, dtype=self._get_bit_depth(self._timestamp_bit_depth))[0])
        timestamp_us = timestamp_data*10**6 // timestamp_resolution
        
        # import matplotlib.pyplot as plt
        # plt.imshow(image_data, cmap='hot')
        # plt.colorbar()
        # plt.show()
        
        list_intensity = np.mean(image_data,axis=0)
        list_wavelength = list(range(1, len(list_intensity) + 1))
        
        list_wavelength = [float(wavelength) for wavelength in list_wavelength]
        list_intensity = [float(intensity) for intensity in list_intensity]
        
        timestamp_us_int = init_timestamp + timestamp_us
        integration_time = self.get_integration_time_us(fromdev=False)
        
        spectra = pd.DataFrame({
            DataAnalysisConfigEnum.WAVELENGTH_LABEL.value: list_wavelength,
            DataAnalysisConfigEnum.INTENSITY_LABEL.value: list_intensity,
        })
        
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
            time.sleep(5)
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
    test_device()
    pass