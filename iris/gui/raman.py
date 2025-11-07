
"""
A class that manages the motion controller aspect for the Ocean Direct Raman spectrometer
"""
import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer, QCoreApplication, QMetaType

import os
import multiprocessing.pool as mpp

import threading
import queue
from typing import Callable, Any, TypedDict
from enum import Enum

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
from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping
from iris.data.measurement_Raman import MeaRaman, MeaRaman_Plotter
from iris.multiprocessing.dataStreamer_Raman import DataStreamer_Raman, initialise_manager_raman, initialise_proxy_raman
from iris.multiprocessing.basemanager import get_my_manager

from iris.controllers import Controller_Spectrometer

from iris import DataAnalysisConfigEnum
from iris.gui import AppRamanEnum

from iris.resources.raman_ui import Ui_Raman

class Wdg_Raman(qw.QWidget, Ui_Raman):
    """
    A class defining the Raman spectrometer GUI.
    """
    def __init__(self, parent:Any) -> None:
        super().__init__(parent)
        self.setupUi(self)
        vlayout = qw.QVBoxLayout()
        self.setLayout(vlayout)
        vlayout.addWidget(self.groupBox_plt)
        vlayout.addWidget(self.groupBox_params)



class RamanMeasurement_Analysis_Worker(QObject):
    """
    A class defining the worker functions for Raman measurement analysis.
    """
    sig_start_autoplotter = Signal()
    sig_plot_redrawn = Signal()
    
    def __init__(
        self,
        processor:mpp.Pool,
        plotter:MeaRaman_Plotter,
        queue_analysis:queue.Queue,
        queue_return:queue.Queue) -> None:
        
        super().__init__()
        self._processor = processor
        self._plotter = plotter
        self._q_analysis = queue_analysis
        self._q_return = queue_return
        
        self._plt_isrunning = False
        
    @Slot(MeaRaman,bool)
    def analyse_plot_rawlist2mea(self,measurement:MeaRaman, plot:bool) -> None:
        """
        Analyses the Raman measurement by averaging the raw list and plots the raw and averaged spectrum.
        
        Args:
            measurement (MeaRaman): The Raman measurement to be analysed.
            plot (bool): Whether to plot the analysed measurement.
        """
        rawlist = measurement.get_raw_list()
        if len(rawlist) > 1:
            result_analysis = self._processor.apply_async(func=MeaRaman.average, args=(rawlist,))
            spectrum_avg = result_analysis.get()
        else:
            spectrum_avg = rawlist[0]
        measurement.set_analysed(spectrum_analysed=spectrum_avg)
        
        self._q_return.put(measurement)

class Spectrometer_Control_Workers(QObject):
    """
    A class defining the worker functions for the Raman spectrometer controller.
    """
    sig_integration_time_us = Signal(int)

    def __init__(self, controller: Controller_Spectrometer) -> None:
        super().__init__()
        self._controller = controller
        
    @Slot(int)
    def set_integration_time_us(self, new_value_us: int) -> None:
        """
        Sets the integration time of the spectrometer.

        Args:
            new_value_us (int): New integration time [us]

        Returns:
            int: The actual integration time set [us]
        """
        inttime_ms = self._controller.set_integration_time_us(new_value_us)
        self.sig_integration_time_us.emit(inttime_ms)
        
        
    @Slot()
    def get_integration_time_us(self) -> None:
        """
        Gets the integration time of the spectrometer.

        Returns:
            int: The current integration time [us]
        """
        current_time_us = self._controller.get_integration_time_us()
        self.sig_integration_time_us.emit(current_time_us)
        
class AcquisitionParams(TypedDict):
    accumulation: int
    int_time_ms: int
    laserpower_mW: float
    laserwavelength_nm: float
    extra_metadata: dict

class Enum_ContinuousMeasurementTrigger(Enum):
    """
    Enum for the continuous measurement trigger options.
    """
    START = 'start'
    PAUSE = 'pause'
    FINISH = 'finish'
    STORE = 'store'
    IGNORE = 'ignore'

