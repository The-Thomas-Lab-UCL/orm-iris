"""A class that allows the control of the Andor spectrometers.

Self notes:
This script is based on the Andor CCD iVac 416 though, the it should 
be applicable to most of Andor's other spectrometers with minimal to
no adjustments (aside from the advance features).

Acknowledgement:
pylablib as a learning material for the development of this controller, though
no code from it has been reused in this controller.
"""
#%% Main import
import os
import sys
import time
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import pandas as pd
import numpy as np
if not __name__ == '__main__': matplotlib.use('Agg')

import ctypes
from enum import Enum
from typing import Literal

#%% Other imports 
if __name__ == '__main__':
    import sys
    import os
    SCRIPT_DIR = os.path.abspath(r'.\library')
    sys.path.append(os.path.dirname(SCRIPT_DIR))    

from library.general_functions import *
from library.controllers.class_spectrometer_controller import Class_SpectrometerController

from library import DataAnalysisConfigEnum
from library.controllers import ControllerSpecificConfigEnum

# %% Andor dll imports
# Add the path to the Andor SDK2 DLLs
path_dll_andor = ControllerSpecificConfigEnum.ANDOR_ATMCD64D_DLL_PATH.value
path_dll_spectrograph = ControllerSpecificConfigEnum.ANDOR_ATSPECTROGRAPH_DLL_PATH.value

list_dirpath_dll = [os.path.abspath(p) for p in os.environ.get("PATH","").split(os.pathsep) if p]
list_dirpath_dll.append(os.path.abspath("."))
list_dirpath_dll.append(os.path.abspath(os.path.split(path_dll_andor)[0]))
list_dirpath_dll.append(os.path.abspath(os.path.split(path_dll_spectrograph)[0]))
list_dir_dll = []

for path in list_dirpath_dll:
    try: list_dir_dll.append(os.add_dll_directory(path))
    except Exception as e: print(e)

andorDLL = ctypes.cdll.LoadLibrary(path_dll_andor)
specDLL = ctypes.cdll.LoadLibrary(path_dll_spectrograph)

for dir_dll in list_dir_dll:
    dir_dll.close()

print("Andor spectrometer: DLLs loaded successfully")

#%% Andor structures
class AndorCapabilities(ctypes.Structure):
    _fields_ = [
        ('ulSize', ctypes.c_ulong),
        ('ulAcqModes', ctypes.c_ulong),
        ('ulReadModes', ctypes.c_ulong),
        ('ulTriggerModes', ctypes.c_ulong),
        ('ulCameraType', ctypes.c_ulong),
        ('ulPixelMode', ctypes.c_ulong),
        ('ulSetFunctions', ctypes.c_ulong),
        ('ulGetFunctions', ctypes.c_ulong),
        ('ulFeatures', ctypes.c_ulong),
        ('ulPCICard', ctypes.c_ulong),
        ('ulEMGainControl', ctypes.c_ulong),
    ]

#%% Andor DLL function definitions
# >>> Initialisations
Initialize = andorDLL.Initialize
Initialize.argtypes = [ctypes.c_char_p] # [initialization directory]
Initialize.restype = ctypes.c_uint

Getstatus = andorDLL.GetStatus
Getstatus.argtypes = [ctypes.POINTER(ctypes.c_uint)] # [status refer to enum]
Getstatus.restype = ctypes.c_uint

Shutdown = andorDLL.ShutDown
Shutdown.argtypes = []
Shutdown.restype = ctypes.c_uint

# >>> Device information
GetCameraSerialNumber = andorDLL.GetCameraSerialNumber
GetCameraSerialNumber.argtypes = [ctypes.POINTER(ctypes.c_int)] # [serial number]
GetCameraSerialNumber.restype = ctypes.c_uint

GetCapabilities = andorDLL.GetCapabilities
GetCapabilities.argtypes = [ctypes.POINTER(AndorCapabilities)] # [capabilities structure]
GetCapabilities.restype = ctypes.c_uint

GetDetector = andorDLL.GetDetector
GetDetector.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)] # [x pixels, y pixels]
GetDetector.restype = ctypes.c_uint

GetFastestRecommendedVSSpeed = andorDLL.GetFastestRecommendedVSSpeed
GetFastestRecommendedVSSpeed.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_float)] # [index of the speed, speed]
GetFastestRecommendedVSSpeed.restype = ctypes.c_uint

GetNumberVSSpeeds = andorDLL.GetNumberVSSpeeds
GetNumberVSSpeeds.argtypes = [ctypes.POINTER(ctypes.c_int)] # [number of the available speeds]
GetNumberVSSpeeds.restype = ctypes.c_uint

GetVSSpeed = andorDLL.GetVSSpeed
GetVSSpeed.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_float)] # [index to get, speed]
GetVSSpeed.restype = ctypes.c_uint

# >>> Temperature
GetTemperatureRange = andorDLL.GetTemperatureRange
GetTemperatureRange.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)] # Min and max temp
GetTemperatureRange.restype = ctypes.c_uint

SetTemperature = andorDLL.SetTemperature
SetTemperature.argtypes = [ctypes.c_int] # [temperature]
SetTemperature.restype = ctypes.c_uint

GetTemperature = andorDLL.GetTemperature
GetTemperature.argtypes = [ctypes.POINTER(ctypes.c_int)] # [temperature]
GetTemperature.restype = ctypes.c_uint

CoolerON = andorDLL.CoolerON
CoolerON.argtypes = []
CoolerON.restype = ctypes.c_uint

CoolerOFF = andorDLL.CoolerOFF
CoolerOFF.argtypes = []
CoolerOFF.restype = ctypes.c_uint

# >>> Readout settings
SetReadMode = andorDLL.SetReadMode
SetReadMode.argtypes = [ctypes.c_int] # [readout mode index: 0-FVB,1-MultiTrack,2-RandomTrack,3-SingleTrack,4-Image]
SetReadMode.restype = ctypes.c_uint

SetImage = andorDLL.SetImage
SetImage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int] # [hbin, vbin, hstart, hend, vstart, vend]
    # int hbin: number of pixels to bin horizontally.
    # int vbin: number of pixels to bin vertically.
    # int hstart: Start column (inclusive).
    # int hend: End column (inclusive).
    # int vstart: Start row (inclusive).
    # int vend: End row (inclusive)
