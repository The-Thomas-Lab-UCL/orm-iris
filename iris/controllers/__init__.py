"""
This module is used to import the correct controller classes based on the configuration file.
"""
################################################################################
# >>>>> Global variable setups <<<<<
################################################################################
import os
from enum import Enum

# Camera controller imports
if __name__ == '__main__':
    import sys
    SCRIPT_DIR = os.path.abspath(r'.\library')
    sys.path.insert(0, os.path.dirname(SCRIPT_DIR))


from iris.utils.general import read_update_config_file_section

dict_controller_options_default = {
    # > Simulation related <
    'simulation_mode': False,   # If True, the program will run in simulation mode
    # > Stage parameters <
    'stage_invertx': False,     # Flip the stage x-axis coordinate system direction
    'stage_inverty': False,     # Flip the stage y-axis coordinate system direction
    'stage_flipxy': False, # Flip the XY stage coordinate system
    # > Camera <
    'camera_index': 0,          # Index of the camera device to be used for capturing
    'videofeed_height': 250,    # Height of the video feed window
    'camera_mirrorx': False,    # Flip the video feed in the x-axis
    'camera_mirrory': False,    # Flip the video feed in the y-axis
    'scalebar_length_ratio': 0.2,   # Length of the scale bar in relation to the image width
    'scalebar_height_ratio': 0.045, # Height of the scale bar in relation to the image height
    'scalebar_font': 'arialbd.ttf', # Font of the scale bar. Default: 'arialbd.ttf' for Arial Bold
    'scalebar_font_ratio': 1.75,    # Font size of the scale bar in relation to the image width
    }


dict_controller_options_comments = {
    # > Simulation related <
    'simulation related': '\n# Simulation related',
    'simulation_mode': 'If True, the program will run in simulation mode',
    # > Stage parameters <
    'stage_invertx': 'Flip the stage x-axis coordinate system direction',
    'stage_inverty': 'Flip the stage y-axis coordinate system direction',
    'stage_flipxy': 'Flip the x and y axis of the XY stage coordinate system',
    # > Camera <
    'camera_index': 'Index of the camera device to be used for capturing',
    'videofeed_height': 'Height of the video feed window',
    'camera_mirrorx': 'Flip the video feed in the x-axis',
    'camera_mirrory': 'Flip the video feed in the y-axis',
    'scalebar_length_ratio': 'Length of the scale bar in relation to the image width',
    'scalebar_height_ratio': 'Height of the scale bar in relation to the image height',
    'scalebar_font': 'Font of the scale bar. Default: "arialbd.ttf" for Arial Bold',
    'scalebar_font_ratio': 'Font size of the scale bar in relation to the image width',
    }

dict_controller_options_read = read_update_config_file_section(
    dict_controllers_default=dict_controller_options_default,
    dict_controllers_comments=dict_controller_options_comments,
    section='CONTROLLER OPTIONS',
)

# > Controller choices <
dict_controller_choices = {
    'camera_controller': 'dummy',         # select between: 'dummy', 'webcam', 'thorlabs_mono', 'thorlabs_color'    
    'spectrometer_controller': 'dummy',   # select between: 'dummy', 'pi', 'qepro', 'andor', 'wasatch_enlighten'
    'stagexy_controller': 'dummy',        # select between: 'dummy', 'm30xym', 'zaber', 'pi'
    'stagez_controller': 'dummy',         # select between: 'dummy', 'z825b', 'mcm301', 'pfm450'
    }

# > Controller choices <
dict_controller_choices_comments = {
    'camera_controller': 'select between: "dummy", "webcam", "thorlabs_mono", "thorlabs_color"',
    'spectrometer_controller': 'select between: "dummy", "pi", "qepro", "andor", "wasatch_enlighten"',
    'stagexy_controller': 'select between: "dummy", "m30xym", "zaber", "pi"',
    'stagez_controller': 'select between: "dummy", "z825b", "mcm301", "pfm450"',
    }

dict_controller_choices_read = read_update_config_file_section(
    dict_controllers_default=dict_controller_choices,
    dict_controllers_comments=dict_controller_choices_comments,
    section='CONTROLLER CHOICES',
)

dict_controller_directions = {
    'xfwd': 'xfwd',
    'xrev': 'xrev',
    'yfwd': 'yfwd',
    'yrev': 'yrev',
    'zfwd': 'zfwd',
    'zrev': 'zrev',
    }

