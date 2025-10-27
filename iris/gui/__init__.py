from enum import Enum
import os

from iris.utils.general import read_update_config_file_section

########################################################################################################################
# >>> Raman measurement related parameters <<<
########################################################################################################################

dict_appConfig_default = {
    'default_integration_time_ms': 50,    # Default integration time [millisec] set at startup
    'default_single_measurement_accumulation': 1,    # Default acquisition for the single measurements set at startup
    'default_continuous_measurement_accumulation': 1, # Default acquisition for the continuous measurements set at startup
    'continuous_measurement_buffer_size': 500,     # Number of allowable measurements in the queue before the entire process is paused for data processing
    'continuous_speed_modifier': 0.5, # Speed modifier for xy stage as it is performing the continuous measurements (final speed = speed * modifier)
    # > Autosave features <
    'autosave_freq_discreet': 50, # Autosave frequency for the discrete measurements coordinates (NOT the actual data!). e.g., 10 means the remaining unscanned coordinates are saved every 10 measurements
    'autosave_freq_continuous': 5, # Autosave frequency for the continuous measurements coordinates (NOT the actual data!). e.g., 10 means the remaining unscanned coordinates are saved every 10 measurements
}

dict_appConfig_comments = {
    'default_integration_time_ms': 'Default integration time [millisec] set at startup',
    'default_single_measurement_accumulation': 'Default acquisition for the single measurements set at startup',
    'default_continuous_measurement_accumulation': 'Default acquisition for the continuous measurements set at startup',
    'continuous_measurement_buffer_size': 'Number of allowable measurements in the queue before the entire process is paused for data processing',
    'continuous_speed_modifier': 'Speed modifier for xy stage as it is performing the continuous measurements (final speed = speed * modifier)',
    # > Autosave features <
    'autosave_freq_discreet': 'Autosave frequency for the discrete measurements coordinates (NOT the actual data!). e.g., 10 means the remaining unscanned coordinates are saved every 10 measurements',
    'autosave_freq_continuous': 'Autosave frequency for the continuous measurements coordinates (NOT the actual data!). e.g., 10 means the remaining unscanned coordinates are saved every 10 measurements',
}

dict_appConfig_read = read_update_config_file_section(
    dict_controllers_default=dict_appConfig_default,
    dict_controllers_comments=dict_appConfig_comments,
    section='APP - RAMAN MEASUREMENT CONTROLLER'
)

class AppRamanEnum(Enum):
    DEFAULT_INTEGRATION_TIME_MS = dict_appConfig_read['default_integration_time_ms']
    DEFAULT_SINGMEA_ACCUMULATION = dict_appConfig_read['default_single_measurement_accumulation']
    DEFAULT_CONTMEA_ACCUMULATION = dict_appConfig_read['default_continuous_measurement_accumulation']
    CONTINUOUS_MEASUREMENT_BUFFER_SIZE = dict_appConfig_read['continuous_measurement_buffer_size']
    CONTINUOUS_SPEED_MODIFIER = dict_appConfig_read['continuous_speed_modifier']
    # > Autosave features <
    TEMPORARY_FOLDER = r'./temp' # Temporary folder for the data acquisition
    AUTOSAVE_FREQ_DISCRETE = dict_appConfig_read['autosave_freq_discreet'] # Autosave frequency for the discrete measurements coordinates (NOT the actual data!). e.g., 10 means the remaining unscanned coordinates are saved every 10 measurements
    AUTOSAVE_FREQ_CONTINUOUS = dict_appConfig_read['autosave_freq_continuous'] # Autosave frequency for the continuous measurements coordinates (NOT the actual data!). e.g., 10 means the remaining unscanned coordinates are saved every 10 measurements
    
    if not os.path.exists(TEMPORARY_FOLDER):
        os.makedirs(TEMPORARY_FOLDER)
    
########################################################################################################################
# >>> Plotter parameters <<<
########################################################################################################################

from iris import DataAnalysisConfigEnum