SetImage.restype = ctypes.c_uint
    # DRV_SUCCESS: All parameters accepted.
    # DRV_NOT_INITIALIZED: System not initialized.
    # DRV_ACQUIRING: Acquisition in progress.
    # DRV_P1INVALID: Binning parameters invalid.
    # DRV_P2INVALID: Binning parameters invalid.
    # DRV_P3INVALID: Sub-area co-ordinate is invalid.
    # DRV_P4INVALID: Sub-area co-ordinate is invalid.
    # DRV_P5INVALID: Sub-area co-ordinate is invalid.
    # DRV_P6INVALID: Sub-area co-ordinate is invalid.

SetAcquisitionMode = andorDLL.SetAcquisitionMode
SetAcquisitionMode.argtypes = [ctypes.c_int] # [acquisition mode index: 1-singleScan,2-accumulate,3-kinetics,4-fastKinetics,5-RunTillAbort]
SetAcquisitionMode.restype = ctypes.c_uint

AbortAcquisition = andorDLL.AbortAcquisition # Aborts acquisition for the RunTillAbort mode
AbortAcquisition.argtypes = []
AbortAcquisition.restype = ctypes.c_uint

WaitForAcquisitionTimeOut  = andorDLL.WaitForAcquisitionTimeOut  # Blocks the calling thread until acquisition is complete
WaitForAcquisitionTimeOut.argtypes = [ctypes.c_int] # [timeout in milliseconds]
WaitForAcquisitionTimeOut.restype = ctypes.c_uint

CancelWait = andorDLL.CancelWait # Cancels the wait for acquisition blocking event
CancelWait.argtypes = []
CancelWait.restype = ctypes.c_uint

PrepareAcquisition = andorDLL.PrepareAcquisition
PrepareAcquisition.argtypes = []
PrepareAcquisition.restype = ctypes.c_uint

StartAcquisition = andorDLL.StartAcquisition # Starts the acquisition process
StartAcquisition.argtypes = []
StartAcquisition.restype = ctypes.c_uint # Read the docs for the return value references

SetExposureTime = andorDLL.SetExposureTime
SetExposureTime.argtypes = [ctypes.c_float] # [exposure time in seconds]
SetExposureTime.restype = ctypes.c_uint

GetAcquisitionTimings = andorDLL.GetAcquisitionTimings
GetAcquisitionTimings.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)] # [exposure time [s], accummulate [s], kinetic time [s]]
GetAcquisitionTimings.restype = ctypes.c_uint

SetSingleTrack = andorDLL.SetSingleTrack
SetSingleTrack.argtypes = [ctypes.c_int, ctypes.c_int] # [idx center of track, idx height]
SetSingleTrack.restype = ctypes.c_uint

SendSoftwareTrigger = andorDLL.SendSoftwareTrigger
SendSoftwareTrigger.argtypes = []
SendSoftwareTrigger.restype = ctypes.c_uint # 

IsTriggerModeAvailable = andorDLL.IsTriggerModeAvailable
IsTriggerModeAvailable.argtypes = [ctypes.c_int] # [trigger mode index (see set trigger mode)]
IsTriggerModeAvailable.restype = ctypes.c_uint # DRV_SUCCESS or DRV_INVALID_MODE for available and not available respectively

SetTriggerMode = andorDLL.SetTriggerMode
SetTriggerMode.argtypes = [ctypes.c_int] # [trigger mode index: 0. Internal, 1. External, 6. External Start, 7. External Exposure (Bulb), 9. External FVB EM (only valid for EM Newton models in FVB mode), 10. Software Trigger, 12. External Charge Shifting]
SetTriggerMode.restype = ctypes.c_uint # DRV_SUCCESS : Trigger mode set., DRV_NOT_INITIALIZED : System not initialized., DRV_ACQUIRING : Acquisition in progress., DRV_P1INVALID : Trigger mode invalid.

SetKineticCycleTime = andorDLL.SetKineticCycleTime
SetKineticCycleTime.argtypes = [ctypes.c_float] # [kinetic cycle time in seconds]
SetKineticCycleTime.restype = ctypes.c_uint # DRV_SUCCESS: Cycle time accepted., DRV_NOT_INITIALIZED: System not initialized., DRV_ACQUIRING: Acquisition in progress., DRV_P1INVALID: Time invalid.

SetNumberAccumulations = andorDLL.SetNumberAccumulations
SetNumberAccumulations.argtypes = [ctypes.c_int] # [number of accumulations]
SetNumberAccumulations.restype = ctypes.c_uint # DRV_SUCCESS: Number of accumulations set., DRV_NOT_INITIALIZED: System not initialized., DRV_ACQUIRING: Acquisition in progress., DRV_P1INVALID: Invalid number of accumulations.

GetMostRecentImage = andorDLL.GetMostRecentImage
GetMostRecentImage.argtypes = [ctypes.POINTER(ctypes.c_long),ctypes.c_ulong] # [array to store the image, sized to the sensor, number of pixels]
GetMostRecentImage.restype = ctypes.c_uint # DRV_SUCCESS: Image has been copied into array., DRV_NOT_INITIALIZED: System not initialized., DRV_ERROR_ACK: Unable to communicate with card., DRV_P1INVALID: Invalid pointer (i.e. NULL)., DRV_P2INVALID: Array size is incorrect., DRV_NO_NEW_DATA: There is no new data yet.

#%% Device responses
DRV_SUCCESS = 20002
DRV_IDLE = 20073