class RamanMeasurement_Worker(QObject):
    """
    A class defining the worker functions for Raman measurement acquisition.
    """
    sig_acq_done = Signal()  # Signal emitted when the acquisition process is complete (both single and continuous)
    sig_acq = Signal() # Signal emitted when a measurement is acquired
    sig_mea_error = Signal(str) # Signal emitted when an error occurs during measurement acquisition
    
    sig_mea = Signal(MeaRaman) # Signal emitted when a measurement is acquired (for burst mode)
    
    mode_discrete = 0
    mode_continuous = 1

    def __init__(self, ramanHub: DataStreamer_Raman) -> None:
        super().__init__()
        self._ramanHub = ramanHub
        self._isacquiring = False
        self._timer_continuous = QTimer()
        
        self._acquisition_params:AcquisitionParams|None = None
        self._list_queue_observer:list[queue.Queue] = []    
        
        self._last_measurement:MeaRaman|None = None
               
    @Slot(queue.Queue, threading.Event)
    def append_queue_observer_measurement(self, queue_observer: queue.Queue, done:threading.Event) -> None:
        """
        Appends a queue observer to the list of queue observers.

        Args:
            queue_observer (queue.Queue): The queue observer to be appended.
            done (threading.Event): The event to signal when done.
        """
        assert isinstance(queue_observer, queue.Queue), "queue_observer must be an instance of queue.Queue"
        self._list_queue_observer.append(queue_observer)
        done.set()
        
    @Slot(queue.Queue)
    def remove_queue_observer_measurement(self, queue_observer: queue.Queue) -> None:
        """
        Removes a queue observer from the list of queue observers.

        Args:
            queue_observer (queue.Queue): The queue observer to be removed.
        """
        assert isinstance(queue_observer, queue.Queue), "queue_observer must be an instance of queue.Queue"
        try: self._list_queue_observer.remove(queue_observer)
        except: pass
        
    @Slot()
    def stop_acquisition(self) -> None:
        """
        Stops the continuous acquisition of Raman measurements.
        """
        self._isacquiring = False
        
    @Slot(AcquisitionParams)
    def acquire_continuous_measurement(self, params: AcquisitionParams):
        self._acquisition_params = params
        self._ramanHub.resume_auto_measurement()
        
        self._isacquiring = True
        self._schedule_next_acquisition_cycle(params)
        
    @Slot(AcquisitionParams)
    def acquire_single_measurement(self, params:AcquisitionParams):
        self._acquisition_params = params
        self._ramanHub.resume_auto_measurement()
        
        self._acquire_one_measurement(params)
        
        self.sig_acq_done.emit()
        self._ramanHub.pause_auto_measurement()
        
    
    @Slot(AcquisitionParams, queue.Queue, queue.Queue, threading.Event)
    def acquire_continuous_burst_measurement_trigger(
        self,
        params:AcquisitionParams,
        q_trigger:queue.Queue[Enum_ContinuousMeasurementTrigger],
        q_return:queue.Queue[MeaRaman],
        event_ready:threading.Event,
        ):
        """
        Acquires the spectrum in a continuous manner (one after another consecutively)
        and puts them in the return queue or ignore them based on the commands from q_trigger.
        For the full list of available commands, refer to the Enum_ContinuousMeasurementTrigger class.
        
        NOTE: The first command in q_trigger MUST be START to begin the measurement, followed by either
        STORE or IGNORE commands. To stop the measurement, send the FINISH command.
        
        NOTE: This function **blocks** the thread until the FINISH command is received.
        
        Args:
            params (AcquisitionParams): The acquisition parameters that will be fixed to the acquired measurements.
            q_trigger (queue.Queue): The trigger queue to command the measurement actions.
            q_return (queue.Queue): The return queue where the acquired measurements are put.
            event_ready (threading.Event): The event to signal when the process is ready for the next command,
                triggered after receiving the START command and after the measurements are put in the return queue
                after each STORE command.
        """
        self._acquisition_params = params
        self._ramanHub.resume_auto_measurement()
        
        trigger = q_trigger.get()
        if not trigger == Enum_ContinuousMeasurementTrigger.START:
            raise ValueError('The first trigger command must be START to begin the continuous measurement.')
        
        list_timestamp_trigger = [get_timestamp_us_int()]
        self._isacquiring = True
        
        EnumTrig = Enum_ContinuousMeasurementTrigger
        
        event_ready.set()
        while self._isacquiring:
            # Wait for the trigger to start the next measurement or to stop
            trigger = q_trigger.get()
            if trigger == EnumTrig.FINISH: break
            
            # Retrieve the measurements
            list_timestamp_trigger.append(get_timestamp_us_int())
            list_timestamp_mea_int,list_spectrum,list_integration_time_ms=\
                self._ramanHub.get_measurement(
                    timestamp_start=list_timestamp_trigger[-2],
                    timestamp_end=list_timestamp_trigger[-1])
            list_timestamp_trigger.pop(0) # Remove the first element (not needed anymore)
            
            if trigger == EnumTrig.IGNORE: continue
            
            list_measurement = []
            for ts_int,spectrum_raw,int_time_ms in zip(list_timestamp_mea_int,list_spectrum,list_integration_time_ms):
                measurement = MeaRaman(
                    timestamp=ts_int,
                    int_time_ms=int_time_ms,
                    laserPower_mW=params['laserpower_mW'],
                    laserWavelength_nm=params['laserwavelength_nm'],
                    extra_metadata=params['extra_metadata'])
                measurement.set_raw_list(df_mea=spectrum_raw, timestamp_int=ts_int)
                list_measurement.append(measurement)
            
            # Return the measurement result
            for mea in list_measurement:
                mea.calculate_analysed()
                q_return.put(mea)
                self._notify_queue_observers(measurement=mea)
                
            event_ready.set()
            
        self.sig_acq_done.emit()
        self._ramanHub.pause_auto_measurement()
        
    @Slot(AcquisitionParams)
    def _schedule_next_acquisition_cycle(self, params:AcquisitionParams):
        """
        Executes one measurement unit and schedules the next one if still running.
        This is the core of the non-blocking loop.
        """
        if not self._isacquiring:
            self.sig_acq_done.emit()
            self._ramanHub.pause_auto_measurement()
            return
            
        try:
            self._acquire_one_measurement(params)
            QTimer.singleShot(0, lambda: self._schedule_next_acquisition_cycle(params))
        except Exception as e:
            self._isacquiring = False
            self.sig_mea_error.emit(f'Critical error in acquisition cycle: {e}')
            self.sig_acq_done.emit()
            self._ramanHub.pause_auto_measurement()

    def _acquire_one_measurement(self, params:AcquisitionParams):
        """
        Acquire a single measurement

        Args:
            params (AcquisitionParams | None, optional): The acquisition parameters. Defaults to None.
            continuous (bool, optional): Whether the acquisition is continuous. Defaults to False.
        """
        # try: print(f'Gap between measurements: {(time.time()-self._t1)*1e3:.0f} ms')
        # except: pass
        # self._t1 = time.time()
        timestamp = get_timestamp_us_int()
        measurement = MeaRaman(
            timestamp=timestamp,
            int_time_ms=params['int_time_ms'],
            laserPower_mW=params['laserpower_mW'],
            laserWavelength_nm=params['laserwavelength_nm'],
            extra_metadata=params['extra_metadata'],
            )

        for _ in range(params['accumulation']):    
            # Performs a measurement and add it to the storage
            timestamp_request = get_timestamp_us_int()
            result = self._ramanHub.get_measurement(timestamp_request,WaitForMeasurement=False,getNewOnly=True)
            spectrum_raw = result[1][-1]
            
            measurement.set_raw_list(
                df_mea=spectrum_raw,
                timestamp_int=timestamp_request,
                max_accumulation=params['accumulation']
                )
            
            self._notify_queue_observers(measurement)
            self.sig_acq.emit()
        
        self._last_measurement = measurement
        time.sleep(0.001) # Small delay to prevent overloading the CPU
        
    @Slot()
    def request_last_measurement(self) -> None:
        """
        Returns the last acquired measurement.
        """
        if self._last_measurement is not None:
            self.sig_mea.emit(self._last_measurement)
        
    def _notify_queue_observers(self, measurement:MeaRaman) -> None:
        """
        Notifies all queue observers with the acquired measurement.

        Args:
            measurement (MeaRaman): The acquired Raman measurement.
        """
        for q in self._list_queue_observer:
            try: q.put(measurement)
            except Exception as e: print(f'Error in _notify_queue_observers: {e}')