dict_controller_directions_comments = {
    'xfwd': 'Insert "xfwd", "xrev", "yfwd", or "yrev" to exchange the move direction button in the app GUI',
    'xrev': 'Insert "xfwd", "xrev", "yfwd", or "yrev" to exchange the move direction button in the app GUI',
    'yfwd': 'Insert "xfwd", "xrev", "yfwd", or "yrev" to exchange the move direction button in the app GUI',
    'yrev': 'Insert "xfwd", "xrev", "yfwd", or "yrev" to exchange the move direction button in the app GUI',
    'zfwd': 'Insert "zfwd" or "zrev" to exchange the move direction button in the app GUI',
    'zrev': 'Insert "zfwd" or "zrev" to exchange the move direction button in the app GUI',
    }

dict_controller_directions_read = read_update_config_file_section(
    dict_controllers_default=dict_controller_directions,
    dict_controllers_comments=dict_controller_directions_comments,
    section='CONTROLLER DIRECTION REMAP',
)

# >>> Set the enum for app-wide use <<<
class ControllerConfigEnum(Enum):
    """
    Configuration parameters for the controllers.
    """
    # > Simulation related <
    SIMULATION_MODE = dict_controller_options_read['simulation_mode']

    # > Stage parameters <
    STAGE_INVERTX = dict_controller_options_read['stage_invertx']
    STAGE_INVERTY = dict_controller_options_read['stage_inverty']
    STAGE_FLIPXY = dict_controller_options_read['stage_flipxy']

    # > Camera <
    CAMERA_INDEX = dict_controller_options_read['camera_index']
    VIDEOFEED_HEIGHT = dict_controller_options_read['videofeed_height']
    CAMERA_MIRRORX = dict_controller_options_read['camera_mirrorx']
    CAMERA_MIRRORY = dict_controller_options_read['camera_mirrory']
    SCALEBAR_LENGTH_RATIO = dict_controller_options_read['scalebar_length_ratio']
    SCALEBAR_HEIGHT_RATIO = dict_controller_options_read['scalebar_height_ratio']
    SCALEBAR_FONT = dict_controller_options_read['scalebar_font']
    SCALEBAR_FONT_RATIO = dict_controller_options_read['scalebar_font_ratio']
    
    # > Controller choices <
    CAMERA_CONTROLLER = dict_controller_choices_read['camera_controller']
    SPECTROMETER_CONTROLLER = dict_controller_choices_read['spectrometer_controller']
    STAGEXY_CONTROLLER = dict_controller_choices_read['stagexy_controller']
    STAGEZ_CONTROLLER = dict_controller_choices_read['stagez_controller']
    
class ControllerDirectionEnum(Enum):
    """
    Configuration parameters for the controller directions.
    """
    XFWD = dict_controller_directions_read['xfwd']
    XREV = dict_controller_directions_read['xrev']
    YFWD = dict_controller_directions_read['yfwd']
    YREV = dict_controller_directions_read['yrev']
    ZFWD = dict_controller_directions_read['zfwd']
    ZREV = dict_controller_directions_read['zrev']
    
    assert all([value in ['xfwd', 'xrev', 'yfwd', 'yrev', 'zfwd', 'zrev'] for value in [XFWD, XREV, YFWD, YREV, ZFWD, ZREV]]), 'Invalid controller direction remap value. Please check the configuration file.'
    assert len(set([XFWD, XREV, YFWD, YREV, ZFWD, ZREV])) == 6, 'Duplicate controller direction remap value. Please check the configuration file.'