class ErrorCodes(Enum):
    DRV_ERROR_CODES = 20001
    DRV_SUCCESS = 20002
    DRV_VXDNOTINSTALLED = 20003
    DRV_ERROR_SCAN = 20004
    DRV_ERROR_CHECK_SUM = 20005
    DRV_ERROR_FILELOAD = 20006
    DRV_UNKNOWN_FUNCTION = 20007
    DRV_ERROR_VXD_INIT = 20008
    DRV_ERROR_ADDRESS = 20009
    DRV_ERROR_PAGELOCK = 20010
    DRV_ERROR_PAGE_UNLOCK = 20011
    DRV_ERROR_BOARDTEST = 20012
    DRV_ERROR_ACK = 20013
    DRV_ERROR_UP_FIFO = 20014
    DRV_ERROR_PATTERN = 20015
    DRV_ACQUISITION_ERRORS = 20017
    DRV_ACQ_BUFFER = 20018
    DRV_ACQ_DOWNFIFO_FULL = 20019
    DRV_PROC_UNKNOWN_INSTRUCTION = 20020
    DRV_ILLEGAL_OP_CODE = 20021
    DRV_KINETIC_TIME_NOT_MET = 20022
    DRV_ACCUM_TIME_NOT_MET = 20023
    DRV_NO_NEW_DATA = 20024
    PCI_DMA_FAIL = 20025
    DRV_SPOOLERROR = 20026
    DRV_SPOOLSETUPERROR = 20027
    SATURATED = 20029
    DRV_TEMPERATURE_CODES = 20033
    DRV_TEMPERATURE_OFF = 20034
    DRV_TEMP_NOT_STABILIZED = 20035
    DRV_TEMPERATURE_STABILIZED = 20036
    DRV_TEMPERATURE_NOT_REACHED = 20037
    DRV_TEMPERATURE_OUT_RANGE = 20038
    DRV_TEMPERATURE_NOT_SUPPORTED = 20039
    DRV_TEMPERATURE_DRIFT = 20040
    DRV_GENERAL_ERRORS = 20049
    DRV_INVALID_AUX = 20050
    DRV_COF_NOTLOADED = 20051
    DRV_FPGAPROG = 20052
    DRV_FLEXERROR = 20053
    DRV_GPIBERROR = 20054
    ERROR_DMA_UPLOAD = 20055
    DRV_DATATYPE = 20064
    DRV_DRIVER_ERRORS = 20065
    DRV_P1INVALID = 20066
    DRV_P2INVALID = 20067
    DRV_P3INVALID = 20068
    DRV_P4INVALID = 20069
    DRV_INIERROR = 20070
    DRV_COFERROR = 20071
    DRV_ACQUIRING = 20072
    DRV_IDLE = 20073
    DRV_TEMPCYCLE = 20074
    DRV_NOT_INITIALIZED = 20075
    DRV_P5INVALID = 20076
    DRV_P6INVALID = 20077
    DRV_INVALID_MODE = 20078
    DRV_INVALID_FILTER = 20079
    DRV_I2CERRORS = 20080
    DRV_DRV_I2CDEVNOTFOUND = 20081
    DRV_I2CTIMEOUT = 20082
    DRV_P7INVALID = 20083
    DRV_USBERROR = 20089
    DRV_IOCERROR = 20090
    DRV_VRMVERSIONERROR = 20091
    DRV_USB_INTERRUPT_ENDPOINT_ERROR = 20093
    DRV_RANDOM_TRACK_ERROR = 20094
    DRV_INVALID_TRIGGER_MODE = 20095
    DRV_LOAD_FIRMWARE_ERROR = 20096
    DRV_DIVIDE_BY_ZERO_ERROR = 20097
    DRV_INVALID_RINGEXPOSURES = 20098
    DRV_BINNING_ERROR = 20099
    DRV_ERROR_NOCAMERA = 20990
    DRV_NOT_SUPPORTED = 20991
    DRV_NOT_AVAILABLE = 20992
    DRV_ERROR_MAP = 20115
    DRV_ERROR_UNMAP = 20116
    DRV_ERROR_MDL = 20117
    DRV_ERROR_UNMDL = 20118
    DRV_ERROR_BUFFSIZE = 20119
    DRV_ERROR_NOHANDLE = 20121
    DRV_GATING_NOT_AVAILABLE = 20130
    DRV_FPGA_VOLTAGE_ERROR = 20131
    DRV_INVALID_AMPLIFIER = 20100
    DRV_INVALID_COUNTCONVERT_MODE = 20101

def read_return_message(error_code) -> str|None:
    """
    Returns the error message corresponding to the given error code.

    Args:
        error_code (int): The error code to look up.

    Returns:
        str: The corresponding error message, or None if the code is for DRV_SUCCESS.
    """
    if error_code == ErrorCodes.DRV_SUCCESS.value: return None
    try: return ErrorCodes(error_code).name
    except ValueError: return "Unknown error"

#%% Function wrappers for the functions above
def initialize(dirpath: str) -> None:
    """
    Initialize the Andor SDK and set the working directory.
    
    Raises:
        RuntimeError: If initialization fails.
    """
    # Call the original function
    ret = Initialize(dirpath.encode('utf-8'))
    if read_return_message(ret):
        raise RuntimeError(f"Failed to initialize Andor SDK: {ret}")

def shutdown() -> None:
    """
    Shutdown the Andor SDK and release resources.
    """
    try: abortAcquisition()
    except: pass
    
    ret = Shutdown()
    if read_return_message(ret):
        raise RuntimeError(f"Failed to shutdown Andor SDK: {ret}")

def getCameraSerialNumber() -> int:
    """
    Get the camera serial number.

    Returns:
        int: The camera serial number.
    """
    serial_number = ctypes.c_int()
    ret = GetCameraSerialNumber(ctypes.byref(serial_number))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get camera serial number: {msg}")
    return serial_number.value

def getDetector() -> tuple[int,int]:
    """
    Get the sensor size [pixel x pixel]

    Returns:
        tuple[int,int]: The x and y pixels of the sensor in pixels.
    """
    x_pixel = ctypes.c_int()
    y_pixel = ctypes.c_int()
    ret = GetDetector(ctypes.byref(x_pixel), ctypes.byref(y_pixel))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get detector: {msg}")
    return x_pixel.value, y_pixel.value

def getTemperatureRange() -> tuple[float, float]:
    """
    Get the temperature range of the Andor SDK.

    Returns:
        tuple[float, float]: The minimum and maximum temperature.
    """
    min_temp = ctypes.c_float()
    max_temp = ctypes.c_float()
    ret = GetTemperatureRange(ctypes.byref(min_temp), ctypes.byref(max_temp))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get temperature range: {msg}")
    return min_temp.value, max_temp.value

def setTemperature(target_temp: int) -> None:
    """
    Set the temperature of the Andor SDK.

    Args:
        target_temp (int): The target temperature to set [degC].
    """
    target_temp = int(target_temp)
    ret = SetTemperature(ctypes.c_int(target_temp))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set temperature: {msg}")

def getTemperature() -> int:
    """
    Get the current temperature of the Andor SDK.

    Returns:
        int: The current temperature [degC].
    """
    current_temp = ctypes.c_int()
    GetTemperature(ctypes.byref(current_temp))
    return current_temp.value

