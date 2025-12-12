"""
A class that processes the measurement data from a Raman spectrometer
(spectra_dummy for an example file format)

Designed around the QE Pro spectrometer from Ocean Insight.

Note:
    Note that the timestamp is meant to indicate the time the measurement was taken.
        - Only 1 timestamp can be saved even if there are multiple raw spectra saved.
        - In such case, it is recommended to use multiple measurement instances instead.
        - The multiple really are only intended for background measurements and multi-acquisition measurements.
        
    Operations such as background subtraction, calibration, etc. are done externally and their results should 
    be saved separately as a new measurement instance.
"""
import matplotlib
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.colorbar import Colorbar
import matplotlib.pyplot as plt

# Force matplotlib to use the backend to prevent memory leak
matplotlib.use('Agg')
plt.tight_layout()

import pandas as pd
import numpy as np
import cv2
import queue
import os
from typing import Self, Literal

import bisect

from glob import glob
import pickle

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))


from iris.utils.general import *

from iris import DataAnalysisConfigEnum
from iris.gui import AppPlotEnum

class MeaRaman():
    """Analyses the data given a dataset and plot it
    """
    def __init__(self,
                 timestamp:int|None=None,
                 int_time_ms:int|None=None,
                 laserPower_mW:float|None=None,
                 laserWavelength_nm:float|None=None,
                 extra_metadata:dict={},
                 reconstruct:bool=False) -> None:
        """
        Initialises the raman measurement.
        
        Args:
            timestamp (int): measurement timestamp in integer [microsec]
            int_time (int): integration time used for the measurement
            laserPower_mW (float, optional): laser power in mW
            laserWavelength_nm (float, optional): laser wavelength in nm
            dict_extra_metadata (dict, optional): extra metadata to be stored. Defaults to None.
            reconstruct (bool, optional): reconstruct the measurement from a saved file. Defaults to False.
        
        Note:
            - If reconstruct is True, the parameter checks are bypassed
        """
        if not reconstruct: assert all([isinstance(timestamp,(int,float)),isinstance(int_time_ms,(int,float)),isinstance(laserPower_mW,(int,float)),
            isinstance(laserWavelength_nm,(int,float)),isinstance(extra_metadata,(dict,type(None)))]),\
            'Timestamp, integration time, and laser power, and laser wavelength should be integers, integers, and floats respectively'
        
    # >>> Class version <<<
        self.version = '0.2.0_2024.08.22'  # Version of the class
        
    # >>> Measurement storage <<<
        self._measurement_time = timestamp       # Created instance time
        self._integration_time_ms:int = int_time_ms    # Integration time used for the measuremrent in milliseconds
        
        self._spectrum_rawlist:list[pd.DataFrame] = []      # list of pandas df (of the raw measurements): for storage
        
        self._spectrum_analysed:pd.DataFrame|None = None            # pandas df: stores the averaged spectrum
        
    # >>> Name parameters <<<
        self.label_wavelength = DataAnalysisConfigEnum.WAVELENGTH_LABEL.value
        self.label_intensity = DataAnalysisConfigEnum.INTENSITY_LABEL.value
        
    # >>> Analysis parameters <<<
        self._tolerance = DataAnalysisConfigEnum.SIMILARITY_THRESHOLD.value  # Tolerance to see if a wavelength is close to another for operations
        
    # >>> Data verification related <<<
        self._flg_uptodate = True    # Indicates if the stored background averaged spectrum is up to date with the raw_list measurements
        
    # >>> Offloading/storage <<<
        self._dict_metadata = {
            'integration_time_ms':self._integration_time_ms,
            'accumulation':0,
            'laser_power_milliwatt': laserPower_mW,
            'laser_wavelength_nm': laserWavelength_nm,
            'version': self.version
        }
        
        self._noneditable_metadata_keys = ['version','integration_time_ms','accumulation']
        assert all([key in self._dict_metadata.keys() for key in self._noneditable_metadata_keys]), 'Non-editable metadata keys are not in the metadata dictionary'
        
        assert all([key not in self._dict_metadata.keys() for key in extra_metadata.keys()]),\
            'Extra metadata keys should not overlap with the default metadata keys'
        self._dict_metadata.update(extra_metadata) # Add extra metadata if any
        
    def reconstruct(self,measurement_id:int,metadata:dict,spec_analysed:pd.DataFrame,spec_rawlist:list[pd.DataFrame]|None=None):
        """
        Reconstructs the measurement from a saved file
        
        Args:
            measurement_id (int): ID of the measurement, usually the timestamp [microsec] in integer
            metadata (dict): metadata of the measurement
            spec_analysed (pd.DataFrame): analysed spectrum
            spec_rawlist (list[pd.DataFrame], optional): raw measurements. Defaults to None.
        
        Note:
            Since the rawlist is rarely used, it can be skipped if not needed
        """
        # For backward compatibility. 'acquisition_number' is changed to 'accumulation' in version 2.4.0
        if 'acquisition_number' in list(metadata.keys()):
            metadata['accumulation'] = metadata['acquisition_number']
            metadata.pop('acquisition_number')
        
        assert all([isinstance(measurement_id,int),isinstance(metadata,dict),isinstance(spec_analysed,pd.DataFrame),isinstance(spec_rawlist,(type(None),list))]),\
            'metadata should be a dictionary, spec_analysed should be a pandas DataFrame, and spec_rawlist should be a list of pandas DataFrames'
        assert all([key in metadata.keys() for key in self._dict_metadata.keys()]), 'The metadata keys are not the same'
        assert all([key in spec_analysed.columns for key in [self.label_wavelength,self.label_intensity]]),\
            'The analysed spectrum columns does not contain the required columns'
        
        self._dict_metadata = metadata
        self._spectrum_analysed = spec_analysed
        self._measurement_time = measurement_id
        self._integration_time_ms = metadata['integration_time_ms']
        if spec_rawlist:
            self._spectrum_rawlist = spec_rawlist
        
    def get_latest_timestamp(self) -> int:
        """
        Returns the latest timestamp of the measurement
        
        Returns:
            int: latest timestamp
        """
        return self._measurement_time
        
    def update_editable_metadata(self,key:str,value):
        """
        Updates the editable metadata
        
        Args:
            key (str): key to update
            value: value to update
        """
        assert key in self._dict_metadata.keys(), 'The key is not in the metadata dictionary'
        assert key not in self._noneditable_metadata_keys, 'The key is non-editable'
        self._dict_metadata[key] = value
        
    def get_editable_metadata_keys(self) -> list[str]:
        """
        Returns the editable metadata keys
        
        Returns:
            list: list of editable metadata keys
        """
        list_keys = [key for key in self._dict_metadata.keys() if key not in self._noneditable_metadata_keys]
        return list_keys
        
    def get_measurements(self) -> tuple[list[pd.DataFrame],pd.DataFrame]:
        """
        Returns the stored measurements
        
        Returns:
            tuple[list[pd.DataFrame],pd.DataFrame]: list of raw measurements, averaged spectrum
        """
        return self._spectrum_rawlist,self._spectrum_analysed
        
    def check_measurement_exist(self) -> bool:
        """
        Checks if the measurement data exists
        
        Returns:
            bool: True if the measurement data exists, False otherwise
        """
        if len(self._spectrum_rawlist) == 0 and not isinstance(self._spectrum_analysed,pd.DataFrame): return False
        self.check_uptodate(autoupdate=True)
        return True
        
    def print_reports(self):
        """
        Prints the reports of the recorded measurements so far
        """
        print('Measurement time:',self._measurement_time)
        print('Integration time:',self._integration_time_ms)
        print('Collected measurements:',len(self._spectrum_rawlist))
        
    def get_laser_params(self) -> tuple[float,float]:
        """
        Returns the laser parameters
        
        Returns:
            tuple[float,float]: laser power, laser wavelength
        """
        return self._dict_metadata['laser_power_milliwatt'],self._dict_metadata['laser_wavelength_nm']
        
    def get_laserMetadata_key(self) -> tuple[str,str]:
        """
        Returns the keys of the laser metadata
        
        Returns:
            tuple[str]: keys of the laser metadata (laser power, laser wavelength)
        """
        return ('laser_power_milliwatt','laser_wavelength_nm')
        
    def get_metadata(self):
        """
        Returns the metadata of the measurement
        
        Returns:
            dict: metadata
        """
        self.check_uptodate(autoupdate=True)
        return self._dict_metadata
        
    def check_uptodate(self,autoupdate=True):
        """
        Checks if the analysed variables (avg and sub) are up-to-date and
        automatically updates them. Also updates the metadata.
        
        Returns:
            bool: final state of the variables (up-to-date or not)
        """
        # Updates the metadata first
        self._dict_metadata['accumulation'] = len(self._spectrum_rawlist)
        
        if autoupdate and not self._flg_uptodate:
            self._spectrum_analysed = self.average(self._spectrum_rawlist)
            self._flg_uptodate = True
        return self._flg_uptodate
    
    def get_intensity(self, wavelength:float|None=None, raman_shift:float|None=None) -> float:
        """
        Retrieves the intensity at a specific wavelength.

        Args:
            wavelength (float | None, optional): The wavelength to search for. Defaults to None.
            raman_shift (float | None, optional): The Raman shift value to retrieve. Defaults to None.

        Returns:
            float: The intensity at the specified wavelength.
        """
        if not any([isinstance(wavelength,(type(None),int,float)),isinstance(raman_shift,(type(None),int,float))]):
            raise ValueError("Either 'wavelength' or 'raman_shift' must be provided")
        if all([isinstance(wavelength,(int,float)),isinstance(raman_shift,(int,float))]):
            raise ValueError("Only one of 'wavelength' or 'raman_shift' should be provided")
        
        if raman_shift is not None:
            # If raman_shift is provided, convert it to wavelength
            wavelength = convert_ramanshift_to_wavelength(raman_shift, self.get_laser_params()[1])
        
        idx = self.get_wavelength_index(wavelength)
        
        idx_start = self._spectrum_analysed.index[0]
        intensity = self._spectrum_analysed[self.label_intensity][idx+idx_start]
        
        return intensity

    def get_wavelength_index(self,wavelength:float) -> int:
        """
        Returns the index of the given wavelength in the spectrum (if it does not exist, returns the closest index)

        Args:
            wavelength (float): wavelength to search for

        Returns:
            int: index of the wavelength in the spectrum
        """
        assert isinstance(wavelength,(int,float)), 'wavelength should be an integer or float'
        if len(self._spectrum_rawlist) == 0 and len(self._spectrum_analysed) == 0: raise ValueError('No measurements have been taken yet')
        
        if len(self._spectrum_rawlist) == 0: spectrum = self._spectrum_analysed
        else: spectrum = self._spectrum_rawlist[0]
        
        # Get the wavelength list
        wavelength_list = spectrum[self.label_wavelength].values
        # Get the index of the closest wavelength
        idx = bisect.bisect_left(wavelength_list,wavelength)
        
        # Convert idx to the closest wavelength
        if idx == 0 or idx == len(wavelength_list):
            idx = idx
        # Check if the wavelength is closer to the current or the next one
        elif abs(wavelength_list[idx-1]-wavelength) < abs(wavelength_list[idx]-wavelength):
            idx = idx-1
        return idx
    
    def get_raw_list(self):
        """
        Returns the raw list of measurements
        
        Returns:
            list: pd.df of raw measurements
        """
        return self._spectrum_rawlist
    
    def set_raw_list(self,df_mea:pd.DataFrame,timestamp_int:int,max_accumulation:int=1000) -> list[pd.DataFrame]:
        """
        Adds a measurement dataframe to the stored list of continuous measurements
        
        Args:
            df_mea (pd.DataFrame, optional): df of the measurement. Defaults to None.
            timestamp_int (int, optional): timestamp of the measurement in integer [microsec].
            If none, takes the current timestamp. Defaults to None.
        """
        assert isinstance(df_mea,pd.DataFrame), "'df_mea' should be a pandas DataFrame"
        assert isinstance(timestamp_int,int), "'timestamp_int' should be an integer"
        
        self._measurement_time = timestamp_int
        
        # Updates the flag to let the class know that a new measurement has been added to the list
        self._flg_uptodate = False

        if len(self._spectrum_rawlist) < max_accumulation:
            self._spectrum_rawlist.append(df_mea)
        else:
            self._spectrum_rawlist.pop(0)
            self._spectrum_rawlist.append(df_mea)
        return self._spectrum_rawlist
        
    def get_average_rawlist(self,spectrum_rawlist) -> pd.DataFrame:
        """
        Updates the value of the averaged and background substracted 
        spectra of the multimeasurement
        
        Args:
            spectrum_rawlist (list): list of raw measurements (pd.df)
        
        Returns:
            pd.df: averaged spectrum
        """
        spectrum_avg = self.average(spectrum_rawlist)
        return spectrum_avg
    
    def calculate_analysed(self) -> pd.DataFrame:
        """
        Calculates the analysed values (averaged and subtracted)
        
        Returns:
            pd.DataFrame: analysed spectra
        """
        spectrum_analysed = self.average(self._spectrum_rawlist)
        self._flg_uptodate = True
        self._spectrum_analysed = spectrum_analysed
        return spectrum_analysed
    
    def set_analysed(self,spectrum_analysed:pd.DataFrame|np.ndarray):
        """
        Sets the analysed values (averaged and subtracted)
        
        Args:
            spectrum_analysed (pd.DataFrame|np.ndarray): analysed spectra
        """
        if not isinstance(spectrum_analysed,(pd.DataFrame,np.ndarray)):
            raise TypeError("'spectrum_analysed' should be a pandas DataFrame or numpy array")
        self._flg_uptodate = True
        if isinstance(spectrum_analysed,pd.DataFrame): self._spectrum_analysed = spectrum_analysed
        else:
            if not spectrum_analysed.shape[1] == 2: raise ValueError("'spectrum_analysed' should have 2 columns (wavelength, intensity)")
            self._spectrum_analysed = pd.DataFrame(spectrum_analysed, columns=[self.label_wavelength, self.label_intensity])
        
    def get_analysed(self, type:Literal['DataFrame','array']='DataFrame') -> pd.DataFrame|np.ndarray|None:
        """
        Get the analysed spectra.
        
        Args:
            type (Literal['DataFrame', 'array']): The type of the output
            
        Returns:
            pd.DataFrame|np.ndarray|None: analysed spectra or None if not available
        """
        if not self._flg_uptodate: print('!!!!! Returned analysed spectra are NOT UP-TO-DATE !!!!!')
        if not isinstance(self._spectrum_analysed, pd.DataFrame): return None
        
        if type == 'DataFrame': ret = self._spectrum_analysed
        else: ret = self._spectrum_analysed.to_numpy()

        return ret
    
    def _get_any_measurement(self) -> pd.DataFrame:
        """
        Returns a dataframe, either from the analysed or the rawlist

        Returns:
            pd.DataFrame: Dataframe of the measurement.
        """
        assert self.check_measurement_exist(), 'No valid measurement exists to get Raman shift array.'
        if not isinstance(self._spectrum_analysed, pd.DataFrame):
            return self._spectrum_rawlist[-1]
        elif isinstance(self._spectrum_analysed, pd.DataFrame):
            return self._spectrum_analysed
        else: raise ValueError('Analysed spectra is not in a valid format')
    
    def get_arr_wavelength(self) -> np.ndarray:
        """
        Returns the wavelength array of the analysed spectra

        Returns:
            np.ndarray: Wavelength array
        """
        df = self._get_any_measurement()
        return df[self.label_wavelength].to_numpy()

    def get_arr_ramanshift(self) -> np.ndarray:
        """
        Returns the Raman shift array of the analysed spectra
        
        Returns:
            np.ndarray: Raman shift array
        """
        df = self._get_any_measurement()
        
        laser_wavelength = self.get_laser_params()[1]
        wavelength_array = df[self.label_wavelength].to_numpy()
        ramanshift_array = convert_wavelength_to_ramanshift(wavelength_array, laser_wavelength)
        
        return ramanshift_array # type: ignore ; It's definitely a np.ndarray
    
    def get_arr_intensity(self, mea_type:Literal['analysed','raw','any']='analysed') -> np.ndarray:
        """
        Returns the intensity array of the analysed or raw spectra
        
        Args:
            mea_type (Literal['analysed','raw'], optional): Type of spectra to get the intensity from. Defaults to 'analysed'.
        
        Returns:
            np.ndarray: Intensity array
        """
        assert mea_type in ['analysed','raw','any'], "'type' should be either 'analysed', 'raw', or 'any'"
        assert self.check_measurement_exist(), 'No valid measurement exists to get intensity array.'
        if mea_type == 'analysed': df = self._spectrum_analysed
        elif mea_type == 'raw': df = self._spectrum_rawlist[-1]
        elif mea_type == 'any': df = self._get_any_measurement()
        df:pd.DataFrame
        return df[self.label_intensity].to_numpy()

    @staticmethod
    def average(spectra_list:list[pd.DataFrame]) -> pd.DataFrame:
        """
        Averages a given spectra list. Refer to the wavelenght_name and intensity_name
        for the required column names in the input dataframes.
        
        The program also checks if the spectra being averaged the same up to 0.1nm

        Args:
            spectra_list (list): List of spectra dataframes in the same form as the one for plot

        Returns:
            Dataframe: Average spectra in the same form as the input
        """
        lbl_wvl = DataAnalysisConfigEnum.WAVELENGTH_LABEL.value
        lbl_int = DataAnalysisConfigEnum.INTENSITY_LABEL.value
        intensity_list = [spectra[lbl_int].values for spectra in spectra_list]
        wavelength_list = [spectra[lbl_wvl].values for spectra in spectra_list]
        tolerance = DataAnalysisConfigEnum.SIMILARITY_THRESHOLD.value
        
        def wavelength_similarity_check(wavelength_list):
            def check(wl1, wl2):
                return all(abs(w1 - w2) <= tolerance for w1, w2 in zip(wl1, wl2))
            similar = all(check(wl, wavelength_list[0]) for wl in wavelength_list[1:])
            return similar
        
        # Check if the wavelengths are similar and warns the user if they're different
        if not wavelength_similarity_check(wavelength_list):
            print("!!!!! SPECTRA WITH DIFFERENT WAVELENGTHS BEING AVERAGED !!!!!")
            
        # Calculate the average spectrum, extract the wavelengths, and put on the current timestamp
        all_intensities = np.vstack([intensity_list[i] for i in range(len(intensity_list))])
        avg_intensity = np.mean(all_intensities, axis=0)
        wavelength = spectra_list[0][lbl_wvl]
        
        # Write the average spectrum dataframe
        avg_spectra = pd.DataFrame({
            lbl_wvl: wavelength,
            lbl_int: avg_intensity
        })
        return avg_spectra
    
    def copy(self) -> Self: # type: ignore
        """
        Creates a copy of the current MeaRaman instance.

        Returns:
            MeaRaman: A new copy of the current instance.
        """
        new_copy = MeaRaman(reconstruct=True)
        if not self.check_measurement_exist():
            raise ValueError("No valid measurement exists to copy.")
        
        new_copy.reconstruct(
            measurement_id=self._measurement_time,
            metadata=self._dict_metadata.copy(),
            spec_analysed=self._spectrum_analysed.copy(),
            spec_rawlist=self._spectrum_rawlist.copy()
        )
    
    def self_report(self):
        """
        Prints out all the attributes of the class
        """
        print('Class attributes:')
        attributes = vars(self)
        for attr, value in attributes.items():
            print(f"{attr}: {value}")
        print()
    
    def test_generate_dummy(self):
        """
        Generates a dummy spectra for testing purposes
        """
        # Set the parameters
        timestamp = get_timestamp_us_int()
        int_time = 51.163
        laser_power = 24.5
        laser_wavelength = 785.123
        
        # Generate the dummy spectra
        wavelength = np.linspace(400, 800, 100)
        intensity = np.random.rand(100)
        df = pd.DataFrame({
            self.label_wavelength: wavelength,
            self.label_intensity: intensity
        })
        
        # Set the parameters
        self._measurement_time = timestamp
        self._integration_time_ms = int_time
        self._dict_metadata['integration_time_ms'] = int_time
        self._dict_metadata['laser_power_milliwatt'] = laser_power
        self._dict_metadata['laser_wavelength_nm'] = laser_wavelength
        
        # Set the raw list
        self.set_raw_list(df,timestamp)
        self.check_uptodate(autoupdate=True)
        