################################################################################
# >>>>> Enum setup for specific controllers <<<<<
################################################################################
dict_controllerSpecific_default = {
    # > Ocean Insight spectrometer <
    'oceaninsight_api_dirpath': '', # Path to the Ocean Optics OceanDirect API module
    'oceaninsight_mode': 'continuous', # Select between "discrete" and "continuous" mode. "continuous" collects spectra consecutively without waiting for the "measure_spectrum()" to be called. Default: "continuous"
    # > PIXIS camera (Princeton Instrument) <
    'pixis_roi_row_min': '0', # Low value cutoff for the row ROI. Insert '' to specify the start of the sensor
    'pixis_roi_row_max': '10000', # High value cutoff for the row ROI. Insert '' to specify the end of the sensor
    'pixis_roi_col_min': '', # Low value cutoff for the column ROI. Insert '' to specify the start of the sensor
    'pixis_roi_col_max': '', # High value cutoff for the column ROI. Insert '' to specify the end of the sensor
    'pixis_roi_bin_row': 'max', # Number of binned rows. Insert 'max' to use the maximum possible value or 'min' to use the minimum possible value
    'pixis_roi_bin_col': 'min', # Number of binned columns. Insert 'max' to use the maximum possible value or 'min' to use the minimum possible value
    # > Thorlabs camera parameters <
    'thorlabs_camera_dll_path': '', # Path to the Thorlabs camera DLL
    'thorlabs_camera_exposure_time': 100, # Camera exposure time in [us], default: 10000
    'thorlabs_camera_framepertrigger': 0,   # Number of frames per trigger, default: 0 for continuous acquisition mode
    'thorlabs_camera_imagepoll_timeout': 1000,  # Timeout for the image polling in [ms], default: 1000
    # > Stage parameters <
    'm30xym_polling_interval': 250, # Polling interval for the M30XYM stage in [ms], default: 25
    'zaber_comport': '',    # COM (communication) port for the Zaber stage controller
    'pi_slow_comrate_ms': 50, # Slow communication rate for the PI stage in [ms]
    # > Andor camera parameters <
    'andor_atmcd64d_dll_path': '', # Path to the Andor camera DLL
    'andor_atspectrograph_dll_path': '', # Path to the Andor spectrograph DLL
    'andor_roi_row_min': 1, # Minimum row index for the region of interest (ROI) for the Andor camera
    'andor_roi_row_max': 10000, # Maximum row index for the region of interest (ROI) for the Andor camera
    'andor_roi_col_min': 1, # Minimum column index for the region of interest (ROI) for the Andor camera
    'andor_roi_col_max': 10000, # Maximum column index for the region of interest (ROI) for the Andor camera
    'andor_roi_bin_row': 10000, # Binning factor for the row axis for the Andor camera.
    'andor_roi_bin_col': 1, # Binning factor for the column axis for the Andor camera.
    'andor_operational_temperature': '', # Operational temperature for the Andor camera in degree Celcius. Set it to '' to disable temperature control (default)
    'andor_termination_temperature': '', # Termination temperature for the Andor camera in degree Celcius. Set it to '' to use the default termination temperature (default)
    # > PFM450 stage parameters <
    'pfm450_serial': '',    # Serial number of the PFM450 stage
    # > Physik Instrumente (PI) stage parameters <
    'pistage_serial': '',  # Serial number of the PI (Physik Instrumente) stage
    'pistage_autoreconnect_hours': 5.0, # Number of hours to wait before auto-resetting the connection with the PI stage
    'pistage_devtimestamp': True, # Option to (or not) use the device timestamp, which is more accurate but not all device has
    # > M30XYM stage parameters <
    'm30xym_serial': '',  # Serial number of the M30XYM stage
    # > Z825B stage parameters <
    'z825b_serial': '',  # Serial number of the Z825B stage
    # > Thorlabs MCM301 stage parameters <
    'mcm301_sdk_dirpath': r'C:\Program Files (x86)\Thorlabs\MCM301\Sample\Thorlabs_MCM301_PythonSDK',    # Dirpath to the MCM301 Thorlabs stage's Python SDK
    # > Wasatch Enlighten spectrometer parameters <
    'wasatch_laser_enable': True,  # Enable or disable the laser on the Wasatch spectrometer (through Englighten)
    'wasatch_laser_power_mw': 450,  # Set the laser power in [mW] for the Wasatch spectrometer (through Englighten)
}