dict_appPlot_default = {
    'plt_map_size_pixel_width': 300,          # Size of the mapping plot in pixels - width
    'plt_map_size_pixel_height': 300,          # Size of the mapping plot in pixels - height
    'plt_lbl_x_axis': 'X-coordinate [mm]',        # Label for the x-axis
    'plt_lbl_y_axis': 'Y-coordinate [mm]',        # Label for the y-axis
    'plt_lbl_intensity': DataAnalysisConfigEnum.INTENSITY_LABEL.value, # Label for the intensity axis
    'plt_lbl_title_prefix': 'Mapping: ',          # Prefix for the plot title
    'plt_colour_map': 'viridis',                      # Colour map for the plots
    'plt_shading': 'flat',                            # Shading for the plots
    'plt_edge_colour': 'k',                           # Colour for the edges of the plot points
    'plt_aspect': 'equal',                             # Aspect ratio for the plots
    'plt_size_1d_pixel_width': 255,      # Size of the 1D spectrum plot in pixels - width
    'plt_size_1d_pixel_height': 255,      # Size of the 1D spectrum plot in pixels - height
    'plt_size_1d_inch_width': 5,           # Size of the 1D spectrum plot in inches - width
    'plt_size_1d_inch_height': 5,           # Size of the 1D spectrum plot in inches - height
    'imgcal_showhints': True,  # Show hints on how to use the extension
    'imgcal_img_size_width': 300,  # Size of the image displayed on the canvas - width
    'imgcal_img_size_height': 250,  # Size of the image displayed on the canvas - height
    'display_coordinate_refresh_rate': 10, # Refresh rate for the display of the xyz-stage coordinates in [Hz]
    'map_method_image_video_width': 400, # Width of the image displayed in the mapping coordinate generation method (image and video based)
    'map_method_image_video_height': 300, # Height of the image displayed in the mapping coordinate generation method (image and video based)
}

dict_appPlot_comments = {
    'plt_map_size_pixel_width': 'Size of the mapping plot in pixels - width',
    'plt_map_size_pixel_height': 'Size of the mapping plot in pixels - height',
    'plt_lbl_x_axis': 'Label for the x-axis',
    'plt_lbl_y_axis': 'Label for the y-axis',
    'plt_lbl_intensity': 'Label for the intensity axis',
    'plt_lbl_title_prefix': 'Prefix for the plot title',
    'plt_colour_map': 'Colour map for the plots',
    'plt_shading': 'Shading for the plots',
    'plt_edge_colour': 'Colour for the edges of the plot points',
    'plt_aspect': 'Aspect ratio for the plots',
    'plt_size_1d_pixel_width': 'Size of the 1D spectrum plot in pixels - width',
    'plt_size_1d_pixel_height': 'Size of the 1D spectrum plot in pixels - height',
    'plt_size_1d_inch_width': 'Size of the 1D spectrum plot in inches - width',
    'plt_size_1d_inch_height': 'Size of the 1D spectrum plot in inches - height',
    'imgcal_showhints': 'Show hints toggle on how to use the image calibration tool',
    'imgcal_img_size_width': 'Size of the image displayed on the canvas - width',
    'imgcal_img_size_height': 'Size of the image displayed on the canvas - height',
    'display_coordinate_refresh_rate': 'Refresh rate for the display of the xyz-stage coordinates in [Hz]',
    'map_method_image_video_width': 'Width of the image displayed in the mapping coordinate generation method (image and video based)',
    'map_method_image_video_height': 'Height of the image displayed in the mapping coordinate generation method (image and video based)',
}

dict_appPlot_read = read_update_config_file_section(
    dict_controllers_default=dict_appPlot_default,
    dict_controllers_comments=dict_appPlot_comments,
    section='APP - PLOTTER'
)

