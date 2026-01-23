"""
This class generates the calibration for the spectrometer to map pixels to wavelengths,
and the intensity calibration of a Raman spectrometer
"""
import os
import sys
import time
from typing import Any, Callable

import threading
import multiprocessing as mp
from multiprocessing.managers import DictProxy
from multiprocessing.connection import Connection, Pipe

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer

from scipy.optimize import curve_fit
import numpy as np

import pandas as pd

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
matplotlib.use('Agg')

import json

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))


from iris import LibraryConfigEnum, DataAnalysisConfigEnum

from iris.resources.spectrometer_calibration_ui import Ui_spectrometerCalibrator

# Make a calibration parameters class to standardise the calibration parameters to store the following info:
# wavelen_poly_coeffs, wavelen_list_measured, wavelen_list_reference, intensity_poly_coeffs, intensity_list_measured, intensity_list_reference
class CalibrationParams(dict):
    def __init__(self):
        super().__init__()
        self['wavelen_poly_coeffs'] = (1,0)
        self['wavelen_list_measured'] = []
        self['wavelen_list_reference'] = []
        self['intensity_poly_coeffs'] = (0,1)
        self['intensity_list_pixel_idx'] = []
        self['intensity_list_measured'] = []
        self['intensity_list_reference'] = []
        
        # Polynomial coefficients of the transfer function y = poly_coeffs[0]x^(len(poly_coeffs)-1) + poly_coeffs[1]x^(len(poly_coeffs)-2) + ... + poly_coeffs[-1]
        # Note: the intensity list has to be in the order of the spectrometer pixel idx