def coolerON() -> None:
    """
    Turn on the cooler of the Andor SDK.
    """
    ret = CoolerON()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to turn on cooler: {msg}")

def coolerOFF() -> None:
    """
    Turn off the cooler of the Andor SDK.
    """
    ret = CoolerOFF()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to turn off cooler: {msg}")

def checkCoolingStatus() -> None:
    """
    Checks if the target temperature has been achieved.

    Raises:
        RuntimeError: If the return value is not DRV_TEMPERATURE_STABILIZED.
            (either not reached, not stabilised, or error occurred)
    """
    current_temp = ctypes.c_int()
    ret = GetTemperature(ctypes.byref(current_temp))
    if ret != ErrorCodes.DRV_TEMPERATURE_STABILIZED.value:
        raise RuntimeError(f"Failed to get cooling status: {read_return_message(ret)}")

def setImage(hbin:int, vbin:int, hstart:int, hend:int, vstart:int, vend:int) -> None:
    """
    Set the image parameters for the instrument (only for the 'Image' mode!).
    Example to get a full image: SetImage(1,1,1,1024,1,256) for a 1024x256 detector.
    Refer to page 41 (Section 3 - Readout modes - Image) of the Andor SDK2 programming manual
    for more details.

    Args:
        hbin (int): Number of pixels to bin horizontally.
        vbin (int): Number of pixels to bin vertically.
        hstart (int): Start column (inclusive).
        hend (int): End column (inclusive).
        vstart (int): Start row (inclusive).
        vend (int): End row (inclusive).
    """
    ret = SetImage(ctypes.c_int(hbin), ctypes.c_int(vbin), ctypes.c_int(hstart), ctypes.c_int(hend), ctypes.c_int(vstart), ctypes.c_int(vend))
    
    if ret == ErrorCodes.DRV_NOT_INITIALIZED.value: raise RuntimeError('System not initialized')
    elif ret == ErrorCodes.DRV_ACQUIRING.value: raise RuntimeError('Acquisition in progress')
    elif ret == ErrorCodes.DRV_P1INVALID.value: raise ValueError('Horizontal binning parameters invalid')
    elif ret == ErrorCodes.DRV_P2INVALID.value: raise ValueError('Vertical binning parameters invalid')
    elif ret == ErrorCodes.DRV_P3INVALID.value: raise ValueError('Horizontal start sub-area co-ordinate is invalid')
    elif ret == ErrorCodes.DRV_P4INVALID.value: raise ValueError('Horizontal end sub-area co-ordinate is invalid')
    elif ret == ErrorCodes.DRV_P5INVALID.value: raise ValueError('Vertical start sub-area co-ordinate is invalid')
    elif ret == ErrorCodes.DRV_P6INVALID.value: raise ValueError('Vertical end sub-area co-ordinate is invalid')

def setReadMode(mode:Literal['0. Full Vertical Binning', '1. Multi-Track', '2. Random-Track',
                             '3. Single-Track', '4. Image']) -> None:
    """
    Set the read mode of the Andor SDK.

    Args:
        mode (Literal['0. Full Vertical Binning', '1. Multi-Track', '2. Random-Track',
            '3. Single-Track', '4. Image']): The read mode to set.
    """
    if mode not in ['0. Full Vertical Binning', '1. Multi-Track', '2. Random-Track',
                    '3. Single-Track', '4. Image']: raise ValueError(f"Invalid read mode: {mode}")
    mode_cint = ctypes.c_int(int(mode.split('.')[0]))
    ret = SetReadMode(mode_cint)
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set read mode: {msg}")

def setAcquisitionMode(mode:Literal['1. Single','2. Accumulate','3. Kinetics','4. FastKinetics','5. RunTillAbort']) -> None:
    """
    Set the acquisition mode of the Andor SDK.

    Args:
        mode (Literal['1. Single','2. Accumulate','3. Kinetics','4. FastKinetics','5. RunTillAbort']): The acquisition mode to set.
    """
    if mode not in ['1. Single','2. Accumulate','3. Kinetics','4. FastKinetics','5. RunTillAbort']: raise ValueError(f"Invalid acquisition mode: {mode}")
    mode_cint = ctypes.c_int(int(mode.split('.')[0]))
    ret = SetAcquisitionMode(mode_cint)
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set acquisition mode: {msg}")

def abortAcquisition() -> None:
    """
    Abort the current acquisition on the Andor SDK.
    """
    ret = AbortAcquisition()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to abort acquisition: {msg}")

def waitForAcquisitionTimeOut(timeout_ms:int) -> bool:
    """
    Wait for the acquisition to complete or time out.

    Args:
        timeout_ms (int): The timeout duration in milliseconds.
        
    Returns:
        bool: True if the acquisition completed successfully, False if it timed out.
    """
    timeout_ms = int(timeout_ms)
    ret = WaitForAcquisitionTimeOut(ctypes.c_int(timeout_ms))
    if ret == ErrorCodes.DRV_NO_NEW_DATA.value: return False
    else: return True

def cancelWait() -> None:
    """
    Cancel the wait for acquisition timeout.
    """
    ret = CancelWait()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to cancel wait: {msg}")

def prepareAcquisition() -> None:
    """
    Prepare the acquisition. It is also automatically called by startAcquisition
    but, calling this early might save time prior to the actual acquisition.
    """
    ret = PrepareAcquisition()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to prepare acquisition: {msg}")

def startAcquisition() -> None:
    """
    Start the acquisition on the Andor SDK.
    """
    ret = StartAcquisition()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to start acquisition: {msg}")

def setExposureTime(exposure_time_sec:float) -> None:
    """
    Set the exposure time for the Andor SDK.
    """
    exposure_time_sec = float(exposure_time_sec)
    exposure_time_cfloat = ctypes.c_float(exposure_time_sec)
    ret = SetExposureTime(exposure_time_cfloat)
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set exposure time: {msg}")

def getAcquisitionTimings_sec() -> tuple[float, float, float]:
    """
    Get the acquisition timings of the current instrument setup (readout and trigger settings).
    Refer to page 46 (Section 4 - Kinetic Series) of the Andor SDK2 programming manual.
    
    Returns:
        tuple[float, float, float]: The exposure time, accumulate cycle time, and kinetic cycle times, all in [sec]
    """
    exposure_time = ctypes.c_float()
    accumulate_cycle_time = ctypes.c_float()
    kinetic_cycle_time = ctypes.c_float()
    ret = GetAcquisitionTimings(ctypes.byref(exposure_time), ctypes.byref(accumulate_cycle_time), ctypes.byref(kinetic_cycle_time))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get acquisition timings: {msg}")
    return exposure_time.value, accumulate_cycle_time.value, kinetic_cycle_time.value