dict_controllerSpecific_comments = {
    # > Ocean Insight spectrometer <
    'oceaninsight_api_dirpath': 'Path to the Ocean Optics OceanDirect API module',
    'oceaninsight_mode': 'Select between "discrete" and "continuous" mode. "continuous" collects spectra consecutively without waiting for the "measure_spectrum()" to be called. Default: "discrete"',
    # > PIXIS camera (Princeton Instrument) <
    'pixis_roi_row_min': 'Low value cutoff for the row ROI. Insert "" to specify the start of the sensor',
    'pixis_roi_row_max': 'High value cutoff for the row ROI. Insert "" to specify the end of the sensor',
    'pixis_roi_col_min': 'Low value cutoff for the column ROI. Insert "" to specify the start of the sensor',
    'pixis_roi_col_max': 'High value cutoff for the column ROI. Insert "" to specify the end of the sensor',
    'pixis_roi_bin_row': 'Number of binned rows. Insert "max" to use the maximum possible value or "min" to use the minimum possible value',
    'pixis_roi_bin_col': 'Number of binned columns. Insert "max" to use the maximum possible value or "min" to use the minimum possible value',
    # > Thorlabs camera parameters <
    'thorlabs_camera_dll_path': 'Path to the Thorlabs camera DLL',
    'thorlabs_camera_exposure_time': 'Camera exposure time in [us], default: 10000',
    'thorlabs_camera_framepertrigger': 'Number of frames per trigger, default: 0 for continuous acquisition mode',
    'thorlabs_camera_imagepoll_timeout': 'Timeout for the image polling in [ms], default: 1000',
    # > Stage parameters <
    'm30xym_polling_interval': 'Polling interval for the M30XYM stage in [ms], default: 25',
    'zaber_comport': 'COM (communication) port for the Zaber stage controller',
    'pi_slow_comrate_ms': 'Slow communication rate for the PI stage in [ms]',
    # > Andor camera parameters <
    'andor_atmcd64d_dll_path': 'Path to the Andor camera DLL',
    'andor_atspectrograph_dll_path': 'Path to the Andor spectrograph DLL',
    'andor_roi_row_min': 'Minimum row index for the region of interest (ROI) for the Andor camera',
    'andor_roi_row_max': 'Maximum row index for the region of interest (ROI) for the Andor camera',
    'andor_roi_col_min': 'Minimum column index for the region of interest (ROI) for the Andor camera',
    'andor_roi_col_max': 'Maximum column index for the region of interest (ROI) for the Andor camera',
    'andor_roi_bin_row': 'Binning factor for the row axis for the Andor camera',
    'andor_roi_bin_col': 'Binning factor for the column axis for the Andor camera',
    'andor_operational_temperature': 'Operational temperature for the Andor camera in degree Celcius. Set it to "" to disable temperature control (default)',
    'andor_termination_temperature': 'Termination temperature for the Andor camera in degree Celcius. Set it to "" to use the default termination temperature (default)',
    # > PFM450 stage parameters <
    'pfm450_serial': 'Serial number of the PFM450 stage',
    # > Physik Instrumente (PI) stage parameters <
    'pistage_serial': 'Serial number of the PI (Physik Instrumente) stage',
    'pistage_autoreconnect_hours': 'Number of hours to wait before auto-resetting the connection with the PI stage',
    'pistage_devtimestamp': 'Option to (or not) use the device timestamp, which is more accurate but not all device has',
    # > M30XYM stage parameters <
    'm30xym_serial': 'Serial number of the M30XYM stage',
    # > Z825B stage parameters <
    'z825b_serial': 'Serial number of the Z825B stage',
    # > Thorlabs MCM301 stage parameters <
    'mcm301_sdk_dirpath': "Dirpath to the MCM301 Thorlabs stage's Python SDK",
    # > Wasatch Enlighten spectrometer parameters <
    'wasatch_laser_enable': 'Enable or disable the laser on the Wasatch spectrometer (through Enlighten)',
    'wasatch_laser_power_mw': 'Set the laser power in [mW] for the Wasatch spectrometer (through Enlighten)',
}

dict_controllerSpecific_read = read_update_config_file_section(
    dict_controllers_default=dict_controllerSpecific_default,
    dict_controllers_comments=dict_controllerSpecific_comments,
    section='CONTROLLER SPECIFIC PARAMETERS',
)

