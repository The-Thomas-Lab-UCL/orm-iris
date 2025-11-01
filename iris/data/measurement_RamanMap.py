"""
This module provides structured data management and analysis capabilities for mapping measurements.
"""
from tkinter import filedialog
import platform

import os
import gc
import numpy as np
import pandas as pd
from copy import deepcopy

import threading
import queue

import dill
import sqlite3 as sql
import json
import uuid
from typing import Callable, Self
from enum import Enum

import matplotlib
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.colorbar import Colorbar
import matplotlib.pyplot as plt
# matplotlib.use('Agg')

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))
    

from iris.utils.general import *
from iris.data.measurement_Raman import MeaRaman

from iris import DataAnalysisConfigEnum as DAEnum
from iris.data import SaveParamsEnum
from iris.gui import AppPlotEnum

class MeaRMap_Unit():
    """
    This is a class to store a list of measurement data during a mapping measurement.
    Essentially, it's a subunit of the mapping_measurement class.
    Use case:
    - To store a list of raw measurement from a mapping measurement
    - To store a list calibration/background measurements
    - To store a list of analysed dataframes
    
    A mapping_measurement_unit object can then be appended to a mapping_measurement object,
    which keeps track of the collection of mapping_measurement_unit objects.
    """
    def __init__(self, unit_name='raw_measurement', unit_id:str|None=None, extra_metadata:dict={}) -> None:
        # Make sure that mea_id is a valid name for a database table
        assert isinstance(unit_name, str), 'mapping_measurement_unit: The input data type is not correct. Expected a string.'
        assert isinstance(extra_metadata, dict), 'mapping_measurement_unit: The input data type is not correct. Expected a dictionary.'
        if unit_id is None: unit_id = uuid.uuid4().hex
        else: unit_id = unit_id; assert unit_id.isidentifier, 'mapping_measurement_unit: The input unit_id is not a valid identifier.'
        
        self._version = '0.1.0-2024.05.24'  # Version of the data storage format
        self._unit_id = unit_id             # Measurement unit ID to be used for the database
        self._unit_name = unit_name         # Measurement name (e.g., 'raw_measurement', 'calibration', 'background', 'analysed-1', etc.)
        self._unit_id_key = SaveParamsEnum.DATABASE_ID_KEY.value # Key for the measurement ID in the metadata dictionary
        self._unit_name_key = SaveParamsEnum.DATABASE_NAME_KEY.value # Key for the measurement name in the metadata dictionary
        self._mea_id_key = DAEnum.ID_TIMESTAMP_LABEL.value      # Key for the measurement timestamp in the measurement dictionary
        
        # Parameters for the database storage
        self._flg_measurement_exist = False   # Flag to check if the measurement data exists
        self._flg_metadata_exist = False     # Flag to check if the metadata exists
        
        # Additional attributes for ease of use in other programs (for reference during plotting)
        self._label_ts = DAEnum.ID_TIMESTAMP_LABEL.value    # Timestamp column name for the dictionary
        self._label_x = DAEnum.COORX_LABEL.value            # X-coordinate column name for the dictionary
        self._label_y = DAEnum.COORY_LABEL.value            # Y-coordinate column name for the dictionary
        self._label_z = DAEnum.COORZ_LABEL.value            # Z-coordinate column name for the dictionary
        self._label_listmea = DAEnum.LIST_MEA_LABEL.value   # Key for the list of raw dataframes in the measurement dictionary
        self._label_avemea = DAEnum.AVE_MEA_LABEL.value     # Key for the averaged dataframe in the measurement dictionary
        
        # Column names to access the pd.DataFrame values
        self._dflabel_wavelength = DAEnum.WAVELENGTH_LABEL.value    # Wavelength column name corresponding to the dataframe of the measurements
        self._dflabel_intensity = DAEnum.INTENSITY_LABEL.value      # Intensity column name corresponding to the dataframe of the measurements
        
        self._extra_metadata = extra_metadata   # Extra metadata to be stored in the measurement unit
        self._dict_metadata = {
            self._unit_id_key: self._unit_id,
            self._unit_name_key: unit_name,
            'measurement_metadata': extra_metadata.copy()
        }
        
        self._dict_metadata_types = {   # Type definition for loading the metadata from the database
            self._unit_id_key: str,
            self._unit_name_key: str,
            'measurement_metadata': dict
        }
        
        assert all([key in self._dict_metadata_types.keys() for key in self._dict_metadata.keys()]),\
            'mapping_measurement_unit: The metadata keys are not the same as the metadata types.'
        
        # Measurement data storage
        self._dict_measurement = {
            self._label_ts: [],
            self._label_x: [],
            self._label_y: [],
            self._label_z: [],
            self._label_listmea: [],      # List of raw dataframes in an accumulation (e.g., background measurements may require multiple acquisitions)
            self._label_avemea: []   # Averaged dataframe from 'list_df'
        }
        
        self._dict_measurement_types = {    # Type definition for loading the measurement data from the database
            self._label_ts: int,
            self._label_x: float,
            self._label_y: float,
            self._label_z: float,
            self._label_listmea: list[pd.DataFrame],  # !!! Note that list_df can also be None !!!
            self._label_avemea: pd.DataFrame
        }
        
        self._lock_measurement = threading.Lock()
        
        assert all([key in self._dict_measurement_types.keys() for key in self._dict_measurement.keys()]),\
            'mapping_measurement_unit: The measurement keys are not the same as the measurement types.'
        
        # Observer setup
        self._list_observers = []
        
    def get_laser_params(self) -> tuple[float,float]:
        """
        Returns the laser wavelength and power metadata
        
        Returns:
            tuple: laser power, laser wavelength
        """
        if not self._flg_metadata_exist: raise ValueError('get_laser_metadata: The metadata does not exist.')
        metadata = self.get_dict_measurement_metadata()
        power_key,wavelength_key = MeaRaman(reconstruct=True).get_laserMetadata_key()
        return (metadata[power_key],metadata[wavelength_key])
        
    def get_measurementId_from_coor(self, coor:tuple[float,float]):
        """
        Retrieves the measurement ID from the coordinates closest to the given coordinates.
        
        Args:
            coor (tuple[float,float]): coordinates to retrieve the ID from. (x,y)
        
        Returns:
            str: measurement ID
        """
        assert isinstance(coor,tuple), 'Coordinates should be in a tuple'
        assert len(coor) == 2, 'Coordinates should be in a tuple of 2 elements'
        assert all([isinstance(val,(float,int)) for val in coor]), 'Coordinates should be in float or integer'
        
        list_coor = list(zip(self._dict_measurement[self._label_x],self._dict_measurement[self._label_y]))
        list_dist = [np.linalg.norm(np.array(coor)-np.array(c)) for c in list_coor]
        idx_min = np.argmin(list_dist)
        
        return self._dict_measurement[self._mea_id_key][idx_min]
        
    def get_keys_dict_measurement(self) -> tuple[str,str,str,str,str,str]:
        """
        Returns the keys for the measurement data stored in the object
        
        Returns:
            tuple: keys for the timestamp, x, y, z, list_df, and averaged_df
        """
        return (self._mea_id_key,self._label_x,self._label_y,self._label_z,self._label_listmea,self._label_avemea)
        
    def get_key_measurementId(self) -> str:
        """
        Returns the key storing the id for the Raman measurement stored in the measurement dictionary
        """
        return self._mea_id_key
        
    def set_dict_metadata(self,measurementUnit_metadata:dict):
        """
        Sets the metadata for the measurement analysis
        
        Args:
            measurementUnit_metadata (dict): dictionary of the metadata
        """
        # For compatibility with previous versions
        if self._unit_name_key not in measurementUnit_metadata.keys() and self._unit_id_key in measurementUnit_metadata.keys():
            measurementUnit_metadata[self._unit_name_key] = measurementUnit_metadata[self._unit_id_key]
        
        # Check the input data type
        assert isinstance(measurementUnit_metadata, dict), 'set_unit_metadata: The input data type is not correct. Expected a dictionary.'
        assert all([key in measurementUnit_metadata.keys() for key in self._dict_metadata.keys()]),\
            'set_unit_metadata: The metadata keys are not the same as the metadata types.'
            
        self._set_measurement_metadata(measurementUnit_metadata['measurement_metadata'])
        self._unit_id = measurementUnit_metadata[self._unit_id_key]
        self._unit_name = measurementUnit_metadata[self._unit_name_key]
        
        if self.check_measurement_and_metadata_exist(): self._notify_observers()
        
    def set_dict_measurements(self,dict_measurement:dict):
        """
        Sets the measurement data stored in the object.
        
        Args:
            dict_measurement (dict): dictionary of the measurement data
        """
        assert isinstance(dict_measurement, dict), 'set_dict_measurements: The input data type is not correct. Expected a dictionary.'
        assert all([key in dict_measurement.keys() for key in self._dict_measurement.keys()]),\
            'set_dict_measurements: The input dictionary keys are not the same as the stored data keys.'
        
        self._dict_measurement = dict_measurement
        self._flg_measurement_exist = True
        
        if self.check_measurement_and_metadata_exist(): self._notify_observers()
        
    def get_dict_measurements(self) -> dict:
        """
        Returns the measurement data stored in the object.
        
        Returns:
            dict: dictionary of the measurement data
        """
        return self._dict_measurement
        
    def get_dict_types(self) -> tuple[dict,dict]:
        """
        Returns the dictionary of the data types stored in the class
        
        Returns:
            tuple: dictionary of the metadata types, dictionary of the measurement types
        """
        return (self._dict_metadata_types, self._dict_measurement_types)
        
    def check_measurement_and_metadata_exist(self):
        """
        Check if the measurement data and metadata exist
        """
        # Note: KeyError and AttributeError are bypassed as there are cases where the object (self)
        # itself have been deleted but the reference to it still remains in other parts of the program
        # This would typically trigger KeyError as self._dict_measurement becomes empty. An example of
        # This issue happens with the heatmap plotter when a unit currently being plot is suddenly
        # deleted in the mappingHub (e.g., through the dataHub gui).
        try:
            if len(self._dict_measurement[self._label_ts]) == 0: self._flg_measurement_exist = False
        except (KeyError, AttributeError): self._flg_measurement_exist = False
        
        try:
            if len(self._dict_metadata) == len(self._extra_metadata): self._flg_metadata_exist = False
        except (KeyError, AttributeError): self._flg_metadata_exist = False
        
        return self._flg_measurement_exist and self._flg_metadata_exist
        
    def set_unitName(self,unit_name:str):
        """
        Sets the measurement unit name
        
        Args:
            unit_name (str): measurement unit name
        """
        assert isinstance(unit_name, str), 'set_unit_id: The input data type is not correct. Expected a string.'
        
        self._unit_name = unit_name
        self._dict_metadata[self._unit_name_key] = unit_name
        
        if self.check_measurement_and_metadata_exist(): self._notify_observers()
        
    def set_unitName_and_unitID(self,unit_name:str, unit_id:str|None=None):
        """
        Sets the measurement unit name and resets the measurement unit id
        
        Args:
            unit_name (str): measurement unit name
            unit_id (str|None): measurement unit id. A new UUID will be generated if None
        """
        assert isinstance(unit_name, str), 'set_unit_id: The input data type is not correct. Expected a string.'
        
        self._unit_name = unit_name
        self._dict_metadata[self._unit_name_key] = unit_name
        
        if not isinstance(unit_id, str): unit_id = uuid.uuid4().hex
        self._unit_id = unit_id
        self._dict_metadata[self._unit_id_key] = self._unit_id

        if self.check_measurement_and_metadata_exist(): self._notify_observers()

    def get_unit_name(self) -> str:
        """
        Returns the measurement unit name
        
        Returns:
            str: measurement unit name
        """
        return self._unit_name
        
    def get_unit_id(self) -> str:
        """
        Returns the measurement unit id

        Returns:
            str: measurement unit id
        """
        return self._unit_id

    def get_numMeasurements(self) -> int:
        """
        Returns the number of measurements stored in the object.
        
        Returns:
            int: number of measurements
        """
        return len(self._dict_measurement[self._label_ts])
    
    def get_dict_measurement_metadata(self) -> dict:
        """
        Returns the measurement metadata of the object.
        
        Returns:
            dict: measurement metadata dictionary
        """
        return self._dict_metadata['measurement_metadata']
    
    def get_dict_unit_metadata(self) -> dict:
        """
        Returns the measurement unit id and metadata of the object.
        
        Returns:
            dict: measurement unit metadata dictionary
        """
        return self._dict_metadata
        
    def generate_unit_metadata(self, unit_id:str|None=None, unit_name:str|None=None) -> dict:
        """
        Generates a new unit metadata dictionary based on the this unit's metadata but,
        with a new unit_id and unit_name.
        
        Args:
            unit_id (str|None): new unit ID to be used. If None, a new UUID will be generated.
            unit_name (str|None): new unit name to be used. If None, the unit_name will be set to 'unit_name_copy'.
        
        Returns:
            dict: new unit metadata dictionary with a new unit_id and unit_name
        """
        new_unit_metadata = {}
        
        if unit_id is None: unit_id = uuid.uuid4().hex
        if unit_name is None: unit_name = f'{self._unit_name}_copy'
        
        new_unit_metadata[self._unit_id_key] = unit_id
        new_unit_metadata[self._unit_name_key] = unit_name
        
        for key in self._dict_metadata.keys():
            if key not in [self._unit_id_key, self._unit_name_key]:
                new_unit_metadata[key] = deepcopy(self._dict_metadata[key])
        
        return new_unit_metadata
        
    def _set_measurement_metadata(self,measurement_metadata:dict):
        """
        Sets the metadata for the measurement analysis
        
        Args:
            measurement_metadata (dict): dictionary of the metadata
        
        Note:
            Will raise an error if the given metadata is different from the stored metadata.
        """
        assert isinstance(measurement_metadata, dict), 'set_metadata: The input data type is not correct. Expected a dictionary.'
        
        if not self._flg_metadata_exist:
            self._dict_metadata['measurement_metadata'].update(measurement_metadata)
            self._flg_metadata_exist = True
        else:
            assert all([key in self._dict_metadata['measurement_metadata'].keys() for key in measurement_metadata.keys()]),\
                'set_metadata: The input metadata is different from the stored metadata.'
            assert all([val == self._dict_metadata['measurement_metadata'][key] for key,val in measurement_metadata.items()]),\
                'set_metadata: The input metadata is different from the stored metadata.'
                
    def append_dict_measurement_data(self,dict_measurement:dict):
        """
        Appends the measurement data into the list of stored measurements.
        
        Args:
            dict_measurement (dict): dictionary of the measurement data. Has to have the same keys as the stored data.
        """
        assert isinstance(dict_measurement, dict), 'append_dict_measurement_data: The input data type is not correct. Expected a dictionary.'
        assert all([key in dict_measurement.keys() for key in self._dict_measurement.keys()]),\
            'append_dict_measurement_data: The input dictionary keys are not the same as the stored data keys.'
            
        for key in dict_measurement.keys():
            self._dict_measurement[key].append(dict_measurement[key])
            
        self._flg_measurement_exist = True
        
        self._notify_observers()
        
    def append_ramanmeasurement_data(self,timestamp:int,coor:tuple[float,float,float],measurement:MeaRaman):
        """
        Appends the measurement data into the list of stored measurements.
        
        Args:
            timestamp (int): timestamp of the measurement
            coor (tuple): coordinates of the measurement
            measurement (raman_measurement): raman measurement data object to be stored
            autoupdate (bool): automatically update the averaged_df based on the current 'list_df'. Defaults to False.
        """
        assert isinstance(measurement, MeaRaman), 'append_measurement_data: The input data type is not correct. Expected raman_measurement object.'
        assert isinstance(coor, tuple) and len(coor) == 3, 'append_measurement_data: The input coordinate is not correct. Expected a tuple of length 3.'
        assert all(isinstance(item, (int,float)) for item in coor), 'append_measurement_data: The input coordinate is not correct. Expected a tuple of integers or floats.'
        assert isinstance(timestamp, int), 'append_measurement_data: The input timestamp is not correct. Expected an integer.'
        assert measurement.check_measurement_exist(), 'append_measurement_data: The measurement data does not exist.'
        assert timestamp not in self._dict_measurement[self._label_ts], 'append_measurement_data: The timestamp already exists in the stored data.'
        
        # Check if the measurement metadata is the same as the stored metadata
        measurement_metadata = measurement.get_metadata()
        if not self._flg_metadata_exist: self._set_measurement_metadata(measurement_metadata)
        elif not all([key in measurement_metadata.keys() for key in self._dict_metadata['measurement_metadata'].keys()]) and \
            not all([val == self._dict_metadata['measurement_metadata'][key] for key,val in measurement_metadata.items()]):
            raise ValueError('append_measurement_data: The measurement metadata does not match the stored metadata.')
        
        with self._lock_measurement:
            self._dict_measurement[self._label_ts].append(timestamp)
            self._dict_measurement[self._label_x].append(coor[0])
            self._dict_measurement[self._label_y].append(coor[1])
            self._dict_measurement[self._label_z].append(coor[2])
            self._dict_measurement[self._label_listmea].append(measurement.get_raw_list())
            self._dict_measurement[self._label_avemea].append(measurement.get_analysed())
        
        self._flg_measurement_exist = True
        
        self._notify_observers()
        
    def append_dfmeasurement_data(self,timestamp:str,coor:tuple[float,float,float],measurement_df:pd.DataFrame,
                                  list_df:list[pd.DataFrame]|None=None):
        """
        Appends the measurement data into the list of stored measurements.
        
        Args:
            timestamp (str): timestamp of the measurement
            coor (tuple): coordinates of the measurement
            measurement_df (pd.DataFrame): measurement df to be stored
            list_df (list): list of raw dataframes of the measurement. Defaults to None.
        """
        assert isinstance(measurement_df, pd.DataFrame), 'append_measurement_data: The input data type is not correct. Expected a pandas.DataFrame.'
        assert isinstance(coor, tuple) and len(coor) == 3, 'append_measurement_data: The input coordinate is not correct. Expected a tuple of length 3.'
        assert all(isinstance(item, (int,float)) for item in coor), 'append_measurement_data: The input coordinate is not correct. Expected a tuple of integers or floats.'
        assert isinstance(timestamp, str), 'append_measurement_data: The input timestamp is not correct. Expected a string.'
        
        with self._lock_measurement:
            if list_df is not None:
                assert isinstance(list_df, list), 'append_measurement_data: The input list_df is not correct. Expected a list of pandas.DataFrame objects.'
                assert all(isinstance(item, pd.DataFrame) for item in list_df), 'append_measurement_data: The input list_df is not correct. Expected a list of pandas.DataFrame objects.'
                self._dict_measurement[self._label_listmea].append(list_df)
            else:
                self._dict_measurement[self._label_listmea].append(None)
            self._dict_measurement[self._label_ts].append(timestamp)
            self._dict_measurement[self._label_x].append(coor[0])
            self._dict_measurement[self._label_y].append(coor[1])
            self._dict_measurement[self._label_z].append(coor[2])
            self._dict_measurement[self._label_avemea].append(measurement_df)
        
        self._flg_measurement_exist = True
        
        self._notify_observers()
        
    def get_RamanMeasurement_df_fromIdx(self,idx:int) -> pd.DataFrame:
        """
        Grabs the averaged dataframe stored
        
        Args:
            idx (int): index of the measurement
        
        Returns:
            pd.DataFrame: averaged dataframe of the measurement
        """
        assert self._flg_measurement_exist, 'get_avg_df: The measurement data does not exist.'
        assert 0<=idx < len(self._dict_measurement[self._label_ts]), 'get_avg_df: The index is out of range.'
        
        df = self._dict_measurement[self._label_avemea][idx]
        
        return df
        
    def get_dict_RamanMeasurement_summary(self,measurement_id:int|str,exclude_id:bool=False) -> dict:
        """
        Returns the summary of the measurement data stored in the object.
        Summarises the measurement data based on the measurement_id and returns
        all the data in a dictionary that is either a string, integer, or float.
        
        Args:
            measurement_id (int|str): timestamp of the measurement in microsec in int or str format
            exclude_id (bool): exclude the measurement ID from the summary. Defaults to False.
        
        Returns:
            dict: dictionary of the measurement data
        """
        if isinstance(measurement_id,str): measurement_id = int(float(measurement_id))
        assert measurement_id in self._dict_measurement[self._mea_id_key], 'get_summary: The measurement ID does not exist in the stored data.'
        assert self._flg_measurement_exist, 'get_summary: The measurement data does not exist.'
        assert isinstance(exclude_id,bool), 'get_summary: The input data type is not correct. Expected a boolean.'
        
        dict_mea = {}
        mea_idx = self._dict_measurement[self._mea_id_key].index(measurement_id)
        for key in self._dict_measurement.keys():
            item = self._dict_measurement[key][mea_idx]
            if exclude_id and key == self._mea_id_key: continue
            if isinstance(item,(str,int,float)):
                dict_mea[key] = str(item)
        return dict_mea
        
    def get_RamanMeasurement(self,measurement_id:int|str) -> MeaRaman:
        """
        Retrieves the measurement dataframe from the stored data, reconstruct
        the RamanMeasurement object, and returns it.
        
        Args:
            measurement_id (int|str): timestamp of the measurement in microsec in int or str format
        
        Returns:
            RamanMeasurement: reconstructed RamanMeasurement object
        """
        assert isinstance(measurement_id,(int,str)), 'get_RamanMeasurement: The input data type is not correct. Expected an integer or a string of integer.'
        if isinstance(measurement_id,str):
            try: measurement_id = int(float(measurement_id))
            except: raise ValueError('get_RamanMeasurement: The measurement ID is not an integer.')
        assert measurement_id in self._dict_measurement[self._mea_id_key],\
            'get_RamanMeasurement: The requested measurement does not exist in the stored data.'
            
        mea_df = self.get_RamanMeasurement_df(measurement_id)
        mea_metadata = self.get_dict_measurement_metadata()
        mea = MeaRaman(reconstruct=True)
        mea.reconstruct(measurement_id=measurement_id,metadata=mea_metadata,spec_analysed=mea_df)
        return mea
        
    def get_RamanMeasurement_df(self,measurement_id:int) -> pd.DataFrame:
        """
        Grabs the averaged dataframe stored
        
        Args:
            measurement_id (int): measurement_id of the measurement
        
        Returns:
            pd.DataFrame: averaged dataframe of the measurement
        """
        assert self._flg_measurement_exist, 'get_avg_df: The measurement data does not exist.'
        assert measurement_id in self._dict_measurement[self._mea_id_key], 'get_avg_df: The timestamp does not exist in the stored data.'
        
        idx = self._dict_measurement[self._mea_id_key].index(measurement_id)
        df = self._dict_measurement[self._label_avemea][idx]
        
        return df
        
    def get_list_RamanMeasurement_ids(self) -> list:
        """
        Returns the list of timestamps stored in the measurement data
        
        Returns:
            list: list of timestamps
        """
        return self._dict_measurement[self._label_ts]
    
    def get_list_wavelengths(self) -> list[float]:
        """
        Returns the list of wavelengths stored in the measurement data
        
        Returns:
            list: list of wavelengths
        """
        # assert self._flg_measurement_exist, 'get_list_wavelengths: The measurement data does not exist.'
        if not self._flg_measurement_exist: return []
        
        df:pd.DataFrame = self._dict_measurement[self._label_avemea][-1]
        list_wavelengths = df[self._dflabel_wavelength].tolist()
        return list_wavelengths
    
    def get_list_Raman_shift(self) -> list[float]:
        """
        Returns the list of Raman shifts stored in the measurement data
        
        Returns:
            list: list of Raman shifts
        """
        list_wavelengths = self.get_list_wavelengths()
        list_raman_shift = [convert_wavelength_to_ramanshift(wavelength=wvl,\
            excitation_wavelength=self.get_laser_params()[1]) for wvl in list_wavelengths]
        return list_raman_shift
    
    def convert(self, wavelength:float|None=None, Raman_shift:float|None=None):
        """
        Converts between wavelength and Raman shift by giving EITHER one based on
        the laser params stored internally.
        
        Args:
            wavelength (float | None, optional): Wavelength to convert. Defaults to None.
            Raman_shift (float | None, optional): Raman shift to convert. Defaults to None.
        """
        if (isinstance(wavelength,(int,float)) and isinstance(Raman_shift,(int,float)))\
            or (isinstance(wavelength, type(None)) and isinstance(Raman_shift, type(None))):
            raise ValueError('convert: Please provide either wavelength or Raman shift, not both or neither.')
        
        if isinstance(wavelength,(int,float)):
            return convert_wavelength_to_ramanshift(wavelength,self.get_laser_params()[1])
        elif isinstance(Raman_shift,(int,float)):
            return convert_ramanshift_to_wavelength(Raman_shift,self.get_laser_params()[1])
        else: raise TypeError('Wavelength or Raman shift has to be in integer or float')
        
    def get_closest_wavelength(self,wavelength:float) -> float:
        """
        Returns the closest wavelength in the list of wavelengths stored in the measurement data

        Args:
            wavelength (float): wavelength to be retrieved (closest wavelength will be used)

        Returns:
            float: closest wavelength in the list of wavelengths
        """
        assert self._flg_measurement_exist, 'get_closest_wavelength: The measurement data does not exist.'
        assert isinstance(wavelength, (int, float)), 'get_closest_wavelength: The input data type is not correct. Expected an integer or a float.'
        
        wavelength_idx = self.get_wavelength_idx(wavelength=wavelength)
        wavelength = self.get_list_wavelengths()[wavelength_idx]
        
        return wavelength
    
    def get_closest_raman_shift(self,raman_shift:float) -> float:
        """
        Returns the closest Raman shift in the list of Raman shifts stored in the measurement data

        Args:
            raman_shift (float): Raman shift to be retrieved (closest Raman shift will be used)

        Returns:
            float: closest Raman shift in the list of Raman shifts
        """
        assert self._flg_measurement_exist and self._flg_metadata_exist, 'get_closest_raman_shift: The measurement or metadata does not exist.'
        assert isinstance(raman_shift, (int, float)), 'get_closest_raman_shift: The input data type is not correct. Expected an integer or a float.'
        return self.get_list_Raman_shift()[self.get_wavelength_idx(convert_ramanshift_to_wavelength(raman_shift,self.get_laser_params()[1]))]
        
    def get_wavelength_idx(self,wavelength:float) -> int:
        """
        Returns the index of the wavelength in the list of wavelengths stored in the measurement data

        Args:
            wavelength (float): wavelength to be retrieved (closest wavelength will be used)

        Returns:
            int: index of the wavelength in the list of wavelengths
        """
        assert self._flg_measurement_exist, 'get_wavelength_idx: The measurement data does not exist.'
        assert isinstance(wavelength, (int, float)), 'get_wavelength_idx: The input data type is not correct. Expected an integer or a float.'
        
        def find_nearest(array, value):
            array = np.asarray(array)
            idx = np.argmin(np.abs(array - value))
            return array[idx]
        
        closest_wavelength = find_nearest(self.get_list_wavelengths(),wavelength)
        
        df:pd.DataFrame = self._dict_measurement[self._label_avemea][-1]
        wavelength_idx = df[self._dflabel_wavelength].tolist().index(closest_wavelength)
        
        return wavelength_idx

    def get_raman_shift_idx(self,raman_shift:float) -> int:
        """
        Returns the index of the Raman shift in the list of Raman shifts stored in the measurement data

        Args:
            raman_shift (float): Raman shift to be retrieved (closest Raman shift will be used)

        Returns:
            int: index of the Raman shift in the list of Raman shifts
        """
        assert self._flg_measurement_exist and self._flg_metadata_exist, 'get_raman_shift_idx: The measurement or metadata does not exist.'
        assert isinstance(raman_shift, (int, float)), 'get_raman_shift_idx: The input data type is not correct. Expected an integer or a float.'
        wvl = convert_ramanshift_to_wavelength(raman_shift,self.get_laser_params()[1])
        return self.get_wavelength_idx(wavelength=wvl)

    def get_labels(self) -> tuple:
        """
        Returns the labels for the x, y, z coordinates, and the wavelength and intensity keys
        
        Returns:
            tuple: (x_label,y_label,z_label,wavelength_label,intensity_label)
        """
        return (self._label_x,self._label_y,self._label_z,self._dflabel_wavelength,self._dflabel_intensity)
    
    def get_heatmap_table(self,wavelength:float) -> pd.DataFrame:
        """
        Returns the coordinates and intensities of all measurements at the requested wavelength
        
        Args:
            wavelength (float): wavelength to be retrieved (closest wavelength will be used)
        
        Returns:
            pd.DataFrame: dataframe of the coordinates and intensities, according to the internal labels
        
        Note:
            The labels can be retrieved using the get_labels() method
        """
        assert self._flg_measurement_exist, 'get_coor_intensity: The measurement data does not exist.'
        
        def find_nearest(array, value):
            array = np.asarray(array)
            idx = np.argmin(np.abs(array - value))
            return array[idx]
        
        closest_wavelength = find_nearest(self.get_list_wavelengths(),wavelength)
        
        df:pd.DataFrame = self._dict_measurement[self._label_avemea][-1]
        wavelength_idx = df[self._dflabel_wavelength].tolist().index(closest_wavelength)
        
        df_result = pd.DataFrame(columns=[self._label_x,self._label_y,self._label_z,
                                          self._dflabel_wavelength,self._dflabel_intensity])
        
        with self._lock_measurement:
            x_coor = self._dict_measurement[self._label_x].copy()
            y_coor = self._dict_measurement[self._label_y].copy()
            z_coor = self._dict_measurement[self._label_z].copy()
            intensities = [df.iloc[wavelength_idx, df.columns.get_loc(self._dflabel_intensity)] for df in self._dict_measurement[self._label_avemea].copy()]
        
        df_result = pd.DataFrame({
            self._label_x: x_coor,
            self._label_y: y_coor,
            self._label_z: z_coor,
            self._dflabel_wavelength: closest_wavelength,  # Constant value
            self._dflabel_intensity: intensities
        })
        return df_result

    def add_observer(self, observer: Callable) -> None:
        """
        Adds an observer to the list of observers.
        """
        assert callable(observer), 'add_observer: The input data type is not correct. Expected a callable.'
        self._list_observers.append(observer)

    def remove_observer(self, observer: Callable) -> None:
        """
        Removes an observer from the list of observers.
        """
        try: self._list_observers.remove(observer)
        except Exception as e: print(f"Error removing observer: {e}")

    def _notify_observers(self) -> None:
        """
        Notifies all observers of a change.
        """
        for observer in self._list_observers:
            try: observer()
            except Exception as e: print(f"Error notifying observer: {e}")
    
    def copy(self, flg_newID:bool=True) -> Self: # type: ignore
        """
        Creates a copy of the current object.
        
        Args:
            flg_newID (bool): Flag to indicate if a new ID should be assigned. Default is True.
            
        Returns:
            Self: A copy of the current object.
        """
        if flg_newID: unit_id = uuid.uuid4().hex
        else: unit_id = self._unit_id
        
        new_copy = MeaRMap_Unit(unit_name=self._unit_name,unit_id=unit_id)
        new_copy.set_dict_measurements(deepcopy(self._dict_measurement))
        new_copy.set_dict_metadata(deepcopy(self._dict_metadata))
        return new_copy # type: ignore

    def delete_self(self):
        """
        A protocol to delete the object to remove the allocated memory, in a proper way.
        """
        # Removing the metadata dictionary
        self._dict_metadata.clear()
        self._dict_metadata.clear()
        
        # Emptying the measurement dictionary lists
        for key in self._dict_measurement.keys():
            try: self._dict_measurement[key].clear()
            except: pass
        self._dict_measurement.clear()
        self._dict_measurement_types.clear()
        
        self._notify_observers()
    
    def self_report(self):
        """
        Prints all the attributes of the object
        """
        print('MappingMeasurement_Unit:')
        attributes = vars(self)
        for key in attributes.keys():
            print(f'{key}: {attributes[key]}')
        print()
    
    def test_generate_dummy(self):
        """
        Generates dummy data for testing purposes
        """
        for i in range(10):
            x = float(np.random.rand(1)[0])
            y = float(np.random.rand(1)[0])
            z = float(0)
            timestamp = get_timestamp_us_int() + i
            mea = MeaRaman(reconstruct=True)
            mea.test_generate_dummy()
            
            self.append_ramanmeasurement_data(
                timestamp=timestamp,
                coor=(x,y,z),
                measurement=mea
            )
            
            
            
    