def setSingleTrack(centre_pixel:int,height_pixel:int) -> None:
    """
    Set the single track mode for the Andor SDK.
    
    Args:
        centre_pixel (int): The centre pixel for the single track.
        height_pixel (int): The height pixel for the single track.
    """
    centre_pixel = int(centre_pixel)
    height_pixel = int(height_pixel)
    centre_pixel_cint = ctypes.c_int(centre_pixel)
    height_pixel_cint = ctypes.c_int(height_pixel)
    ret = SetSingleTrack(centre_pixel_cint, height_pixel_cint)
    if ret == ErrorCodes.DRV_P1INVALID.value:
        raise ValueError('Centre row invalid')
    elif ret == ErrorCodes.DRV_P2INVALID.value:
        raise ValueError('Track height invalid')

def sendSoftwareTrigger() -> None:
    """
    Send a software trigger to the instrument
    """
    ret = SendSoftwareTrigger()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to send software trigger: {msg}")

def isTriggerModeAvailable(mode:Literal[ '0. Internal', '1. External', '6. External Start',
    '7. External Exposure (Bulb)', '9. External FVB EM', '10. Software Trigger',
    '12. External Charge Shifting']) -> bool:
    """
    Check if the trigger mode is available on the instrument.
    
    Args:
        mode (Literal): The trigger mode to check.
    """
    mode_idx = int(mode.split('.')[0])
    ret = IsTriggerModeAvailable(ctypes.c_int(mode_idx))
    if ret == ErrorCodes.DRV_SUCCESS.value: mode_available = True
    elif ret == ErrorCodes.DRV_INVALID_MODE.value: mode_available = False
    else: raise RuntimeError(f"Failed to check trigger mode availability: {read_return_message(ret)}")
    return mode_available

def setTriggerMode(mode:Literal[ '0. Internal', '1. External', '6. External Start',
    '7. External Exposure (Bulb)', '9. External FVB EM', '10. Software Trigger',
    '12. External Charge Shifting']) -> bool:
    """
    Check if the trigger mode is available on the instrument.
    
    Args:
        mode (Literal): The trigger mode to set.
        
    Raises:
        RuntimeError: If the trigger mode cannot be set.
        ValueError: If the trigger mode is invalid.
    """
    if mode not in ['0. Internal', '1. External', '6. External Start',
                    '7. External Exposure (Bulb)', '9. External FVB EM', '10. Software Trigger',
                    '12. External Charge Shifting']:
        raise ValueError(f"Invalid trigger mode: {mode}")
    mode_idx = int(mode.split('.')[0])
    ret = SetTriggerMode(ctypes.c_int(mode_idx))
    if ret == ErrorCodes.DRV_SUCCESS.value: return True
    elif ret == ErrorCodes.DRV_NOT_INITIALIZED.value: raise RuntimeError('System not initialized.')
    elif ret == ErrorCodes.DRV_ACQUIRING.value: raise RuntimeError('Acquisition in progress.')
    elif ret == ErrorCodes.DRV_P1INVALID.value: raise ValueError('Invalid trigger mode.')

def setKineticCycleTime(time_sec: float) -> None:
    """
    Set the kinetic cycle time for the Andor SDK.
    """
    time_sec = float(time_sec)
    time_sec_cfloat = ctypes.c_float(time_sec)
    ret = SetKineticCycleTime(time_sec_cfloat)
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set kinetic cycle time: {msg}")

def setNumberAccumulations(num_accum:int) -> None:
    """
    This function will set the number of scans accumulated in memory. This will only take
    effect if the acquisition mode is either Accumulate or Kinetic Series.
    
    Args:
        num_accum (int): The number of accumulations to set.
    """
    num_accum = int(num_accum)
    num_accum_cint = ctypes.c_int(num_accum)
    ret = SetNumberAccumulations(num_accum_cint)
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set number of accumulations: {msg}")
    
def getMostRecentImage(xpixel:int,ypixel:int,total_pixels:int) -> np.ndarray:
    """
    Get the most recent image from the instrument.
    
    Args:
        xpixel (int): The x pixel size
        ypixel (int): The y pixel size
        total_pixels (int): The total number of pixels
        
    Raises:
        RuntimeError("Library is not initialised")
        RuntimeError("Unable to communicate with card")
        SyntaxError("Invalid pointer (i.e. NULL).")
        ValueError("Array size is incorrect.")
        BufferError("There is no new data yet")
        
    Returns:
        np.ndarray: The most recent image
    """
    total_pixels = xpixel*ypixel
    image_array = (ctypes.c_long * total_pixels)()
    total_pixels_long = ctypes.c_ulong(total_pixels)
    
    ret = GetMostRecentImage(image_array, total_pixels_long)
    if ret == ErrorCodes.DRV_NOT_INITIALIZED.value: raise RuntimeError("Library is not initialised")
    elif ret == ErrorCodes.DRV_ERROR_ACK.value: raise RuntimeError("Unable to communicate with card")
    elif ret == ErrorCodes.DRV_P1INVALID.value: raise SyntaxError("Invalid pointer (i.e. NULL).")
    elif ret == ErrorCodes.DRV_P2INVALID.value: raise ValueError("Array size is incorrect.")
    elif ret == ErrorCodes.DRV_NO_NEW_DATA.value: raise BufferError("There is no new data yet")
    
    return np.ctypeslib.as_array(image_array).reshape((ypixel, xpixel))

#%% KEY PARAMETERS
SAFE_SHUTDOWN_TEMP = -10    # Temperature above which it is safe for the device to be shut down.
                            # Any lower temperatures risks DAMAGING the sensor in the long term.
                            # Naturally, DO NOT MODIFY THIS CONSTANT! Safe temp: -20degC
assert SAFE_SHUTDOWN_TEMP >= -20, f"Safe shutdown temperature must be at least -20 degC, but got {SAFE_SHUTDOWN_TEMP} degC"

