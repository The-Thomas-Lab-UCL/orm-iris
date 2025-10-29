"""
A class that manages the motion controller aspect for the Ocean Direct Raman spectrometer
"""
import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer

import os
import multiprocessing.pool as mpp

import threading
import queue
from typing import Callable, Any

import time
import cv2
import numpy as np

import matplotlib as mpl
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
mpl.use('Agg')

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))


from iris.utils.general import *
from iris.gui.dataHub_MeaRMap import Frm_DataHub_Mapping
from iris.data.measurement_Raman import MeaRaman, MeaRaman_Plotter
from iris.multiprocessing.dataStreamer_Raman import DataStreamer_Raman, initialise_manager_raman, initialise_proxy_raman
from iris.multiprocessing.basemanager import get_my_manager

from iris.controllers import Controller_Spectrometer

from iris import DataAnalysisConfigEnum
from iris.gui import AppRamanEnum

class RamanMeasurement_Analysis_Worker(QObject):
    """
    A class defining the worker functions for Raman measurement analysis.
    """
    finished = Signal(bool)
    
    @Slot()
    def analyse_rawlist2mea(self,processor:mpp.Pool, measurement: MeaRaman, raw_list: list) -> None:
        """
        Analyses the Raman measurement by averaging the raw list.
        Args:
            measurement (MeaRaman): The Raman measurement to be analysed.
            raw_list (list): The list of raw data to be analysed.
        """
        # Gap 1: measure the average ~10ms
        result = processor.apply_async(func=measurement.get_average_rawlist,args=(raw_list,))
        spectrum_avg = result.get()
        measurement.set_analysed(spectrum_analysed=spectrum_avg)
        self.finished.emit(True)
        
    @Slot()
    def analyse_plot_rawlist2mea(self,
        processor:mpp.Pool,
        plotter:MeaRaman_Plotter,
        measurement:MeaRaman,
        raw_list:list,
        plot_raw:bool,
        plot_ramanshift:bool,
        limits:tuple[float|None,float|None,float|None,float|None],
        ) -> None:
        """
        Analyses the Raman measurement by averaging the raw list and plots the raw and averaged spectrum.
        Args:
            processor (mpp.Pool): The multiprocessing pool for data processing.
            plotter (MeaRaman_Plotter): The Raman measurement plotter.
            measurement (MeaRaman): The Raman measurement to be analysed.
            raw_list (list): The list of raw data to be analysed.
            limits (tuple): The plot limits (xmin, xmax, ymin, ymax).
            plot_add_kwargs (dict, optional): Additional keyword arguments for the plotter. Defaults to {}.
        """
        result_analysis = processor.apply_async(func=measurement.get_average_rawlist,args=(raw_list,))
        spectrum_avg = result_analysis.get()
        measurement.set_analysed(spectrum_analysed=spectrum_avg)
        
        dict_plotter = {}
        
        # 3. Generate the averaged plot
        dict_plotter['title'] = 'Averaged measurement'
        
        plotter.plot_RamanMeasurement_new(
            measurement=measurement,
            title='Raw measurement',
            flg_plot_ramanshift=plot_ramanshift,
            plot_raw=plot_raw,
            limits=limits,
        )
        self.finished.emit(True)
        
class Spectrometer_Control_Workers(QObject):
    """
    A class defining the worker functions for the Raman spectrometer controller.
    """
    finished = Signal(bool)
    new_integration_time_us = Signal(int)

    def __init__(self, parent: Any, controller: Controller_Spectrometer) -> None:
        super().__init__(parent)
        self._controller = controller
        
    def set_integration_time_us(self, new_value_us: int) -> None:
        """
        Sets the integration time of the spectrometer.

        Args:
            new_value_us (int): New integration time [us]

        Returns:
            int: The actual integration time set [us]
        """
        actual_time_us = self._controller.set_integration_time_us(new_value_us)
        self.new_integration_time_us.emit(actual_time_us)
        self.finished.emit(True)
        
