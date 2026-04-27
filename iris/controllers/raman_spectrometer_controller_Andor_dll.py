"""A class that allows the control of the Andor spectrometers.

Self notes:
This script is based on the Andor CCD iVac 416 though, the it should 
be applicable to most of Andor's other spectrometers with minimal to
no adjustments (aside from the advance features).

Acknowledgement:
pylablib as a learning material for the development of this controller, though
no code from it has been reused in this controller.

Changelog (30Hz patch):
- Added DLL bindings for GetNumberHSSpeeds, GetHSSpeed, SetHSSpeed
- Added Python wrappers: getNumberHSSpeeds, getHSSpeed, setHSSpeed
- SpectrometerController_Andor.__init__: 
    - Uses getFastestRecommendedVSSpeed() return value (not hardcoded index)
    - Sets HS speed to index 0 (fastest) on the conventional amplifier (typ=1 for iVac)
- SpectrometerController_Andor.measure_spectrum:
    - Switched to RunTillAbort + GetMostRecentImage for sustained throughput
    - startAcquisition() called once in __init__ / initialisation; measure_spectrum
      just triggers and retrieves
"""
#%% Main import
import os
import sys
import threading
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
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.utils.general import get_timestamp_us_int, get_timestamp_us_str
from iris.controllers.class_spectrometer_controller import Class_SpectrometerController

from iris import DataAnalysisConfigEnum
from iris.controllers import ControllerSpecificConfigEnum

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

SetVSSpeed = andorDLL.SetVSSpeed
SetVSSpeed.argtypes = [ctypes.c_int] # [index of the speed to set]
SetVSSpeed.restype = ctypes.c_uint

SetVSAmplitude = andorDLL.SetVSAmplitude
SetVSAmplitude.argtypes = [ctypes.c_int] # [state of the amplitude: 0. Low, 1. High]
SetVSAmplitude.restype = ctypes.c_uint

# >>> Horizontal shift speed (NEW)
# unsigned int WINAPI GetNumberHSSpeeds(int channel, int typ, int* speeds)
GetNumberHSSpeeds = andorDLL.GetNumberHSSpeeds
GetNumberHSSpeeds.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
GetNumberHSSpeeds.restype = ctypes.c_uint

# unsigned int WINAPI GetHSSpeed(int channel, int typ, int index, float* speed)
GetHSSpeed = andorDLL.GetHSSpeed
GetHSSpeed.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_float)]
GetHSSpeed.restype = ctypes.c_uint

# unsigned int WINAPI SetHSSpeed(int typ, int index)
SetHSSpeed = andorDLL.SetHSSpeed
SetHSSpeed.argtypes = [ctypes.c_int, ctypes.c_int]
SetHSSpeed.restype = ctypes.c_uint

SetShutterEx = andorDLL.SetShutterEx
SetShutterEx.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
SetShutterEx.restype = ctypes.c_uint

# >>> Temperature
GetTemperatureRange = andorDLL.GetTemperatureRange
GetTemperatureRange.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
GetTemperatureRange.restype = ctypes.c_uint

SetTemperature = andorDLL.SetTemperature
SetTemperature.argtypes = [ctypes.c_int]
SetTemperature.restype = ctypes.c_uint

GetTemperature = andorDLL.GetTemperature
GetTemperature.argtypes = [ctypes.POINTER(ctypes.c_int)]
GetTemperature.restype = ctypes.c_uint

CoolerON = andorDLL.CoolerON
CoolerON.argtypes = []
CoolerON.restype = ctypes.c_uint

CoolerOFF = andorDLL.CoolerOFF
CoolerOFF.argtypes = []
CoolerOFF.restype = ctypes.c_uint

# >>> Readout settings
SetReadMode = andorDLL.SetReadMode
SetReadMode.argtypes = [ctypes.c_int]
SetReadMode.restype = ctypes.c_uint

SetImage = andorDLL.SetImage
SetImage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
SetImage.restype = ctypes.c_uint

SetAcquisitionMode = andorDLL.SetAcquisitionMode
SetAcquisitionMode.argtypes = [ctypes.c_int]
SetAcquisitionMode.restype = ctypes.c_uint

AbortAcquisition = andorDLL.AbortAcquisition
AbortAcquisition.argtypes = []
AbortAcquisition.restype = ctypes.c_uint