#%% Test functions (low level)
def initialisation_and_connection_test():
    # Library initialisation
    init_dir = os.path.split(path_dll_andor)[0]

    ret_code_init = Initialize(init_dir.encode('utf-8'))
    
    if read_return_message(ret_code_init) is not None: 
        print(f"Initialisation failed. Error code: {ret_code_init}")
        return
    else: print("Initialisation successful. Checking status...")

    status_code = ctypes.c_uint()
    ret_code_status = Getstatus(ctypes.byref(status_code))
    
    if ret_code_status == DRV_SUCCESS and status_code.value == DRV_IDLE:
        print('Status check successful. The camera is idle and ready')
    else:
        print(f'Status check failed. Error code: {ret_code_status}, Status code: {status_code.value}')

def cooler_tests():
    xpixels = ctypes.c_int()
    ypixels = ctypes.c_int()
    ret = GetDetector(ctypes.byref(xpixels), ctypes.byref(ypixels))
    if ret == DRV_SUCCESS:
        print("Parameter initialisation tests successful.")
        print(f"Detector X Pixels: {xpixels.value}")
        print(f"Detector Y Pixels: {ypixels.value}")
    else:
        print(f"Parameter initialisation tests failed. Error code: {ret}")
        
    idx = ctypes.c_int()
    speed = ctypes.c_float()
    ret = GetFastestRecommendedVSSpeed(ctypes.byref(idx), ctypes.byref(speed))
    if ret == DRV_SUCCESS:
        print("GetFastestRecommendedVSSpeed successful.")
        print(f"Fastest recommended speed index: {idx.value} [idx]")
        print(f"Fastest recommended speed value: {speed.value} [microsec/pixel shift]")
    else:
        print(f"GetFastestRecommendedVSSpeed failed. Error code: {ret}")
        
    num_speeds = ctypes.c_int()
    ret = GetNumberVSSpeeds(ctypes.byref(num_speeds))
    if ret == DRV_SUCCESS:
        print("GetNumberVSSpeeds successful.")
        print(f"Number of VSSpeeds: {num_speeds.value}")
    else:
        print(f"GetNumberVSSpeeds failed. Error code: {ret}")

    speed = ctypes.c_float()
    ret = GetVSSpeed(idx.value, ctypes.byref(speed))
    if ret == DRV_SUCCESS:
        print("GetVSSpeed successful.")
        print(f"VSSpeed: {speed.value} [microsec/pixel shift]")
    else:
        print(f"GetVSSpeed failed. Error code: {ret}")
        # Search for the error message
        error_message = read_return_message(ret)
        print(f"Error message: {error_message}")

def capabilities_check():
    # Check for capabilities
    caps = AndorCapabilities()
    caps.ulSize = ctypes.sizeof(AndorCapabilities)
    ret_code_capabilities = GetCapabilities(ctypes.byref(caps))
    if ret_code_capabilities == DRV_SUCCESS:
        print("Capabilities check successful.")
        print(f'Single Acquisition Mode: {"YES" if caps.ulAcqModes & 2**0 else "NO"}')
        print(f'Frame Transfer Mode: {"YES" if caps.ulAcqModes & 2**4 else "NO"}')

        print(f'Full image read mode: {"YES" if caps.ulAcqModes & 2**0 else "NO"}')
        print(f'Single track read mode: {"YES" if caps.ulAcqModes & 2**2 else "NO"}')
        print(f'Full Vertical Binning (FVB) read mode: {"YES" if caps.ulAcqModes & 2**3 else "NO"}')
        print(f'Multi track read mode: {"YES" if caps.ulAcqModes & 2**4 else "NO"}')

        print(f'Internal trigger: {"YES" if caps.ulTriggerModes & 2**0 else "NO"}')
        print(f'External trigger: {"YES" if caps.ulTriggerModes & 2**1 else "NO"}')
        print(f'Software (continuous) trigger: {"YES" if caps.ulTriggerModes & 2**3 else "NO"}')
        
        print(f'Camera: {caps.ulCameraType}')
        print(f'Camera PDA: {"YES" if caps.ulCameraType == 0 else "NO"}')
        print(f'Camera iDus: {"YES" if caps.ulCameraType == 7 else "NO"}')
    else:
        print(f"Capabilities check failed. Error code: {ret_code_capabilities}")

def device_termination():
    print("Shutting down...")
    ret_code_shutdown = Shutdown()
    if ret_code_shutdown == DRV_SUCCESS:
        print("Shutdown successful.")
    else:
        print(f"Shutdown failed. Error code: {ret_code_shutdown}")

#%% Test functions (Python wrapped)
def connection_test():
    print(">>>>> Running initialisation and connection test... <<<<<")
    initialize(os.path.split(path_dll_andor)[0])
    
    serial_number = getCameraSerialNumber()
    print(f"Camera serial number: {serial_number}")

    sensor_size = getDetector()
    print(f"Sensor size (X, Y): {sensor_size}")
    
    try: abortAcquisition()
    except: pass

def cooler_tests():
    print(">>>>> Running cooler tests... <<<<<")
    target_temp = 0
    
    coolerON()
    setTemperature(target_temp)
    print(f'Cooler turned ON, target temperature: {target_temp} degC, current temperature: {getTemperature()} degC')
    for _ in range(60):
        print(f'Temperature: {getTemperature()}, time: {get_timestamp_us_str()}')
        time.sleep(1)
        if checkCoolingStatus(): break
        
    termination_temp = 10
    setTemperature(termination_temp)
    while not checkCoolingStatus():
        print(f'Temperature: {getTemperature()}, time: {get_timestamp_us_str()}')
        time.sleep(1)
        if getTemperature() >= SAFE_SHUTDOWN_TEMP: break

def acquisition_test_img(integration_time_ms:float=100.0) -> np.ndarray:
    """
    Run an image acquisition test with the specified integration time.

    Args:
        integration_time_ms (float): The integration time for the acquisition in milliseconds. Default is 100.0 ms.
        
    Returns:
        np.ndarray: The acquired image data.
    """
    print(">>>>> Running image acquisition test... <<<<<")
    
    setAcquisitionMode(mode='1. Single')
    setReadMode(mode='4. Image')
    
    pixelx,pixely = getDetector()
    print(f"Detector size (X, Y): {pixelx}, {pixely}")
    
    setExposureTime(integration_time_ms * 1e-3)
    setTriggerMode('10. Software Trigger')
    setNumberAccumulations(1)
    setKineticCycleTime(0)
    setImage(1, 1, 1, pixelx, 1, pixely)
    print(f'Acquisition timings: {getAcquisitionTimings_sec()}')
    
    kinetic_cycle_time_sec = getAcquisitionTimings_sec()[2]
    
    t1 = time.time()
    print('Acquiring image')
    startAcquisition()
    
    waitForAcquisitionTimeOut(kinetic_cycle_time_sec*1e3*1.5)
    print(f'Image acquisition complete. Time taken: {time.time()-t1} sec')
    
    img = getMostRecentImage(pixelx,pixely,pixelx*pixely)
    return img