class RamanMeasurement_Worker(QObject):
    """
    A class defining the worker functions for Raman measurement acquisition.
    """
    finished = Signal(bool)
    mea_acquired = Signal()
    mea_acquired_get = Signal(MeaRaman)
    
    def __init__(self, ramanHub: DataStreamer_Raman) -> None:
        super().__init__()
        self._ramanHub = ramanHub
        self._isrunning = False
        self._timer_single = QTimer()
        
        self._timer_params = {}
        self._timer_single.setInterval(1)
        self._timer_single.setSingleShot(True)
        self._timer_single.timeout.connect(self._acquire_single_measurement_timeout)

    @Slot()
    def stop_acquisition(self) -> None:
        """
        Stops the continuous acquisition of Raman measurements.
        """
        self._isrunning = False
        
    @Slot()
    def acquire_single_measurement_nonstop(
        self,
        accumulation:int,
        int_time_ms:int,
        laserpower_mW:float,
        laserwavelength_nm:float,
        extra_metadata:dict,
        queue_mea:queue.Queue|None=None,
        emit_measurement:bool=False
        ):
        self._ramanHub.resume_auto_measurement()
        self._isrunning = True
        
        self._timer_params = {
            'accumulation': accumulation,
            'int_time_ms': int_time_ms,
            'laserpower_mW': laserpower_mW,
            'laserwavelength_nm': laserwavelength_nm,
            'extra_metadata': extra_metadata,
            'queue_mea': queue_mea,
            'emit_measurement': emit_measurement
        }
        
        self._timer_single.start()

    @Slot()
    def _acquire_single_measurement_timeout(self):
        try:print(f'elapsed time before measurement: {time.time()-self._time:.4f} sec')
        except: pass
        self._time = time.time()
        accumulation = self._timer_params['accumulation']
        int_time_ms = self._timer_params['int_time_ms']
        laserpower_mW = self._timer_params['laserpower_mW']
        laserwavelength_nm = self._timer_params['laserwavelength_nm']
        extra_metadata = self._timer_params['extra_metadata']
        queue_mea = self._timer_params['queue_mea']
        emit_measurement = self._timer_params['emit_measurement']
        
        if not self._isrunning:
            self._timer_single.stop()
            self._ramanHub.pause_auto_measurement()
            self.finished.emit(True)
            return
        
        timestamp = get_timestamp_us_int()
        measurement = MeaRaman(
            timestamp=timestamp,
            int_time_ms=int_time_ms,
            laserPower_mW=laserpower_mW,
            laserWavelength_nm=laserwavelength_nm,
            extra_metadata=extra_metadata,
            )
            
        for _ in range(accumulation):
            # Performs a measurement and add it to the storage
            timestamp_request = get_timestamp_us_int()
            print(timestamp_request)
            
            # result = self._ramanHub.get_measurement(timestamp_request,WaitForMeasurement=False,getNewOnly=True)
            # spectrum_raw = result[1][-1]
                
            # measurement.set_raw_list(
            #     df_mea=spectrum_raw,
            #     timestamp_int=timestamp,
            #     max_accumulation=accumulation
            #     )
                
        # if queue_mea: queue_mea.put(measurement)
        # self.mea_acquired.emit()
        # if emit_measurement: self.mea_acquired_get.emit(measurement)
        
        self._timer_single.start()
        
    @Slot()
    def acquire_continuous_measurement(self):
        pass
        
    @Slot()
    def acquire_single_measurement(
        self,
        accumulation:int,
        int_time_ms:int,
        laserpower_mW:float,
        laserwavelength_nm:float,
        extra_metadata:dict,
        queue_mea:queue.Queue|None=None,
        measurement:MeaRaman|None=None
        ):
        self._ramanHub.resume_auto_measurement()
        self._isrunning = True
        timestamp = get_timestamp_us_int()
        if measurement is None:
            measurement = MeaRaman(
                timestamp=timestamp,
                int_time_ms=int_time_ms,
                laserPower_mW=laserpower_mW,
                laserWavelength_nm=laserwavelength_nm,
                extra_metadata=extra_metadata,
                )
        
        for _ in range(accumulation):    
            # Performs a measurement and add it to the storage
            timestamp_request = get_timestamp_us_int()
            result = self._ramanHub.get_measurement(timestamp_request,WaitForMeasurement=False,getNewOnly=True)
            spectrum_raw = result[1][-1]
            
            measurement.set_raw_list(
                df_mea=spectrum_raw,
                timestamp_int=timestamp_request,
                max_accumulation=accumulation
                )
            
            if queue_mea: queue_mea.put(measurement)
            self.mea_acquired.emit()
            
        self._ramanHub.pause_auto_measurement()
        self.finished.emit(True)
        
    def acquire_continuous_measurement_trigger(
        self,
        q_trigger:queue.Queue,
        q_return:queue.Queue,
        laserpower_mW:float,
        laserwavelength_nm:float,
        extra_metadata:dict,
        ):
        self._ramanHub.wait_MeasurementUpdate()
        trigger = q_trigger.get()
        list_timestamp_trigger = [get_timestamp_us_int()]
        self._isrunning = True
        while self._isrunning:
            # Wait for the trigger to start the next measurement or to stop
            trigger = q_trigger.get()
            if trigger == 0: self._isrunning = False; break
            
            # Retrieve the measurements
            list_timestamp_trigger.append(get_timestamp_us_int())
            list_timestamp_mea_int,list_spectrum,list_integration_time_ms=\
                self._ramanHub.get_measurement(
                    timestamp_start=list_timestamp_trigger[-2],
                    timestamp_end=list_timestamp_trigger[-1])
            list_timestamp_trigger.pop(0) # Remove the first element (not needed anymore)
            
            # >>> Skips the measurement if the trigger is 1. <<<
            # This REMOVES the measurement between the trigger timestamp
            # and the previous timestamp
            if trigger == 1: continue
            
            list_measurement = []
            for ts_int,spectrum_raw,int_time_ms in zip(list_timestamp_mea_int,list_spectrum,list_integration_time_ms):
                measurement = MeaRaman(
                    timestamp=ts_int,
                    int_time_ms=int_time_ms,
                    laserPower_mW=laserpower_mW,
                    laserWavelength_nm=laserwavelength_nm,
                    extra_metadata=extra_metadata)
                measurement.set_raw_list(df_mea=spectrum_raw, timestamp_int=ts_int)
                list_measurement.append(measurement)
            
            # Return the measurement result
            for i, measurement in enumerate(list_measurement):
                measurement.calculate_analysed()
                q_return.put((list_timestamp_mea_int[i], measurement))
                self.mea_acquired_get.emit(measurement)
                
        self._ramanHub.pause_auto_measurement()
        self.finished.emit(True)