class Wdg_SpectrometerController(qw.QWidget):
    """
    A class defining the app subwindow for the Raman spectrometer.
    """
    sig_set_integration_time_us = Signal(int)
    
    _sig_request_mea_sngl = Signal(AcquisitionParams)
    _sig_request_mea_cont = Signal(AcquisitionParams)
    _sig_request_mea_stop = Signal()
    
    _sig_request_lastmea = Signal() # Signal to request the last measurement from the acquisition worker
    _sig_append_queue_observer = Signal(queue.Queue, threading.Event)    # Signal to append a queue observer to the acquisition worker
    _sig_remove_queue_observer = Signal(queue.Queue)    # Signal to remove a queue observer from the acquisition worker
    
    def __init__(
        self,
        parent:Any,
        processor:mpp.Pool,
        controller:Controller_Spectrometer,
        ramanHub:DataStreamer_Raman,
        dataHub:Wdg_DataHub_Mapping|None,
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
        

# >>> Threading and worker setups <<<
    # >> Communciation with the controller <<
        self._thread_controller = QThread(self)
        self._worker_controller = Spectrometer_Control_Workers(controller=self._controller)
        self._worker_controller.moveToThread(self._thread_controller)
        self.destroyed.connect(self._thread_controller.quit)
        self._thread_controller.finished.connect(self._worker_controller.deleteLater)
        self._thread_controller.finished.connect(self._thread_controller.deleteLater)
        self._thread_controller.start()
        
    # >> Acquisition <<
        self._thread_acquisition = QThread(self)
        self._worker_acquisition = RamanMeasurement_Worker(
            ramanHub=self._ramanHub
        )
        self._worker_acquisition.moveToThread(self._thread_acquisition)
        self.destroyed.connect(self._thread_acquisition.quit)
        self._thread_acquisition.finished.connect(self._worker_acquisition.deleteLater)
        self._thread_acquisition.finished.connect(self._thread_acquisition.deleteLater)
        self._thread_acquisition.start()

    # >> Connection setups <<
        self._init_request_integration_time_connection()
        self._init_btn_measurements_connection()
        
# >>> Get controller parameters <<<
        self._controller_id = self._controller.get_identifier()
        
# >>> GUI setup <<<
        self._main_layout = qw.QVBoxLayout()
        self.setLayout(self._main_layout)
        
        self._main_widget = Wdg_Raman(self)
        self._main_layout.addWidget(self._main_widget)
        widget = self._main_widget
        
# >>> Spectrometer control and data handling setup <<<
        # Spectrometer parameters setup
        self.integration_time_ms = AppRamanEnum.DEFAULT_INTEGRATION_TIME_MS.value 
        self._accumulation = AppRamanEnum.DEFAULT_SINGMEA_ACCUMULATION.value
        
        # Is-running flags
        self._flg_isrunning = threading.Event()
        
        # Spectrometer internal data storage setup
        self._sngl_measurement:MeaRaman = MeaRaman(reconstruct=True)    # single measurement
        self._cont_measurement:MeaRaman = MeaRaman(reconstruct=True)    # continuous measurement
        
        # Plotter setup
        self._plotter = MeaRaman_Plotter()
        self._q_plt_mea = queue.Queue() # Queue for plotting measurements (will plot the latest measurement only)
        self._plt_timer = QTimer()
        self._plt_timer.timeout.connect(self._auto_update_plot)
        self._plt_timer.setSingleShot(True)
        self._plt_timer.setInterval(50) # Update every 50 ms (will be dynamically adjusted later)
        self._plt_timer.start()
        
# >>> Control frames setup <<<
        # Initialise the statusbar
        self._statbar = qw.QStatusBar(self)
        self._statbar.showMessage("Raman controller initialisation")
        self._main_layout.addWidget(self._statbar)
        
# >>> Measurement control widgets setup <<<
    # Plot widget setup
        self._plotter = MeaRaman_Plotter()
        self._fig, self._ax = self._plotter.get_fig_ax()
        self._fig_widget = FigureCanvas(self._fig)
        widget.lyt_plot.addWidget(self._fig_widget)
        
    # Basic plot control widgets
        # Add widgets for additional plot options
        self._bool_PlotRamanShift = widget.chk_ramanshift
        self._bool_PlotRamanShift.setChecked(True)

    # Additional plot control widgets
        # Widgets for the plot limits
        self._entry_xmin = widget.ent_plt_xmin
        self._entry_xmax = widget.ent_plt_xmax
        self._entry_ymin = widget.ent_plt_ymin
        self._entry_ymax = widget.ent_plt_ymax
        widget.btn_reset_plot_limits.clicked.connect(lambda: self._reset_plot_limits())
        
        @Slot(MeaRaman)
        def _put_lastmea_into_plotqueue(measurement: MeaRaman): self._q_plt_mea.put(measurement)

        self._worker_acquisition.sig_mea.connect(_put_lastmea_into_plotqueue)
        self._sig_request_lastmea.connect(self._worker_acquisition.request_last_measurement)

        [widget.textChanged.connect(lambda: self._sig_request_lastmea.emit())\
            for widget in get_all_widgets(widget.groupBox_plt) if isinstance(widget,qw.QLineEdit)]
        
    # Raman controller setups
        self._btn_sngl_mea = widget.btn_snglmea
        self._btn_cont_mea = widget.btn_contmea
        
        self._btn_sngl_mea.clicked.connect(self._perform_single_measurement)
        self._btn_cont_mea.clicked.connect(self._perform_continuous_measurement)
        
    # Add buttons and labels for device parameter setups
        ## Label to notify the users of the current device parameters
        self._lbl_dev_stat_inttime = widget.lbl_inttime_ms
        self._lbl_dev_stat_accum = widget.lbl_accum
        
        ## Label to show the current setting, spinbox to let the user enter new parameters,
        ## button to call the command and update the label
        ### for single measurement integration time
        self._spin_inttime = widget.spin_inttime_ms
        
        self._spin_inttime.returnPressed.connect(lambda: self._request_integration_time(
            new_value_ms=int(self._spin_inttime.value())))
        
        ### for single measurement number of accumulation
        self._lbl_sngl_acq = widget.lbl_accum
        self._spin_sngl_acq = widget.spin_accum
        
        self._spin_sngl_acq.returnPressed.connect(lambda: self.set_accumulation(
            new_value=int(self._spin_sngl_acq.value())))
        
        if main: self.initialise_spectrometer_n_analyser()
        
    # >>> Data management widgets setup <<<
        # Datasave widget
        self._btn_saveto_datahub = widget.btn_savetomanager
        if isinstance(self._dataHub,Wdg_DataHub_Mapping):
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
        qw.QErrorMessage().showMessage('Objective info save not implemented yet!')
        
        # Entry widgets and button to set the metadata
        self._entry_laserpower = widget.ent_laserpower_mW
        self._entry_laserwavelength = widget.ent_laserwavelength_nm
        
        # Default values
        self._entry_laserpower.setText(str(DataAnalysisConfigEnum.LASER_POWER_MILLIWATT.value))
        self._entry_laserwavelength.setText(str(DataAnalysisConfigEnum.LASER_WAVELENGTH_NM.value))
        
        # Bind the value change to setting the laser metadata
        self._entry_laserpower.textChanged.connect(lambda: self._set_laserMetadata())
        self._entry_laserwavelength.textChanged.connect(lambda: self._set_laserMetadata())
        
    # >>> Connections setup <<<
        # Connect the append queue observer signal to the acquisition worker
        self._sig_append_queue_observer.connect(self._worker_acquisition.append_queue_observer_measurement)
        self._sig_remove_queue_observer.connect(self._worker_acquisition.remove_queue_observer_measurement)
        self._sig_append_queue_observer.emit(self._q_plt_mea, threading.Event())
        
        # Connect the acquisition done signal to reset the widgets and statusbar
        self._worker_acquisition.sig_acq_done.connect(lambda: self._statbar.showMessage("Raman controller ready"))
        self._worker_acquisition.sig_acq_done.connect(lambda: self._statbar.setStyleSheet(""))
        self._worker_acquisition.sig_acq_done.connect(lambda: self.reset_enable_widgets())
        
    # >>> Finalise the setup <<<
        # Update the statusbar
        self._statbar.showMessage("Raman controller ready")
    
    def get_mea_worker(self) -> RamanMeasurement_Worker:
        """
        Returns the Raman measurement worker

        Returns:
            RamanMeasurement_Worker: The Raman measurement worker
        """
        return self._worker_acquisition
    
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
    
    @Slot(int)
    def update_label_device_parameters(self,int_time_ms:int|None=None,accum:int|None=None):
        """
        Updates the label showing the device integration time from the device itself
        and accumulation from the input
        
        Args:
            int_time (int): new integration time to be displayed
            accum (int): new accumulation to be displayed
        """
        if int_time_ms is not None:
            self._lbl_dev_stat_inttime.setText(f'{int_time_ms}')
            self.integration_time_ms = int_time_ms
        if accum is not None:
            self._lbl_dev_stat_accum.setText(f'{accum}')
            self._accumulation = accum

    def set_accumulation(self,new_value):
        """
        Set the accumulation for measurements
        
        Args:
            new_value (int): The new accumulation value
        """
        self._accumulation = new_value
        self._lbl_sngl_acq.setText(f'{self._accumulation}')

    def get_integration_time_ms(self):
        """
        Returns the integration time in milliseconds

        Returns:
            int: Integration time in milliseconds
        """
        return self.integration_time_ms

    @Slot(int)
    def _request_integration_time(self,new_value_ms):
        """
        Sets the integration time of the spectrometer by taking in a variable. It also updates the variable

        Args:
            new_value_ms (int): New integration time [ms]
            tkcontainer (tk.label): Tkinter label which text is to be updated
        """
        self._spin_inttime.setEnabled(False)
        if not isinstance(new_value_ms,int) or new_value_ms <= 0:
            qw.QErrorMessage(self).showMessage('Invalid integration time input')
            self._statbar.showMessage('Invalid integration time input',5000)
            self._spin_inttime.setEnabled(True)
            return
        
        self.sig_set_integration_time_us.emit(new_value_ms*1000)

    def _init_request_integration_time_connection(self):
        """
        Initializes the connection for requesting integration time updates
        """
        self.sig_set_integration_time_us.connect(self._worker_controller.set_integration_time_us)
        self._worker_controller.sig_integration_time_us.connect(lambda: self._spin_inttime.setEnabled(True))
        self._worker_controller.sig_integration_time_us.connect(
            lambda int_time:self.update_label_device_parameters(int_time_ms=int_time//1000))
            
    def _init_btn_measurements_connection(self):
        """
        Initializes the connection for the measurement buttons
        """
        # Connection to the acquisition worker
        self._sig_request_mea_sngl.connect(self._worker_acquisition.acquire_single_measurement)
        self._sig_request_mea_cont.connect(self._worker_acquisition.acquire_continuous_measurement)
        self._sig_request_mea_stop.connect(self._worker_acquisition.stop_acquisition)
        
        self._sig_request_mea_sngl.connect(self.disable_widgets)
        self._sig_request_mea_cont.connect(lambda: self.disable_widgets(exclude_cont=True))

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
    
    @Slot()
    def _perform_continuous_measurement(self):
        """
        Perform continuous measurement until stopped.
        """
        # Disable the widgets to prevent command overlaps
        self._statbar.showMessage("Continuous measurement in progress")
        self._statbar.setStyleSheet("background-color: yellow;")
        
        # Turn the continuous measurement button into a stop button
        self._btn_cont_mea.clicked.disconnect()
        self._btn_cont_mea.setText('STOP')
        self._btn_cont_mea.setStyleSheet("background-color: red;")
        self._btn_cont_mea.clicked.connect(self._sig_request_mea_stop.emit)
        
        # Sets the integration time and accumulation
        self.update_label_device_parameters(accum=self._accumulation)
        
        dict_params = self.generate_acquisition_params()
        
        # Start the measurement
        self._sig_request_mea_cont.emit(dict_params)
        
    def generate_acquisition_params(self) -> AcquisitionParams:
        """
        Generates the acquisition parameters based on the current settings

        Returns:
            AcquisitionParams: The acquisition parameters
        """
        # Sets the integration time and accumulation
        int_time_ms = self._controller.set_integration_time_us(int(self.integration_time_ms*1000))//1000
        
        # Initialise the measurement parameters
        dict_metadata_extra = self._generate_metadata_dict()
        dict_params:AcquisitionParams = {
            'accumulation': self._accumulation,
            'int_time_ms': int_time_ms,
            'laserpower_mW': self._laserpower_mW,
            'laserwavelength_nm': self._laserwavelength_nm,
            'extra_metadata': dict_metadata_extra,
        }
        return dict_params
        
    @Slot()
    def _perform_single_measurement(self):
        """
        Perform multiple measurements based on the self.measurement_accumulation, averages, and 
        updates the displayed figure all the time.
        """
        # Notify the user that the measurement is starting
        self._statbar.showMessage("Single measurement in progress")
        self._statbar.setStyleSheet("background-color: yellow;")
        
        # Sets the integration time and accumulation
        self.update_label_device_parameters(accum=self._accumulation)
        
        dict_params = self.generate_acquisition_params()
        
        # Start the measurement
        self._sig_request_mea_sngl.emit(dict_params)
        
    def _append_remove_observer_queue_to_worker(self, queue_observer:queue.Queue):
        """
        Appends a queue observer to the measurement worker and removes it when the acquisition is done.

        Args:
            queue_observer (queue.Queue): The queue observer to be added
        """
        append_done = threading.Event()
        self._sig_append_queue_observer.emit(queue_observer, append_done)
        self._worker_acquisition.sig_acq_done.connect(lambda: self._sig_remove_queue_observer.emit(queue_observer))
        append_done.wait()

    def _auto_update_plot(self):
        """
        Auto-update the plot with the latest measurement in the queue
        """
        try:
            measurement:MeaRaman|None = None
            while not self._q_plt_mea.empty():
                measurement = self._q_plt_mea.get_nowait()
            if not isinstance(measurement,MeaRaman) and not measurement is None:
                raise TypeError("Invalid measurement type in the plot queue") # pyright: ignore[reportPossiblyUnboundVariable] ; it is guaranteed to be assigned if no exception is raised
            self._update_plot(measurement, title='Raw Raman Spectrum')
        except queue.Empty: pass
        finally: self._plt_timer.start()

    def _update_plot(self, measurement:MeaRaman|None, title='Single Raman Measurement',):
        if measurement is None or not measurement.check_measurement_exist(): return
        self._plotter.plot_RamanMeasurement_new(
            measurement=measurement,
            title=title,
            flg_plot_ramanshift=self._bool_PlotRamanShift.isChecked(),
            plot_raw=True,
            limits=self._get_plot_limits(),
        )
        self._fig_widget.draw()
        
        try: print(f'Gap between plots: {(time.time()-self._t1)*1e3:.0f} ms')
        except: pass
        self._t1 = time.time()
        
    def initialise_spectrometer_n_analyser(self):
        """
        Sets up the raman spectrometer controller and analyser in a worker thread
        """
        # Configure the integration time config
        intTime_min, intTime_max, intTime_inc = self._controller.get_integration_time_limits_us()
        self._spin_inttime.setRange(intTime_min, intTime_max)

        # Set and get the current device integration time
        self._request_integration_time(self.integration_time_ms)
        self.integration_time_ms = int(self._controller.get_integration_time_us()/1000)
        
        # Update the current device integration time being
        self.update_label_device_parameters()
        
        # Activates all spectrometer controls once done with the initialisation
        self.reset_enable_widgets()
    
    def disable_widgets(self, exclude_cont:bool=False):
        """
        Disables all widgets in a Tkinter frame and sub-frames
        """
        widget:qw.QWidget
        for widget in get_all_widgets(self._main_widget.groupBox_params):
            widget.setEnabled(False)
            
        if exclude_cont: self._btn_cont_mea.setEnabled(True)

    def reset_enable_widgets(self):
        """
        Enable all widgets in a Tkinter frame and sub-frames
        """
        widget:qw.QWidget
        for widget in get_all_widgets(self._main_widget.groupBox_params):
            widget.setEnabled(True)
            
        # Resets the continuous measurement button
        self._btn_cont_mea.clicked.disconnect()
        self._btn_cont_mea.setText('Continuous measurement')
        self._btn_cont_mea.setStyleSheet("")
        self._btn_cont_mea.clicked.connect(self._perform_continuous_measurement)
        self._btn_cont_mea.setEnabled(True)
        
    def terminate(self):
        """Terminates the controller and the processor
        """
        self._plt_timer.stop()
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

def generate_dummy_spectrometer_controller(parent:qw.QWidget, processor:mpp.Pool,
    dataHub:Wdg_DataHub_Mapping|None=None) -> Wdg_SpectrometerController:
    """
    Generates a dummy spectrometer controller for testing purposes.

    Args:
        parent (qw.QWidget): The parent widget for the controller.
        processor (mpp.Pool): The multiprocessing pool for data processing.
    """
    base_manager = get_my_manager()
    initialise_manager_raman(base_manager)
    base_manager.start()
    RamanController_proxy, dict_MeaRaman_proxy = initialise_proxy_raman(base_manager)
    RamanHub = DataStreamer_Raman(RamanController_proxy,dict_MeaRaman_proxy)
    RamanHub.start()

    wdg_Raman = Wdg_SpectrometerController(
        parent=parent,
        processor=processor,
        controller=RamanController_proxy,
        ramanHub=RamanHub,
        dataHub=dataHub,
    )
    return wdg_Raman
    

if __name__ == '__main__':
    # base_manager = get_my_manager()
    # initialise_manager_raman(base_manager)
    # base_manager.start()
    # RamanController_proxy, dict_MeaRaman_proxy = initialise_proxy_raman(base_manager)
    # RamanHub = DataStreamer_Raman(RamanController_proxy,dict_MeaRaman_proxy)
    # RamanHub.start()
    
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
    raman_frame = generate_dummy_spectrometer_controller(
        parent=central_widget,
        processor=processor,
        dataHub=None,
    )
    layout.addWidget(raman_frame)
    main_window.show()
    
    app.exec()
    raman_frame.terminate()