WaitForAcquisition = andorDLL.WaitForAcquisition
WaitForAcquisition.argtypes = []
WaitForAcquisition.restype = ctypes.c_uint

WaitForAcquisitionTimeOut = andorDLL.WaitForAcquisitionTimeOut
WaitForAcquisitionTimeOut.argtypes = [ctypes.c_int]
WaitForAcquisitionTimeOut.restype = ctypes.c_uint

CancelWait = andorDLL.CancelWait
CancelWait.argtypes = []
CancelWait.restype = ctypes.c_uint

PrepareAcquisition = andorDLL.PrepareAcquisition
PrepareAcquisition.argtypes = []
PrepareAcquisition.restype = ctypes.c_uint

StartAcquisition = andorDLL.StartAcquisition
StartAcquisition.argtypes = []
StartAcquisition.restype = ctypes.c_uint

SetExposureTime = andorDLL.SetExposureTime
SetExposureTime.argtypes = [ctypes.c_float]
SetExposureTime.restype = ctypes.c_uint

GetAcquisitionTimings = andorDLL.GetAcquisitionTimings
GetAcquisitionTimings.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)]
GetAcquisitionTimings.restype = ctypes.c_uint

SetSingleTrack = andorDLL.SetSingleTrack
SetSingleTrack.argtypes = [ctypes.c_int, ctypes.c_int]
SetSingleTrack.restype = ctypes.c_uint

SendSoftwareTrigger = andorDLL.SendSoftwareTrigger
SendSoftwareTrigger.argtypes = []
SendSoftwareTrigger.restype = ctypes.c_uint

IsTriggerModeAvailable = andorDLL.IsTriggerModeAvailable
IsTriggerModeAvailable.argtypes = [ctypes.c_int]
IsTriggerModeAvailable.restype = ctypes.c_uint

SetTriggerMode = andorDLL.SetTriggerMode
SetTriggerMode.argtypes = [ctypes.c_int]
SetTriggerMode.restype = ctypes.c_uint

SetKineticCycleTime = andorDLL.SetKineticCycleTime
SetKineticCycleTime.argtypes = [ctypes.c_float]
SetKineticCycleTime.restype = ctypes.c_uint

SetNumberAccumulations = andorDLL.SetNumberAccumulations
SetNumberAccumulations.argtypes = [ctypes.c_int]
SetNumberAccumulations.restype = ctypes.c_uint

GetMostRecentImage = andorDLL.GetMostRecentImage
GetMostRecentImage.argtypes = [ctypes.POINTER(ctypes.c_long), ctypes.c_ulong]
GetMostRecentImage.restype = ctypes.c_uint

GetAcquiredData = andorDLL.GetAcquiredData
GetAcquiredData.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_ulong]
GetAcquiredData.restype = ctypes.c_uint

SaveAsSif = andorDLL.SaveAsSif
SaveAsSif.argtypes = [ctypes.c_char_p]
SaveAsSif.restype = ctypes.c_uint

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
    if error_code == ErrorCodes.DRV_SUCCESS.value: return None
    try: return ErrorCodes(error_code).name
    except ValueError: return "Unknown error"

#%% Function wrappers
def initialize(dirpath: str) -> None:
    ret = Initialize(dirpath.encode('utf-8'))
    if read_return_message(ret):
        raise RuntimeError(f"Failed to initialize Andor SDK: {ret}")

def shutdown() -> None:
    try: abortAcquisition()
    except: pass
    ret = Shutdown()
    if read_return_message(ret):
        raise RuntimeError(f"Failed to shutdown Andor SDK: {ret}")

def getCameraSerialNumber() -> int:
    serial_number = ctypes.c_int()
    ret = GetCameraSerialNumber(ctypes.byref(serial_number))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get camera serial number: {msg}")
    return serial_number.value

def getDetector() -> tuple[int,int]:
    x_pixel = ctypes.c_int()
    y_pixel = ctypes.c_int()
    ret = GetDetector(ctypes.byref(x_pixel), ctypes.byref(y_pixel))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get detector: {msg}")
    return x_pixel.value, y_pixel.value

def getFastestRecommendedVSSpeed() -> tuple[int, float]:
    speed = ctypes.c_float()
    index = ctypes.c_int()
    ret = GetFastestRecommendedVSSpeed(ctypes.byref(index), ctypes.byref(speed))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get fastest recommended vertical shift speed: {msg}")
    return index.value, speed.value