class MeaRMap_Hub():
    """This is a class to store all the measurement data, savepaths, etc during a mapping
    measurement. It also has methods to selectively retrive measurement data, and save the
    metadata of the mapping measurement.
    """
    def __init__(self) -> None:
    # >>> Label initialisation <<<
        # Dataframe storing the measurement
        self._version = '0.1.0-2024.05.24'  # Version of the data storage format
                
        self._unit_id_key = SaveParamsEnum.DATABASE_ID_KEY.value  # Key for the measurement ID in the metadata dictionary

        self._dict_mappingMeasurementUnits = {   # Dictionary to store the mapping_measurement_unit objects
            'version': self._version,   # Version of the data storage format
            self._unit_id_key: [],      # measurement_id from the mapping_measurement_unit object
            'measurement_unit': []      # mapping_measurement_unit object
            }
        
        self._dict_mappingUnit_NameID = {}  # Dictionary to store the mapping of the unit name and unit ID with the name as the key
        
        self._list_callbacks = []  # List of callbacks to be called when the mapping measurement is updated
        
        self._last_update_timestamp:int = get_timestamp_us_int()
        
    def add_observer(self,callback:Callable) -> None:
        """
        Adds a callback to be called when the mapping measurement is updated.
        
        Args:
            callback (Callable): callback function to be called
        """
        assert callable(callback), 'add_callback: The input data type is not correct. Expected a callable.'
        self._list_callbacks.append(callback)
        
    def _notify_observers(self) -> None:
        """
        Runs all the callbacks in the list.
        """
        for callback in self._list_callbacks:
            try: callback()
            except Exception as e: print(f'_run_callbacks: Error in callback: {e}')
        
    def copy_mapping_unit(self,source_unit_id:str,dest_unit_name:str,appendToHub:False) -> MeaRMap_Unit:
        """
        Copies the mapping unit data from the source to the destination unit ID
        
        Args:
            source_unit_id (str): source unit ID
            dest_unit_name (str): destination unit name
            appendToHub (bool): append the copied unit to the hub. Defaults to False.
        
        Returns:
            MappingMeasurement_Unit: copied mapping_measurement_unit object
        """
        assert source_unit_id in self._dict_mappingMeasurementUnits[self._unit_id_key], 'copy_mapping_unit: The source unit ID does not exist.'
        
        idx = self._dict_mappingMeasurementUnits[self._unit_id_key].index(source_unit_id)
        source_unit = self._dict_mappingMeasurementUnits['measurement_unit'][idx]
        source_unit:MeaRMap_Unit
        
        # Construct the destination unit
        dest_unit:MeaRMap_Unit = MeaRMap_Unit()
        dest_unit.set_dict_metadata(deepcopy(source_unit.get_dict_unit_metadata()))
        dest_unit.set_dict_measurements(deepcopy(source_unit.get_dict_measurements()))
        dest_unit.set_unitName_and_unitID(dest_unit_name)
        
        if appendToHub:
            self.append_mapping_unit(dest_unit)
        
        return dest_unit
    
    def check_measurement_exist(self):
        """
        Check if the measurement data exists
        """
        return len(self._dict_mappingMeasurementUnits[self._unit_id_key]) > 0
    
    def get_dict_nameToID(self) -> dict:
        """
        Returns the dictionary of the mapping unit name and ID
        
        Returns:
            dict: dictionary of the mapping unit name and ID. {unit_name: unit_id}
        """
        return self._dict_mappingUnit_NameID

    def get_list_MappingUnit_names(self) -> list[str]:
        """
        Returns the list of measurement names stored in the mapping_measurements dictionary.
        
        Returns:
            list: list of measurement names
        """
        return list(self._dict_mappingUnit_NameID.keys())
    
    def get_list_MappingUnit_ids(self) -> list[str]:
        """
        Returns the list of measurement IDs stored in the mapping_measurements dictionary.
        
        Returns:
            list: list of measurement IDs
        """
        return self._dict_mappingMeasurementUnits[self._unit_id_key]
    
    def get_list_MappingUnit(self) -> list[MeaRMap_Unit]:
        """
        Returns the list of mapping measurement units stored in the hub.

        Returns:
            list[MappingMeasurement_Unit]: list of mapping measurement units
        """
        return self._dict_mappingMeasurementUnits['measurement_unit']

    def get_summary_units(self) -> tuple[list[str],list[str],list[dict],list[int]]:
        """
        Returns a  summarises all the stored units and their metadata.
        
        Returns:
            tuple: list of unit IDs, list of unit names,
                list of metadata dictionaries,
                list of number of measurements in the unit
        """
        list_ids = self._dict_mappingMeasurementUnits[self._unit_id_key]
        list_names = []
        list_metadata = []
        list_num_measurements = []
        for unit in self._dict_mappingMeasurementUnits['measurement_unit']:
            unit:MeaRMap_Unit
            list_metadata.append(unit.get_dict_measurement_metadata())
            list_num_measurements.append(unit.get_numMeasurements())
            list_names.append(unit.get_unit_name())
        
        return (list_ids,list_names,list_metadata,list_num_measurements)
    
    def get_MappingUnit(self,unit_id:str|None=None, unit_name:str|None=None) -> MeaRMap_Unit:
        """
        Returns the mapping_measurement_unit object based on the measurement_id.
        
        Args:
            unit_id (str|None): MappingMeasurement_Unit ID to be retrieved. If None, the unit_name will be used.
            unit_name (str|None): MappingMeasurement_Unit name to be retrieved. If None, the unit_id will be used.
            
        Raises:
            ValueError: If both unit_id and unit_name are None.
        
        Returns:
            mapping_measurement_unit: mapping_measurement_unit object
        """
        if unit_id is None and unit_name is None:
            raise ValueError('get_mapping_measurement_unit: Either unit_id or unit_name must be provided.')
        if unit_id is not None and unit_name is not None:
            raise ValueError('get_mapping_measurement_unit: Only one of unit_id or unit_name can be provided.')
        if unit_id is not None and unit_id not in self.get_list_MappingUnit_ids():
            raise ValueError('get_mapping_measurement_unit: The unit_id does not exist.')
        if unit_name is not None and unit_name not in self.get_list_MappingUnit_names():
            raise ValueError('get_mapping_measurement_unit: The unit_name does not exist.')
        
        if unit_name is not None:
            unit_id = self._dict_mappingUnit_NameID[unit_name]
        
        idx = self._dict_mappingMeasurementUnits[self._unit_id_key].index(unit_id)
        return self._dict_mappingMeasurementUnits['measurement_unit'][idx]
    
    def append_mapping_unit(self,mapping_unit:MeaRMap_Unit,notify:bool=True) -> None:
        """
        Appends a mapping_measurement_unit object into the mapping_measurements dictionary.
        
        Args:
            mapping_unit (MappingMeasurement_Unit): MappingMeasurement_Unit object to be stored
            notify (bool): Flag to indicate if observers should be notified. Default is True.
        """
        assert isinstance(mapping_unit, MeaRMap_Unit), 'append_mapping_measurement_unit: The input data type is not correct. Expected mapping_measurement_unit object.'
        # assert measurement_unit.check_measurement_and_metadata_exist(), 'append_mapping_measurement_unit: The measurement data or metadata does not exist.'
        
        unitID = mapping_unit.get_unit_id()
        unitName = mapping_unit.get_unit_name()
        if unitID in self._dict_mappingMeasurementUnits[self._unit_id_key]: raise FileExistsError('append_mapping_measurement_unit: The measurement ID already exists.')
        if unitName in self._dict_mappingUnit_NameID: raise FileExistsError('append_mapping_measurement_unit: The measurement name already exists.')
        
        self._dict_mappingMeasurementUnits[self._unit_id_key].append(unitID)
        self._dict_mappingMeasurementUnits['measurement_unit'].append(mapping_unit)
        
        self._dict_mappingUnit_NameID[mapping_unit.get_unit_name()] = mapping_unit.get_unit_id()

        if notify: self._notify_observers()
        
    def extend_mapping_unit(self,list_mapping_unit:list[MeaRMap_Unit]) -> None:
        """
        Extends the mapping_measurement_unit objects in the mapping_measurements dictionary.

        Args:
            list_mapping_unit (list[MeaRMap_Unit]): List of MappingMeasurement_Unit objects to be added.
        """
        [self.append_mapping_unit(unit, notify=False) for unit in list_mapping_unit]
        self._notify_observers()
        
    def rename_mapping_unit(self,unit_id:str,new_name:str) -> None:
        """
        Renames the mapping_measurement_unit object in the mapping_measurements dictionary

        Args:
            unit_id (str): MappingMeasurement_Unit ID to be renamed
            new_name (str): New name for the mapping_measurement_unit
        """
        assert unit_id in self._dict_mappingMeasurementUnits[self._unit_id_key], 'rename_mapping_measurement_unit: The measurement ID does not exist.'
        assert new_name not in self._dict_mappingUnit_NameID, 'rename_mapping_measurement_unit: The new name already exists.'
        
        unit_idx = self._dict_mappingMeasurementUnits[self._unit_id_key].index(unit_id)
        unit:MeaRMap_Unit = self._dict_mappingMeasurementUnits['measurement_unit'][unit_idx]
        
        old_name = unit.get_unit_name()
        unit.set_unitName(new_name)
        self._dict_mappingUnit_NameID[new_name] = unit_id
        del self._dict_mappingUnit_NameID[old_name]
        
        self._notify_observers()
    
    def remove_mapping_unit_name(self,unit_name:str) -> None:
        """
        Removes a mapping_measurement_unit object from the mapping_measurements dictionary.

        Args:
            unit_name (str): MappingMeasurement_Unit name to be removed
        """
        assert unit_name in self._dict_mappingUnit_NameID, 'remove_mapping_measurement_unit: The measurement name does not exist.'
        unit_id = self._dict_mappingUnit_NameID[unit_name]
        self.remove_mapping_unit_id(unit_id)
        
        self._notify_observers()
    
    def remove_mapping_unit_id(self,unit_id:str) -> None:
        """
        Removes a mapping_measurement_unit object from the mapping_measurements dictionary.
        
        Args:
            unit_id (str): MappingMeasurement_Unit ID to be removed
        """
        assert unit_id in self._dict_mappingMeasurementUnits[self._unit_id_key], 'remove_mapping_measurement_unit: The measurement ID does not exist.'
        
        unit_idx = self._dict_mappingMeasurementUnits[self._unit_id_key].index(unit_id)
        unit_name = self._dict_mappingMeasurementUnits['measurement_unit'][unit_idx].get_unit_name()
        del self._dict_mappingMeasurementUnits[self._unit_id_key][unit_idx]
        del self._dict_mappingUnit_NameID[unit_name]
        
        # Delete the object itself and all of its references
        unit:MeaRMap_Unit = self._dict_mappingMeasurementUnits['measurement_unit'][unit_idx]
        unit.delete_self()
        del self._dict_mappingMeasurementUnits['measurement_unit'][unit_idx]
        
        # # Force the garbage collector to collect the deleted object
        # gc.collect()
        
        self._notify_observers()
        
    def delete_all_mapping_units(self) -> None:
        """
        Deletes all mapping_measurement_unit objects from the mapping_measurements dictionary.
        """
        self._dict_mappingMeasurementUnits[self._unit_id_key].clear()
        self._dict_mappingMeasurementUnits['measurement_unit'].clear()
        self._dict_mappingUnit_NameID.clear()
        self._notify_observers()

    def shift_xycoordinate_timestamp(self, unit_id:str, timeshift_us:int) -> str:
        """
        Shifts the timestamp of the measurement data based on the given timeshift. The timeshift
        is used to calculate the new coordinates (linear approximation) based on the stored coordinates
        and timestamps. The resulting shifted MappingMeasurement_Unit object is stored in the
        mapping_measurements dictionary once the shift is completed.

        Args:
            unit_id (str): MappingMeasurement_Unit ID to be shifted
            timeshift_us (int): Timeshift in microseconds
            
        Returns:
            str: new unit name of the shifted MappingMeasurement
        """
        assert unit_id in self._dict_mappingMeasurementUnits[self._unit_id_key], 'shift_coordinate_timestamp: The measurement ID does not exist.'
        assert isinstance(timeshift_us, int), 'shift_coordinate_timestamp: The input data type is not correct. Expected an integer.'
        unit = self.get_MappingUnit(unit_id)
        unit_name_init = unit.get_unit_name()
        unit_name_shift = unit_name_init + f'_shift {timeshift_us/1000}ms'
        
        dict_mea = unit.get_dict_measurements()
        lbl_ts,lbl_x,lbl_y,_,_,_ = unit.get_keys_dict_measurement()
        
        arr_init_ts_coor = np.array([dict_mea[lbl_ts],dict_mea[lbl_x],dict_mea[lbl_y]])
        arr_init_ts_coor = arr_init_ts_coor.T
        
        arr_shifted_ts_coor = deepcopy(arr_init_ts_coor)
        arr_shifted_ts_coor[:,0] += timeshift_us
        
        def interpolate_coor(init_ts:float, fin_ts:float, init_coor:np.ndarray, fin_coor:np.ndarray, ts:float):
            coor = init_coor + (fin_coor-init_coor)/(fin_ts-init_ts)*(ts-init_ts)
            coor_x = coor[0]
            coor_y = coor[1]
            return coor_x, coor_y
        
        direction = np.sign(timeshift_us)
        direction = 1 if direction == 0 else direction
        
        for idx,ts in enumerate(arr_shifted_ts_coor[:,0]):
            idx_before = idx
            while True:
                if idx_before<0: idx_before = 0; break
                if idx_before>=len(arr_init_ts_coor): idx_before = len(arr_init_ts_coor)-1; break
                
                ts_before = arr_init_ts_coor[idx_before,0]
                if ts_before*direction < ts*direction: break
                if ts_before == ts: break
                idx_before += direction
                
            idx_after = idx_before + direction
            if idx_after<0: idx_before = 0; idx_after = 1
            if idx_after>=len(arr_init_ts_coor): idx_after = len(arr_init_ts_coor)-1; idx_before = len(arr_init_ts_coor)-2
            
            idx_before = int(idx_before)
            idx_after = int(idx_after)
            
            init_coor = np.array([arr_init_ts_coor[idx_before,1],arr_init_ts_coor[idx_before,2]])
            fin_coor = np.array([arr_init_ts_coor[idx_after,1],arr_init_ts_coor[idx_after,2]])
            
            arr_shifted_ts_coor[idx,1], arr_shifted_ts_coor[idx,2] = interpolate_coor(
                init_ts=arr_init_ts_coor[idx_before,0],
                fin_ts=arr_init_ts_coor[idx_after,0],
                init_coor=init_coor,
                fin_coor=fin_coor,
                ts=ts
            )
            
        dict_shifted_mea = deepcopy(dict_mea)
        dict_shifted_mea[lbl_ts] = arr_shifted_ts_coor[:,0].tolist()
        dict_shifted_mea[lbl_x] = arr_shifted_ts_coor[:,1].tolist()
        dict_shifted_mea[lbl_y] = arr_shifted_ts_coor[:,2].tolist()
        
        # Convert the timestamps to integer
        dict_shifted_mea[lbl_ts] = [int(ts) for ts in dict_shifted_mea[lbl_ts]]
        
        unit_shift = self.copy_mapping_unit(
            source_unit_id=unit_id,
            dest_unit_name=unit_name_shift,
            appendToHub=True
        )
        unit_shift.set_dict_measurements(dict_shifted_mea)
        
        return unit_name_shift
        
    def self_report(self):
        """
        Prints all the attributes of the object
        """
        print('MappingMeasurement_Hub:')
        attributes = vars(self)
        for key in attributes.keys():
            print(f'{key}: {attributes[key]}')
        print()
        
    def test_generate_dummy(self, number:int=10):
        """
        Generates dummy measurements for testing purposes
        """
        for i in range(number):
            unit = MeaRMap_Unit(unit_name='dummy {}'.format(i))
            unit.test_generate_dummy()
            self.append_mapping_unit(unit)
        