class SpectrometerCalibrator():
    """
    The backend for the wavelength calibration to be used in the RamanMeasurementHub
    """
    def __init__(self, pipe_update: Connection, pipe_measurement: Connection):
        self._cal_params = CalibrationParams()
        
        # The table to map the measured wavelengths to the reference wavelengths
        self._transTable_wv = {}
        self._transTable_int = {}
        
        # Pipe to receive the path to update the calibration parameters
        self._pipe_update = pipe_update
        self._pipe_mea = pipe_measurement
        self._flg_isrunning = mp.Event()
        self._thd_update = threading.Thread(target=self._auto_update)
        self._thd_update.start()
        self._thd_calibrate = threading.Thread(target=self._auto_calibrate)
        self._thd_calibrate.start()
        
    def terminate(self):
        """
        Terminates the backend
        """
        self._flg_isrunning.clear()
        self._thd_update.join()
        self._pipe_update.close()
        
    def calibrate_measurement(self, measurement:pd.DataFrame):
        """
        Calibrates the spectrometer measurement based on the calibration parameters

        Args:
            measurement (pd.DataFrame): The measurement data to be calibrated
        """
        list_wavelength_raw = measurement[DataAnalysisConfigEnum.WAVELENGTH_LABEL.value].values
        list_intensity_raw = measurement[DataAnalysisConfigEnum.INTENSITY_LABEL.value].values
        list_wavelength_cal = [self.get_wavelength(wavelength_raw)\
            for wavelength_raw in list_wavelength_raw]
        list_intensity_cal = [self.get_intensity(wavelength_raw,intensity_raw)\
            for wavelength_raw,intensity_raw in zip(list_wavelength_raw,list_intensity_raw)]
        
        # Reconstruct the dataframe with the calibrated values
        cal_spectrum = measurement.copy()
        cal_spectrum[DataAnalysisConfigEnum.WAVELENGTH_LABEL.value] = list_wavelength_cal
        cal_spectrum[DataAnalysisConfigEnum.INTENSITY_LABEL.value] = list_intensity_cal
        
        return cal_spectrum
        
    def _auto_calibrate(self):
        """
        Automatically calibrates the spectrometer measurement
        """
        self._flg_isrunning.set()
        while self._flg_isrunning.is_set():
            if self._pipe_mea.poll(timeout=1):
                measurement = self._pipe_mea.recv()
                ret = None
                try: ret = self.calibrate_measurement(measurement)
                except Exception as e: print('ERROR SpectrometerCalibrator._auto_calibrate: ',e)
                finally: self._pipe_mea.send(ret)
        
    def _auto_update(self):
        """
        Automatically updates the calibration parameters
        """
        self._flg_isrunning.set()
        while self._flg_isrunning.is_set():
            if self._pipe_update.poll(timeout=1):
                recv = self._pipe_update.recv()
                self._cal_params = recv
                self._transTable_wv.clear()
                self._transTable_int.clear()
            time.sleep(0.5)
        
    def get_wavelength(self,pixel_idx:float) -> float:
        """
        Gets the wavelength based on the pixel index
        
        Args:
            pixel_idx (float): The pixel index
        
        Returns:
            float: The wavelength
        """
        assert isinstance(pixel_idx,(int,float)), 'ERROR SpectrometerCalibrator.get_wavelength: The pixel index must be a number'
        pixel_req = '{:.3f}'.format(pixel_idx)
        if pixel_req in self._transTable_wv.keys():
            wavelength_cal = self._transTable_wv[pixel_req]
        else:
            wavelength_cal = np.polyval(self._cal_params['wavelen_poly_coeffs'],pixel_idx)
            self._transTable_wv[pixel_req] = wavelength_cal
        return wavelength_cal
    
    def get_intensity(self,pixel_idx:float,intensity:float) -> float:
        """
        Gets the intensity based on the pixel index and the measured intensity
        
        Args:
            pixel_idx (float): The pixel index
            intensity (float): The measured intensity
        
        Returns:
            float: The calibrated intensity
        """
        assert isinstance(pixel_idx,(int,float)), 'ERROR SpectrometerCalibrator.get_intensity: The pixel index must be a number'
        assert isinstance(intensity,(int,float)), 'ERROR SpectrometerCalibrator.get_intensity: The intensity must be a number'
        pixel_req = '{:.3f}'.format(pixel_idx)
        
        if pixel_req in self._transTable_int.keys():
            cal_ratio = self._transTable_int[pixel_req]
        else:
            cal_ratio = np.polyval(self._cal_params['intensity_poly_coeffs'],pixel_idx)
            self._transTable_int[pixel_req] = cal_ratio
            
        intensity_cal = cal_ratio*intensity
        return intensity_cal
        