def getNumberVSSpeeds() -> int:
    num_speeds = ctypes.c_int()
    ret = GetNumberVSSpeeds(ctypes.byref(num_speeds))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get number of vertical shift speeds: {msg}")
    return num_speeds.value

def getVSSpeed(index: int) -> float:
    speed = ctypes.c_float()
    ret = GetVSSpeed(ctypes.c_int(index), ctypes.byref(speed))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get vertical shift speed: {msg}")
    return speed.value

def setVSSpeed(index: int) -> None:
    ret = SetVSSpeed(ctypes.c_int(index))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set vertical shift speed: {msg}")
    
def setVSAmplitude(level: int) -> None:
    ret = SetVSAmplitude(ctypes.c_int(level))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set vertical shift amplitude: {msg}")

# >>> Horizontal shift speed wrappers (NEW) <<<

# iVac 416 uses a conventional CCD register (not EMCCD), so typ=1 throughout.
# channel=0 is the only A/D channel on this camera.
_HS_CHANNEL = 0
_HS_TYP     = 0   # For non-EMCCD cameras (iVac, iDus etc.), typ=0 means conventional.
                  # typ=1 only applies to EMCCD cameras where 0=EM and 1=conventional.
                  # SDK example: GetNumberHSSpeeds(0, 0, &a) — both args are 0.

def getNumberHSSpeeds(channel: int = _HS_CHANNEL, typ: int = _HS_TYP) -> int:
    """
    Return the number of horizontal shift speeds available.

    Args:
        channel (int): A/D channel index (0 for iVac 416).
        typ (int): Output amplifier type.
            For non-EMCCD cameras (iVac, iDus): 0 = conventional (only valid value).
            For EMCCD cameras (iXon etc.): 0 = EM register, 1 = conventional.

    Returns:
        int: Number of available horizontal shift speeds.
    """
    num_speeds = ctypes.c_int()
    ret = GetNumberHSSpeeds(ctypes.c_int(channel), ctypes.c_int(typ), ctypes.byref(num_speeds))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get number of HS speeds: {msg}")
    return num_speeds.value

def getHSSpeed(index: int, channel: int = _HS_CHANNEL, typ: int = _HS_TYP) -> float:
    """
    Return the horizontal shift speed for a given index, in MHz.

    Args:
        index (int): Speed index (0 = fastest).
        channel (int): A/D channel index (0 for iVac 416).
        typ (int): Output amplifier type (1 = conventional for iVac).

    Returns:
        float: Horizontal shift speed in MHz.
    """
    speed = ctypes.c_float()
    ret = GetHSSpeed(ctypes.c_int(channel), ctypes.c_int(typ), ctypes.c_int(index), ctypes.byref(speed))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get HS speed at index {index}: {msg}")
    return speed.value

def setHSSpeed(index: int, typ: int = _HS_TYP) -> None:
    """
    Set the horizontal shift speed by index.
    Index 0 is always the fastest speed available.

    Args:
        index (int): Speed index. 0 = fastest (e.g. 100 kHz on iVac 416).
        typ (int): Output amplifier type (0 = conventional for iVac/non-EMCCD).
    """
    ret = SetHSSpeed(ctypes.c_int(typ), ctypes.c_int(index))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set HS speed: {msg}")

def setShutterEx(type: int, mode: int, closing_time: int, opening_time: int, ext_mode: int) -> None:
    ret = SetShutterEx(ctypes.c_int(type), ctypes.c_int(mode), ctypes.c_int(closing_time), ctypes.c_int(opening_time), ctypes.c_int(ext_mode))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set shutter parameters: {msg}")

def getTemperatureRange() -> tuple[float, float]:
    min_temp = ctypes.c_float()
    max_temp = ctypes.c_float()
    ret = GetTemperatureRange(ctypes.byref(min_temp), ctypes.byref(max_temp))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get temperature range: {msg}")
    return min_temp.value, max_temp.value

def setTemperature(target_temp: int) -> None:
    target_temp = int(target_temp)
    ret = SetTemperature(ctypes.c_int(target_temp))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set temperature: {msg}")

def getTemperature() -> int:
    current_temp = ctypes.c_int()
    GetTemperature(ctypes.byref(current_temp))
    return current_temp.value

def coolerON() -> None:
    ret = CoolerON()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to turn on cooler: {msg}")