class MeaRMap_Handler():
    """
    Handles the mapping measurement data storage and retrieval.
    """
    def __init__(self):
        self._version = '0.1.0-2024.05.24'
        
        self._dict_default_save_parameters = {
            'meta_table': 'metadata',           # Table name for the metadata in the database
        }
        
        # Save parameters
        self._unit_id_key = SaveParamsEnum.DATABASE_ID_KEY.value
        self._unit_name_key = SaveParamsEnum.DATABASE_NAME_KEY.value
        self._default_SaveDir = SaveParamsEnum.DEFAULT_SAVE_PATH.value
        self._default_SubFolder = 'data'
        self._default_separator = '__id__'
        
        self._table_prefix = SaveParamsEnum.MAPUNIT_DB_PREFIX.value  # Prefix for the database name for the mapping measurement not to interfere with other databases naming system
        self._table_prefix_load = None # Prefix to support the old naming system
        
        # Save options
        self._dict_extensions = {
            SaveParamsEnum.SAVE_OPTIONS_CSV.value: 'csv files',
            SaveParamsEnum.SAVE_OPTIONS_TXT.value: 'text files',
            SaveParamsEnum.SAVE_OPTIONS_PARQUET.value: 'parquet files',
            SaveParamsEnum.SAVE_OPTIONS_FEATHER.value: 'feather files',
        }
        
        self._default_extension = SaveParamsEnum.DEFAULT_SAVE_EXT.value
        self._default_extension = SaveParamsEnum.SAVE_OPTIONS_CSV.value if self._default_extension not in self._dict_extensions.keys() else self._default_extension
        
    def _save_MappingMeasurementUnit_metadata_database(self,mappingUnit:MeaRMap_Unit,conn:sql.Connection) -> None:
        """
        Saves the mappingUnit data into a database.
        
        Args:
            mappingUnit (mapping_measurement_unit): mapping_measurement_unit object to be saved
            conn (sql.Connection): connection to the database
            
        Raises:
            AssertionError: If the input data types are not correct or if the measurement data or metadata does not exist.
            ValueError: If the metadata type is not recognised.
        """
        assert isinstance(mappingUnit, MeaRMap_Unit), '_save_mapping_measurement_unit_database: The input data type is not correct. Expected mapping_measurement_unit object.'
        assert mappingUnit.check_measurement_and_metadata_exist(), '_save_mapping_measurement_unit_database: The measurement data or metadata does not exist.'
        assert isinstance(conn, sql.Connection), '_save_mapping_measurement_unit_database: The input data type is not correct. Expected sql.Connection object.'
        
        cursor = conn.cursor()
        
        # Retrieve the metadata
        labeldb_meta = self._table_prefix + self._dict_default_save_parameters['meta_table']
        metadata = mappingUnit.get_dict_unit_metadata()
        
        metadata_key_types = mappingUnit.get_dict_types()[0]
        
        # Get the list of the unit id and check if it exists in the database metadata table
        unit_id = mappingUnit.get_unit_id()
        query = 'SELECT name FROM sqlite_master WHERE type="table" AND name=?'
        cursor.execute(query, (labeldb_meta,))
        result = cursor.fetchone()
        if result is not None:
            query = 'SELECT * FROM {} WHERE {} = ?'.format(labeldb_meta,self._unit_id_key)
            cursor.execute(query, (unit_id,))
            result = cursor.fetchone()
            if result is not None: return   # If the unit ID already exists, do not overwrite the metadata
        
        # Create the metadata table
        query_keys = ''
        values_metadata = []
        for key in metadata.keys():
            if metadata_key_types[key] == str:
                query_keys += ', {} TEXT'.format(key)
                values_metadata.append(metadata[key])
            elif metadata_key_types[key] == float or metadata_key_types[key] == int:
                query_keys += ', {} REAL'.format(key)
                values_metadata.append(metadata[key])
            elif metadata_key_types[key] == dict:
                query_keys += ', {} TEXT'.format(key)
                values_metadata.append(json.dumps(metadata[key]))
            elif metadata_key_types[key] == list:
                query_keys += ', {} TEXT'.format(key)
                values_metadata.append(json.dumps(metadata[key]))
            else:
                raise ValueError('_save_mapping_measurement_unit_database: The metadata type is not recognised: {}'\
                    .format(metadata_key_types[key]))
        
        query_keys = query_keys[2:] # Remove the first comma and space
        query = 'CREATE TABLE IF NOT EXISTS {} ({})'.format(labeldb_meta,query_keys)
        cursor.execute(query)
        
        # Prepare the values for insertion
        query_keys = ', '.join(metadata.keys())
        query_metadata_values = ', '.join(['?' for _ in range(len(values_metadata))])
        query = 'INSERT INTO {} ({}) VALUES ({})'.format(labeldb_meta,query_keys,query_metadata_values)
        cursor.execute(query, values_metadata)
        
        conn.commit()
        return
        
    def _save_MappingMeasurementUnit_measurement_database(
        self,mappingUnit:MeaRMap_Unit,conn:sql.Connection,conn_path:str) -> None:
        """
        Saves the mapping_measurement_unit data into a database.
        
        Args:
            mappingUnit (mapping_measurement_unit): mapping_measurement_unit object to be saved
            conn (sql.Connection): connection to the database
            conn_path (str): path to the database
        """
        assert isinstance(mappingUnit, MeaRMap_Unit), '_save_mapping_measurement_unit_database: The input data type is not correct. Expected mapping_measurement_unit object.'
        assert mappingUnit.check_measurement_and_metadata_exist(), '_save_mapping_measurement_unit_database: The measurement data does not exist.'
        assert isinstance(conn, sql.Connection), '_save_mapping_measurement_unit_database: The input data type is not correct. Expected sql.Connection object.'
        
        cursor = conn.cursor()
        
        # Retrieve the id and measurement data
        mea_id_key = mappingUnit.get_key_measurementId()
        unit_id = mappingUnit.get_unit_id()
        table_name = self._table_prefix + unit_id
        unit_dict = mappingUnit.get_dict_measurements()
        unit_key_types = mappingUnit.get_dict_types()[1]
        
        # Create the measurement table
        query_keys = ''
        for key in unit_dict.keys():
            type_key = unit_key_types[key]
            if type_key == str or type_key == pd.DataFrame or type_key == list[pd.DataFrame]:
                query_keys += ', {} TEXT'.format(key)
            elif type_key == float or type_key == int:
                query_keys += ', {} REAL'.format(key)
            else:
                raise ValueError('_save_mapping_measurement_unit_database: The measurement type is not recognised: {}'\
                    .format(type_key))
        
        query_keys = query_keys[2:] # Remove the first comma and space
        cursor.execute('CREATE TABLE IF NOT EXISTS {} ({})'.format(table_name,query_keys))
        
        # Prepare the values for insertion
        len_entries = len(unit_dict[key])
        query_keys = ', '.join(unit_dict.keys())
        query_values = ', '.join(['?' for _ in range(len(unit_dict))])
        
        
        # Storage for the data
        list_avgdf = []
        list_rawlistdf = []
        
        # Prepare the save directory and file paths
        save_timestamp = get_timestamp_us_str()
        conn_dir = os.path.dirname(conn_path)
        subsavedir = os.path.join(conn_dir,self._default_SubFolder)
        avgdf_savepath = os.path.join(subsavedir,get_timestamp_us_str()+'_avg.parquet')
        rawlistdf_savepath = os.path.join(subsavedir,get_timestamp_us_str()+'_rawlist.parquet')
        avgdf_savepath_rel = os.path.relpath(avgdf_savepath,conn_dir)
        rawlistdf_savepath_rel = os.path.relpath(rawlistdf_savepath,conn_dir)
        if not os.path.exists(subsavedir): os.makedirs(subsavedir)
        if os.path.exists(avgdf_savepath): os.remove(avgdf_savepath)
        if os.path.exists(rawlistdf_savepath): os.remove(rawlistdf_savepath)
        separator = self._default_separator
        
        # Get the list of timestamps in the database table
        cursor.execute('SELECT {} FROM {}'.format(mea_id_key,table_name))
        existing_ids = [str(int(row[0])) for row in cursor.fetchall()]        
        values = []
        for i in range(len_entries):
            entry_values = []
            mea_id = str(unit_dict[mea_id_key][i])
            if str(int(mea_id)) in existing_ids: continue
            for key in unit_dict.keys():
                if unit_dict[key][i] is None:
                    entry_values.append(None)
                elif unit_key_types[key] == pd.DataFrame:
                    list_avgdf.append((mea_id,unit_dict[key][i]))
                    entry_values.append(avgdf_savepath_rel)
                elif unit_key_types[key] == list[pd.DataFrame]:
                    rawlistdf = unit_dict[key][i]
                    list_rawlistdf.extend([(mea_id+separator+str(j),df) for j,df in enumerate(rawlistdf)])
                    entry_values.append(rawlistdf_savepath_rel)
                else:
                    entry_values.append(unit_dict[key][i])
            values.append(tuple(entry_values))

        # Form the df and save them
        df_avg = pd.concat([df for _,df in list_avgdf],keys=[mea_id for mea_id,_ in list_avgdf],axis=0)
        if len(list_rawlistdf) > 0: df_rawlist = pd.concat([df for _,df in list_rawlistdf],keys=[mea_id for mea_id,_ in list_rawlistdf],axis=0)
        else: df_rawlist = pd.DataFrame()
        df_avg.to_parquet(avgdf_savepath)
        df_rawlist.to_parquet(rawlistdf_savepath)
        
        cursor.executemany('INSERT INTO {} ({}) VALUES ({})'.format(table_name, query_keys, query_values), values)
        
        conn.commit()
        
    def save_MappingUnit_ext_prompt(self,mappingUnit:MeaRMap_Unit,flg_saveraw:bool) -> threading.Thread|None:
        """
        Saves a given MappingMeasurement_Unit object into a file extension of the user's choosing
        
        Raises:
            AssertionError: If the input data type is not correct or the measurement data does not exist.
            
        Args:
            mappingUnit (MappingMeasurement_Unit): The MappingUnit to be saved
            flg_saveraw (bool): flag to save the raw data. Defaults to False.

        Returns:
            threading.Thread|None: thread of the saving process or None if the user cancels the saving process
        """
        assert isinstance(mappingUnit, MeaRMap_Unit), 'save_mapping_unit_txt: The input data type is not correct. Expected mapping_measurement_unit object.'
        assert mappingUnit.check_measurement_and_metadata_exist(), 'save_mapping_unit_txt: The measurement data does not exist.'
        
        # Prepare the file dialog
        list_extensions = [(value, '*.'+key) for key,value in self._dict_extensions.items()]
        default_extension = '.' + self._default_extension
        
        # Ask for the file path
        unit_name = mappingUnit.get_unit_name()
        if not isinstance(unit_name,str) or unit_name == '':
            unit_name = 'unit_'+get_timestamp_us_str()
        
        filepath = filedialog.asksaveasfilename(defaultextension=default_extension,filetypes=list_extensions,
                                                initialfile=unit_name+default_extension)
        extension = os.path.splitext(filepath)[1]
        
        if extension == '': return None
        if filepath == '': return None
        
        extension = extension[1:]   # Remove the dot (e.g., .txt -> txt)
        
        return self.save_MappingUnit_ext(mappingUnit,filepath,flg_saveraw,extension)
        
    def get_dict_extensions(self) -> dict:
        """
        Returns the dictionary of supported file extensions and their descriptions.
        
        Returns:
            dict: dictionary of supported file extensions and their descriptions
        """
        return self._dict_extensions.copy()
        
    @thread_assign
    def save_MappingUnit_ext(self,mappingUnit:MeaRMap_Unit,filepath:str,flg_saveraw:bool,extension:str)\
        -> threading.Thread:
        """
        Saves a given MappingMeasurement_Unit object into a tab delimited .csv file.

        Raises:
            AssertionError: If the input data type is not correct or the measurement data does not exist.
            
        Args:
            mappingUnit (MappingMeasurement_Unit): The MappingUnit to be saved
            filepath (str): path to the file to be saved
            flg_saveraw (bool): flag to save the raw data. Defaults to False.
            extension (str): extension of the file to be saved

        Returns:
            threading.Thread: thread of the saving process
        """
        assert isinstance(mappingUnit, MeaRMap_Unit), 'save_mapping_unit_txt: The input data type is not correct. Expected mapping_measurement_unit object.'
        assert mappingUnit.check_measurement_and_metadata_exist(), 'save_mapping_unit_txt: The measurement data does not exist.'

        dict_meta = mappingUnit.get_dict_unit_metadata().copy()
        dict_mea_ori = mappingUnit.get_dict_measurements()
        dict_mea = dict_mea_ori.copy()
        _,dict_meatypes = mappingUnit.get_dict_types()
        dict_meatypes = dict_meatypes.copy()

        _,_,_,lbl_wavelength,lbl_intensity = mappingUnit.get_labels()

        # Remove the list of dataframes from the output
        list_pop = []
        for key in dict_mea.keys():
            if dict_meatypes[key] == list[pd.DataFrame]:
                list_pop.append(key)
                list_mea_key = key
            elif dict_meatypes[key] == pd.DataFrame:
                list_pop.append(key)
                mea_key = key
                
        [dict_mea.pop(key) for key in list_pop]
        [dict_meatypes.pop(key) for key in list_pop]
        
        list_df = []
        num_measurements = mappingUnit.get_numMeasurements()
        for i in range(num_measurements):
            # > Create a new dataframe for the combined measurements
            mea_combined = pd.DataFrame()
            size = dict_mea_ori[mea_key][i].shape[0]
            for key, value_list in dict_mea_ori.items():
                if key != mea_key and key != list_mea_key:
                    mea_combined[key] = [value_list[i]] * size
                    
            # > Add the wavelength and intensity columns from each raw measurements
            if flg_saveraw:
                # > Extract the raw measurements
                list_mea = dict_mea_ori[list_mea_key][i]
                
                size = list_mea[0].shape[0]
            
                mea_combined[lbl_wavelength] = list_mea[0][lbl_wavelength]
                for j,mea in enumerate(list_mea):
                    lbl_intensity_mod = lbl_intensity + f'_{j+1}'
                    mea_combined[lbl_intensity_mod] = mea[lbl_intensity]
            else:
                mea_combined[lbl_wavelength] = dict_mea_ori[mea_key][i][lbl_wavelength]
                mea_combined[lbl_intensity] = dict_mea_ori[mea_key][i][lbl_intensity]
                
            list_df.append(mea_combined)
            
            # Progress bar report
            # print('Percentage of conversion: {}%'.format(i/num_measurements*100))
            if i % 1000 == 0:
                print('Save to .txt progress: Conversion {}% {} of {}'.format(int(i/num_measurements*100),i,num_measurements))
                
        print('Save to .txt progress: Conversion 100% {} of {}'.format(num_measurements,num_measurements))
        print('Save to .txt progress: Concatenating the dataframes')

        df_save = pd.concat(list_df, axis=0, ignore_index=True)

        print('Save to .txt progress: Saving the data')
        def report_save(flg:threading.Event,filepath):
            while not flg.is_set():
                print(f'{time.ctime()} - Still saving the data to {filepath}')
                time.sleep(5)
                
        flg_done = threading.Event()
        threading.Thread(target=report_save, args=(flg_done,filepath)).start()
        
        if extension != SaveParamsEnum.SAVE_OPTIONS_CSV.value and extension != SaveParamsEnum.SAVE_OPTIONS_TXT.value:
            filepath_metadata = os.path.splitext(filepath)[0] + '_metadata.txt'
        else:
            filepath_metadata = filepath
        
        # Save the metadata
        with open(filepath_metadata, 'w') as f:
            f.write('METADATA\n')
            for key, value in dict_meta.items():
                f.write(f'{key}: {value}\n')
            f.write('\n')
            
        # Save the data via pandas
        time1 = time.time()
        
        if extension == SaveParamsEnum.SAVE_OPTIONS_CSV.value or extension == SaveParamsEnum.SAVE_OPTIONS_TXT.value:
            df_save.to_csv(filepath, mode='a', sep='\t', index=False)
        elif extension == SaveParamsEnum.SAVE_OPTIONS_PARQUET.value:
            df_save.to_parquet(filepath)
        elif extension == SaveParamsEnum.SAVE_OPTIONS_FEATHER.value:
            df_save.to_feather(filepath)
        else:
            raise ValueError('save_mapping_unit_txt: The extension is not recognised: {}'.format(extension))
        flg_done.set()

        print(f'DONE! Saved to {filepath}; Time taken: {time.time()-time1} s')
        print('-----------------------------------------------------------------\n')
        
    def save_MappingMeasurementHub_prompt(self,saveDirPath:str|None=None,savename:str|None=None):
        """
        Prompts the user to save the data into a database or pickle file
        
        Args:
            saveDirPath (str): directory path to save the data. Defaults to None.
            savename (str): name of the file to save. Defaults to None.
        
        Returns:
            tuple: directory path to save the data, name of the file, and extension of the file,
            noting that the savepath is the directory path
        """
        assert isinstance(saveDirPath, (str,type(None))), 'save_mapping_measurement: The input data type is not correct. Expected a string.'
        assert isinstance(savename, (str,type(None))), 'save_mapping_measurement: The input data type is not correct. Expected a string.'
        
        filetypes = [('Database files','*.db'),('Pickle files','*.pkl')]
        if saveDirPath is None: saveDirPath = self._default_SaveDir
        saveDirPath = filedialog.asksaveasfilename(defaultextension='.db',filetypes=filetypes,initialfile=savename)
        
        # Check the extension
        savename,extension = os.path.splitext(os.path.basename(saveDirPath))
        saveDirPath = os.path.dirname(saveDirPath)
        return (saveDirPath,savename,extension)
        
    def save_MappingMeasurementHub_choose(self,mappingHub:MeaRMap_Hub,
        saveDirPath:str|None=None,savename:str|None=None,extension:str|None=None)\
        -> threading.Thread:
        """
        Choose to either save to database or pickle file.
        
        Args:
            mappingHub (MappingMeasurement_Hub): mapping_measurement_hub object to be saved
            saveDirPath (str): path to save the data. Defaults to None.
            savename (str): name of the file to save. Defaults to None.
            extension (str): extension of the file to save: '.db' or '.pkl'. Defaults to None.
        
        Returns:
            threading.Thread: thread of the saving process
        """
        assert isinstance(mappingHub, MeaRMap_Hub), 'save_mapping_measurement: The input data type is not correct. Expected mapping_measurement_new object.'
        if any([isinstance(saveDirPath, type(None)), isinstance(savename, type(None)), isinstance(extension, type(None))]):
            saveDirPath,savename,extension = self.save_MappingMeasurementHub_prompt()
        
        # Check the extension and save accordingly
        if extension == '.db':
            thread = self.save_MappingHub_database(mappingHub,saveDirPath,savename)
        else:
            thread = self.save_MappingHub_pickle(mappingHub,saveDirPath,savename)
        savename = savename + extension
        return thread
        
    @thread_assign
    def save_MappingHub_database(self,mappingHub:MeaRMap_Hub,savedirpath:str,savename:str) -> threading.Thread:
        """
        Saves the mapping measurement data into a database.
        
        Args:
            mappingHub (mapping_measurement_new): mapping_measurement_new object to be saved
            savepath (str): path to save the data. Defaults to None.
        """
        assert isinstance(mappingHub, MeaRMap_Hub), 'save_mapping_measurement: The input data type is not correct. Expected mapping_measurement_new object.'
        assert mappingHub.check_measurement_exist(), 'save_mapping_measurement: The measurement data does not exist.'
        assert os.path.exists(savedirpath) and os.path.isdir(savedirpath), 'save_mapping_measurement: The input savedirpath is not correct. Expected a valid directory path.'
        assert isinstance(savename,str) and savename != '', 'save_mapping_measurement: The input savename is not correct. Expected a valid filename.'
        
        if savename[-3:] != '.db': savename += '.db'
        savepath = os.path.join(savedirpath,savename)
            
        # Connect to the database
        conn:sql.Connection = sql.connect(savepath)
        
        # Save the mapping_measurement_unit metadata and measurement data
        list_unit_ids = mappingHub.get_list_MappingUnit_ids()
        list_measurement_units = [mappingHub.get_MappingUnit(id) for id in list_unit_ids]
        for measurement_unit in list_measurement_units:
            self._save_MappingMeasurementUnit_metadata_database(measurement_unit,conn)    
            self._save_MappingMeasurementUnit_measurement_database(measurement_unit,conn,savepath)
            
        conn.close()
    
    @thread_assign
    def save_MappingHub_pickle(self,mappingHub:MeaRMap_Hub,savedirpath:str,
                               savename:str,q_return:queue.Queue=None) -> threading.Thread:
        """
        Saves the mapping measurement data into a database or pickle file.
        
        Args:
            mappingHub (mapping_measurement_new): mapping_measurement_new object to be saved
            savepath (str): path to save the data. Defaults to None.
            savepath (str): path to save the data. Defaults to None.
            q_return (queue.Queue): queue to return the saved path. Defaults to None.
        """
        assert isinstance(mappingHub, MeaRMap_Hub), 'save_mapping_measurement: The input data type is not correct. Expected mapping_measurement_new object.'
        assert mappingHub.check_measurement_exist(), 'save_mapping_measurement: The measurement data does not exist.'
        assert os.path.exists(savedirpath) and os.path.isdir(savedirpath), 'save_mapping_measurement: The input savedirpath is not correct. Expected a valid directory path.'
        assert isinstance(savename,str) and savename != '', 'save_mapping_measurement: The input savename is not correct. Expected a valid filename.'
        
        if savename[-4:] != '.pkl': savename += '.pkl'
        savepath = os.path.join(savedirpath,savename)
        
        try:
            with open(savepath, 'wb') as file:
                dill.dump(mappingHub, file)
        except Exception as e:
            print('save_mapping_measurement: Error in saving the data: {}'.format(e))
            savepath = None
            
        if q_return is not None: q_return.put(savepath)
            
    def _load_MappingMeasurementUnit_metadata_database(self,unit_id:str,conn:sql.Connection,
                                                       mappingUnit:MeaRMap_Unit) -> MeaRMap_Unit:
        """
        Loads the mapping_measurement_unit metadata data from a database.
        
        Args:
            unit_id (str): measurement ID corresponding to the database table name
            conn (sql.Connection): connection to the database
        
        Returns:
            mapping_measurement_unit: mapping_measurement_unit object with metadata loaded
        """
        assert isinstance(unit_id, str), '_load_mappingMeasurementUnit_metadata_database: The input data type is not correct. Expected a string.'
        assert isinstance(conn, sql.Connection), '_load_mappingMeasurementUnit_metadata_database: The input data type is not correct. Expected sql.Connection object.'
        
        conn.row_factory = sql.Row  # To access the column names
        cursor = conn.cursor()
        
        # Search for the metadata row corresponding to the measurement_id in the metadata table
        assert self._table_prefix_load is not None, '_load_mappingMeasurementUnit_metadata_database: The table prefix is not set.'
        labeldb_meta = self._table_prefix_load + self._dict_default_save_parameters['meta_table']
        
        cursor.execute('SELECT * FROM {} WHERE {}="{}"'.format(labeldb_meta,self._unit_id_key,unit_id))
        row:sql.Row = cursor.fetchone()
        
        types_metadata = mappingUnit.get_dict_types()[0]
        dict_unit_metadata = {}
        for key in row.keys():
            if types_metadata[key] == dict:
                dict_unit_metadata[key] = json.loads(row[key])
            else:
                dict_unit_metadata[key] = row[key]
            
        mappingUnit.set_dict_metadata(dict_unit_metadata) # Set the metadata and automatically set the unit name and id
        
        return mappingUnit
    
    def _load_MappingMeasurementUnit_measurement_database(self,unit_id:str,conn:sql.Connection,conn_path:str,
        mappingUnit:MeaRMap_Unit,flg_readraw:bool) -> MeaRMap_Unit:
        """
        Loads the mapping_measurement_unit measurement data from a database.
        
        Args:
            unit_id (str): measurement ID corresponding to the database table name
            conn (sql.Connection): connection to the database
            conn_path (str): path to the database
            mappingUnit (MappingMeasurement_Unit): mapping_measurement_unit object to be loaded
            flg_readraw (bool): flag to read the raw data. Defaults to False.
        
        Returns:
            mapping_measurement_unit: mapping_measurement_unit object with measurement data loadeds
        """
        assert isinstance(unit_id, str), '_load_mappingMeasurementUnit_measurement_database: The input data type is not correct. Expected a string.'
        assert isinstance(conn, sql.Connection), '_load_mappingMeasurementUnit_measurement_database: The input data type is not correct. Expected sql.Connection object.'
        assert os.path.exists(conn_path) and os.path.isfile(conn_path), '_load_mappingMeasurementUnit_measurement_database: The input conn_path is not correct. Expected a valid file path.'
        
        conn.row_factory = sql.Row  # To access the column names
        cursor = conn.cursor()
        conn_dirpath = os.path.dirname(conn_path)
        
        # > Search for the measurement data corresponding to the measurement_id in the measurement table
        # Modify the table name to include the prefix
        assert self._table_prefix_load is not None, '_load_mappingMeasurementUnit_measurement_database: The table prefix is not set.'
        load_unit_id = self._table_prefix_load + unit_id
        cursor.execute('SELECT * FROM {}'.format(load_unit_id))
        rows = cursor.fetchall()
        if len(rows) == 0: return mappingUnit
        
        value_types = mappingUnit.get_dict_types()[1]
        assert all([key in value_types.keys() for key in rows[0].keys()]),\
            '_load_mappingMeasurementUnit_measurement_database: The keys in the database do not match the expected keys.'
        
        # Load the data into the measurement_unit object
        mea_id_key = mappingUnit.get_key_measurementId()
        separator = self._default_separator
        path_avg = None
        path_rawlist = None
        for row in rows:
            row:sql.Row
            dict_row = {}
            mea_id = str(int(row[mea_id_key]))
            for key in row.keys():
                if row[key] is None:
                    dict_row[key] = None
                elif value_types[key] == str:
                    dict_row[key] = row[key]
                elif value_types[key] == float:
                    dict_row[key] = float(row[key])
                elif value_types[key] == int:
                    dict_row[key] = int(float(row[key]))
                elif value_types[key] == pd.DataFrame:
                    path = row[key]
                    path = os.path.join(conn_dirpath,path)
                    if platform.system() == 'Windows':
                        path = path.replace('/', '\\')
                    elif platform.system() == 'Darwin':  # macOS
                        path = path.replace('\\', '/')
                    if path != path_avg:
                        path_avg = path
                        avg_df_read = pd.read_parquet(path_avg)
                    avg_df = avg_df_read.loc[mea_id]
                    dict_row[key] = avg_df
                elif value_types[key] == list[pd.DataFrame]:
                    if not flg_readraw: dict_row[key] = []; continue
                    path = row[key]
                    path = os.path.join(conn_dirpath,path)
                    if platform.system() == 'Windows':
                        path = path.replace('/', '\\')
                    elif platform.system() == 'Darwin':  # macOS
                        path = path.replace('\\', '/')
                    if path != path_rawlist:
                        path_rawlist = path
                        rawlist_df_read = pd.read_parquet(path_rawlist)
                        keys = rawlist_df_read.index.get_level_values(0).unique()
                        list_id = [key.split(separator)[0] for key in keys]
                        list_df_combined = [rawlist_df_read.loc[key] for key in keys]
                    list_df = [df for df_id,df in zip(list_id,list_df_combined) if df_id == mea_id]
                    dict_row[key] = list_df
                else:
                    raise ValueError('_load_mappingMeasurementUnit_measurement_database: The value type is not recognised: {}'\
                        .format(value_types[key]))
            mappingUnit.append_dict_measurement_data(dict_row)
        
        return mappingUnit
            
    def load_MappingMeasurementHub_database(self,hub:MeaRMap_Hub,loadpath:str,
        flg_readraw:bool=True) -> MeaRMap_Hub:
        """
        Loads the mapping measurement data from a database.
        
        Args:
            hub (MappingMeasurement_Hub): mapping_measurement_hub object to be loaded into
            loadpath (str): path to load the data
            flg_readraw (bool): flag to read the raw data (in addition to the averaged spectrum). Defaults to False.
        
        Returns:
            mapping_measurement_new: mapping_measurement object
        """
        assert os.path.exists(loadpath) and os.path.isfile(loadpath), 'load_mappingMeasurement_database: The input loadpath is not correct. Expected a valid file path.'
        assert loadpath[-3:] == '.db', 'load_mappingMeasurement_database: The input loadpath is not correct. Expected a valid database file.'
        
        # Connect to the database
        conn:sql.Connection = sql.connect(loadpath)
        conn.row_factory = sql.Row  # To access the column names
        cursor = conn.cursor()
        
        # Query the sqlite_schema table to get table names
        # Check if the any of the metadata table names exist (check for with and without prefix)
        acceptable_metaTableNames = []
        acceptable_metaTableNames.append(self._dict_default_save_parameters['meta_table'])
        acceptable_metaTableNames.append(self._table_prefix + self._dict_default_save_parameters['meta_table'])
        
        cursor.execute("SELECT name FROM sqlite_schema WHERE type='table';")
        found_tableNames = [row[0] for row in cursor.fetchall()]
        found_metaTableNames = [table_name for table_name in acceptable_metaTableNames if table_name in found_tableNames]
        assert len(found_metaTableNames) == 1, ('load_mappingMeasurement_database: The database does not contain the mapping metadata '
            'table OR more than 1 mapping metadata table found. Metadata table(s) found: {}'.format(found_metaTableNames))
        db_tableName_meta:str = found_metaTableNames[0]
        self._table_prefix_load = self._table_prefix if db_tableName_meta.startswith(self._table_prefix) else ''
        
        # Get the metadata table and store it as a dictionary
        dict_unit_id_to_name = {}
        cursor.execute('SELECT * FROM {}'.format(db_tableName_meta))
        rows = cursor.fetchall()
        for row in rows:
            row: sql.Row
            unit_id = row[self._unit_id_key]
            unit_name = row[self._unit_name_key]
            dict_unit_id_to_name[unit_id] = unit_name
        
        # Load the metadata and measurement data
        # mapping_measurement = MappingMeasurement_Hub()
        mapping_measurement = hub
        for unit_id in dict_unit_id_to_name.keys():
            table_name = self._table_prefix + unit_id
            unit_name = dict_unit_id_to_name[unit_id]
            mappingUnit = MeaRMap_Unit(unit_name=unit_name,unit_id=unit_id)
            mappingUnit = self._load_MappingMeasurementUnit_metadata_database(unit_id,conn,mappingUnit)
            mappingUnit = self._load_MappingMeasurementUnit_measurement_database(unit_id,conn,loadpath,mappingUnit,flg_readraw)
            mapping_measurement.append_mapping_unit(mappingUnit)
        return mapping_measurement
    
    def load_MappingMeasurement_pickle(self,hub:MeaRMap_Hub,loadpath:str) -> MeaRMap_Hub:
        """
        Loads the mapping measurement data from a pickle file.
        
        Args:
            hub (MappingMeasurement_Hub): mapping_measurement_hub object to be loaded into
            loadpath (str): path to load the data
        
        Returns:
            mapping_measurement_new: mapping_measurement object
        """
        assert os.path.exists(loadpath) and os.path.isfile(loadpath), 'load_mappingMeasurement_pickle: The input loadpath is not correct. Expected a valid file path.'
        assert loadpath[-4:] == '.pkl', 'load_mappingMeasurement_pickle: The input loadpath is not correct. Expected a valid pickle file.'
        
        with open(loadpath, 'rb') as file:
            mapping_measurement:MeaRMap_Hub = dill.load(file)
            
        for unitid in mapping_measurement.get_list_MappingUnit_ids():
            hub.append_mapping_unit(mapping_measurement.get_MappingUnit(unitid))
    
    def load_choose(self,mappingHub:MeaRMap_Hub,callback_fast:Callable|None=None,
                    callback:Callable|None=None) -> threading.Thread:
        """
        Choose to either load from database or pickle file.
        
        Args:
            mappingHub (MappingMeasurement_Hub): mapping_measurement_hub object to be loaded into
            callback_fast (Callable): callback function to run after the filedialog. Defaults to None.
            callback (Callable): callback function to run after the loading process. Defaults to None.
        
        Returns:
            threading.Thread: thread of the loading process
        
        Note:
            - The loaded data will be returned in the queue q_out as a tuple of:
                (loaded_measurement,loadpath)
        """
        loadpath = filedialog.askopenfilename(defaultextension='.db',filetypes=[('Database files','*.db'),('Pickle files','*.pkl')])
        
        if loadpath == '':
            if callback is not None: callback()
            return None
        
        if callback_fast is not None: callback_fast()
        
        if loadpath.endswith('.db'):
            self.load_MappingMeasurementHub_database(mappingHub,loadpath)
        elif loadpath.endswith('.pkl'):
            self.load_MappingMeasurement_pickle(mappingHub,loadpath)
            
        if callback is not None: callback()

    def test_database_save_load(self,hub:MeaRMap_Hub):
        """
        Test the saving and loading of the mapping measurement data into and from a database
        
        Args:
            hub (MappingMeasurement_Hub): mapping_measurement_hub object to be used in the test
        """
        print('>>>>> Testing the database save and load <<<<<')
        savedirpath = './sandbox'
        savename = 'test - Copy'
        savepath = os.path.join(savedirpath,savename+'.db')
        thread = self.save_MappingHub_database(hub,savedirpath=savedirpath,savename=savename)
        thread.join()
        mapping_measurement_loaded = self.load_MappingMeasurementHub_database(savepath)
        
        savename2 = 'test - Copy2'
        thread = self.save_MappingHub_database(mapping_measurement_loaded,savedirpath=savedirpath,savename=savename2)
        thread.join()
        print('>>>>> Testing the database save and load: Done <<<<<')