class Frm_RamanSpectrometerController(qw.QGroupBox):
    """
    A class defining the app subwindow for the Raman spectrometer.
    """
    def __init__(
        self,
        parent:Any,
        processor:mpp.Pool,
        controller:Controller_Spectrometer,
        ramanHub:DataStreamer_Raman,
        dataHub:Frm_DataHub_Mapping|None,
        main:bool=False
        ) -> None:
        """
        Initialises the Raman spectrometer controller window
        
        Args:
            parent (Any): The parent PyQt widget, window, etc.
            processor (mpp.Pool): The multiprocessing pool for the data processing
            controller (raman_spectrometer_controller): The Raman spectrometer controller
            ramanHub (RamanMeasurementHub): The Raman measurement hub to retrieve measurements from
            dataHub (Frm_DataHub): The data hub for the measurements
            main (bool, optional): If true, initialises the spectrometer and analyser. Defaults to False.
        
        Note:
            if not main, the initialisation of the spectrometer and analyser should be done manually when ready
        """
# >>> Main initialisation <<<
        super().__init__(parent)
        self._processor = processor
        self._controller = controller   # Raman spectrometer controller
        self._ramanHub = ramanHub       # Raman measurement hub
        self._dataHub = dataHub         # Data hub for the measurements
        
# >>> Get controller parameters <<<
        self._controller_id = self._controller.get_identifier()
        
# >>> Spectrometer control and data handling setup <<<
        # Spectrometer parameters setup
        self.integration_time_ms = AppRamanEnum.DEFAULT_INTEGRATION_TIME_MS.value 
        self.singMea_accumulation = AppRamanEnum.DEFAULT_SINGMEA_ACCUMULATION.value
        self.contMea_accumulation = AppRamanEnum.DEFAULT_CONTMEA_ACCUMULATION.value
        
        # Is-running flags
        self._flg_isrunning = threading.Event()
        
        # Spectrometer internal data storage setup
        self._sngl_measurement:MeaRaman = MeaRaman(reconstruct=True)    # single measurement
        self._cont_measurement:MeaRaman = MeaRaman(reconstruct=True)    # continuous measurement
        self._last_measurement:MeaRaman = MeaRaman(reconstruct=True)    # last plot measurement
        
        # Plotter setup
        self._plotter = MeaRaman_Plotter()
        
# >>> Control frames setup <<<
    # Create the subframes to show the plots and controls
        main_layout = qw.QVBoxLayout()
        self.setLayout(main_layout)
        
        slyt_plot = qw.QVBoxLayout()
        self._slyt_controls = qw.QGridLayout()
        self._slyt_data = qw.QGridLayout()
        
        main_layout.addLayout(slyt_plot)
        main_layout.addLayout(self._slyt_controls)
        main_layout.addLayout(self._slyt_data)
        
        # Initialise the statusbar
        self._statbar = qw.QStatusBar(self)
        self._statbar.showMessage("Raman controller initialisation")
        main_layout.addWidget(self._statbar)
        