def coolerOFF() -> None:
    ret = CoolerOFF()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to turn off cooler: {msg}")

def checkCoolingStatus() -> None:
    current_temp = ctypes.c_int()
    ret = GetTemperature(ctypes.byref(current_temp))
    if ret != ErrorCodes.DRV_TEMPERATURE_STABILIZED.value:
        raise RuntimeError(f"Failed to get cooling status: {read_return_message(ret)}")

def setImage(hbin:int, vbin:int, hstart:int, hend:int, vstart:int, vend:int) -> None:
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
    if mode not in ['0. Full Vertical Binning', '1. Multi-Track', '2. Random-Track',
                    '3. Single-Track', '4. Image']: raise ValueError(f"Invalid read mode: {mode}")
    mode_cint = ctypes.c_int(int(mode.split('.')[0]))
    ret = SetReadMode(mode_cint)
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set read mode: {msg}")

def setAcquisitionMode(mode:Literal['1. Single','2. Accumulate','3. Kinetics','4. FastKinetics','5. RunTillAbort']) -> None:
    if mode not in ['1. Single','2. Accumulate','3. Kinetics','4. FastKinetics','5. RunTillAbort']: raise ValueError(f"Invalid acquisition mode: {mode}")
    mode_cint = ctypes.c_int(int(mode.split('.')[0]))
    ret = SetAcquisitionMode(mode_cint)
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set acquisition mode: {msg}")

def abortAcquisition() -> None:
    ret = AbortAcquisition()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to abort acquisition: {msg}")

def waitForAcquisition() -> bool:
    ret = WaitForAcquisition()
    if ret == ErrorCodes.DRV_SUCCESS.value: return True
    elif ret == ErrorCodes.DRV_NO_NEW_DATA.value: return False
    else: raise RuntimeError(f"Failed to wait for acquisition: {read_return_message(ret)}")

def waitForAcquisitionTimeOut(timeout_ms:int|float) -> bool:
    timeout_ms = int(timeout_ms)
    ret = WaitForAcquisitionTimeOut(ctypes.c_int(timeout_ms))
    if ret == ErrorCodes.DRV_NO_NEW_DATA.value: return False
    else: return True

def cancelWait() -> None:
    ret = CancelWait()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to cancel wait: {msg}")

def prepareAcquisition() -> None:
    ret = PrepareAcquisition()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to prepare acquisition: {msg}")

def startAcquisition() -> None:
    ret = StartAcquisition()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to start acquisition: {msg}")

def setExposureTime(exposure_time_sec:float) -> None:
    exposure_time_sec = float(exposure_time_sec)
    exposure_time_cfloat = ctypes.c_float(exposure_time_sec)
    ret = SetExposureTime(exposure_time_cfloat)
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set exposure time: {msg}")

def getAcquisitionTimings_sec() -> tuple[float, float, float]:
    exposure_time = ctypes.c_float()
    accumulate_cycle_time = ctypes.c_float()
    kinetic_cycle_time = ctypes.c_float()
    ret = GetAcquisitionTimings(ctypes.byref(exposure_time), ctypes.byref(accumulate_cycle_time), ctypes.byref(kinetic_cycle_time))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to get acquisition timings: {msg}")
    return exposure_time.value, accumulate_cycle_time.value, kinetic_cycle_time.value

def setSingleTrack(centre_pixel:int,height_pixel:int) -> None:
    centre_pixel = int(centre_pixel)
    height_pixel = int(height_pixel)
    ret = SetSingleTrack(ctypes.c_int(centre_pixel), ctypes.c_int(height_pixel))
    if ret == ErrorCodes.DRV_P1INVALID.value: raise ValueError('Centre row invalid')
    elif ret == ErrorCodes.DRV_P2INVALID.value: raise ValueError('Track height invalid')

def sendSoftwareTrigger() -> None:
    ret = SendSoftwareTrigger()
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to send software trigger: {msg}")

def isTriggerModeAvailable(mode:Literal[ '0. Internal', '1. External', '6. External Start',
    '7. External Exposure (Bulb)', '9. External FVB EM', '10. Software Trigger',
    '12. External Charge Shifting']) -> bool:
    mode_idx = int(mode.split('.')[0])
    ret = IsTriggerModeAvailable(ctypes.c_int(mode_idx))
    if ret == ErrorCodes.DRV_SUCCESS.value: return True
    elif ret == ErrorCodes.DRV_INVALID_MODE.value: return False
    else: raise RuntimeError(f"Failed to check trigger mode availability: {read_return_message(ret)}")