class ControllerSpecificConfigEnum(Enum):
    """
    Configuration parameters for the specific controllers.
    """
    # > Ocean Insight spectrometer <
    OCEANINSIGHT_API_DIRPATH = dict_controllerSpecific_read['oceaninsight_api_dirpath']
    OCEANINSIGHT_MODE = dict_controllerSpecific_read['oceaninsight_mode']
    # > PIXIS camera <
    PIXIS_ROI_ROW_MIN = dict_controllerSpecific_read['pixis_roi_row_min']
    PIXIS_ROI_ROW_MAX = dict_controllerSpecific_read['pixis_roi_row_max']
    PIXIS_ROI_COL_MIN = dict_controllerSpecific_read['pixis_roi_col_min']
    PIXIS_ROI_COL_MAX = dict_controllerSpecific_read['pixis_roi_col_max']
    PIXIS_ROI_BIN_ROW = dict_controllerSpecific_read['pixis_roi_bin_row']
    PIXIS_ROI_BIN_COL = dict_controllerSpecific_read['pixis_roi_bin_col']
    # > Thorlabs camera parameters <
    THORLABS_CAMERA_DLL_PATH = dict_controllerSpecific_read['thorlabs_camera_dll_path']
    THORLABS_CAMERA_EXPOSURE_TIME = dict_controllerSpecific_read['thorlabs_camera_exposure_time']
    THORLABS_CAMERA_FRAMEPERTRIGGER = dict_controllerSpecific_read['thorlabs_camera_framepertrigger']
    THORLABS_CAMERA_IMAGEPOLL_TIMEOUT = dict_controllerSpecific_read['thorlabs_camera_imagepoll_timeout']
    # > Stage parameters <
    M30XYM_POLLING_INTERVAL = dict_controllerSpecific_read['m30xym_polling_interval']
    ZABER_COMPORT = dict_controllerSpecific_read['zaber_comport']
    PI_SLOW_COMRATE_MS = dict_controllerSpecific_read['pi_slow_comrate_ms']
    # > Andor camera parameters <
    ANDOR_ATMCD64D_DLL_PATH = dict_controllerSpecific_read['andor_atmcd64d_dll_path']
    ANDOR_ATSPECTROGRAPH_DLL_PATH = dict_controllerSpecific_read['andor_atspectrograph_dll_path']
    ANDOR_ROI_ROW_MIN = dict_controllerSpecific_read['andor_roi_row_min']
    ANDOR_ROI_ROW_MAX = dict_controllerSpecific_read['andor_roi_row_max']
    ANDOR_ROI_COL_MIN = dict_controllerSpecific_read['andor_roi_col_min']
    ANDOR_ROI_COL_MAX = dict_controllerSpecific_read['andor_roi_col_max']
    ANDOR_ROI_BIN_ROW = dict_controllerSpecific_read['andor_roi_bin_row']
    ANDOR_ROI_BIN_COL = dict_controllerSpecific_read['andor_roi_bin_col']
    ANDOR_OPERATIONAL_TEMPERATURE = dict_controllerSpecific_read['andor_operational_temperature']
    ANDOR_TERMINATION_TEMPERATURE = dict_controllerSpecific_read['andor_termination_temperature']
    # > PFM450 stage parameters <
    PFM450_SERIAL = dict_controllerSpecific_read['pfm450_serial']
    # > Physik Instrumente (PI) stage parameters <
    PISTAGE_SERIAL = dict_controllerSpecific_read['pistage_serial']
    PISTAGE_AUTORECONNECT_HOURS = dict_controllerSpecific_read['pistage_autoreconnect_hours']
    PISTAGE_DEVTIMESTAMP = dict_controllerSpecific_read['pistage_devtimestamp']
    # > M30XYM stage parameters <
    M30XYM_SERIAL = dict_controllerSpecific_read['m30xym_serial']
    # > Z825B stage parameters <
    Z825B_SERIAL = dict_controllerSpecific_read['z825b_serial']
    # > Thorlabs MCM301 stage parameters <
    MCM301_SDK_DIRPATH = dict_controllerSpecific_read['mcm301_sdk_dirpath']
    # > Wasatch Enlighten spectrometer parameters <
    WASATCH_LASER_ENABLE = dict_controllerSpecific_read['wasatch_laser_enable']
    WASATCH_LASER_POWER_MW = dict_controllerSpecific_read['wasatch_laser_power_mw']

################################################################################
# >>>>> Imports for the controllers <<<<<
################################################################################

import sys
import os
sys.path.append(os.path.dirname(ControllerSpecificConfigEnum.OCEANINSIGHT_API_DIRPATH.value))
sys.path.append(os.path.dirname(ControllerSpecificConfigEnum.MCM301_SDK_DIRPATH.value))