# >>> Measurement control widgets setup <<<
    # Setup the widget to show the plot
        # Subframe setups for the plot and control widgets
        sslyt_plot = qw.QVBoxLayout()
        sslyt_plot_control_basic = qw.QGridLayout() # For basic control widgets
        sslyt_plot_control_add = qw.QGridLayout()   # For additional control widgets
        
        slyt_plot.addLayout(sslyt_plot)
        slyt_plot.addLayout(sslyt_plot_control_basic)
        slyt_plot.addLayout(sslyt_plot_control_add)
        
    # Plot widget setup
        self._plotter = MeaRaman_Plotter()
        self._fig, self._ax = self._plotter.get_fig_ax()
        self._fig_widget = FigureCanvas(self._fig)
        sslyt_plot.addWidget(self._fig_widget)
        
    # Basic plot control widgets
        # Add widgets for additional plot options
        self._bool_PlotRawOnly = qw.QCheckBox('Plot raw only')
        self._bool_PlotRawOnly.setChecked(True)
        
        self._bool_PlotRamanShift = qw.QCheckBox('Plot Raman-shift')
        self._bool_PlotRamanShift.setChecked(True)
        
        sslyt_plot_control_basic.addWidget(self._bool_PlotRawOnly,0,0)
        sslyt_plot_control_basic.addWidget(self._bool_PlotRamanShift,0,1)

    # Additional plot control widgets
        # Widgets for the plot limits
        lbl_xmin = qw.QLabel(text='x-min: ')
        lbl_xmax = qw.QLabel(text='x-max: ')
        lbl_ymin = qw.QLabel(text='y-min: ')
        lbl_ymax = qw.QLabel(text='y-max: ')
        self._entry_xmin = qw.QLineEdit()
        self._entry_xmax = qw.QLineEdit()
        self._entry_ymin = qw.QLineEdit()
        self._entry_ymax = qw.QLineEdit()
        btn_reset = qw.QPushButton('Reset limits')
        btn_reset.clicked.connect(lambda: self._reset_plot_limits())
        
        sslyt_plot_control_add.addWidget(lbl_xmin,0,0)
        sslyt_plot_control_add.addWidget(self._entry_xmin,0,1)
        sslyt_plot_control_add.addWidget(lbl_xmax,0,2)
        sslyt_plot_control_add.addWidget(self._entry_xmax,0,3)
        sslyt_plot_control_add.addWidget(lbl_ymin,1,0)
        sslyt_plot_control_add.addWidget(self._entry_ymin,1,1)
        sslyt_plot_control_add.addWidget(lbl_ymax,1,2)
        sslyt_plot_control_add.addWidget(self._entry_ymax,1,3)
        sslyt_plot_control_add.addWidget(btn_reset,0,4,2,1)
        
        [widget.textChanged.connect(lambda: self._force_update_plot())\
            for widget in get_all_widgets_from_layout(sslyt_plot_control_add) if isinstance(widget,qw.QLineEdit)]
        
    # Raman controller setups
        self._btn_sngl_mea = qw.QPushButton('Single measurement')
        self._btn_cont_mea = qw.QPushButton('Continuous measurement')
        
        self._btn_sngl_mea.clicked.connect(lambda: self.perform_single_measurement())
        self._btn_cont_mea.clicked.connect(lambda: self.perform_continuous_measurement())
        
        self._slyt_controls.addWidget(self._btn_sngl_mea,0,0)
        self._slyt_controls.addWidget(self._btn_cont_mea,0,1)
        
    # Add buttons and labels for device parameter setups
        ## Label to notify the users of the current device parameters
        self._lbl_dev_stat_inttime = qw.QLabel(
            text='Device integration time: {} microsec'
            .format(self.integration_time_ms))
        self._lbl_dev_stat_acq = qw.QLabel(
            text='Device accumulation: {} times/average'
            .format(self.contMea_accumulation))
        
        ## Label to show the current setting, spinbox to let the user enter new parameters,
        ## button to call the command and update the label
        ### for single measurement integration time
        lbl_inttime = qw.QLabel(text='Set integration time [ms]: ')
        self._spin_inttime = qw.QSpinBox()
        self._btn_inttime = qw.QPushButton('Set')
        
        self._spin_inttime.valueChanged.connect(lambda: self._set_integration_time(
            new_value_ms=int(self._spin_inttime.value())))
        self._btn_inttime.clicked.connect(lambda: self._set_integration_time(
            new_value_ms=int(self._spin_inttime.value())))
        
        self._slyt_controls.addWidget(lbl_inttime,1,0)
        self._slyt_controls.addWidget(self._spin_inttime,1,1)
        self._slyt_controls.addWidget(self._btn_inttime,1,2)
        
        ### for single measurement number of accumulation
        self._lbl_sngl_acq = qw.QLabel(text='Set the single measurement accumulation: {}'.format(self.singMea_accumulation))
        self._spin_sngl_acq = qw.QSpinBox()
        self._btn_sngl_acq = qw.QPushButton('Set')
        
        self._btn_sngl_acq.clicked.connect(lambda: self.set_singMea_accumulation(
            new_value=int(self._spin_sngl_acq.value())))
        self._spin_sngl_acq.valueChanged.connect(lambda: self.set_singMea_accumulation(
            new_value=int(self._spin_sngl_acq.value())))
        
        self._slyt_controls.addWidget(self._lbl_sngl_acq,2,0)
        self._slyt_controls.addWidget(self._spin_sngl_acq,2,1)
        self._slyt_controls.addWidget(self._btn_sngl_acq,2,2)
        
        ### for the continuous measurement accumulation
        self._lbl_cont_acq = qw.QLabel(text='Set the continuous measurement accumulation: {}'.format(self.contMea_accumulation))
        self._spin_cont_acq = qw.QSpinBox()
        self._btn_cont_acq = qw.QPushButton('Set')

        self._btn_cont_acq.clicked.connect(lambda: self.set_contMea_accumulation(
            new_value=int(self._spin_cont_acq.value())))
        self._spin_cont_acq.valueChanged.connect(lambda: self.set_contMea_accumulation(
            new_value=int(self._spin_cont_acq.value())))

        self._slyt_controls.addWidget(self._lbl_cont_acq,3,0)
        self._slyt_controls.addWidget(self._spin_cont_acq,3,1)
        self._slyt_controls.addWidget(self._btn_cont_acq,3,2)
        
        if main: self.initialise_spectrometer_n_analyser()
        
    # >>> Data management widgets setup <<<
        # Datasave widget
        self._btn_saveto_datahub = qw.QPushButton("Save 'single measurement' to data hub")
        if isinstance(self._dataHub,Frm_DataHub_Mapping):
            self._btn_saveto_datahub.clicked.connect(
                lambda data=self._sngl_measurement: self._dataHub.append_RamanMeasurement_multi(data)) # type: ignore ; it is guaranteed to be Frm_DataHub_Mapping here
        else: self._btn_saveto_datahub.setEnabled(False)
        
        # Metadata parameters
        self._laserpower_mW = DataAnalysisConfigEnum.LASER_POWER_MILLIWATT.value
        self._laserwavelength_nm = DataAnalysisConfigEnum.LASER_WAVELENGTH_NM.value
        self._objective_info = DataAnalysisConfigEnum.OBJECTIVE_INFO.value
        
        # Metadata widgets
        self._lbl_laserpower = qw.QLabel('Laser power: {} mW'.format(self._laserpower_mW))
        self._lbl_laserwavelength = qw.QLabel('Laser wavelength: {} nm'.format(self._laserwavelength_nm))
        self._lbl_objectiveinfo = qw.QLabel('Objective info: {}'.format(self._objective_info))
        
        # Entry widgets and button to set the metadata
        self._entry_laserpower = qw.QLineEdit()
        self._entry_laserwavelength = qw.QLineEdit()
        self._entry_objectiveinfo = qw.QLineEdit()
        btn_set_lasermetadata = qw.QPushButton('Set laser metadata')
        btn_set_lasermetadata.clicked.connect(lambda: self._set_laserMetadata())
        
        # Default values
        self._entry_laserpower.setText(str(DataAnalysisConfigEnum.LASER_POWER_MILLIWATT.value))
        self._entry_laserwavelength.setText(str(DataAnalysisConfigEnum.LASER_WAVELENGTH_NM.value))
        self._entry_objectiveinfo.setText(str(DataAnalysisConfigEnum.OBJECTIVE_INFO.value))
        
        # Bind the value change to setting the laser metadata
        self._entry_laserpower.textChanged.connect(lambda: self._set_laserMetadata())
        self._entry_laserwavelength.textChanged.connect(lambda: self._set_laserMetadata())
        self._entry_objectiveinfo.textChanged.connect(lambda: self._set_objectiveMetadata())

        # Grid the widgets
        self._slyt_data.addWidget( self._btn_saveto_datahub,0,0)
        self._slyt_data.addWidget( btn_set_lasermetadata,0,1)
        self._slyt_data.addWidget( self._lbl_laserpower,1,0)
        self._slyt_data.addWidget( self._entry_laserpower,1,1)
        self._slyt_data.addWidget( self._lbl_laserwavelength,2,0)
        self._slyt_data.addWidget( self._entry_laserwavelength,2,1)
        self._slyt_data.addWidget( self._lbl_objectiveinfo,3,0)
        self._slyt_data.addWidget( self._entry_objectiveinfo,3,1)
        
    # >> Thread and worker setup <<<

        
    # >>> Finalise the setup <<<
        # Update the statusbar
        self._statbar.showMessage("Raman controller ready")
    
    def _set_objectiveMetadata(self):
        """
        Sets the objective metadata based on the entry widgets
        """
        try:
            objective_info = self._entry_objectiveinfo.text()
            self._lbl_objectiveinfo.setText('Objective info: {}'.format(objective_info))
            
            self._objective_info = objective_info
        except Exception as e: print('_set_objectiveMetadata',e); self.status_update('Objective metadata setup failed',bg_colour='red')
    
    def _set_laserMetadata(self):
        """
        Sets the laser metadata based on the entry widgets
        """
        try:
            laserpower_mW = float(self._entry_laserpower.text())
            laserwavelength_nm = float(self._entry_laserwavelength.text())
            self._lbl_laserpower.setText('Laser power: {} mW'.format(laserpower_mW))
            self._lbl_laserwavelength.setText('Laser wavelength: {} nm'.format(laserwavelength_nm))
            
            self._laserpower_mW = laserpower_mW
            self._laserwavelength_nm = laserwavelength_nm
        except Exception as e:
            qw.QErrorMessage(self).showMessage('Invalid laser metadata input')
            self._statbar.showMessage('Invalid laser metadata input',5000)
    
    def _generate_metadata_dict(self) -> dict:
        """
        Generates the metadata dictionary for the measurement based on the current settings
        
        Returns:
            dict: The metadata dictionary
        """
        dict_metadata = {
            'objective_info': self._objective_info,
            'spectrometer_id': self._controller_id
        }
        return dict_metadata
    
    def get_controller_identifier(self):
        """
        Returns the identifier of the spectrometer controller

        Returns:
            str: The identifier of the spectrometer controller
        """
        return self._controller_id
    
    def get_single_measurement(self):
        return self._sngl_measurement
    
    def update_label_device_parameters(self,accum=None):
        """
        Updates the label showing the device integration time from the device itself
        and accumulation from the input
        
        Args:
            accum (int): new accumulation to be displayed
        """
        int_time = self._controller.get_integration_time_us() # in microsec
        self._lbl_dev_stat_inttime.setText(f'Device integration time: {int(int_time/1000)} millisec')
        if accum != None:
            self._lbl_dev_stat_acq.setText(f'Device accumulation: {accum} times/average')
            
    def set_contMea_accumulation(self,new_value):
        """
        Set the accumulation for the continuous measurement.

        Args:
            new_value (int): The new accumulation
        """
        self.contMea_accumulation = new_value
        self._lbl_cont_acq.setText('Set the continuous measurement accumulation: {}'.format(self.contMea_accumulation))
    
    def set_singMea_accumulation(self,new_value):
        """
        Set the accumulation for the single measurement.

        Args:
            new_value (int): The new accumulation value
        """
        self.singMea_accumulation = new_value
        self._lbl_sngl_acq.setText('Set the single measurement accumulation: {}'.format(self.singMea_accumulation))

    def get_integration_time_ms(self):
        """
        Returns the integration time in milliseconds

        Returns:
            int: Integration time in milliseconds
        """
        return self.integration_time_ms
    
    def _set_integration_time(self,new_value_ms):
        """
        Sets the integration time of the spectrometer by taking in a variable. It also updates the variable

        Args:
            new_value_ms (int): New integration time [ms]
            tkcontainer (tk.label): Tkinter label which text is to be updated
        """
        self._btn_inttime.setEnabled(False)
        self._spin_inttime.setEnabled(False)
        
        @Slot()
        def reenable_widgets():
            self._btn_inttime.setEnabled(True)
            self._spin_inttime.setEnabled(True)

        @Slot(int)
        def set_self_integration_time(new_value_ms:int):
            self.integration_time_ms = new_value_ms
            self._lbl_dev_stat_inttime.setText(f'Device integration time: {new_value_ms} millisec')
            self.update_label_device_parameters()
            
        thread = QThread()
        worker = Spectrometer_Control_Workers(parent=self,controller=self._controller)
        worker.moveToThread(thread)
        
        thread.started.connect(lambda: worker.set_integration_time_us(int(new_value_ms*1000)))
        
        worker.new_integration_time_us.connect(
            lambda actual_time_us: set_self_integration_time(int(actual_time_us/1000))
        )
        
        worker.finished.connect(reenable_widgets)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
            
    def get_running_status(self):
        """
        Returns the status of scanning operation.
        
        Returns:
            bool: True if any of the scanning operations are running
        """
        return self._flg_isrunning.is_set()
    
    def _get_plot_limits(self) -> tuple[float|None,float|None,float|None,float|None]:
        """
        Reads the plot limit entry widgets and return the user-determined plot limits
        for the plot to be displayed.

        Returns:
            tuple[float,float,float,float]: (xmin,xmax,ymin,ymax)
        """
        try: xmin = float(self._entry_xmin.text())
        except: xmin = None
        try: xmax = float(self._entry_xmax.text())
        except: xmax = None
        try: ymin = float(self._entry_ymin.text())
        except: ymin = None
        try: ymax = float(self._entry_ymax.text())
        except: ymax = None
        
        return xmin,xmax,ymin,ymax
        
    def _reset_plot_limits(self):
        """
        Resets the entry inputs for the plot limits
        """
        self._entry_xmin.setText('')
        self._entry_xmax.setText('')
        self._entry_ymin.setText('')
        self._entry_ymax.setText('')
    
    def force_stop_measurement(self):
        """
        Forces any running measurement to stop.
        """
        self._flg_isrunning.clear()
    
    def perform_continuous_single_measurements(self,queue_mea:queue.Queue|None=None):
        """
        Perform continuous measurement until stopped. Generates a single measurement for each iteration, which is put into the queue.
        The measurement is then analysed and plotted. Accumulation is set to 1.
        
        Args:
            queue_mea (queue.Queue, optional): A queue to put the result in. Defaults to None.
        """
        self._statbar.showMessage("Continuous single measurements in progress")
        self._statbar.setStyleSheet("background-color: yellow;")
        
        # Turn the continuous measurement button into a stop button
        self._btn_cont_mea.setText('STOP')
        self._btn_cont_mea.setStyleSheet("background-color: red;")
        self._btn_cont_mea.clicked.disconnect()
        
        int_time_ms = int(self._controller.set_integration_time_us(int(self.integration_time_ms*1000))/1000)
        self.update_label_device_parameters(self.contMea_accumulation)
        extra_metadata = self._generate_metadata_dict()
        
        # Start the measurement worker
        thread = QThread()
        worker = RamanMeasurement_Worker(ramanHub=self._ramanHub)
        worker.moveToThread(thread)
        
        thread.started.connect(worker.acquire_single_measurement_nonstop(
            max_accumulation=self.singMea_accumulation,
            int_time_ms=int_time_ms,
            laserpower_mW=self._laserpower_mW,
            laserwavelength_nm=self._laserwavelength_nm,
            extra_metadata=extra_metadata,
            queue_mea=queue_mea
        ))
        
        worker.finished.connect(self.pause_auto_measurement)
        worker.finished.connect(lambda: self._statbar.showMessage("Raman controller ready"))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        self._btn_cont_mea.clicked.connect(lambda: worker.stop_acquisition())
        
        thread.start()
    
    def perform_continuous_measurement(self):
        """
        Perform continuous measurement until stopped.
        """
        # Disable the widgets to prevent command overlaps
        self._statbar.showMessage("Continuous measurement in progress")
        self._statbar.setStyleSheet("background-color: yellow;")
        self.disable_widgets()
        
        # Turn the continuous measurement button into a stop button
        self._btn_cont_mea.clicked.disconnect()
        self._btn_cont_mea.setText('STOP')
        self._btn_cont_mea.setStyleSheet("background-color: red;")
        self._btn_cont_mea.setEnabled(True)
        
        int_time_ms = self._controller.set_integration_time_us(int(self.integration_time_ms*1000))//1000
        self.update_label_device_parameters(self.contMea_accumulation)
        
        dict_metadata_extra = self._generate_metadata_dict()
        
        # Initializes the measurement
        self._thread = QThread()
        self._worker = RamanMeasurement_Worker(ramanHub=self._ramanHub)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(lambda: self._worker.acquire_single_measurement_nonstop(
            accumulation=self.contMea_accumulation,
            int_time_ms=int_time_ms,
            laserpower_mW=self._laserpower_mW,
            laserwavelength_nm=self._laserwavelength_nm,
            extra_metadata=dict_metadata_extra,
            emit_measurement=True,
        ))
        self._worker.mea_acquired_get.connect(
            lambda mea: self._update_plot(mea, title='Continuous Raman Measurement')
        )
        self._worker.finished.connect(lambda: self.reset_enable_widgets())
        self._worker.finished.connect(lambda: self._statbar.showMessage("Raman controller ready"))
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        
        self._btn_cont_mea.clicked.connect(lambda: self._worker.stop_acquisition())
        
        self._thread.start()
            
    def perform_ContinuousMeasurement_trigger(self) -> tuple[threading.Thread,queue.Queue,Callable,Callable,Callable,Callable]:
        """
        Wraps the _perform_ContinuousMeasurement_trigger function to be used in a separate process,
        and return the thread, queues, and functions to trigger and stop the measurement.
        
        Returns:
            tuple[threading.Thread,queue.Queue,Callable,Callable,Callable,Callable]: 
                The thread, return queue, start function, store function, ignore function, and stop function
        """
        q_trigger = queue.Queue()
        q_return = queue.Queue()
        thread = self._perform_ContinuousMeasurement_trigger(q_trigger,q_return)
        
        def start_measurement(): q_trigger.put(None)
        def store_prev_measurements(): q_trigger.put(None)
        def ignore_prev_measurements(): q_trigger.put(1)
        def stop_measurement(): q_trigger.put(0)
        
        return thread,q_return,start_measurement,store_prev_measurements,ignore_prev_measurements,stop_measurement
    
    def _perform_ContinuousMeasurement_trigger(self,q_trigger:queue.Queue,q_return:queue.Queue) -> threading.Thread:
        """
        Perform continuous measurement until stopped.
        
        Idea: clicking the button once should activate the mode and clicking it again should turn it off
        
        Args:
            q_trigger (queue.Queue): A queue to trigger the resume/stop of the continuous measurement. True to trigger the next measurement, False to stop.
            q_return (queue.Queue): A queue to return the result of the measurement after every trigger command.
            
        Usage:
            1. Prepare an external queue for the trigger and return
            2. Call this function
            3. Put anything to trigger to initialise the measurement
            4. For every next [any], measurements between this trigger and the previous trigger timestmap
            5. Put 0 to stop the measurement or 1 to skip the measurements
                between this trigger and the previous timestamp (e.g., when the stage is moving
                and the measurement is not needed)
        """
        if not self._ramanHub.isrunning_auto_measurement(): self.resume_auto_measurement()
        else: print('!!!!! Auto-measurement is already running, a part of the program did NOT TERMINATE it properly !!!!!')
        
        # Disable the widgets to prevent command overlaps
        self.disable_widgets()
        
        self._statbar.showMessage("Continuous measurement in progress")
        self._statbar.setStyleSheet("background-color: yellow;")
        
        int_time_ms = self._controller.set_integration_time_us(int(self.integration_time_ms*1000))//1000
        self.update_label_device_parameters(self.contMea_accumulation)
        
        # Initialise the analyser and plotter
        extra_metadata = self._generate_metadata_dict()
        
        # Initializes the measurement
        self._ramanHub.wait_MeasurementUpdate()
        
        # Initialise the thread and worker
        self._thread_mea = QThread()
        self._worker_mea = RamanMeasurement_Worker(ramanHub=self._ramanHub)
        self._worker_mea.moveToThread(self._thread_mea)
        self._thread_mea.started.connect(lambda: self._worker_mea.acquire_continuous_measurement_trigger(
            q_trigger=q_trigger,
            q_return=q_return,
            laserpower_mW=self._laserpower_mW,
            laserwavelength_nm=self._laserwavelength_nm,
            extra_metadata=extra_metadata,
        ))
        self._worker_mea.mea_acquired_get.connect(
            lambda mea: self._update_plot(mea, title='Continuous Raman Measurement')
        )
        self._worker_mea.finished.connect(lambda: self.reset_enable_widgets())
        self._worker_mea.finished.connect(lambda: self._statbar.showMessage("Raman controller ready"))
        self._worker_mea.finished.connect(self._thread_mea.quit)
        self._worker_mea.finished.connect(self._worker_mea.deleteLater)
        self._thread_mea.finished.connect(self._thread_mea.deleteLater)
        
        self._thread_mea.start()
    
    @Slot()
    def pause_auto_measurement(self):
        """
        Pauses the auto-measurement in the RamanHub
        """
        self._ramanHub.pause_auto_measurement()
        
    def resume_auto_measurement(self):
        """
        Resumes the auto-measurement in the RamanHub
        """
        self._ramanHub.resume_auto_measurement()
        
    def perform_single_measurement(self, queue_measurement:queue.Queue|None=None):
        """
        Perform multiple measurements based on the self.measurement_accumulation, averages, and 
        updates the displayed figure all the time.
        """
        if self._ramanHub.isrunning_auto_measurement():
            self.pause_auto_measurement()
            print('!!!!! Auto-measurement is already running, a part of the program did NOT TERMINATE it properly !!!!!')
        
        # Notify the user that the measurement is starting
        self._statbar.showMessage("Single measurement in progress")
        self._statbar.setStyleSheet("background-color: yellow;")
        
        # Sets the integration time and accumulation
        int_time_ms = self._controller.set_integration_time_us(int(self.integration_time_ms*1000))//1000
        self.update_label_device_parameters(self.singMea_accumulation)
        
        # Initialise the measurement
        dict_metadata_extra = self._generate_metadata_dict()
        self._sngl_measurement = MeaRaman(
            timestamp=get_timestamp_us_int(),
            int_time_ms=int_time_ms,
            laserPower_mW=self._laserpower_mW,
            laserWavelength_nm=self._laserwavelength_nm,
            extra_metadata=dict_metadata_extra
            )
        
        # Performs the measurements
        accumulation = self.singMea_accumulation
        
        self._thread_mea = QThread()
        self._worker_mea = RamanMeasurement_Worker(ramanHub=self._ramanHub)
        self._worker_mea.moveToThread(self._thread_mea)
        
        self._thread_mea.started.connect(lambda: self._worker_mea.acquire_single_measurement(
            measurement=self._sngl_measurement,
            accumulation=accumulation,
            int_time_ms=int_time_ms,
            laserpower_mW=self._laserpower_mW,
            laserwavelength_nm=self._laserwavelength_nm,
            queue_mea=queue_measurement,
            extra_metadata=dict_metadata_extra,
        ))
        
        self._worker_mea.finished.connect(lambda: self._statbar.showMessage("Raman controller ready"))
        self._worker_mea.finished.connect(lambda: self._update_plot(self._sngl_measurement, 
                                                                title='Single Raman Measurement'))
        self._worker_mea.finished.connect(self.pause_auto_measurement)
        
        self._worker_mea.finished.connect(self._thread_mea.quit)
        self._worker_mea.finished.connect(self._worker_mea.deleteLater)
        self._thread_mea.finished.connect(self._thread_mea.deleteLater)
        
        self._thread_mea.start()
        
    @Slot()
    def _update_plot(self, measurement:MeaRaman, title='Single Raman Measurement',):
        if hasattr(self,'_isplotting') and self._isplotting: return
        self._isplotting = True
        self._plotter.plot_RamanMeasurement_new(
            measurement=measurement,
            title=title,
            flg_plot_ramanshift=self._bool_PlotRamanShift.isChecked(),
            plot_raw=self._bool_PlotRawOnly.isChecked(),
            limits=self._get_plot_limits(),
        )
        self._fig_widget.draw()
        self._isplotting = False

    def initialise_spectrometer_n_analyser(self):
        """
        Sets up the raman spectrometer controller and analyser in a worker thread
        """
        # Configure the integration time config
        intTime_min, intTime_max, intTime_inc = self._controller.get_integration_time_limits_us()
        self._spin_inttime.setRange(intTime_min, intTime_max)

        # Set and get the current device integration time
        self._set_integration_time(self.integration_time_ms)
        self.integration_time_ms = int(self._controller.get_integration_time_us()/1000)
        
        # Update the current device integration time being
        self.update_label_device_parameters()
        
        # Activates all spectrometer controls once done with the initialisation
        self.reset_enable_widgets()
    
    def disable_widgets(self):
        """
        Disables all widgets in a Tkinter frame and sub-frames
        """
        widget:qw.QWidget
        for widget in get_all_widgets_from_layout(self._slyt_controls):
            widget.setEnabled(False)
            
        for widget in get_all_widgets_from_layout(self._slyt_data):
            widget.setEnabled(False)

    def reset_enable_widgets(self):
        """
        Enable all widgets in a Tkinter frame and sub-frames
        """
        widget:qw.QWidget
        for widget in get_all_widgets_from_layout(self._slyt_controls):
            widget.setEnabled(True)
            
        for widget in get_all_widgets_from_layout(self._slyt_data):
            widget.setEnabled(True)
            
        # Resets the continuous measurement button
        self._btn_cont_mea.setText('Continuous measurement')
        self._btn_cont_mea.setStyleSheet("")
        self._btn_cont_mea.clicked.disconnect()
        self._btn_cont_mea.clicked.connect(lambda: self.perform_continuous_measurement())
        self._btn_cont_mea.setEnabled(True)
        
    def terminate(self):
        """Terminates the controller and the processor
        """
        self._controller.terminate()
        
        