def plot_img(img:np.ndarray):
    """
    Plot the acquired image and its profiles.

    Args:
        img (np.ndarray): The acquired image data.
    """
    profile_x = np.sum(img, axis=0)
    profile_y = np.sum(img, axis=1)
    y_pixel_indices = np.arange(len(profile_y))

    plt.figure(figsize=(12.5,7.5))

    plt.subplot(2,2,1)
    plt.imshow(img, cmap='inferno')
    plt.title('Acquired Image')
    plt.gca().invert_yaxis()
    plt.colorbar()
    
    plt.subplot(2,2,2)
    plt.plot(profile_y, y_pixel_indices)
    plt.title('Sum Y Profile')
    plt.xlabel('Intensity')
    plt.ylabel('Pixel Index')
    
    plt.subplot(2,2,3)
    plt.plot(profile_x)
    plt.title('Sum X Profile')
    plt.xlabel('Pixel Index')
    plt.ylabel('Intensity')
    
    plt.show()

def continuous_acquisition_test(integration_time_ms:float=30.0) -> None:
    """
    Run a continuous image acquisition test with the specified integration time and plots it.

    Args:
        integration_time_ms (float): The integration time for the acquisition in milliseconds. Default is 100.0 ms.
    """
    print(">>>>> Running continuous image acquisition test... <<<<<")
    
    pixelx,pixely = getDetector()
    print(f"Detector size (X, Y): {pixelx}, {pixely}")
    
    setReadMode(mode='4. Image')
    start_pixel, height_pixel = 0, 255
    setImage(hbin=1,vbin=height_pixel,hstart=1,hend=pixelx,vstart=start_pixel+1,vend=start_pixel+height_pixel)
    setKineticCycleTime(0)
    setAcquisitionMode(mode='5. RunTillAbort')

    setExposureTime(integration_time_ms * 1e-3)
    
    res = isTriggerModeAvailable('10. Software Trigger')
    print(f'Trigger mode available: {res}')
    setTriggerMode('10. Software Trigger')
    
    print(f'Acquisition timings: {getAcquisitionTimings_sec()}')

    kinetic_cycle_time_sec = getAcquisitionTimings_sec()[2]
    
    print('Acquiring image')
    startAcquisition()
    
    fig, ax = plt.subplots()
    ax:Axes
    fig.show()
    
    while True:
        t1 = time.time()
        sendSoftwareTrigger()
        waitForAcquisitionTimeOut(kinetic_cycle_time_sec*1e3*1.5)
        
        t2 = time.time()
        img = getMostRecentImage(pixelx,1,pixelx*1)
        arr = img.reshape(-1)
        ax.clear()
        ax.plot(arr)
        
        t3 = time.time()
        print(f'Acquisition time: {t2-t1:.3f} sec, Processing time: {t3-t2:.3f} sec')
        if fig.waitforbuttonpress(10e-3): break
        
    abortAcquisition()

#%% Controller class definition
from threading import Lock

ANDOR_OPE_TEMP = ControllerSpecificConfigEnum.ANDOR_OPERATIONAL_TEMPERATURE.value
ANDOR_TEMP_INIT_MARGIN = 5 # temperature margin for initialization [degC]. If temp < ANDOR_OPE_TEMP + ANDOR_TEMP_INIT_MARGIN, then the initialisation finishes