class MeaRaman_Handler():
    """
    Saves the measurement data into a file (from the class raman_measurement)
    """
    def save_measurement_to_txt(self,measurement:MeaRaman,filepath:str,save_raw:bool=False):
        """
        Saves the measurement data into a text file

        Args:
            measurement (raman_measurement): measurement data
            filepath (str): path to save the file
            save_raw (bool, optional): save the raw measurements. Defaults to False.
        """
        try:    
            with open(filepath, 'w') as file:
                file.write('# Timestamp: '+str(measurement.get_latest_timestamp())+'\n')
                file.write('# Integration time: '+str(measurement._integration_time_ms)+'\n')
                file.write('# Laser power: '+str(measurement.get_laser_params()[0])+'\n')
                file.write('# Laser wavelength: '+str(measurement.get_laser_params()[1])+'\n')
                file.write('# Accumulation: '+str(len(measurement.get_raw_list()))+'\n')
                file.write('# Version: '+measurement.version+'\n')
                    
                # Write the analysed measurements
                file.write('\n# Analysed measurements:\n')
                df = measurement.get_analysed()
                header = df.columns
                file.write('# {}\n'.format('\t'.join(header)))
                rows = df.values
                [file.write('\t'.join([str(val) for val in row])+'\n') for row in rows]
                
                if save_raw:
                    # Write the raw measurements
                    file.write('\n# Raw measurements:\n')
                    list_df = measurement.get_raw_list()
                    df = list_df[0]
                    header = df.columns
                    file.write('# {}\n'.format('\t'.join(header)))
                    for df in list_df:
                        rows = df.values
                        [file.write('\t'.join([str(val) for val in row])+'\n') for row in rows]
                        if not df.equals(list_df[-1]): file.write('\n')
                    
        except Exception as e: print('Error: save_measurement_to_txt\n',e)
        
    def save_measurement_to_pickle(self,measurement:MeaRaman,filepath:str,savename:str):
        """
        Saves the measurement data into a pickle file

        Args:
            measurement (raman_measurement): measurement data
            filepath (str): path to save the file

        Returns:
            str: path to the saved file
        """
        # Check if filepath is a directory
        if os.path.isdir(filepath):
            # Add a default filename
            filepath = os.path.join(filepath, savename+'.pkl')
            
        with open(filepath, 'wb') as file:
            pickle.dump(measurement, file)
        return filepath
    
    def load_measurement_from_pickle(self,filepath:str):
        """
        Loads the measurement data from a pickle file

        Args:
            filepath (str): path to the file

        Returns:
            raman_measurement: measurement data
        """
        with open(filepath, 'rb') as file:
            measurement = pickle.load(file)
        return measurement