if ControllerConfigEnum.CAMERA_CONTROLLER.value == 'webcam':
    from .camera_controller_webcam import CameraController_Webcam as CameraController
elif ControllerConfigEnum.CAMERA_CONTROLLER.value == 'thorlabs_mono':
    from .camera_controller_thorlabs_mono import CameraController_ThorlabsMono as CameraController
elif ControllerConfigEnum.CAMERA_CONTROLLER.value == 'thorlabs_color':
    from .camera_controller_thorlabs_color import CameraController_ThorlabsColor as CameraController
else:
    if not ControllerConfigEnum.CAMERA_CONTROLLER.value == 'dummy':
        print(f'\n>>>>> Camera controller {ControllerConfigEnum.CAMERA_CONTROLLER.value} not available. Using dummy camera controller instead.')
    from .camera_controller_dummy import CameraController_Dummy as CameraController

# Spectrometer controller imports
if ControllerConfigEnum.SPECTROMETER_CONTROLLER.value == 'qepro':
    from .raman_spectrometer_controller_QEPro import SpectrometerController_QEPro as Controller_Spectrometer
elif ControllerConfigEnum.SPECTROMETER_CONTROLLER.value == 'pi_legacy':
    from .raman_spectrometer_controller_PI_pylablib import SpectrometerController_PI as Controller_Spectrometer
elif ControllerConfigEnum.SPECTROMETER_CONTROLLER.value == 'pi_dll':
    from .raman_spectrometer_controller_PI_dll import SpectrometerController_PI as Controller_Spectrometer
elif ControllerConfigEnum.SPECTROMETER_CONTROLLER.value == 'andor':
    from .raman_spectrometer_controller_Andor_pylablib import SectrometerController_AndorSDK2 as Controller_Spectrometer
elif ControllerConfigEnum.SPECTROMETER_CONTROLLER.value == 'wasatch_enlighten':
    from .raman_spectrometer_controller_WasatchEnlighten import SpectrometerController_WasatchEnlighten as Controller_Spectrometer
else:
    if not ControllerConfigEnum.SPECTROMETER_CONTROLLER.value == 'dummy':
        print(f'\n>>>>> Spectrometer controller {ControllerConfigEnum.SPECTROMETER_CONTROLLER.value} not available. Using dummy spectrometer controller instead.')
    from .raman_spectrometer_controller_dummy import SpectrometerController_Dummy as Controller_Spectrometer

# XY stage controller imports
if ControllerConfigEnum.STAGEXY_CONTROLLER.value == 'm30xym':
    from .xy_stage_controller_m30xy import XYController_M30XYM as Controller_XY
elif ControllerConfigEnum.STAGEXY_CONTROLLER.value == 'zaber':
    from .xy_stage_controller_zaber import XYController_Zaber as Controller_XY
elif ControllerConfigEnum.STAGEXY_CONTROLLER.value == 'pi':
    # from .xy_stage_controller_PI import XYController_PI as XYController
    from .xy_stage_controller_PI_dll import XYController_PI as Controller_XY
else:
    if not ControllerConfigEnum.STAGEXY_CONTROLLER.value == 'dummy':
        print(f'\n>>>>> XY stage controller {ControllerConfigEnum.STAGEXY_CONTROLLER.value} not available. Using dummy XY stage controller instead.')
    from .xy_stage_controller_dummy import XYController_Dummy as Controller_XY

# Z stage controller imports
if ControllerConfigEnum.STAGEZ_CONTROLLER.value == 'z825b':
    from .z_stage_controller_z825b import ZController_Z825B as Controller_Z
elif ControllerConfigEnum.STAGEZ_CONTROLLER.value == 'mcm301':
    from .z_stage_controller_mcm301 import ZController_MCM301 as Controller_Z
elif ControllerConfigEnum.STAGEZ_CONTROLLER.value == 'pfm450':
    from .z_stage_controller_pfm450 import ZController_PFM450 as Controller_Z
else:
    if not ControllerConfigEnum.STAGEZ_CONTROLLER.value == 'dummy':
        print(f'\n>>>>> Z stage controller {ControllerConfigEnum.STAGEZ_CONTROLLER.value} not available. Using dummy Z stage controller instead.')
    from .z_stage_controller_dummy import ZController_Dummy as Controller_Z