def setTriggerMode(mode:Literal[ '0. Internal', '1. External', '6. External Start',
    '7. External Exposure (Bulb)', '9. External FVB EM', '10. Software Trigger',
    '12. External Charge Shifting']) -> bool:
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
    else: raise RuntimeError(f"Failed to set trigger mode: {read_return_message(ret)}")

def setKineticCycleTime(time_sec: float) -> None:
    ret = SetKineticCycleTime(ctypes.c_float(float(time_sec)))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set kinetic cycle time: {msg}")

def setNumberAccumulations(num_accum:int) -> None:
    ret = SetNumberAccumulations(ctypes.c_int(int(num_accum)))
    msg = read_return_message(ret)
    if msg: raise RuntimeError(f"Failed to set number of accumulations: {msg}")
    
def getMostRecentImage(xpixel:int, ypixel:int, total_pixels:int) -> np.ndarray:
    total_pixels = xpixel * ypixel
    image_array = (ctypes.c_long * total_pixels)()
    ret = GetMostRecentImage(image_array, ctypes.c_ulong(total_pixels))
    if ret == ErrorCodes.DRV_NOT_INITIALIZED.value: raise RuntimeError("Library is not initialised")
    elif ret == ErrorCodes.DRV_ERROR_ACK.value: raise RuntimeError("Unable to communicate with card")
    elif ret == ErrorCodes.DRV_P1INVALID.value: raise SyntaxError("Invalid pointer (i.e. NULL).")
    elif ret == ErrorCodes.DRV_P2INVALID.value: raise ValueError("Array size is incorrect.")
    elif ret == ErrorCodes.DRV_NO_NEW_DATA.value: raise BufferError("There is no new data yet")
    return np.ctypeslib.as_array(image_array).reshape((ypixel, xpixel))

def getAcquiredData(total_pixels:int) -> np.ndarray:
    data_array = (ctypes.c_int32 * total_pixels)()
    ret = GetAcquiredData(data_array, ctypes.c_ulong(total_pixels))
    if ret == ErrorCodes.DRV_NOT_INITIALIZED.value: raise RuntimeError("Library is not initialised")
    elif ret == ErrorCodes.DRV_ACQUIRING.value: raise RuntimeError("Acquisition in progress")
    elif ret == ErrorCodes.DRV_ERROR_ACK.value: raise RuntimeError("Unable to communicate with card")
    elif ret == ErrorCodes.DRV_P1INVALID.value: raise SyntaxError("Invalid pointer (i.e. NULL).")
    elif ret == ErrorCodes.DRV_P2INVALID.value: raise ValueError("Array size is incorrect.")
    elif ret == ErrorCodes.DRV_NO_NEW_DATA.value: raise BufferError("There is no new data yet")
    return np.ctypeslib.as_array(data_array)

def saveAsSif(path: str) -> None:
    path_bytes = path.encode('utf-8')
    ret = SaveAsSif(path_bytes)
    if ret == ErrorCodes.DRV_SUCCESS.value: return
    elif ret == ErrorCodes.DRV_NOT_INITIALIZED.value: raise RuntimeError("System not initialized.")
    elif ret == ErrorCodes.DRV_ACQUIRING.value: raise ChildProcessError("Acquisition in progress.")
    elif ret == ErrorCodes.DRV_ERROR_ACK.value: raise RuntimeError("Unable to communicate with card.")
    elif ret == ErrorCodes.DRV_P1INVALID.value: raise ValueError(f"Invalid filename or path: {path}")
    elif ret == ErrorCodes.DRV_ERROR_PAGELOCK.value: raise MemoryError("File too large to be generated in memory.")
    else: raise Exception(f"Unknown error occurred. Return code: {ret}")

#%% KEY PARAMETERS
SAFE_SHUTDOWN_TEMP = -10
assert SAFE_SHUTDOWN_TEMP >= -20, f"Safe shutdown temperature must be at least -20 degC, but got {SAFE_SHUTDOWN_TEMP} degC"

#%% Controller class definition
from threading import Lock

ANDOR_OPE_TEMP = ControllerSpecificConfigEnum.ANDOR_OPERATIONAL_TEMPERATURE.value
ANDOR_TEMP_INIT_MARGIN = 5