class SpectrometerController_Andor(Class_SpectrometerController):
    def __init__(self):
        self._lock = Lock()
        
    # >>> Device initialisation <<<
        init_dir = os.path.split(path_dll_andor)[0]
        initialize(init_dir)
        
        # Parameter intialisation
        self._x_pixel, self._y_pixel = getDetector()
        self._total_pixel = self._x_pixel * self._y_pixel
        
        # Detector initialisation
        self._set_ROI_parameters()
        
        # Acquisition initialisation
        setReadMode(mode='4. Image')
        setAcquisitionMode(mode='5. RunTillAbort')
        setKineticCycleTime(0.0)
        setTriggerMode('10. Software Trigger')
        
        if not isTriggerModeAvailable(mode='10. Software Trigger'):
            raise SyntaxError('Trigger mode not available either due to hardware limitations or incorrect settings.'\
                '(e.g., Read mode has to be set to 4. Image, and Acquisition mode to 5. RunTillAbort)')
        
        # Acquisition parameters
        self._flg_isacquiring = threading.Event()
        self._integration_time_us:int = 0
        self._theoretical_wait_time_sec:float = 0.0
        
        # Initialise the device for acquisition
        self.initialisation()
        
    def initialisation(self):
        """
        Initialises the spectrometer controller
        """
        self._initialise_cooler()
        self._integration_time_us = self.get_integration_time_us()
        self._start_acquisition()
        
    def terminate(self):
        """
        Terminates the spectrometer controller according to the manufacturer's protocol
        """
        self._cooler_shutdown_protocol()
        self._stop_acquisition()

    def _initialise_cooler(self):
        self._lock.acquire()
        coolerON()
        try: temp = int(ANDOR_OPE_TEMP)
        except ValueError: temp = getTemperature()
        
        try: setTemperature(temp)
        except RuntimeError as e:
            print(f"Failed to set temperature: {e}")
            self._lock.release()
            return
        
        i=0
        while getTemperature() > temp + ANDOR_TEMP_INIT_MARGIN:
            time.sleep(1)
            i+=1
            if i % 5 == 1:
                print(f"Cooling... Current: {getTemperature()} degC. Target: {ANDOR_OPE_TEMP} degC")
                
        try: checkCoolingStatus()
        except RuntimeError as e:
            temp = getTemperature()
            print(f"Cooling failed: {e}. Current: {temp} degC. Target: {ANDOR_OPE_TEMP} degC")
            
        self._lock.release()
        
    def _cooler_shutdown_protocol(self):
        """
        Shutdown protocol for the cooler.
        """
        self._lock.acquire()
        coolerOFF()
        i=0
        while getTemperature() < SAFE_SHUTDOWN_TEMP:
            time.sleep(1)
            i+=1
            if i % 5 == 1:
                print(f"Shutting down... Current: {getTemperature()} degC. Target: {SAFE_SHUTDOWN_TEMP} degC")
        
        self._lock.release()
        
    def _set_ROI_parameters(self):
        """
        Set the Region of Interest (ROI) parameters for the detector according to
        the user-defined settings in the config.ini file.
        """
        xmin_dev = 1
        xmax_dev = self._x_pixel
        ymin_dev = 1
        ymax_dev = self._y_pixel
        
        xmin_user = ControllerSpecificConfigEnum.ANDOR_ROI_COL_MIN.value
        xmax_user = ControllerSpecificConfigEnum.ANDOR_ROI_COL_MAX.value
        xbin_user = ControllerSpecificConfigEnum.ANDOR_ROI_BIN_COL.value
        
        ymin_user = ControllerSpecificConfigEnum.ANDOR_ROI_ROW_MIN.value
        ymax_user = ControllerSpecificConfigEnum.ANDOR_ROI_ROW_MAX.value
        ybin_user = ControllerSpecificConfigEnum.ANDOR_ROI_BIN_ROW.value
        
        xstart = max(xmin_dev, xmin_user)
        xend = min(xmax_dev, xmax_user)
        xbin = min(xbin_user, (xend-xstart+1))
        assert (xend-xstart+1) % xbin == 0, f"Invalid X ROI parameters: {xstart}, {xend}, {xbin}."\
            "The bin must divide the range evenly. Either change the bin or the COL MIN/MAX values."

        ystart = max(ymin_dev, ymin_user)
        yend = min(ymax_dev, ymax_user)
        ybin = min(ybin_user, (yend-ystart+1))

        assert (yend-ystart+1) % ybin == 0, f"Invalid Y ROI parameters: {ystart}, {yend}, {ybin}."\
            "The bin must divide the range evenly. Either change the bin or the ROW MIN/MAX values."
            
        setImage(hbin=xbin, vbin=ybin, hstart=xstart, hend=xend, vstart=ystart, vend=yend)

        self._x_pixel = int((xend - xstart + 1)/xbin)
        self._y_pixel = int((yend - ystart + 1)/ybin)
        self._total_pixel = int(self._x_pixel * self._y_pixel)

        print(f"Binning parameters: xstart={xstart}, xend={xend}, xbin={xbin}, ystart={ystart}, yend={yend}, ybin={ybin}")
        
    def _start_acquisition(self):
        with self._lock:
            startAcquisition()
            self._flg_isacquiring.set()

    def _stop_acquisition(self):
        with self._lock:
            abortAcquisition()
            self._flg_isacquiring.clear()
            
    def get_integration_time_us(self) -> int:
        """
        Returns the integration time of the device
        
        Returns:
            int: Integration time in microseconds
        """
        with self._lock:
            exposure_sec,_,kineticCycle_sec = getAcquisitionTimings_sec()
        self._integration_time_us = int(exposure_sec * 1e6)  # Convert seconds to microseconds
        self._theoretical_wait_time_sec = kineticCycle_sec
        return self._integration_time_us
    
    def get_integration_time_limits_us(self):
        """
        Get the integration time limits of the device

        Returns:
            tuple: A tuple containing the minimum, maximum, and increment of the integration time in [us]
        """
        return (10, 1e9, 1)
    
    def set_integration_time_us(self, integration_time:int) -> int:
        """Sets the integration time of the device

        Args:
            integration_time (int): Integration time in [device unit] 
            (microseconds for the QE Pro)

        Returns:
            int: Device integrationt time after set up in microseconds
        """
        if not isinstance(integration_time,int) and not isinstance(integration_time,float):
            raise ValueError("Integration time must be an integer")
        integration_time = int(integration_time)
        
        with self._lock: setExposureTime(integration_time * 1e-6)
        
        self._integration_time_us = self.get_integration_time_us()
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
            timestamp = get_timestamp_us_int()
            sendSoftwareTrigger()
            waitForAcquisitionTimeOut(self._theoretical_wait_time_sec * 1e3 * 1.5)
            intensity = getMostRecentImage(self._x_pixel,self._y_pixel,self._total_pixel)
        
        intensity = np.sum(intensity, axis=0).reshape(-1).tolist()
        wavelength = np.arange(1,self._x_pixel+1).tolist()
        
        intensity = [float(i) for i in intensity]
        wavelength = [float(i) for i in wavelength]
        
        spectra = pd.DataFrame({
            DataAnalysisConfigEnum.WAVELENGTH_LABEL.value: wavelength,
            DataAnalysisConfigEnum.INTENSITY_LABEL.value: intensity,
        })
        return (spectra, timestamp, self._integration_time_us)

#%% Tests
if __name__ == "__main__":
    matplotlib.use('TkAgg')
    # try: initialisation_and_connection_test()
    # except Exception as e: print(f"Initialisation and connection test failed: {e}")

    # try: parameter_initialisation_tests()
    # except Exception as e: print(f'Parameter initialisation tests failed: {e}')
    
    # try: capabilities_check()
    # except Exception as e: print(f'Capabilities check failed: {e}')

    # try: device_termination()
    # except Exception as e: print(f"Device termination failed: {e}")
    
    # try: connection_test()
    # except Exception as e: print(f"Connection test failed: {e}")
    
    # try: cooler_tests()
    # except Exception as e: print(f"Cooler tests failed: {e}")
    
    # try: img = acquisition_test_img(); plot_img(img)
    # except Exception as e: print(f"Acquisition test failed: {e}")
    
    # try: continuous_acquisition_test()
    # except Exception as e: print(f"Continuous acquisition test failed: {e}")
    
    # try: shutdown()
    # except Exception as e: print(f"Shutdown failed: {e}")
    
    controller = SpectrometerController_Andor()
    t1 = time.time()
    for i in range(20):
        controller.measure_spectrum()
    t2 = time.time()
    
    t1 = time.time()
    for i in range(100):
        controller.measure_spectrum()
    t2 = time.time()
    print(f"Time taken for 100 measurements: {t2 - t1} seconds, time per measurement: {(t2 - t1) / 100} seconds")
    controller.terminate()