class AppPlotEnum(Enum):
    # > Mapping plot parameters <
    PLT_MAP_SIZE_PIXEL = (dict_appPlot_read['plt_map_size_pixel_width'], dict_appPlot_read['plt_map_size_pixel_height'])
    PLT_LBL_X_AXIS = dict_appPlot_read['plt_lbl_x_axis']
    PLT_LBL_Y_AXIS = dict_appPlot_read['plt_lbl_y_axis']
    PLT_LBL_INTENSITY = dict_appPlot_read['plt_lbl_intensity']
    PLT_LBL_TITLE_PREFIX = dict_appPlot_read['plt_lbl_title_prefix']
    PLT_COLOUR_MAP = dict_appPlot_read['plt_colour_map']
    PLT_SHADING = dict_appPlot_read['plt_shading']
    PLT_EDGE_COLOUR = dict_appPlot_read['plt_edge_colour']
    PLT_ASPECT = dict_appPlot_read['plt_aspect']
    # > 1D spectrum plot parameters <
    PLT_SIZE_1D_PIXEL = (dict_appPlot_read['plt_size_1d_pixel_width'], dict_appPlot_read['plt_size_1d_pixel_height'])
    PLT_SIZE_1D_INCH = (dict_appPlot_read['plt_size_1d_inch_width'], dict_appPlot_read['plt_size_1d_inch_height'])
    # > Image calibration parameters <
    IMGCAL_SHOWHINTS = dict_appPlot_read['imgcal_showhints']
    IMGCAL_IMG_SIZE = (dict_appPlot_read['imgcal_img_size_width'], dict_appPlot_read['imgcal_img_size_height'])
    # > Coordinate related parameters <
    DISPLAY_COORDINATE_REFRESH_RATE = dict_appPlot_read['display_coordinate_refresh_rate']
    # > Mapping coordinate generation method parameters <
    MAP_METHOD_IMAGE_VIDEO_SIZE = (dict_appPlot_read['map_method_image_video_width'], dict_appPlot_read['map_method_image_video_height'])
    
########################################################################################################################
# >>> Video feed parameters <<<
########################################################################################################################

dict_appVideo_default = {
    'videofeed_refresh_rate': 15, # Refresh rate for the video feed in [Hz]
}

dict_appVideo_comments = {
    'videofeed_refresh_rate': 'Refresh rate for the video feed in [Hz]',
}

dict_appVideo_read = read_update_config_file_section(
    dict_controllers_default=dict_appVideo_default,
    dict_controllers_comments=dict_appVideo_comments,
    section='APP - VIDEO FEED'
)

class AppVideoEnum(Enum):
    VIDEOFEED_REFRESH_RATE = dict_appVideo_read['videofeed_refresh_rate']
    
########################################################################################################################
# >>> Shortcut configurations <<<
########################################################################################################################

# >>> Stage controller <<<
XY_UP = 'ctrl+i'              # Move xy-stage up
XY_DOWN = 'ctrl+k'            # Move xy-stage down
XY_LEFT = 'ctrl+j'            # Move xy-stage left
XY_RIGHT = 'ctrl+l'           # Move xy-stage right

Z_UP = 'ctrl+y'               # Move z-stage up
Z_DOWN = 'ctrl+h'             # Move z-stage down

XY_JOG_UP = 'ctrl+shift+i'    # Jog xy-stage up
XY_JOG_DOWN = 'ctrl+shift+k'  # Jog xy-stage down
XY_JOG_LEFT = 'ctrl+shift+j'  # Jog xy-stage left
XY_JOG_RIGHT = 'ctrl+shift+l' # Jog xy-stage right

Z_JOG_UP = 'ctrl+shift+y'     # Jog z-stage up
Z_JOG_DOWN = 'ctrl+shift+h'   # Jog z-stage down

XY_SPEED_UP = 'ctrl+='             # Increase xy-stage speed
XY_SPEED_DOWN = 'ctrl+-'           # Decrease xy-stage speed

Z_SPEED_UP = 'ctrl+]'              # Increase z-stage speed
Z_SPEED_DOWN = 'ctrl+['            # Decrease z-stage speed

JOG_MODE_SWITCH = 'ctrl+shift+m'  # Switch between jog and continuous modes

