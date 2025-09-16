"""A class that allows the control of the Princeton Instruments Raman spectrometer.

Technical notes:
Because the PIXIS100 is very slow at capturing single frames,
the acquisition mode is set to 'sequence' and the acquisition
is performed continuously from the creation of the object.
Even with this, as far as I know, the capture rate is still
limited to 10Hz.

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

import pylablib as pll
from pylablib.devices.PrincetonInstruments.picam_lib import PicamLib
from pylablib.core.utils import ctypes_wrap
from pylablib.devices.PrincetonInstruments.picam_defs import *  # enum definitions

import ctypes

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))
    

from iris.utils.general import *

from iris.controllers import ControllerSpecificConfigEnum
from iris import DataAnalysisConfigEnum

# # Add the directory containing the oceandirect module to the Python path
# module_dir = os.path.abspath(ControllerSpecificConfigEnum.OCEANINSIGHT_API_DIRPATH.value)
# sys.path.append(module_dir)

wrapper = ctypes_wrap.CFunctionWrapper(default_rvals="pointer")

# ------------------------------------------------------------------------
# ------------------------------------------------------------------------
# ------------------------------------------------------------------------

def set_integration_time(picamlib, camera_handle, int_time_ms:float):
    """
    Sets the integration time for the camera.

    Args:
        picamlib: The ctypes library object for the PICam library from pylablib.
        camera_handle: The camera handle obtained from Picam_OpenCamera.
        integration_time (float): The integration time in milliseconds.
    """
    func_Picam_GetParameterFloatingPointValue=wrapper(picamlib.Picam_GetParameterFloatingPointValue)
    func_Picam_SetParameterFloatingPointValue=wrapper(picamlib.Picam_SetParameterFloatingPointValue)
    func_Picam_CommitParameters=wrapper(picamlib.Picam_CommitParameters)
    
    # Get the current integration time
    curr_int_time_ms = func_Picam_GetParameterFloatingPointValue(camera_handle, PicamParameter.PicamParameter_ExposureTime)
    print("Current integration time:", curr_int_time_ms)
    
    func_Picam_SetParameterFloatingPointValue(camera_handle, PicamParameter.PicamParameter_ExposureTime, int_time_ms)
    func_Picam_CommitParameters(camera_handle)
    
    # Get the new integration time
    curr_int_time_ms = func_Picam_GetParameterFloatingPointValue(camera_handle, PicamParameter.PicamParameter_ExposureTime)
    print("New integration time:", curr_int_time_ms)
    
    return

def set_ROI(picamlib, camera_handle, row:tuple[float,float]|None=None, col:tuple[float,float]|None=None, bin_row:int|None=None):
    """
    Sets the Region of Interest (ROI) for the camera as well as the binning.

    Args:
        picamlib: The ctypes library object for the PICam library from pylablib.
        camera_handle: The camera handle obtained from Picam_OpenCamera.
        row (tuple[float,float]|None, optional): The range of rows to be used for the ROI (min, max).
            if None, the default ROI will be used. Defaults to None.
        col (tuple[float,float]|None, optional): The range of columns to be used for the ROI (min, max).
            if None, the default ROI will be used. Defaults to None.
        bin_row (int | None, optional): The number of rows to bin, if larger than the ROI size,
            the min of the two will be chosen. If None, the default binning will be used. Defaults to None.
    """
    func_Picam_GetParameterRoisDefaultValue=wrapper(picamlib.Picam_GetParameterRoisDefaultValue)
    func_Picam_GetParameterRoisValue = wrapper(picamlib.Picam_GetParameterRoisValue)
    func_Picam_CanSetParameterRoisValue=wrapper(picamlib.Picam_CanSetParameterRoisValue, rvals=["settable"])
    func_Picam_SetParameterRoisValue=wrapper(picamlib.Picam_SetParameterRoisValue, rvals=[])
    func_Picam_DestroyRois=wrapper(picamlib.Picam_DestroyRois, rvals=[])
    func_Picam_CommitParameters=wrapper(picamlib.Picam_CommitParameters)
    
    # Get the default ROI information
    ptr_picamRoisDefault:PicamRois = func_Picam_GetParameterRoisDefaultValue(camera_handle, PicamParameter.PicamParameter_Rois)
    picamRoiDefault = ptr_picamRoisDefault.contents.roi_array[0]  # Get the first ROI
    func_Picam_DestroyRois(ptr_picamRoisDefault)
    
    print("Default ROI:")
    print("  x:", picamRoiDefault.x)
    print("  width:", picamRoiDefault.width)
    print("  x_binning:", picamRoiDefault.x_binning)
    print("  y:", picamRoiDefault.y)
    print("  height:", picamRoiDefault.height)
    print("  y_binning:", picamRoiDefault.y_binning)
    
    # Get the ROI information (assuming a single ROI for now)
    ptr_picamRois:PicamRois = func_Picam_GetParameterRoisValue(camera_handle, PicamParameter.PicamParameter_Rois)
    picamRoi = ptr_picamRois.contents.roi_array[0]  # Get the first ROI
    
    print("Current ROI:")
    print("  x:", picamRoi.x)
    print("  width:", picamRoi.width)
    print("  x_binning:", picamRoi.x_binning)
    print("  y:", picamRoi.y)
    print("  height:", picamRoi.height)
    print("  y_binning:", picamRoi.y_binning)
    
    row = (max(row[0],0), min(row[1],picamRoiDefault.height)) if row else (picamRoi.y, picamRoi.y+picamRoi.height)
    col = (max(col[0],0), min(col[1],picamRoiDefault.width)) if col else (picamRoi.x, picamRoi.x+picamRoi.width)
    bin_row = min(bin_row, row[1]-row[0]) if bin_row else picamRoiDefault.y_binning
    
    new_roi = picamRoi
    new_roi.x = ctypes.c_int(col[0]) if col else picamRoiDefault.x
    new_roi.width = ctypes.c_int(col[1]-col[0]) if col else picamRoiDefault.width
    new_roi.y = ctypes.c_int(row[0]) if row else picamRoiDefault.y
    new_roi.height = ctypes.c_int(row[1]-row[0]) if row else picamRoiDefault.height
    new_roi.y_binning = ctypes.c_int(bin_row) if bin_row else picamRoiDefault.y_binning
    
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
    
    print("New ROI:")
    print("  x:", picamRoi.x)
    print("  width:", picamRoi.width)
    print("  x_binning:", picamRoi.x_binning)
    print("  y:", picamRoi.y)
    print("  height:", picamRoi.height)
    print("  y_binning:", picamRoi.y_binning)
    
    return

def acquire_image(picamlib, camera_handle, timeout:int=1000) -> np.ndarray:
    """
    Acquires an image from the camera.
    
    Args:
        picamlib: The ctypes library object for the PICam library from pylablib.
        camera_handle: The camera handle obtained from Picam_OpenCamera.
        timeout (int): The timeout in milliseconds for the acquisition.
        
    Returns:
        np.ndarray: The acquired image data.
    """
    # Wrap the Picam_Acquire function
    # rconv is used to convert the resulting PicamAvailableData struct to a tuple
    # ctypes.c_int Picam_Acquire(PicamHandle camera, pi64s readout_count, piint readout_time_out, ctypes.POINTER(PicamAvailableData) available, ctypes.POINTER(ctypes.c_int) errors)
    func_Picam_Acquire=wrapper(picamlib.Picam_Acquire,rconv={"available": CPicamAvailableData.tup_struct}, rvals=["available", "errors"])
    
    # Acquire an image
    readout_count = 1  # Number of readouts
    readout_time_out = -1  # Infinite timeout

    # Call the wrapped function
    available, errors = func_Picam_Acquire(camera_handle, readout_count, readout_time_out)
    
    # Get the image data
    ptr_image_data:CPicamAvailableData = available.initial_readout
    print("Total image acquired: ", available.readout_count)
    print("Image data acquired. Pointer:")
    print(ptr_image_data)
    
    # Get the readout stride
    func_Picam_GetParameterIntegerValue=wrapper(picamlib.Picam_GetParameterIntegerValue)
    readout_stride = func_Picam_GetParameterIntegerValue(camera_handle, PicamParameter.PicamParameter_ReadoutStride)
    print("Readout stride:", readout_stride)
    
    # Get the ROI information (assuming a single ROI for now)
    func_Picam_GetParameterRoisValue = wrapper(picamlib.Picam_GetParameterRoisValue)
    
    ptr_picamRois:PicamRois = func_Picam_GetParameterRoisValue(camera_handle, PicamParameter.PicamParameter_Rois)
    picamRois = ptr_picamRois.contents
    num_rois = picamRois.roi_count
    if num_rois == 0: raise ValueError("No ROI found.")
    if num_rois > 1: raise ValueError("Multiple ROIs found. Only one ROI is supported.")
    
    roi = picamRois.roi_array[0]  # Get the first ROI
    roi_size = (roi.width//roi.x_binning, roi.height//roi.y_binning)  # width, height of the ROI
    num_pixels = roi_size[0] * roi_size[1]
    print("ROI size:", roi_size)
    
    # Get the pixel bit depth
    pixel_bit_depth = func_Picam_GetParameterIntegerValue(camera_handle, PicamParameter.PicamParameter_PixelBitDepth)
    print("Pixel bit depth:", pixel_bit_depth)
    
    # Handling the timestamp metadata
    timestamps_param = func_Picam_GetParameterIntegerValue(camera_handle, PicamParameter.PicamParameter_TimeStamps)

    # Check if timestamps are enabled
    if timestamps_param == PicamTimeStampsMask.PicamTimeStampsMask_None: flg_timestamps = 0
    else: flg_timestamps = 1
    
    # Get the timestamp bit depth
    timestamp_bit_depth = func_Picam_GetParameterIntegerValue(camera_handle, PicamParameter.PicamParameter_TimeStampBitDepth)
    print("Timestamp bit depth:", timestamp_bit_depth)
    
    # Calculate the size of the image data for each frame
    image_data_size = (num_pixels * pixel_bit_depth // 8)
    timestamp_data_size = (timestamp_bit_depth + 7) // 8
    frame_data_size = image_data_size + flg_timestamps * timestamp_data_size
    print("Image data size per frame:", frame_data_size)
    
    if frame_data_size != readout_stride: raise ValueError("Readout stride does not match the expected frame data size.")
    
    # > Extract the image data <
    # Create a buffer for the readout data
    readout_buffer = ctypes.create_string_buffer(image_data_size)
    
    # Copy the readout data from the initial readout pointer to the buffer
    ctypes.memmove(readout_buffer, ptr_image_data, image_data_size)
    
    # Convert the buffer to a numpy array based on the pixel bit depth
    image_data:np.ndarray = np.frombuffer(readout_buffer, dtype=get_bit_depth(pixel_bit_depth))
    
    # Reshape the image data
    image_data = image_data.reshape((roi_size[1], roi_size[0])) # Reshape to height x width
    print("Image data shape:", image_data.shape)
    
    # > Extract the timestamp data if available <
    if flg_timestamps:
        # Create a buffer for the timestamp data
        timestamp_buffer = ctypes.create_string_buffer(timestamp_data_size)
        
        # Copy the timestamp data from the initial readout pointer to the buffer
        ctypes.memmove(timestamp_buffer, ptr_image_data + image_data_size, timestamp_data_size)
        
        # Convert the buffer to a numpy array
        func_Picam_GetParameterLargeIntegerValue = wrapper(picamlib.Picam_GetParameterLargeIntegerValue)
        timestamp_resolution = func_Picam_GetParameterLargeIntegerValue(camera_handle, PicamParameter.PicamParameter_TimeStampResolution)
        timestamp_data = int(np.frombuffer(timestamp_buffer, dtype=get_bit_depth(timestamp_bit_depth))[0])
        timestamp_us = timestamp_data*10**6 // timestamp_resolution
        print("Timestamp resolution:", timestamp_resolution)
        print("Timestamp data:", timestamp_data)
        print("Timestamp (us):", timestamp_us)
    
    # import matplotlib.pyplot as plt
    # plt.imshow(image_data, cmap='hot')
    # plt.colorbar()
    # plt.show()
    
    return image_data
    
def get_bit_depth(depth:int):
    if depth == 16:
        return np.uint16
    elif depth == 32:
        return np.uint32
    elif depth == 64:
        return np.uint64
    else:
        raise ValueError("Unsupported timestamp bit depth")
    
def plot_mean_col(image_data:np.ndarray):
    """
    Plots the mean column of the image data. Useful for setting the ROI rows.

    Args:
        image_data (np.ndarray): The image data from acquire_image.
    """
    import matplotlib.pyplot as plt
    mean_col = np.mean(image_data, axis=0)
    plt.plot(mean_col)
    plt.xlabel("Pixel columns")
    plt.ylabel("Mean Intensity")
    plt.title("Mean Column of Image Data")
    plt.minorticks_on()
    plt.grid(which='both', linestyle='--', linewidth=0.5)
    plt.show()
    
def plot_mean_row(image_data:np.ndarray):
    """
    Plots the mean row of the image data. Useful for setting the ROI columns.

    Args:
        image_data (np.ndarray): The image data from acquire_image.
    """
    import matplotlib.pyplot as plt
    mean_row = np.mean(image_data, axis=1)
    plt.plot(mean_row)
    plt.xlabel("Pixel rows")
    plt.ylabel("Mean Intensity")
    plt.title("Mean Row of Image Data")
    plt.minorticks_on()
    plt.grid(which='both', linestyle='--', linewidth=0.5)
    plt.show()

def get_available_camera_ids_old(picam):
    """
    Gets the available camera IDs.

    Args:
        picam: The ctypes library object for the PICam library.

    Returns:
        A list of PicamCameraID objects.
    """
    # Directly wrap the Picam_GetAvailableCameraIDs function
    wrapped_Picam_GetAvailableCameraIDs = wrapper(picam.Picam_GetAvailableCameraIDs)
    
    # Call the wrapped function
    camera_id_pointer_array, id_count = wrapped_Picam_GetAvailableCameraIDs()
    
    # class PicamCameraID(ctypes.Structure):
    #     _fields_ = [
    #         ("model", ctypes.c_int),
    #         ("computer_interface", ctypes.c_int),
    #         ("sensor_name", ctypes.c_char*64),  # Adjust size if needed
    #         ("serial_number", ctypes.c_char*64)   # Adjust size if needed
    #     ]
    
    # camera_id_pointer_array = ctypes.POINTER(PicamCameraID)()
    # id_count = ctypes.c_int()
    
    # # Define the function prototype
    # picam.Picam_GetAvailableCameraIDs.argtypes = [
    #     ctypes.POINTER(ctypes.POINTER(PicamCameraID)), 
    #     ctypes.POINTER(ctypes.c_int)  # Use ctypes.c_int for piint
    # ]
    # picam.Picam_GetAvailableCameraIDs.restype = ctypes.c_int
    
    # picam.Picam_GetAvailableCameraIDs(ctypes.byref(camera_id_pointer_array), ctypes.byref(id_count))
    
    camera_ids = []
    camera_id_pointer_array
    if camera_id_pointer_array:
        # Access the PicamCameraID structure directly
        camera_id = camera_id_pointer_array.contents
        camera_ids.append(camera_id)
        
        # Access and print camera information
        print("Camera Information:")
        print(f"  Model: {camera_id.model}")
        print(f"  Computer Interface: {camera_id.computer_interface}")
        print(f"  Sensor Name: {camera_id.sensor_name.decode('utf-8')}")  # Decode to string
        print(f"  Serial Number: {camera_id.serial_number.decode('utf-8')}") # Decode to string
        
        # picam.Picam_DestroyCameraIDs(camera_id_pointer_array)
    return camera_ids
    
    class PicamCameraID(ctypes.Structure):
        _fields_ = [
            ("model", ctypes.c_int),
            ("computer_interface", ctypes.c_int),
            ("sensor_name", ctypes.c_char*64),  # Adjust size if needed
            ("serial_number", ctypes.c_char*64)   # Adjust size if needed
        ]

    def wrap_available_camera_ids(picam):
        """
        Wraps the Picam_GetAvailableCameraIDs function from the PICam library.

        Args:
            picam_lib: The ctypes library object for the PICam library.

        Returns:
            A wrapped Python function that calls Picam_GetAvailableCameraIDs.
        """

        # Define the function prototype
        picam.Picam_GetAvailableCameraIDs.argtypes = [
            ctypes.POINTER(ctypes.POINTER(PicamCameraID)), 
            ctypes.POINTER(ctypes.c_int)  # Use ctypes.c_int for piint
        ]
        picam.Picam_GetAvailableCameraIDs.restype = ctypes.c_int

        # Create the wrapper function
        def wrapped_func():
            id_array = ctypes.POINTER(PicamCameraID)()
            id_count = ctypes.c_int()
            result = picam.Picam_GetAvailableCameraIDs(ctypes.byref(id_array), ctypes.byref(id_count))

            if result != 0:
                raise ctypes.WinError(result)  # Raise a Windows error if the function fails

            camera_ids = []
            for i in range(id_count.value):
                camera_ids.append(id_array[i])

            # picam_lib.Picam_DestroyCameraIDs(ctypes.cast(id_array, ctypes.POINTER(PicamCameraID)))  # Clean up memory

            return camera_ids

        return wrapped_func

    # Example usage:
    # Assuming you have the PICam library loaded as 'picam_lib'
    get_available_camera_ids = wrap_available_camera_ids(picam)
    camera_ids = get_available_camera_ids()

    for camera_id in camera_ids:
        print(f"Model: {camera_id.model}")
        print(f"Sensor Name: {camera_id.sensor_name.decode('utf-8')}")
        print(f"Serial Number: {camera_id.serial_number.decode('utf-8')}")

def get_available_camera_ids(picamlib) -> tuple[PicamCameraID,list[PicamCameraID]]|None:
    """
    Gets the available camera IDs.

    Args:
        picamlib: The ctypes library object for the PICam library.

    Returns:
        tuple[PicamCameraID,list[PicamCameraID]]|None:
            A tuple containing the selected camera ID and a list of all available camera IDs.
            or None if no camera is detected.
    """
    func_Picam_GetAvailableCameraIDs = wrapper(picamlib.Picam_GetAvailableCameraIDs)
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
        print('No camera detected')
        return None
    
    func_Picam_DestroyCameraIDs = wrapper(picamlib.Picam_DestroyCameraIDs, rvals=[])
    func_Picam_DestroyCameraIDs(camera_ids)
    
    if camera_no==1:
        return camera_ids[0], camera_ids
    else:
        print('Multiple cameras detected. Please select the camera to be used.')
        camera_id = camera_ids[int(input('Enter the camera number: '))]
        return camera_id, camera_ids

def test():
# >>> Initialisation <<<
    print("\n>>> Initialisation <<<")
    # Initialise the library using Pylablib's PicamLib. It already has all the nice wrapper, structs, etc. so
    # we don't have to do it ourselves.
    pll.par["devices/dlls/picam"] = r"C:\Program Files\Princeton Instruments\PICam\Runtime"
    pylablib_picamlib = PicamLib()
    pylablib_picamlib.initlib()
    
    picamlib = pylablib_picamlib.lib   # Get the ctypes library object for the PICam library
    picamlib.Picam_InitializeLibrary() # Make sure that the library is initialised
    
    # Note: In addition to containing the DLL, the picamlib from pylablib also contains
    # the restype, argtypes, and other definitions for the functions in the library.
    # We'll be using these as is for the wrapper function, also obtained from pylablib.
    # The only difference here is that we'll be wrapping the functions ourselves instead
    # of using the already available wrapped functions in the pycamlib from pylablib.
    # This allows us to handle the return values of the functions in a more flexible way.
    # (and also because not all PIXIS functions are available in the picamlib from pylablib)
    
    # Get available camera IDs
    result = get_available_camera_ids(picamlib)
    if not result: print('No camera detected'); return
    camera_id, camera_ids = result
    
    func_Picam_OpenCamera=wrapper(picamlib.Picam_OpenCamera, rvals=["camera"])
    camera_handle = func_Picam_OpenCamera(camera_id)
    
    print("Camera opened:" )
    print(camera_handle)
    
# >>> Configuration: ROI and binning <<<
    set_ROI(picamlib, camera_handle, row=(65,85), bin_row=100)
    
# >>> Configuration: Integration time <<<
    set_integration_time(picamlib, camera_handle, 100.0)
    set_integration_time(picamlib, camera_handle, 50.0)
    
# >>> Configuration: Timestamp mask <<<
    func_Picam_CommitParameters = wrapper(picamlib.Picam_CommitParameters)
    
    func_Picam_GetParameterValueType = wrapper(picamlib.Picam_GetParameterValueType)
    maskvaltype = func_Picam_GetParameterValueType(camera_handle, PicamParameter.PicamParameter_TimeStamps)
    func_Picam_GetParameterIntegerValue = wrapper(picamlib.Picam_GetParameterIntegerValue)
    maskval = func_Picam_GetParameterIntegerValue(camera_handle, PicamParameter.PicamParameter_TimeStamps)
    print("Timestamp mask value type:", maskvaltype)
    print("Timestamp mask value:", maskval)
    
    # Enable the timestamp mask
    func_Picam_SetParameterIntegerValue = wrapper(picamlib.Picam_SetParameterIntegerValue)
    func_Picam_SetParameterIntegerValue(camera_handle, PicamParameter.PicamParameter_TimeStamps, PicamTimeStampsMask.PicamTimeStampsMask_ExposureStarted)
    # Commit the parameters
    func_Picam_CommitParameters(camera_handle)
    
    maskval = func_Picam_GetParameterIntegerValue(camera_handle, PicamParameter.PicamParameter_TimeStamps)
    print("Timestamp mask value: {}\n".format(maskval))
    
    
    
# >>> Acquisition <<<
    print("\n>>> Acquisition <<<")
    # Acquire an image
    data = acquire_image(picamlib, camera_handle)
    plot_mean_row(data)
    plot_mean_col(data)
    
# >>> Cleanup and termination <<<
    print("\n>>> Cleanup and termination <<<")
    # Close the camera
    picamlib.Picam_CloseCamera(camera_handle)

    # Uninitialize the library
    picamlib.Picam_UninitializeLibrary()
    
    print("\n>>> Terminated <<<")
    
    
if __name__ == '__main__':
    test()
    pass