class SpectrometerController_Andor(Class_SpectrometerController):
    def __init__(self):
        self._lock = Lock()
        self._acquisition_running = False  # tracks whether RunTillAbort is active
        
    # >>> Device initialisation <<<
        init_dir = os.path.split(path_dll_andor)[0]
        initialize(init_dir)
        
        # Parameter initialisation
        self._x_pixel, self._y_pixel = getDetector()
        self._total_pixel = self._x_pixel * self._y_pixel
        
        # Detector ROI
        self._set_ROI_parameters()
        
        # --- Readout speed setup ---
        # VS speed: use the SDK's own recommended fastest index (not hardcoded).
        vs_idx, vs_speed_us = getFastestRecommendedVSSpeed()
        setVSSpeed(vs_idx)
        print(f"VS speed set to index {vs_idx} ({vs_speed_us:.1f} µs/pixel shift)")

        # HS speed: index 0 is always the fastest available.
        # For the iVac 416 this corresponds to 100 kHz (per spec sheet).
        # We enumerate and print all options so the user can verify.
        n_hs = getNumberHSSpeeds()
        print(f"Available HS speeds ({n_hs} total):")
        for i in range(n_hs):
            spd = getHSSpeed(i)
            print(f"  index {i}: {spd:.3f} MHz")
        setHSSpeed(0)   # index 0 = fastest
        print(f"HS speed set to index 0 ({getHSSpeed(0):.3f} MHz)")

        # --- Acquisition mode: RunTillAbort for lowest per-frame overhead ---
        setReadMode(mode='0. Full Vertical Binning')
        setAcquisitionMode(mode='5. RunTillAbort')
        setKineticCycleTime(0.0)   # minimum possible cycle time
        setTriggerMode('0. Internal')

        # Acquisition parameters
        self._integration_time_us:int = 0
        self._theoretical_wait_time_sec:float = 0.0
        
        # Initialise the device (cooler + first timing read)
        self._identifier = None
        self.initialisation()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_continuous_acquisition(self) -> None:
        """
        (Re)start the RunTillAbort acquisition loop.
        Must be called with self._lock held or before lock is needed.
        """
        if self._acquisition_running:
            try: abortAcquisition()
            except: pass
        startAcquisition()
        self._acquisition_running = True

    def _stop_continuous_acquisition(self) -> None:
        if self._acquisition_running:
            try: abortAcquisition()
            except: pass
            self._acquisition_running = False
        
    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_identifier(self) -> str:
        if self._identifier is None:
            self._identifier = f"Andor_{getCameraSerialNumber()}"
        return self._identifier
        
    def initialisation(self):
        self._identifier = f"Andor_{getCameraSerialNumber()}"
        self._initialise_cooler()
        self._integration_time_us = self.get_integration_time_us()
        # Start the continuous acquisition loop now that everything is configured.
        with self._lock:
            self._start_continuous_acquisition()
        
    def terminate(self):
        with self._lock:
            self._stop_continuous_acquisition()
        self._cooler_shutdown_protocol()
        
    def _open_ex_shutter(self):
        try: setShutterEx(1,1,100,100,1)
        except Exception as e: print(f"Failed to open external shutter: {e}")
            
    def _close_ex_shutter(self):
        try: setShutterEx(1,1,100,100,2)
        except Exception as e: print(f"Failed to close external shutter: {e}")
        
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
        assert (xend-xstart+1) % xbin == 0, \
            f"Invalid X ROI parameters: {xstart}, {xend}, {xbin}. " \
            "The bin must divide the range evenly."

        ystart = max(ymin_dev, ymin_user)
        yend = min(ymax_dev, ymax_user)
        ybin = min(ybin_user, (yend-ystart+1))
        assert (yend-ystart+1) % ybin == 0, \
            f"Invalid Y ROI parameters: {ystart}, {yend}, {ybin}. " \
            "The bin must divide the range evenly."
            
        setImage(hbin=xbin, vbin=ybin, hstart=xstart, hend=xend, vstart=ystart, vend=yend)

        self._x_pixel = int((xend - xstart + 1) / xbin)
        self._y_pixel = int((yend - ystart + 1) / ybin)
        self._total_pixel = int(self._x_pixel * self._y_pixel)

        print(f"ROI: xstart={xstart}, xend={xend}, xbin={xbin}, "
              f"ystart={ystart}, yend={yend}, ybin={ybin} "
              f"→ effective pixels: {self._x_pixel} x {self._y_pixel}")
            
    def get_integration_time_us(self) -> int:
        with self._lock:
            exposure_sec, _, kinetic_sec = getAcquisitionTimings_sec()
        self._integration_time_us = int(exposure_sec * 1e6)
        self._theoretical_wait_time_sec = kinetic_sec
        return self._integration_time_us
    
    def get_integration_time_limits_us(self):
        return (10, 1e9, 1)
    
    def set_integration_time_us(self, integration_time: int) -> int:
        """
        Set the integration time.  RunTillAbort is restarted automatically
        after the exposure time change so the new setting takes effect.
        """
        if not isinstance(integration_time, (int, float)):
            raise ValueError("Integration time must be a number")
        integration_time = int(integration_time)

        with self._lock:
            # Must stop acquisition before changing exposure time
            self._stop_continuous_acquisition()
            setExposureTime(integration_time * 1e-6)
            self._start_continuous_acquisition()
        
        self._integration_time_us = self.get_integration_time_us()
        return self._integration_time_us
    
    def measure_spectrum(self) -> tuple[pd.DataFrame, int, int]:
        """
        Measure a spectrum using the RunTillAbort circular buffer.

        The acquisition loop is started once during initialisation and kept
        running continuously.  Each call to measure_spectrum simply waits for
        the next completed frame and retrieves it with GetMostRecentImage,
        which avoids the per-frame StartAcquisition overhead that was
        preventing 30 Hz operation.

        Returns:
            tuple[pd.DataFrame, int, int]:
                - DataFrame with wavelength and intensity columns.
                - Timestamp of the measurement in microseconds (integer).
                - Integration time used in microseconds.
        """
        with self._lock:
            timestamp = get_timestamp_us_int()

            # Wait for one new frame.  Timeout = 1.5× the kinetic cycle time,
            # but at least 500 ms so a very short exposure never times out too fast.
            timeout_ms = max(500, int(self._theoretical_wait_time_sec * 1e3 * 1.5))
            frame_ready = waitForAcquisitionTimeOut(timeout_ms)
            if not frame_ready:
                raise TimeoutError(
                    f"No new frame arrived within {timeout_ms} ms "
                    f"(kinetic cycle = {self._theoretical_wait_time_sec*1e3:.1f} ms)"
                )

            # In FVB + RunTillAbort the SDK collapses all rows, so the result
            # is a 1-D array of length x_pixel stored as a (1 × x_pixel) image.
            image = getMostRecentImage(self._x_pixel, 1, self._x_pixel)
            intensity = image.reshape(-1)

        wavelength = np.arange(1, self._x_pixel + 1, dtype=float).tolist()
        intensity_list = intensity.astype(float).tolist()

        spectra = pd.DataFrame({
            DataAnalysisConfigEnum.WAVELENGTH_LABEL.value: wavelength,
            DataAnalysisConfigEnum.INTENSITY_LABEL.value: intensity_list,
        })
        return (spectra, timestamp, self._integration_time_us)
    
    def _test_save_last_measurement_as_sif(self, path: str) -> None:
        with self._lock:
            saveAsSif(path)


#%% Tests
if __name__ == "__main__":
    matplotlib.use('TkAgg')

    controller = SpectrometerController_Andor()
    controller._open_ex_shutter()
    
    int_time_us = int(100e3)   # 100 ms
    controller.set_integration_time_us(int_time_us)
    print(f"Integration time set to {controller.get_integration_time_us()/1e3:.1f} ms")

    # Throughput benchmark
    fig, ax = plt.subplots()
    t_start = time.time()
    count = 0
    while True:
        mea, _, _ = controller.measure_spectrum()
        count += 1
        elapsed = time.time() - t_start
        if elapsed >= 1.0:
            print(f"Throughput: {count / elapsed:.1f} frames/sec")
            count = 0
            t_start = time.time()

        ax.clear()
        ax.plot(mea[DataAnalysisConfigEnum.WAVELENGTH_LABEL.value],
                mea[DataAnalysisConfigEnum.INTENSITY_LABEL.value])
        fig.canvas.draw()
        fig.canvas.flush_events()
        if fig.waitforbuttonpress(1e-3): break

    controller.terminate()