def generate_dummy_mappingHub(numx:int=6,numy:int=8,repeat:int=3) -> MeaRMap_Hub:
    """
    Generates a dummy mapping measurement data for testing purposes.
    
    Args:
        numx (int): number of x-coordinates. Defaults to 6.
        numy (int): number of y-coordinates. Defaults to 8.
        repeat (int): number of repeated measurements. Defaults to 3.
    
    Returns:
        mapping_measurement_new: mapping_measurement object
    """
    from iris.controllers.raman_spectrometer_controller_dummy import SpectrometerController_Dummy as raman_spectrometer_controller
    import numpy as np
    
    spectrometer = raman_spectrometer_controller()
    
    print('>>>>> Generating the data <<<<<')
    z = 2
    listx = list(np.linspace(0,3,numx))
    listy = list(np.linspace(0,4,numy))
    storage_unit = MeaRMap_Unit(unit_name='dummy'+get_timestamp_sec())
    max_len = len(listx)*len(listy)
    i=0
    for x in listx:
        for y in listy:
            # Generate the measurements
            mea_single = MeaRaman(timestamp=get_timestamp_us_int(),int_time_ms=10,
                laserPower_mW=DAEnum.LASER_POWER_MILLIWATT.value,laserWavelength_nm=DAEnum.LASER_WAVELENGTH_NM.value)
            for _ in range(repeat):
                df,_,_ = spectrometer.measure_spectrum()
                mea_single.set_raw_list(df_mea=df,timestamp_int=get_timestamp_us_int())
        
            mea_single.check_uptodate(autoupdate=True)
            
            # Assign the measurement to a storage unit
            coor = (x,y,z)
            storage_unit.append_ramanmeasurement_data(get_timestamp_us_int(),coor,mea_single)
            i+=1
            print('Generating data: {} of {}'.format(i,max_len))
    
    # Assign the storage unit to the main storage
    print('>>>>> Assigning the data to the storage <<<<<')
    storage_main = MeaRMap_Hub()
    storage_main.append_mapping_unit(storage_unit)
    
    return storage_main
    
