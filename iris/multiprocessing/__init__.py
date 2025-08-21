import os
from enum import Enum

# Camera controller imports
if __name__ == '__main__':
    import sys
    SCRIPT_DIR = os.path.abspath(r'.\library')
    sys.path.append(os.path.dirname(SCRIPT_DIR))


from iris.utils.general import read_update_config_file_section

dict_mpHub_default = {
    # > Maximum storage <
    'stagehub_maxstorage': 500,   # Maximum number of measurements stored in the stage measurement hub. Default: 500
    'ramanhub_maxstorage': 500,   # Maximum number of measurements stored in the Raman measurement hub. Default: 500
    # > Sampling interval and time offset between the stage and the stage measurement hub <
    'stagehub_maxinterval': 100,      # Maximum interval for between stage coordinate reportings in [ms]. Default: 100
    'stagehub_request_interval': 20,  # Interval for the stage measurement hub to request the stage position in [ms]. Default: 20
    'stagehub_time_offset_ms': 75,    # Time offset for the stage measurement hub in [ms] between the get_coordinate() request
}

dict_mpHub_comments = {
    # > Maximum storage <
    'stagehub_maxstorage': 'Maximum number of measurements stored in the stage measurement hub. Default: 500',
    'ramanhub_maxstorage': 'Maximum number of measurements stored in the Raman measurement hub. Default: 500',
    # > Sampling interval and time offset between the stage and the stage measurement hub <
    'stagehub_maxinterval': 'Maximum interval for between stage coordinate reportings in [ms]. Default: 100',
    'stagehub_request_interval': 'Interval for the stage measurement hub to request the stage position in [ms]. Default: 20',
    'stagehub_time_offset_ms': 'Time offset for the stage measurement hub in [ms] between the get_coordinate() request'
                               'and the retrieved coordinate, default: 75',
}

dict_mpHub_read = read_update_config_file_section(
    dict_controllers_default=dict_mpHub_default,
    dict_controllers_comments=dict_mpHub_comments,
    section='STAGE AND RAMAN MEASUREMENT HUB PARAMETERS',
)

# >>> Enum setup <<<
class MPMeaHubEnum(Enum):   # Short for Multiprocessing Measurement Hub Enum
    STAGEHUB_MAXSTORAGE = dict_mpHub_read['stagehub_maxstorage']
    RAMANHUB_MAXSTORAGE = dict_mpHub_read['ramanhub_maxstorage']
    STAGEHUB_MAXINTERVAL = dict_mpHub_read['stagehub_maxinterval']
    STAGEHUB_REQUEST_INTERVAL = dict_mpHub_read['stagehub_request_interval']
    STAGEHUB_TIME_OFFSET_MS = dict_mpHub_read['stagehub_time_offset_ms']