def create_dummy_image(counter):
    """
    Creates a white 250x250 image with a counter text displayed in the center.

    Args:
        counter: The number to display on the image.

    Returns:
        A NumPy array representing the white image with the counter text.
    """
    # Create a white image
    image = np.ones((250, 250, 3), dtype=np.uint8) * 255

    # Set font properties
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    font_thickness = 2
    text_color = (0, 0, 0)  # Black text color

    # Get text size
    text_size, _ = cv2.getTextSize(str(counter), font, font_scale, font_thickness)

    # Calculate text placement coordinates
    text_x = int((image.shape[1] - text_size[0]) / 2)
    text_y = int((image.shape[0] + text_size[1]) / 2)

    # Add counter text to the image
    cv2.putText(image, str(counter), (text_x, text_y), font, font_scale, text_color, font_thickness)

    return image

if __name__ == '__main__':
    base_manager = get_my_manager()
    initialise_manager_raman(base_manager)
    base_manager.start()
    RamanController_proxy, dict_MeaRaman_proxy = initialise_proxy_raman(base_manager)
    RamanHub = DataStreamer_Raman(RamanController_proxy,dict_MeaRaman_proxy)
    RamanHub.start()
    
    print(os.cpu_count())
    processor = mpp.Pool()
    
    app = qw.QApplication()
    main_window = qw.QMainWindow()
    main_window.setWindowTitle("Raman Spectrometer Controller Test")
    
    central_widget = qw.QWidget()
    main_window.setCentralWidget(central_widget)
    layout = qw.QVBoxLayout(central_widget)
    
    # root = tk.Tk()
    
    # dataHub = Frm_DataHub_Mapping(master=root)
    raman_frame = Frm_RamanSpectrometerController(
        parent=central_widget,
        processor=processor,
        controller=RamanController_proxy,
        ramanHub=RamanHub,
        dataHub=None
    )
    layout.addWidget(raman_frame)
    main_window.show()
    
    app.exec()
    raman_frame.terminate()