class PlotterOptions(Enum):
    """
    Enum class for the plotter options
    """
    interp = 'Triangle interpolation'
    scatt = 'Scatter plot'
    empty = 'Empty plot'
    scatt_kw_size = 'size'
    
class MeaRMap_Plotter:
    """
    Class to plot the mapping measurement data from the MappingMeasurement_Unit object
    """
    def __init__(self, figsize_pxl = (800,600)):
        self._figsize_pxl = figsize_pxl
        self._dpi = plt.rcParams['figure.dpi']
        self._figsize_in = (self._figsize_pxl[0]/self._dpi,self._figsize_pxl[1]/self._dpi)
        
        self.dict_plotter_options = {
            PlotterOptions.interp.value: self.plot_heatmap_interp,
            PlotterOptions.scatt.value: self.plot_heatmap_scatter,
            PlotterOptions.empty.value: self.plot_heatmap_nothing
        }
        
        self.dict_plotter_kwargs = {
            PlotterOptions.interp.value: {},
            PlotterOptions.scatt.value: {
                PlotterOptions.scatt_kw_size.value: (float,'Size of the scatter plot')
            },
            PlotterOptions.empty.value: {}
        }
        
    def get_plotter_options(self) -> tuple[dict,dict]:
        """
        Returns the plotter options
        
        Returns:
            tuple: dictionary of plotter options and dictionary of plotter kwargs
            
        Note:
            - The plotter options are the plotter functions corresponding to the plotter options
            - The plotter kwargs are the arguments to be passed to the plotter options containing
                a dict of tuples of (arg_name,arg_type) for each argument, and the key is the plotter option
                corresponding to the plotter option in the plotter options dictionary
        """
        return (self.dict_plotter_options,self.dict_plotter_kwargs)

    def plot_typehinting(self, mapping_unit:MeaRMap_Unit|None=None, wavelength:float|None=None,
                     clim:tuple[float,float]|None=None,title = '2D Mapping', fig:Figure|None=None, ax:Axes|None=None,
                     clrbar:Colorbar|None=None) -> tuple[Figure,Axes,Colorbar]:
        """
        DOES NOTHING but to show the type hinting for the plotter functions
        
        Plots a heatmap plot from a mapping unit, given its coordinates, and labels indicating the data column info.
        
        Note:
            - not providing the mapping_unit will plot and return an empty heatmap
            - providing a figure and axis will plot the heatmap on the given figure and axis. BOTH fig and ax should be provided.
            - providing a colorbar will reset the colorbar. If no fig and ax are provided, this option is ignored.
            
        Args:
            mapping_unit (MappingMeasurement_Unit): MappingMeasurement_Unit object to plot
            wavelength (float): wavelength to plot the heatmap
            clim (tuple[float,float], optional): color limit for the heatmap. Defaults to None.
            title (str, optional): title of the resulting graph. Defaults to '2D Mapping'.
            fig (matplotlib.figure.Figure, optional): figure to plot the heatmap. Defaults to None.
            ax (matplotlib.axes._subplots.AxesSubplot, optional): axis to plot the heatmap. Defaults to None.
            clrbar (matplotlib.colorbar.Colorbar, optional): colorbar to plot the heatmap. Defaults to None.
            
        Returns:
            tuple: (figure, axis, clrbar) of the plot
        """
        raise NotImplementedError('plot_typehinting: This function is only for typehinting.')
    
    def plot_heatmap_nothing(self, mapping_unit:MeaRMap_Unit|None=None, wavelength:float|None=None,
                     clim:tuple[float,float]|None=None,title = '2D Mapping', fig:Figure|None=None, ax:Axes|None=None,
                     clrbar:Colorbar|None=None) -> tuple[Figure,Axes,Colorbar]:
        """
        Plots nothing but returns the figure, axis, and colorbar

        Args:
            mapping_unit (MappingMeasurement_Unit): MappingMeasurement_Unit object to plot
            wavelength (float): wavelength to plot the heatmap
            clim (tuple[float,float], optional): color limit for the heatmap. Defaults to None.
            title (str, optional): title of the resulting graph. Defaults to '2D Mapping'.
            fig (matplotlib.figure.Figure, optional): figure to plot the heatmap. Defaults to None.
            ax (matplotlib.axes._subplots.AxesSubplot, optional): axis to plot the heatmap. Defaults to None.
            clrbar (matplotlib.colorbar.Colorbar, optional): colorbar to plot the heatmap. Defaults to None.
            
        Returns:
            tuple: (figure, axis, clrbar) of the plot
        """
        if isinstance(mapping_unit,MeaRMap_Unit) and wavelength is not None:    
            # Retrieve the measurement data
            df_plot:pd.DataFrame = mapping_unit.get_heatmap_table(wavelength)
            label_x,label_y,_,_,label_intensity = mapping_unit.get_labels()
            
            # Convert the x-coordinate and y-coordinate into string to prevent any issues
            values = df_plot.values
            x_loc = df_plot.columns.get_loc(label_x)
            y_loc = df_plot.columns.get_loc(label_y)
            intensity_loc = df_plot.columns.get_loc(label_intensity)
            
            x_val = [val for val in values[:,x_loc]]
            y_val = [val for val in values[:,y_loc]]
            
            x_min = min(x_val)
            x_max = max(x_val)
            y_min = min(y_val)
            y_max = max(y_val)
        
        if any([not isinstance(mapping_unit,MeaRMap_Unit), wavelength is None]):
            return (fig,ax,None)
        
        if all([isinstance(fig,Figure), isinstance(ax,Axes)]):
            try:
                if isinstance(clrbar,Colorbar):
                    clrbar.remove()
                ax.clear()
            except:
                fig,ax = plt.subplots(figsize=self._figsize_in)
        else:
            fig,ax = plt.subplots(figsize=self._figsize_in)
        
        if any([not isinstance(mapping_unit,MeaRMap_Unit), wavelength is None]):
            return (fig,ax,None)
        
        ax:Axes
        ax.set_aspect(AppPlotEnum.PLT_ASPECT.value)
        ax.set_title(title)
        ax.set_xlabel(AppPlotEnum.PLT_LBL_X_AXIS.value)
        ax.set_ylabel(AppPlotEnum.PLT_LBL_Y_AXIS.value)
        
        ax.set_xlim(x_min,x_max)
        ax.set_ylim(y_min,y_max)
        
        return (fig,ax,None)
    
    def plot_heatmap_interp(self, mapping_unit:MeaRMap_Unit|None=None, wavelength:float|None=None,
                     clim:tuple[float,float]|None=None,title = '2D Mapping', fig:Figure|None=None, ax:Axes|None=None,
                     clrbar:Colorbar|None=None) -> tuple[Figure,Axes,Colorbar]:
        """
        Plots a heatmap plot from a mapping unit, given its coordinates, and labels indicating the data column info.
        
        Note:
            - not providing the mapping_unit will plot and return an empty heatmap
            - providing a figure and axis will plot the heatmap on the given figure and axis. BOTH fig and ax should be provided.
            - providing a colorbar will reset the colorbar. If no fig and ax are provided, this option is ignored.
            
        Args:
            mapping_unit (MappingMeasurement_Unit): MappingMeasurement_Unit object to plot
            wavelength (float): wavelength to plot the heatmap
            clim (tuple[float,float], optional): color limit for the heatmap. Defaults to None.
            title (str, optional): title of the resulting graph. Defaults to '2D Mapping'.
            fig (matplotlib.figure.Figure, optional): figure to plot the heatmap. Defaults to None.
            ax (matplotlib.axes._subplots.AxesSubplot, optional): axis to plot the heatmap. Defaults to None.
            clrbar (matplotlib.colorbar.Colorbar, optional): colorbar to plot the heatmap. Defaults to None.
            
        Returns:
            tuple: (figure, axis, clrbar) of the plot
        """
        # Do the calculation first for a lower figure off time
        # (i.e., when the ax is cleared and not yet reassigned)
        if isinstance(mapping_unit,MeaRMap_Unit) and wavelength is not None:    
            # Retrieve the measurement data
            df_plot:pd.DataFrame = mapping_unit.get_heatmap_table(wavelength)
            label_x,label_y,_,_,label_intensity = mapping_unit.get_labels()
            
            # Convert the x-coordinate and y-coordinate into string to prevent any issues
            values = df_plot.values
            x_loc = df_plot.columns.get_loc(label_x)
            y_loc = df_plot.columns.get_loc(label_y)
            intensity_loc = df_plot.columns.get_loc(label_intensity)
            
            x_val = [val for val in values[:,x_loc]]
            y_val = [val for val in values[:,y_loc]]
            intensity = values[:,intensity_loc]
        
        if all([isinstance(fig,Figure), isinstance(ax,Axes)]):
            try:
                if isinstance(clrbar,Colorbar):
                    clrbar.remove()
                ax.clear()
            except:
                fig,ax = plt.subplots(figsize=self._figsize_in)
        else:
            fig,ax = plt.subplots(figsize=self._figsize_in)
        
        if any([not isinstance(mapping_unit,MeaRMap_Unit), wavelength is None]):
            return (fig,ax,None)
        
        # Check if the the data can be plot using tripcolor
        if any([len(intensity) < 3, len(set(x_val)) < 2, len(set(y_val)) < 2]):
            return (fig,ax,None)
        
        ax:Axes
        ax.set_aspect(AppPlotEnum.PLT_ASPECT.value)
        
        # Plot the tripcolor using your existing data
        # Note we're passing x, y directly, and not using `triangles`
        tpc = ax.tripcolor(x_val, y_val, intensity, cmap=AppPlotEnum.PLT_COLOUR_MAP.value,
                           shading=AppPlotEnum.PLT_SHADING.value, edgecolors=AppPlotEnum.PLT_EDGE_COLOUR.value)
        
        # Add colourbar and labels
        cbar = fig.colorbar(ax.collections[0], ax=ax)
        ax.set_title(title)
        ax.set_xlabel(AppPlotEnum.PLT_LBL_X_AXIS.value)
        ax.set_ylabel(AppPlotEnum.PLT_LBL_Y_AXIS.value)
        
        # Set the colourbar limits
        if isinstance(clim,tuple) and len(clim) == 2:
            if isinstance(clim[0],float) and isinstance(clim[1],float):
                list(clim).sort()
            cbar.mappable.set_clim(vmin=clim[0],vmax=clim[1])
        
        # print(f"Number of figures: {plt.get_fignums()}")
        # print(f"Number of axes: {len(fig.axes)}")
        
        return (fig,ax,cbar)
    
    def plot_heatmap_scatter(self, mapping_unit:MeaRMap_Unit|None=None, wavelength:float|None=None,
                     clim:tuple[float,float]|None=None, title = '2D Mapping', size:float|None=None,
                     fig:Figure|None=None, ax:Axes|None=None, clrbar:Colorbar|None=None) -> tuple[Figure,Axes,Colorbar]:
        """
        Plots a heatmap plot from a mapping unit, given its coordinates, and labels indicating the data column info.
        
        Note:
            - not providing the mapping_unit will plot and return an empty heatmap
            - providing a figure and axis will plot the heatmap on the given figure and axis. BOTH fig and ax should be provided.
            - providing a colorbar will reset the colorbar. If no fig and ax are provided, this option is ignored.
            
        Args:
            mapping_unit (MappingMeasurement_Unit): MappingMeasurement_Unit object to plot
            wavelength (float): wavelength to plot the heatmap
            clim (tuple[float,float], optional): color limit for the heatmap. Defaults to None.
            title (str, optional): title of the resulting graph. Defaults to '2D Mapping'.
            size (float, optional): size of the scatter plot. Defaults to None.
            fig (matplotlib.figure.Figure, optional): figure to plot the heatmap. Defaults to None.
            ax (matplotlib.axes._subplots.AxesSubplot, optional): axis to plot the heatmap. Defaults to None.
            clrbar (matplotlib.colorbar.Colorbar, optional): colorbar to plot the heatmap. Defaults to None.
            
        Returns:
            tuple: (figure, axis, clrbar) of the plot
        """
        # Do the calculation first for a lower figure off time
        # (i.e., when the ax is cleared and not yet reassigned)
        if isinstance(mapping_unit,MeaRMap_Unit) and wavelength is not None:    
            # Retrieve the measurement data
            df_plot:pd.DataFrame = mapping_unit.get_heatmap_table(wavelength)
            label_x,label_y,_,_,label_intensity = mapping_unit.get_labels()
            
            # Convert the x-coordinate and y-coordinate into string to prevent any issues
            values = df_plot.values
            x_loc = df_plot.columns.get_loc(label_x)
            y_loc = df_plot.columns.get_loc(label_y)
            intensity_loc = df_plot.columns.get_loc(label_intensity)
            
            x_val = [val for val in values[:,x_loc]]
            y_val = [val for val in values[:,y_loc]]
            intensity = values[:,intensity_loc]
        
        if all([isinstance(fig,Figure), isinstance(ax,Axes)]):
            try:
                if isinstance(clrbar,Colorbar):
                    clrbar.remove()
                ax.clear()
            except:
                fig,ax = plt.subplots(figsize=self._figsize_in)
        else:
            fig,ax = plt.subplots(figsize=self._figsize_in)
        
        if any([not isinstance(mapping_unit,MeaRMap_Unit), wavelength is None]):
            return (fig,ax,None)
        
        # Check if the the data can be plot using tripcolor
        if any([len(intensity) < 3, len(set(x_val)) < 2, len(set(y_val)) < 2]):
            return (fig,ax,None)
        
        ax:Axes
        ax.set_aspect(AppPlotEnum.PLT_ASPECT.value)
        
        figsize = fig.get_size_inches()
        number_of_points = len(x_val)
        
        point_size = (figsize[0]*figsize[1])/number_of_points*750 if not isinstance(size,float) else size
        ax.scatter(x_val, y_val, c=intensity, cmap=AppPlotEnum.PLT_COLOUR_MAP.value, s=point_size, linewidths=0, marker='s')

        # Add colourbar and labels
        cbar:Colorbar = fig.colorbar(ax.collections[0], ax=ax)
        ax.set_title(title)
        ax.set_xlabel(AppPlotEnum.PLT_LBL_X_AXIS.value)
        ax.set_ylabel(AppPlotEnum.PLT_LBL_Y_AXIS.value)
        
        # Set the colourbar limits
        if isinstance(clim,tuple) and len(clim) == 2:
            if isinstance(clim[0],float) and isinstance(clim[1],float):
                list(clim).sort()
            cbar.mappable.set_clim(vmin=clim[0],vmax=clim[1])
        
        return (fig,ax,cbar)
    