dict_shortcuts_default = {
    'xy_up': 'ctrl+i',              # Move xy-stage up
    'xy_down': 'ctrl+k',            # Move xy-stage down
    'xy_left': 'ctrl+j',            # Move xy-stage left
    'xy_right': 'ctrl+l',           # Move xy-stage right
    
    'z_up': 'ctrl+y',               # Move z-stage up
    'z_down': 'ctrl+h',             # Move z-stage down
    
    'xy_jog_up': 'ctrl+w',      # Jog xy-stage up
    'xy_jog_down': 'ctrl+s',    # Jog xy-stage down
    'xy_jog_left': 'ctrl+a',    # Jog xy-stage left
    'xy_jog_right': 'ctrl+d',   # Jog xy-stage right
    
    'z_jog_up': 'ctrl+r',     # Jog z-stage up
    'z_jog_down': 'ctrl+f',   # Jog z-stage down
    
    'xy_speed_up': 'ctrl+=',             # Increase xy-stage speed
    'xy_speed_down': 'ctrl+-',           # Decrease xy-stage speed
    
    'z_speed_up': 'ctrl+]',              # Increase z-stage speed
    'z_speed_down': 'ctrl+[',            # Decrease z-stage speed
    
    'jog_mode_switch': 'ctrl+shift+m',  # Switch between jog and continuous modes
}

dict_shortcuts_comments = {
    'xy_up': 'Move xy-stage up',
    'xy_down': 'Move xy-stage down',
    'xy_left': 'Move xy-stage left',
    'xy_right': 'Move xy-stage right',
    
    'z_up': 'Move z-stage up',
    'z_down': 'Move z-stage down',
    
    'xy_jog_up': 'Jog xy-stage up',
    'xy_jog_down': 'Jog xy-stage down',
    'xy_jog_left': 'Jog xy-stage left',
    'xy_jog_right': 'Jog xy-stage right',
    
    'z_jog_up': 'Jog z-stage up',
    'z_jog_down': 'Jog z-stage down',
    
    'xy_speed_up': 'Increase xy-stage speed',
    'xy_speed_down': 'Decrease xy-stage speed',
    
    'z_speed_up': 'Increase z-stage speed',
    'z_speed_down': 'Decrease z-stage speed',
    
    'jog_mode_switch': 'Switch between jog and continuous modes',
}

dict_shortcuts_read = read_update_config_file_section(
    dict_controllers_default=dict_shortcuts_default,
    dict_controllers_comments=dict_shortcuts_comments,
    section='SHORTCUTS',
    config_file='config_shortcuts.ini'
)

class ShortcutsEnum(Enum):
    XY_UP = dict_shortcuts_read['xy_up']
    XY_DOWN = dict_shortcuts_read['xy_down']
    XY_LEFT = dict_shortcuts_read['xy_left']
    XY_RIGHT = dict_shortcuts_read['xy_right']
    
    Z_UP = dict_shortcuts_read['z_up']
    Z_DOWN = dict_shortcuts_read['z_down']
    
    XY_JOG_UP = dict_shortcuts_read['xy_jog_up']
    XY_JOG_DOWN = dict_shortcuts_read['xy_jog_down']
    XY_JOG_LEFT = dict_shortcuts_read['xy_jog_left']
    XY_JOG_RIGHT = dict_shortcuts_read['xy_jog_right']
    
    Z_JOG_UP = dict_shortcuts_read['z_jog_up']
    Z_JOG_DOWN = dict_shortcuts_read['z_jog_down']
    
    XY_SPEED_UP = dict_shortcuts_read['xy_speed_up']
    XY_SPEED_DOWN = dict_shortcuts_read['xy_speed_down']
    
    Z_SPEED_UP = dict_shortcuts_read['z_speed_up']
    Z_SPEED_DOWN = dict_shortcuts_read['z_speed_down']

    JOG_MODE_SWITCH = dict_shortcuts_read['jog_mode_switch']