class MeaRaman_Plotter():
    """
    A class for plotting Raman spectra from a RamanMeasurement instance
    """
    def __init__(self, plt_size:list|None=None) -> None:
        # >>> Plot parameters <<<
        self.plt_size = AppPlotEnum.PLT_SIZE_1D_PIXEL.value      # Plot size in [pixel x pixel]
        
        self.wavelength_name = DataAnalysisConfigEnum.WAVELENGTH_LABEL.value     # The wavelength column name
        self.intensity_name = DataAnalysisConfigEnum.INTENSITY_LABEL.value       # The spectra intensity column name
        self.ramanshift_name = DataAnalysisConfigEnum.RAMANSHIFT_LABEL.value     # The Raman shift column name
        
        self._fig, self._ax = plt.subplots(figsize=plt_size)
        
    def get_fig_ax(self) -> tuple[Figure, Axes]:
        """
        Returns the figure and axes used for plotting

        Returns:
            tuple[Figure, Axes]: figure and axes
        """
        return self._fig, self._ax
    
    def plot_RamanMeasurement_new(
        self,
        measurement:MeaRaman,
        title='Spectra',
        flg_plot_ramanshift=False,
        plot_raw:bool=False,
        limits:tuple[float|None,float|None,float|None,float|None]=(None,None,None,None),
        ) -> None:
        """
        Plot a given Ramanmeasurement into the internal figure.

        Args:
            measurement (RamanMeasurement): Measurement instance to plot.
            title (str, optional): Title of the plot. Defaults to 'Spectra'.
            showplot (bool, optional): Show the plot with a matplotlib window. Defaults to False.
            flg_plot_ramanshift (bool, optional): Plot the Raman shift instead of the wavelength. Defaults to False.
            plot_raw (bool, optional): Plot the raw data instead of the analysed data. Defaults to False.
            limits (tuple[float,float,float,float], optional): Limits of the plot (xmin,xmax,ymin,ymax). Defaults to (None,None,None,None).
        """
        assert isinstance(measurement,MeaRaman), "'measurement' should be a RamanMeasurement instance"
        assert measurement.check_measurement_exist(), "No valid measurement exists to plot."
        
        fig,ax = self.get_fig_ax()
        ax.clear()
        
        if not plot_raw: mea_type = 'analysed'
        else: mea_type = 'raw'
        
        if flg_plot_ramanshift: arr_specpos = measurement.get_arr_ramanshift()
        else: arr_specpos = measurement.get_arr_wavelength()
        
        arr_intensity = measurement.get_arr_intensity(mea_type=mea_type)
        
        ax.plot(arr_specpos, arr_intensity)
        ax.set_xlabel(self.ramanshift_name if flg_plot_ramanshift else self.wavelength_name)
        ax.set_ylabel(self.intensity_name)
        ax.set_title(title)
        ax.set_xlim(limits[0], limits[1])
        ax.set_ylim(limits[2], limits[3])
    
    def plot_RamanMeasurement(
        self,
        measurement:MeaRaman|None=None,
        title='Spectra',
        showplot=False,
        plt_size:list|None=None,
        flg_plot_ramanshift=False,
        plot_raw:bool=False,
        limits:tuple[float,float,float,float]|tuple[None,None,None,None]=(None,None,None,None),
        ) -> np.ndarray:
        """
        Plots a given spectra.
        
        Args:
            measurement (RamanMeasurement): Measurement instance to plot.
            title (str, optional): Title of the plot. Defaults to 'Spectra'.
            showplot (bool, optional): Show the plot with a matplotlib window. Defaults to False.
            plt_size (list, optional): Manually change the plot size, [y-pixel, x-pixel].
            flg_plot_ramanshift (bool, optional): Plot the Raman shift instead of the wavelength. Defaults to False.
            plot_raw (bool, optional): Plot the raw data instead of the analysed data. Defaults to False.
            limits (tuple[float,float,float,float], optional): Limits of the plot (xmin,xmax,ymin,ymax). Defaults to (None,None,None,None).
        
        Returns:
            ndarray: The resized image of the plot.
        
        Note:
            - If the given 'spectra' variable is not a pandas DataFrame, a white image will be returned.
            - The plot will be resized based on the specified plt_size or the default plt_size if not provided.
            - Raman shift will be plot if flg_plot_ramanshift is True.
        """
        if isinstance(plt_size,type(None)):
            plt_size = self.plt_size
        
        # Check if the given 'spectra' variable is a measurement. Otherwise, returns an white image
        if not isinstance(measurement,MeaRaman): return np.full((plt_size[0],plt_size[1], 3), 255, dtype=np.uint8)
        
        # Initialises the plot
        if not plot_raw: df = measurement.get_analysed()
        else: df = measurement.get_raw_list()[-1]
        list_wavelength = df[measurement.label_wavelength]
        list_intensity = df[measurement.label_intensity]
        
        dpi = plt.rcParams['figure.dpi']
        plt_size_in = [int(plt_size[0]/dpi),int(plt_size[1]/dpi)]
        fig = plt.figure(figsize=plt_size_in,constrained_layout=True)
        # plt.tight_layout(h_pad=0.5,w_pad=0.5)
        
        if flg_plot_ramanshift:
            laser_wavelength = measurement.get_laser_params()[1]
            list_raman_shift = [convert_wavelength_to_ramanshift(wavelength,laser_wavelength) for wavelength in list_wavelength]
            list_spectralposition = list_raman_shift
            xlabel = self.ramanshift_name
        else:
            list_spectralposition = list_wavelength
            xlabel = self.wavelength_name
        # Slice the list spectral position based on the given x limits
        if isinstance(limits[0],float):
            idx_start = bisect.bisect_left(list_spectralposition,limits[0])
            list_spectralposition = list_spectralposition[idx_start:]
            list_intensity = list_intensity[idx_start:]
        if isinstance(limits[1],float):
            idx_end = bisect.bisect_right(list_spectralposition,limits[1])
            list_spectralposition = list_spectralposition[:idx_end]
            list_intensity = list_intensity[:idx_end]
        
        plt.plot(list_spectralposition, list_intensity)
        plt.xlabel(xlabel)
        plt.ylabel(self.intensity_name)
        plt.title(title)
        
        xmin = float(limits[0]) if isinstance(limits[0],(float,int)) else None
        xmax = float(limits[1]) if isinstance(limits[1],(float,int)) else None
        ymin = float(limits[2]) if isinstance(limits[2],(float,int)) else None
        ymax = float(limits[3]) if isinstance(limits[3],(float,int)) else None

        plt.xlim(xmin,xmax)
        plt.ylim(ymin,ymax)
        
        # Get the plot as a NumPy array directly
        fig = plt.gcf()  # Get the current figure
        fig.canvas.draw()  # Force a draw 

        renderer = fig.canvas.get_renderer()

        # Extract pixel data as RGBA and convert to BGRA
        rgba_data = renderer.buffer_rgba()
        img = np.frombuffer(rgba_data, dtype=np.uint8).reshape(fig.canvas.get_width_height()[::-1] + (4,))

        # Remove alpha channel (OpenCV expects BGR)
        img = img[..., :3]

        # Resize the image
        img_resized = cv2.resize(img, (plt_size[0], plt_size[1]))
        
        if showplot:
            plt.show()
        else:
            plt.close()
        return img_resized

    def plot_with_scatter_RamanMeasurement(
            self,
            measurement:MeaRaman|None,
            title='Spectra',
            list_scatter_wavelength:list=[],
            list_scatter_intensity:list=[],
            flg_plot_ramanshift=False,
            limits:tuple[float,float,float,float]|tuple[None,None,None,None]=(None,None,None,None)
            ) -> None:
        """
        Plots a given spectra with scatter points.
        
        Args:
            measurement (RamanMeasurement): Measurement instance to plot.
            title (str, optional): Title of the plot. Defaults to 'Spectra'.
            list_scatter_wavelength (list, optional): List of scatter points' wavelengths. Defaults to [].
            list_scatter_intensity (list, optional): List of scatter points' intensities. Defaults to [].
            flg_plot_ramanshift (bool, optional): Plot the Raman shift instead of the wavelength. Defaults to False.
            limits (tuple[float,float,float,float], optional): Limits of the plot (xmin,xmax,ymin,ymax). Defaults to (None,None,None,None).
        
        Returns:
            None
        
        Note:
            - If the given 'spectra' variable is not a pandas DataFrame, a white image will be returned.
            - The plot will be resized based on the specified plt_size or the default plt_size if not provided.
        """
        fig = self._fig
        ax = self._ax
            
        # Initialises the plot
        if isinstance(fig,type(None)) and isinstance(ax,type(None)):
            fig,ax = plt.subplots()
        elif isinstance(fig,type(None)) or isinstance(ax,type(None)):
            raise ValueError('Both fig and ax should be given')
        
        # Check if the given 'spectra' variable is a measurement. Otherwise, returns an white image
        if not isinstance(measurement,MeaRaman): return
        
        # Extracts the data
        df = measurement.get_analysed()
        list_wavelength = df[measurement.label_wavelength]
        list_intensity = df[measurement.label_intensity]
        
        # Convert to Raman shift if required
        if flg_plot_ramanshift:
            laser_wavelength = measurement.get_laser_params()[1]
            list_SpectraPosition = [convert_wavelength_to_ramanshift(wavelength,laser_wavelength) for wavelength in list_wavelength]
            list_SpectraPosition_scatter = [convert_wavelength_to_ramanshift(wavelength,laser_wavelength) for wavelength in list_scatter_wavelength]
            xlabel = self.ramanshift_name
        else:
            list_SpectraPosition = list_wavelength
            list_SpectraPosition_scatter = list_scatter_wavelength
            xlabel = self.wavelength_name
        
        assert len(list_SpectraPosition) == len(list_intensity), 'The length of the wavelength and intensity should be the same'
        
        # Slice the list spectral position based on the given x limits
        if isinstance(limits[0],float):
            idx_start = bisect.bisect_left(list_SpectraPosition,limits[0])
            list_SpectraPosition = list_SpectraPosition[idx_start:]
            list_intensity = list_intensity[idx_start:]
            idx_start_scatter = bisect.bisect_left(list_SpectraPosition_scatter,limits[0])
            list_SpectraPosition_scatter = list_SpectraPosition_scatter[idx_start_scatter:]
            list_scatter_intensity = list_scatter_intensity[idx_start_scatter:]
        if isinstance(limits[1],float):
            idx_end = bisect.bisect_right(list_SpectraPosition,limits[1])
            list_SpectraPosition = list_SpectraPosition[:idx_end]
            list_intensity = list_intensity[:idx_end]
            idx_end_scatter = bisect.bisect_right(list_SpectraPosition_scatter,limits[1])
            list_SpectraPosition_scatter = list_SpectraPosition_scatter[:idx_end_scatter]
            list_scatter_intensity = list_scatter_intensity[:idx_end_scatter]
        
        list_label_scatter = ['{:.1f}'.format(val) for val in list_SpectraPosition_scatter]
        list_SpectraPosition_scatter = [float(val) for val in list_SpectraPosition_scatter]
        list_scatter_intensity = [float(val) for val in list_scatter_intensity]
        
        ax.clear()
        ax.plot(list_SpectraPosition, list_intensity)
        if len(list_scatter_intensity) > 0: ax.scatter(list_SpectraPosition_scatter,list_scatter_intensity,color='red')
        for i, txt in enumerate(list_label_scatter): ax.annotate(txt, (list_SpectraPosition_scatter[i], list_scatter_intensity[i]))
        
        xmin = limits[0] if limits[0] else None
        xmax = limits[1] if limits[1] else None
        ymin = limits[2] if limits[2] else None
        ymax = limits[3] if limits[3] else None
        ax.set_xlim(xmin,xmax)
        ax.set_ylim(ymin,ymax)
        
        ax.set_xlabel(xlabel)
        ax.set_ylabel(self.intensity_name)
        ax.set_title(title)
        # ax.legend()
        
        fig.tight_layout()

def test():
    """
    Test the RamanMeasurement class
    """
    # Initialises the class
    raman = MeaRaman(reconstruct=True)
    raman.test_generate_dummy()
    raman.self_report()
    

if __name__ == '__main__':
# Test the class
    pass
    test()
    