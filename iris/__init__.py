import os
from enum import Enum

from .utils.general import read_update_config_file_section

dict_lib_default = {
    'spectrometer_calibration_path': '',
    'objective_calibration_directory': './calibrations/objectives/',
}

dict_lib_comments = {
    'spectrometer_calibration_path': 'Path to the spectrometer calibration file',
    'objective_calibration_directory': 'Path to the objective calibration directory',
}

dict_lib_read = read_update_config_file_section(
    dict_controllers_default=dict_lib_default,
    dict_controllers_comments=dict_lib_comments,
    section='LIBRARY',
)

for key in dict_lib_default.keys():
    if key.endswith('_path'):
        if dict_lib_read[key] == '': continue
        assert os.path.isfile(dict_lib_read[key]),\
            f"Error: {key} directory inserted in the config.ini file is invalid.\
            Please check the directory path and try again."
            
class LibraryConfigEnum(Enum):
    """
    Enum class for the app-wide configuration parameters.
    """
    SPECTROMETER_CALIBRATION_PATH = dict_lib_read['spectrometer_calibration_path']
    OBJECTIVE_CALIBRATION_DIR = dict_lib_read['objective_calibration_directory']
    
    SPECTROMETER_CALIBRATION_DIR_DEFAULT = './calibrations/spectrometers/'
    
############################################################################################################
# >>>>>> Data analysis specific parameters <<<<<<
############################################################################################################
dict_dataAnalysis_default = {
    # > Basic data analysis parameters <
    'laser_wavelength_nm': float(785),
    'similarity_threshold': 0.1,
    'laser_power_milliwatt': float(50),
    # > Labels <
    'wavelength_label': 'Wavelength [nm]',  # Label for the wavelength dataframe column and plot axis
    'intensity_label': 'Intensity [a.u.]',  # Label for the intensity dataframe column and plot axis
    'raman_shift_label': 'Raman Shift [cm^-1]', # Label for the Raman shift plot axis
}

dict_dataAnalysis_comments = {
    # > Basic data analysis parameters <
    'laser_wavelength_nm': 'Default value for the laser excitation wavelength in [nm] metadata',
    'similarity_threshold': 'Threshold for the similarity of the spectra for wavelength similarity check',
    'laser_power_milliwatt': 'Default value for the laser power in [mW] metadata',
    # > Labels <
    'wavelength_label': 'Label for the wavelength dataframe column and plot axis',
    'intensity_label': 'Label for the intensity dataframe column and plot axis',
    'raman_shift_label': 'Label for the Raman shift plot axis',
}

dict_dataAnalysis_read = read_update_config_file_section(
    dict_controllers_default=dict_dataAnalysis_default,
    dict_controllers_comments=dict_dataAnalysis_comments,
    section='DATA ANALYSIS',
)

class DataAnalysisConfigEnum(Enum):
    """
    Enum class for the app-wide configuration parameters.
    """
    # > Basic data analysis parameters <
    LASER_WAVELENGTH_NM = dict_dataAnalysis_read['laser_wavelength_nm']
    SIMILARITY_THRESHOLD = dict_dataAnalysis_read['similarity_threshold']
    LASER_POWER_MILLIWATT = dict_dataAnalysis_read['laser_power_milliwatt']
    # > Labels <
    WAVELENGTH_LABEL = dict_dataAnalysis_read['wavelength_label']
    INTENSITY_LABEL = dict_dataAnalysis_read['intensity_label']
    RAMANSHIFT_LABEL = dict_dataAnalysis_read['raman_shift_label']
    COORX_LABEL = 'coor_x'
    COORY_LABEL = 'coor_y'
    COORZ_LABEL = 'coor_z'
    ID_TIMESTAMP_LABEL = 'timestamp'
    LIST_MEA_LABEL = 'list_df'
    AVE_MEA_LABEL = 'averaged_df'