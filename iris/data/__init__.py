from enum import Enum
import os

from iris.utils.general import read_update_config_file_section

dict_save_params_default = {
    'database_id_key': "unit_id",   # Key for the measurement ID in the database
    'database_name_key': "unit_name",   # Key for the mappingUnit name in the database
    'default_save_path': r"./data out/",    # Main directory path for save data location prompt from root directory (where main controller.py is at)
    'default_save_ext': r".db", # ".db" or ".pkl" Default extension for the save files for mapping measurements
    'delete_pickle_post_measurement': True, # "True" or "False" Delete the pickle file after the mapping measurement is saved to a database
    # > Local database parameters <
    'imgunit_db_prefix': 'img_', # Prefix for the database table names for the ImageMeasurementUnit saves
    'mapunit_db_prefix': 'map_', # Prefix for the database table names for the MappingMeasurementUnit saves
    # > Save options <
    'default_save_ext': 'csv',  # Default save extension for the save files for mapping measurements. Choose between: "txt", "csv", "parquet", "feather"
    'autosave_interval_hours': 0.5,  # Interval in hours for autosaving the mapping measurements. If set to 0, autosaving is disabled.
}

dict_save_params_comments = {
    'database_id_key': 'Key for the measurement ID in the database',
    'database_name_key': 'Key for the mappingUnit name in the database',
    'default_save_path': 'Main path for save data location prompt from root directory (where main controller.py is at)',
    'default_save_ext': 'Default extension for the save files for mapping measurements',
    'delete_pickle_post_measurement': 'Delete the pickle file after the mapping measurement is saved to a database',
    # > Local database parameters <
    'imgunit_db_prefix': 'Prefix for the database table names for the ImageMeasurementUnit saves',
    'mapunit_db_prefix': 'Prefix for the database table names for the MappingMeasurementUnit saves',
    # > Save options <
    'default_save_ext': 'Default save extension for the save files for mapping measurements. Choose between: "txt", "csv", "parquet", "feather"',
    'autosave_interval_hours': 'Interval in hours for autosaving the mapping measurements. If set to 0, autosaving is disabled.',
}

dict_save_params_read = read_update_config_file_section(
    dict_controllers_default=dict_save_params_default,
    dict_controllers_comments=dict_save_params_comments,
    section='SAVE PARAMETERS',
)

class SaveParamsEnum(Enum):
    """
    Enum class for the app-wide data saving-realted configuration parameters.
    """
    DATABASE_ID_KEY = dict_save_params_read['database_id_key']
    DATABASE_NAME_KEY = dict_save_params_read['database_name_key']
    DEFAULT_SAVE_PATH = dict_save_params_read['default_save_path']
    DEFAULT_SAVE_EXT = dict_save_params_read['default_save_ext']
    DELETE_PICKLE_POST_MEASUREMENT = dict_save_params_read['delete_pickle_post_measurement']
    IMGUNIT_DB_PREFIX = dict_save_params_read['imgunit_db_prefix']
    MAPUNIT_DB_PREFIX = dict_save_params_read['mapunit_db_prefix']
    # > Save options <
    SAVE_OPTIONS_TXT = 'txt'
    SAVE_OPTIONS_CSV = 'csv'
    SAVE_OPTIONS_PARQUET = 'parquet'
    SAVE_OPTIONS_FEATHER = 'feather'
    SAVE_OPTIONS_DEFAULT = dict_save_params_read['default_save_ext']
    AUTOSAVE_INTERVAL_HOURS = dict_save_params_read['autosave_interval_hours']
    AUTOSAVE_ENABLED = AUTOSAVE_INTERVAL_HOURS > 0
    AUTOSAVE_DIRPATH_MEA = r'./autosave/measurements/'  # Default directory path for autosaving the mapping measurements
    AUTOSAVE_DIRPATH_COOR = r'./autosave/coordinates/'  # Default directory path for autosaving the mapping coordinates
    
    if not os.path.exists(AUTOSAVE_DIRPATH_MEA): os.makedirs(AUTOSAVE_DIRPATH_MEA)
    if not os.path.exists(AUTOSAVE_DIRPATH_COOR): os.makedirs(AUTOSAVE_DIRPATH_COOR)
    
dict_image_processing_params = {
    'low_resolution_scale': 0.1,  # Scale for low resolution images to be used for the displays (the full resolution images will always be saved)
}

dict_image_processing_params_comments = {
    'low_resolution_scale': 'Scale for low resolution images to be used for the displays (the full resolution images will always be saved)',
}

dict_image_processing_params_read = read_update_config_file_section(
    dict_controllers_default=dict_image_processing_params,
    dict_controllers_comments=dict_image_processing_params_comments,
    section='IMAGE PROCESSING PARAMETERS',
)
class ImageProcessingParamsEnum(Enum):
    """
    Enum class for the app-wide image processing-related configuration parameters.
    """
    LOW_RESOLUTION_SCALE = dict_image_processing_params_read['low_resolution_scale']
    
    if not 0<LOW_RESOLUTION_SCALE<1:
        LOW_RESOLUTION_SCALE = 0.1
        print(f"Warning: LOW_RESOLUTION_SCALE should be between 0 and 1. Setting to default value of {LOW_RESOLUTION_SCALE}.")