class Wdg_SpectrometerCalibrationGenerator(Ui_spectrometerCalibrator, qw.QWidget):
    """
    GUI for the spectrometer calibration generator

    Args:
        master (tk.Tk): The root window
        pipe_update (Connection): The pipe to update the calibration parameters in the backend
        dict_cal (DictCalibration): The calibration parameters dictionary
    """
    def __init__(self, parent:qw.QWidget, pipe_update: Connection):
        super().__init__(parent)
        self.setupUi(self)
        
    # >> General parameters <<
        figsize_in = (3.5,3.5)
        
    # >> Backend functions <<
        # Pipe to update the calibration parameters in the backend
        self._pipe_update = pipe_update
        
    # >> Global calibration parameters and widgets <<
        # Frontend params to temporarily store the calibration parameters
        self._cal_params = CalibrationParams()
        
        # Buttons to load, save, and calculate the calibration params
        self.btnLoad.clicked.connect(self._load_calibration)
        self.btnSave.clicked.connect(self._save_calibration)
        
    # >> Wavelength calibration parameters and widgets <<
        # Canvas to show the wavelength calibration transfer function
        self._fig_wv, self._ax_wv = plt.subplots(1,1,figsize=figsize_in)
        self._canvas_wv = FigureCanvas(figure=self._fig_wv)
        self.lytPixelmapCanvas.addWidget(self._canvas_wv)
        self._canvas_wv.draw_idle()
        
        # Treeview to show the measured and reference wavelengths
        self._tree = self.treePixelmap
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(['Measured peak loc [pixel OR nm]','Reference peak loc [nm]'])
        
        # Button to load the measured and reference wavelengths
        self.btnLoadPixelmap.clicked.connect(self._load_wavelength)
        
    # >> Intensity calibration parameters and widgets<<
        # Canvas to show the intensity calibration transfer function
        figsize_in_int = (figsize_in[0]*2,figsize_in[1])
        self._fig_int, axes = plt.subplots(1,2,figsize=figsize_in_int)
        self._ax_int_raw, self._ax_int_cal = axes
        self._canvas_int = FigureCanvas(figure=self._fig_int)
        self.lytIntensityCanvas.addWidget(self._canvas_int)
        self._canvas_int.draw_idle()
        
        # Button to load the measured and reference intensities
        self.btnLoadIntensity.clicked.connect(self._load_intensity)
        
    # >> Auto-load the calibration file from the last session <<
        cal_filepath = LibraryConfigEnum.SPECTROMETER_CALIBRATION_PATH.value
        if os.path.isfile(cal_filepath) and cal_filepath.endswith('.json'):
            QTimer.singleShot(0, lambda: self._load_calibration(cal_filepath))
                
    def _load_calibration(self,loadpath:str|None=None) -> None:
        """
        Loads the calibration file
        
        Args:
            loadpath (str|None): The path to the calibration file. If None, a file dialog will be opened
        
        Returns:
            bool: True if the calibration file is loaded successfully, False otherwise
        """
        if loadpath is None or not os.path.exists(loadpath) or not os.path.isfile(loadpath) or not loadpath.endswith('.json'):
            init_file = LibraryConfigEnum.SPECTROMETER_CALIBRATION_PATH.value
            init_dir = os.path.dirname(init_file) if os.path.exists(init_file) else ''
            loadpath = qw.QFileDialog.getOpenFileName(
                self,
                'Load calibration file',
                init_dir,
                'JSON files (*.json)',
            )[0]
        if loadpath == '': return
        
        with open(loadpath,'r') as f: dict_params = json.load(f)
        try:
            for key in dict_params:
                val = dict_params[key]
                if isinstance(val,list): self._cal_params[key] = [float(v) for v in val]
                elif isinstance(val,tuple): self._cal_params[key] = tuple([float(v) for v in val])
                else: self._cal_params[key] = float(val)
        except Exception as e: print('ERROR _load_calibration file read: ',e); return
        
        try:self._analyse_intensity_calibration_params(calculate_transfunc=False)
        except Exception as e: qw.QMessageBox.warning(self,'Load calibration error','Error in loading intensity calibration parameters:\n{}'.format(e))
        
        try:self._analyse_wavelength_calibration_params(calculate_transfunc=False)
        except Exception as e: qw.QMessageBox.warning(self,'Load calibration error','Error in loading wavelength calibration parameters:\n{}'.format(e))
        
        # Send the loadpath to the backend
        self._pipe_update.send(self._cal_params)
        
    def _save_calibration(self):
        """
        Saves the calibration file as a json file
        """
        filepath = qw.QFileDialog.getSaveFileName(
            self,
            'Save calibration file',
            LibraryConfigEnum.SPECTROMETER_CALIBRATION_DIR_DEFAULT.value,
            'JSON files (*.json)',
        )[0]
        if filepath == '': return
        with open(filepath,'w') as f: json.dump(self._cal_params,f)
        
    def _calculate_transferFunc_int_cubic(self,list_pixel_idx:list[float],list_int_mea:list[float],list_int_ref:list[float])\
        -> tuple[tuple[float,float,float,float],list[tuple[float,float]]]:
        """
        Generates the transfer function from the measured and reference/expected values
        
        Args:
            list_pixel_idx (list[float]): List of the pixel indices
            list_int_mea (list[float]): List of the measured intensities
            list_int_ref (list[float]): List of the reference intensities
        
        Returns:
            tuple[tuple[float,float,float,float],list[tuple[float,float]]]: The coefficients of
                the transfer function (a,b,c,d) for the cubic function of a*x**3 + b*x**2 + c*x + d
                and the list of coordinates of the intensity ratio [ref/mea]
        """
        def cubic(x,a,b,c,d): return a*x**3 + b*x**2 + c*x + d
        
        # Calculate the intensity ratio (reference/measured)
        list_int_ratio = [int_ref/int_mea for int_mea,int_ref in zip(list_int_mea,list_int_ref)]
        
        list_ratio_coors = list(zip(list_pixel_idx,list_int_ratio))
        
        # Fit the transfer function
        popt,_ = curve_fit(cubic,xdata=list_pixel_idx,ydata=list_int_ratio)
        popt = tuple(popt) # Convert the array to tuple for json serialisation during saving
        return popt, list_ratio_coors
        
    def _calculate_pxlMappingFunc_wv_cubic(self,list_mea:list[float],list_ref:list[float])\
        -> tuple[float,float,float,float]:
        """
        Generates the pixel mapping function from the measured and reference/expected values
        
        Args:
            list_mea (list[float]): List of the measured values
            list_ref (list[float]): List of the reference/expected values
        
        Returns:
            tuple[float,float,float,float]: The coefficients of the mapping function (a,b,c,d) for the cubic function of a*x**3 + b*x**2 + c*x + d
        """
        def cubic(x,a,b,c,d): return a*x**3 + b*x**2 + c*x + d
        
        # Fit the transfer function
        popt,_ = curve_fit(cubic,xdata=list_mea,ydata=list_ref)
        popt = tuple(popt) # Convert the array to tuple for json serialisation during saving
        return popt
    
    def _load_intensity(self):
        """
        Loads the measured and reference intensities
        """
        qw.QMessageBox.information(
            self,
            'Load intensity calibration points','Please select the csv file containing the measured'
            ' and reference intensities\nThe csv file should have 3 columns: Pixel index (or raw wavelength),'
            ' Measured intensity [a.u.], Reference intensity [a.u.].\nThe first line (header) will be skipped')
        
        filepath = qw.QFileDialog.getOpenFileName(
            self,
            'Load intensity calibration points',
            '',
            'CSV files (*.csv)',
        )[0]
        if filepath == '': return
        
        df = pd.read_csv(filepath,header=None,skiprows=1)
        
        self._cal_params['intensity_list_pixel_idx'] = df.iloc[:,0].tolist()
        self._cal_params['intensity_list_measured'] = df.iloc[:,1].tolist()
        self._cal_params['intensity_list_reference'] = df.iloc[:,2].tolist()
        
        # Calculate the transfer function and plot it
        self._analyse_intensity_calibration_params()
        self._pipe_update.send(self._cal_params)

    def _analyse_intensity_calibration_params(self,calculate_transfunc:bool=True):
        """
        Analyse the intensity calibration based on the values stored in the
        calibration parameters dictionary. Also assigns the calculatedtransfer function
        coefficients into the dictionary if requested.
        
        Args:
            calculate_transfunc (bool): If True, the transfer function will be calculated and stored
        """
        list_pixel_idx = self._cal_params['intensity_list_pixel_idx']
        list_int_mea = self._cal_params['intensity_list_measured']
        list_int_ref = self._cal_params['intensity_list_reference']
        transfer_func_coeff, list_ratio_coors = self._calculate_transferFunc_int_cubic(list_pixel_idx,list_int_mea,list_int_ref)
        
        # Store the transfer function coefficients
        if calculate_transfunc:self._cal_params['intensity_poly_coeffs'] = transfer_func_coeff
        
        # Plot the transfer function
        self._plot_int_transfer_func(self._cal_params['intensity_list_pixel_idx'],self._cal_params['intensity_list_measured'],
                                    self._cal_params['intensity_list_reference'],list_ratio_coors)
        
    def _plot_int_transfer_func(self,list_pixel_idx:list[float],list_int_mea:list[float],list_int_ref:list[float],
                                list_ratio_coors:list[tuple[float,float]]):
        """
        Plots the raw values and the transfer function for the intensity calibration based on given values
        
        Args:
            list_pixel_idx (list[float]): List of the pixel indices
            list_int_mea (list[float]): List of the measured intensities
            list_int_ref (list[float]): List of the reference intensities
            list_ratio_coors (list[tuple[float,float]]): List of the coordinates of the intensity ratio [ref/mea]
        """
    # > Raw values <
        # Generate the plot for the raw values
        fig,ax = self._fig_int, self._ax_int_raw
        ax.cla()
        ax.scatter(list_pixel_idx,list_int_mea,c='r',label='Measured intensity',marker='x',s=1)
        ax.scatter(list_pixel_idx,list_int_ref,c='b',label='Reference intensity',marker='x',s=1)
        ax.set_xlabel('Pixel index')
        ax.set_ylabel('Intensity [a.u.]')
        ax.set_title('Intensity calibration')
        ax.legend()
        
    # > Transfer function <
        # Grab the transfer function
        transfer_func_coeff = self._cal_params['intensity_poly_coeffs']
        
        # Generate the points for the plot
        x_min = min(list_pixel_idx)
        x_max = max(list_pixel_idx)
        x = np.linspace(x_min,x_max,100)
        y = np.polyval(transfer_func_coeff,x)
        
        x2 = [coor[0] for coor in list_ratio_coors]
        y2 = [coor[1] for coor in list_ratio_coors]
        y2_min = min(y2)
        y2_max = max(y2)
        if y2_min > 0 and y2_max > 0: y2_min = 0
        if y2_min < 0 and y2_max < 0: y2_max = 0
        
        # Generate the plot
        fig,ax = self._fig_int, self._ax_int_cal
        ax:Axes
        ax.cla()
        ax.plot(x,y,c='r',label='Transfer function')
        ax.scatter(x2,y2,c='b',label='Intensity ratio [ref/mea]',marker='x',s=1)
        ax.set_ylim(y2_min-abs(y2_min)*0.1,y2_max+abs(y2_max)*0.1)
        ax.set_xlabel('Pixel index [pixel] OR Wavelength [nm]')
        ax.set_ylabel('Intensity [a.u.]')
        ax.set_title('Intensity calibration transfer function')
        ax.legend()
        
        # Show the plot and redraw the canvas
        self._canvas_int.draw()
        
    def _load_wavelength(self):
        """
        Loads the measured and reference wavelengths
        """
        qw.QMessageBox.information(
            self,
            'Load wavelength calibration points','Please select the csv file containing the measured'
            ' and reference wavelengths\nThe csv file should have 2 columns: Measured peak loc [pixel OR nm],'
            ' Reference peak loc [nm].\nThe first line (header) will be skipped')
        
        filepath = qw.QFileDialog.getOpenFileName(
            self,
            'Load wavelength calibration points',
            '',
            'CSV files (*.csv)',
        )[0]
        if filepath == '': return
        
        df = pd.read_csv(filepath,header=None,skiprows=1)
        
        self._cal_params['wavelen_list_measured'] = df.iloc[:,0].tolist()
        self._cal_params['wavelen_list_reference'] = df.iloc[:,1].tolist()
        
        # Calculate the transfer function
        self._analyse_wavelength_calibration_params()
        self._pipe_update.send(self._cal_params)

    def _analyse_wavelength_calibration_params(self,calculate_transfunc:bool=True):
        """
        Analyse the wavelength calibration based on the values stored in the
        calibration parameters dictionary. Also assigns the calculated transfer function
        coefficients into the dictionary.
        
        Args:
            calculate_transfunc (bool): If True, the transfer function will be calculated
        """
        if calculate_transfunc:
            list_peakRS_mea = self._cal_params['wavelen_list_measured']
            list_peakRS_ref = self._cal_params['wavelen_list_reference']
            transfer_func_coeff = self._calculate_pxlMappingFunc_wv_cubic(list_peakRS_mea,list_peakRS_ref)
            self._cal_params['wavelen_poly_coeffs'] = transfer_func_coeff
        
        # Update the treeview
        self._update_treeview_wv()
        
        # Plot the transfer function
        self._plot_wv_pxlMapping_func(self._cal_params['wavelen_list_measured'],self._cal_params['wavelen_list_reference'])
    
    def _plot_wv_pxlMapping_func(self,list_peakRS_mea:list[float],list_peakRS_ref:list[float]):
        """
        Plots the pixel mapping function for the wavelength calibration
        
        Args:
            list_peakRS_mea (list[float]): List of the Raman shift peaks of the sample representative
            list_peakRS_ref (list[float]): List of the Raman shift peaks of the reference
        """
    # > Grab the transfer function <
        transfer_func_coeff = self._cal_params['wavelen_poly_coeffs']
        
        # Generate the x and y values from the transfer function
        x_min = min(list_peakRS_mea)
        x_max = max(list_peakRS_mea)
        x = np.linspace(x_min,x_max,100)
        y = np.polyval(transfer_func_coeff,x)
        
        # Generate the plot
        fig,ax = self._fig_wv, self._ax_wv
        ax.cla()
        ax.plot(x,y,c='b',label='Pixel mapping func')
        ax.scatter(list_peakRS_mea,list_peakRS_ref,c='r',label='Peaks')
        ax.set_xlabel('Measurement Raman peaks [nm OR pixel]')
        ax.set_ylabel('Reference Raman peaks [nm]')
        ax.set_title('Spectrometer pixel mapping')
        ax.legend()

        # Add a label to each scatter points
        for i,peakRS in enumerate(list_peakRS_mea):
            ax.annotate(str(peakRS),(list_peakRS_mea[i],list_peakRS_ref[i]))
        
        # Show the plot and redraw the canvas
        self._canvas_wv.draw()
            
    def _update_treeview_wv(self):
        """
        Updates the treeview for the wavelength calibration
        """
        self._tree.clear()
        for (mea,ref) in zip(self._cal_params['wavelen_list_measured'],self._cal_params['wavelen_list_reference']):
            item = qw.QTreeWidgetItem()
            item.setText(0,str(mea))
            item.setText(1,str(ref))
            
            self._tree.addTopLevelItem(item)        
    
class MainWindow_SpectrometerCalibrationGenerator(qw.QMainWindow):
    """
    Main window for the spectrometer calibration generator
    """
    def __init__(self, pipe_update: Connection):
        super().__init__()
        self.setWindowTitle('Spectrometer Calibration Generator')
        self._wdg = Wdg_SpectrometerCalibrationGenerator(self, pipe_update)
        self.setCentralWidget(self._wdg)
        
    def get_WdgCalibrator(self) -> Wdg_SpectrometerCalibrationGenerator:
        """
        Gets the calibrator widget
        
        Returns:
            Wdg_SpectrometerCalibrationGenerator: The calibrator widget
        """
        return self._wdg
        
    @Slot()
    def closeEvent(self, event):
        """
        Overrides the close event to hide the window instead of closing it
        """
        self.hide()
        event.ignore()
    
def test():
    app = qw.QApplication([])
    main_window = qw.QMainWindow()
    pipe_update, pipe_update_child = Pipe()
    wdg = Wdg_SpectrometerCalibrationGenerator(main_window, pipe_update)
    # SpectrometerCalibrator(pipe_update_child, Pipe()[0])
    main_window.setCentralWidget(wdg)
    main_window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    test()