def test_datasaveload_system_txt(storage_main:MeaRMap_Hub|None=None):
    if storage_main is None: storage_main = generate_dummy_mappingHub()
    
    handler = MeaRMap_Handler()
    thread = handler.save_MappingUnit_ext_prompt(storage_main.get_MappingUnit(storage_main.get_list_MappingUnit_ids()[0]),flg_saveraw=True)
    thread.join()
    
def test_datasaveload_system(storage_main:MeaRMap_Hub|None=None):
    # Generate the dummy data (mapping measurement hub)
    if storage_main is None: storage_main = generate_dummy_mappingHub()
    
    # Save the measurement
    print('>>>>> Saving the data <<<<<')
    subfolder = 'sandbox'
    mainfolder = os.path.abspath('./')
    subfolder_path = os.path.join(mainfolder,subfolder)
    if not os.path.exists(subfolder_path): os.makedirs(subfolder_path)
    savepath = os.path.join(subfolder_path,'test.db')
    
    savedirpath = os.path.dirname(savepath)
    savename = os.path.basename(savepath)
    
    handler = MeaRMap_Handler()
    thread = handler.save_MappingHub_database(storage_main,savedirpath,savename)
    thread.join()
    
    print('>>>>> Loading the data <<<<<')
    loaded_main = handler.load_MappingMeasurementHub_database(loadpath=savepath)
    
    print('>>>>> Retrieving the unit <<<<<')
    list_id = loaded_main.get_list_MappingUnit_ids()
    print('IDs: {}'.format(list_id))
    loaded_unit = loaded_main.get_MappingUnit(list_id[-1])
    print(loaded_unit)
    
    print('>>>>> Retrieving the data <<<<<')
    wavelength_list = loaded_unit.get_list_wavelengths()
    # print('Wavelengths: {}'.format(wavelength_list))
    print(loaded_unit.get_dict_unit_metadata())
    key_id = loaded_unit.get_key_measurementId()
    measurements = loaded_unit.get_dict_measurements()
    list_id = measurements[key_id]
    id_ex = list_id[-5]
    
    df_avg = loaded_unit.get_RamanMeasurement_df(id_ex)
    print(df_avg)
    
def test_mappingHub():
    """
    Test the MappingMeasurement_Hub class

    Returns:
        MappingMeasurement_Hub: dummy hub object
    """
    dummy_hub = MeaRMap_Hub()
    dummy_hub.test_generate_dummy()
    dummy_hub.self_report()
    return dummy_hub
    
def test_handler():
    hub = test_mappingHub()
    handler = MeaRMap_Handler()
    handler.test_database_save_load(hub)
    
if __name__ == '__main__':
    pass
    test_handler()
    
    # test_datasaveload_system()
    # test_datasaveload_system_txt()