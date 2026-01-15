"""
The Spectrometer Calibration Aid is an extension to assist in the calibration of spectrometers.
It will:
    - Trigger continuous measurements and plot the area under the curve (AUC) of the spectrum in real-time.
    - Plot the AUC of the spectrum in real-time to help see the signal received by the spectrometer.
"""
import sys
import os

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'..\library')
    EXT_DIR = os.path.abspath(r'..\extensions')
    sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
    sys.path.insert(0, os.path.dirname(EXT_DIR))

from PySide6.QtGui import QCloseEvent
import PySide6.QtWidgets as qw
from PySide6.QtCore import Qt # For context
from PySide6.QtCore import Signal, Slot, QTimer, QObject

import threading
import queue
import time

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import pandas as pd

from extensions.extension_template import Extension_MainWindow
from extensions.extension_intermediary import Ext_DataIntermediary as Intermediary

from iris.controllers.class_spectrometer_controller import Class_SpectrometerController as Spectrometer
from iris.gui.raman import Wdg_SpectrometerController as Frm_Raman
from iris.data.measurement_Raman import MeaRaman
from iris import DataAnalysisConfigEnum as DAEnum

from iris.utils.general import convert_ramanshift_to_wavelength
from extensions.optics_calibration_aid.optics_calibration_aid_ui import Ui_optics_calibration_aid

class OpticsCalibrationAid_Design(Ui_optics_calibration_aid, qw.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)

class OpticsCalibrationAid_Worker(QObject):
    
    sig_draw_plot = Signal()
    
    def __init__(self, ax:Axes):
        super().__init__()
        self._ax = ax
        
    @Slot(list,float,bool,bool,bool,float)
    def _update_plot(self, list_measurements:list[float], max_auc:float, plotOneRaman:bool, plotMax:bool,
                     plot0ymin:bool, RamanWavenumber:float) -> None:
        """
        Set the plot with the new data.
        
        Args:
            list_measurements (list[float]): The list of area under the curve (AUC) values to plot.
            max_auc (float): The maximum value to add to the end of the plot.
            plotOneRaman (bool): Whether to plot a specific Raman number.
            plotMax (bool): Whether to plot the maximum value.
            plot0ymin (bool): Whether to set the y-min limit to 0.
            RamanWavenumber (float): The Raman wavenumber to plot if plotOneRaman is True.
        """
        flg_plotOneRaman = plotOneRaman
        if flg_plotOneRaman:
            title = f"Spectrometer area under the curve over time (Raman number {RamanWavenumber})"
            ylabel = "Intensity [a.u.]"
        else:
            title = "Spectrometer area under the curve over time"
            ylabel = "Area under the curve [a.u.]"
        
        self._ax.clear()
        self._ax.set_title(title)
        self._ax.set_xlabel("Scan number [a.u.]")
        self._ax.set_ylabel(ylabel)
        
        self._ax.plot(list_measurements, color='blue')
        self._ax.scatter([i for i in range(len(list_measurements))], list_measurements, color='red', marker='x')
            
        if plotMax:
            self._ax.scatter([len(list_measurements)], [max_auc], color='red', marker='o', label=f"Max {max_auc:.2f}")
            # Annotate the maximum value from the bottom left
            self._ax.annotate(f"Max {max_auc:.2f}", xy=(len(list_measurements), max_auc), xytext=(len(list_measurements)+1, max_auc+0.1),
                              arrowprops=dict(facecolor='black', arrowstyle='->'), fontsize=8, color='black')
            # set the legend on the bottom center of the plot
            self._ax.legend(loc='lower center')
            
        if plot0ymin:
            self._ax.set_ylim(bottom=0)
            
        self.sig_draw_plot.emit()

class Ext_OpticsCalibrationAid(Extension_MainWindow):
    sig_update_plot = Signal(list,float)
    
    _sig_append_queue = Signal(queue.Queue, threading.Event)
    _sig_remove_queue = Signal(queue.Queue)
    _sig_perform_continuous_measurement = Signal()
    
    def __init__(self,master, intermediary: Intermediary) -> None:
        super().__init__(master, intermediary)
        self.setWindowTitle("Optics Calibration Aid")
        self._spectrometer = Spectrometer()
        self._frm_raman:Frm_Raman = self._intermediary.get_raman_controller_gui()
        
    # > Frames for the plot and the controls
        self._wdg = OpticsCalibrationAid_Design(self)
        self.setCentralWidget(self._wdg)
        wdg = self._wdg
        
    # > Initialise the plot
        self._fig, self._ax = plt.subplots()
        self._canvas = FigureCanvas(figure=self._fig)
        self._wdg.lyt_plot.addWidget(self._canvas)
        self._canvas.draw_idle()
        self._init_plot()
        
    # > Control widgets
        # Button to start the measurements
        wdg.btn_start.clicked.connect(self._start_measurements)
        wdg.btn_stop.clicked.connect(self._stop_measurements)
        wdg.btn_restart.clicked.connect(self.restart_measurements)
        wdg.chk_alwaysOnTop.stateChanged.connect(self._toggle_always_on_top)
        
        # Make sure that the current window is always on top
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True) # pyright: ignore[reportAttributeAccessIssue] ; WindowStaysOnTopHint exists
        
    # > Measurement parameters <
        self._flg_isrunning = threading.Event()
        self._mea_worker = self._frm_raman.get_mea_worker()
        self._sig_append_queue.connect(self._mea_worker.append_queue_observer_measurement)
        self._sig_remove_queue.connect(self._mea_worker.remove_queue_observer_measurement)
        self._sig_perform_continuous_measurement.connect(self._frm_raman.perform_continuous_measurement)
        self.sig_update_plot.connect(self._update_plot)
        self._queue_mea:queue.Queue = queue.Queue()
        self._list_mea = []
        
    def closeEvent(self, event: QCloseEvent) -> None:
        self._stop_measurements()
        return super().closeEvent(event)
        
    @Slot()
    def _toggle_always_on_top(self) -> None:
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self._wdg.chk_alwaysOnTop.isChecked()) # pyright: ignore[reportAttributeAccessIssue] ; WindowStaysOnTopHint exists
        self.show()
        
    def _init_plot(self) -> None:
        """
        Initialise the plot.
        """
        self._ax.clear()
        self._ax.set_title("Spectrometer area under the curve over time")
        self._ax.set_xlabel("Scan number [a.u.]")
        self._ax.set_ylabel("Area under the curve [a.u.]")
        self._canvas.draw_idle()
        
    @Slot(list,float)
    def _update_plot(self, list_measurements:list[float], max_auc:float) -> None:
        """
        Set the plot with the new data.
        
        Args:
            list_measurements (list[float]): The list of area under the curve (AUC) values to plot.
            max_auc (float): The maximum value to add to the end of the plot.
        """
        flg_plotOneRaman = self._wdg.rad_plotOneWavenumber.isChecked()
        if flg_plotOneRaman:
            wavenumber = self._wdg.spin_RamanWavenumber.value()
            title = f"Spectrometer area under the curve over time (Raman number {wavenumber})"
            ylabel = "Intensity [a.u.]"
        else:
            title = "Spectrometer area under the curve over time"
            ylabel = "Area under the curve [a.u.]"
        
        self._ax.clear()
        self._ax.set_title(title)
        self._ax.set_xlabel("Scan number [a.u.]")
        self._ax.set_ylabel(ylabel)
        
        self._ax.plot(list_measurements, color='blue')
        self._ax.scatter([i for i in range(len(list_measurements))], list_measurements, color='red', marker='x')
            
        if self._wdg.chk_storeMax.isChecked():
            self._ax.scatter([len(list_measurements)], [max_auc], color='red', marker='o', label=f"Max {max_auc:.2f}")
            # Annotate the maximum value from the bottom left
            self._ax.annotate(f"Max {max_auc:.2f}", xy=(len(list_measurements), max_auc), xytext=(len(list_measurements)+1, max_auc+0.1),
                              arrowprops=dict(facecolor='black', arrowstyle='->'), fontsize=8, color='black')
            # set the legend on the bottom center of the plot
            self._ax.legend(loc='lower center')
            
        if self._wdg.chk_ymin0.isChecked():
            self._ax.set_ylim(bottom=0)
            
        self._canvas.draw_idle()
        
    def _process_listMea(self, list_mea:list[MeaRaman], prev_max_y:float = 0) -> tuple[list[float], float]:
        """
        Process the list of measurements and update the plot.
        
        Args:
            list_mea (list[RamanMeasurement]): The list of measurements to process.
            prev_max_y (float): The previous maximum value to compare with.
            
        Returns:
            tuple[list[float], float]: The list of AUC values and the maximum value.
        """
        assert isinstance(list_mea, list), "list_mea must be a list of RamanMeasurement objects."
        assert all(isinstance(mea, MeaRaman) for mea in list_mea), "list_mea must be a list of RamanMeasurement objects."
        assert len(list_mea) > 0, "list_mea must not be empty."
        
        maxlen = self._wdg.spin_numTrack.value()
        
        while len(list_mea) > maxlen: list_mea.pop(0)
        
        flg_plotOneRaman = self._wdg.rad_plotOneWavenumber.isChecked()
        
        if flg_plotOneRaman:
            try:
                ramanshift = self._wdg.spin_RamanWavenumber.value()
                wavelength=convert_ramanshift_to_wavelength(ramanshift,list_mea[0].get_laser_params()[1])
                wv_idx = list_mea[0].get_wavelength_index(wavelength=wavelength) # pyright: ignore[reportArgumentType] ; Will always be float
                wavelength = list_mea[0].get_raw_list()[0][DAEnum.WAVELENGTH_LABEL.value][wv_idx]
            except:
                qw.QMessageBox.warning(self,'Error','Invalid Raman number. Please enter a valid Raman number.')
                wv_idx = 0
        
        list_y = []
        for mea in list_mea:
            df:pd.DataFrame = mea.get_raw_list()[0]
            list_int = df[DAEnum.INTENSITY_LABEL.value].tolist()
            if flg_plotOneRaman:
                y = df[DAEnum.INTENSITY_LABEL.value][wv_idx] # type: ignore ; wv_idx will always be valid
            else: y = sum(list_int)
            list_y.append(y)
        
        max_y = max(list_y)
        max_y = max(max_y, prev_max_y)
        
        return list_y, max_y
    
    def restart_measurements(self) -> None:
        """
        Restart the measurements.
        """
        self._stop_measurements()
        self._start_measurements()
        
    @Slot()
    def _start_measurements(self) -> None:
        """
        Start the measurements.
        """
        self._init_measurements()
        
        max_y = 0
        self._flg_isrunning.set()
        self._sig_perform_continuous_measurement.emit()
        self._perform_measurement(max_y)

    def _perform_measurement(self, max_y):
        try:
            mea = self._queue_mea.get_nowait()
            self._list_mea.append(mea)
            list_y, max_y = self._process_listMea(self._list_mea, max_y)
            self.sig_update_plot.emit(list_y, max_y)
        except queue.Empty: time.sleep(10e-3)   # Sleep for 10ms to avoid busy waiting
        except Exception as e:
            qw.QMessageBox.critical(self, "Error", f"An error occurred: {e}")
            self._stop_measurements()
            return
        
        if self._flg_isrunning.is_set():
            QTimer.singleShot(10, lambda: self._perform_measurement(max_y))

    def _init_measurements(self):
        # Clear previous measurements
        self._list_mea.clear()
        while not self._queue_mea.empty():
            try: self._queue_mea.get_nowait()
            except queue.Empty: break
            
        # Add the queue observer to the measurement worker
        ev_done = threading.Event()
        self._mea_worker.append_queue_observer_measurement(self._queue_mea, ev_done)
        ev_done.wait()
        
        # Update the buttons
        self._wdg.btn_start.setEnabled(False)
        self._wdg.btn_stop.setEnabled(True)
        self._wdg.btn_restart.setEnabled(True)
        self._wdg.rad_plotOneWavenumber.setEnabled(False)
        self._wdg.rad_plotAUC.setEnabled(False)
        
    @Slot()
    def _stop_measurements(self) -> None:
        """
        Stop the measurements.
        """
        self._flg_isrunning.clear()
        self._frm_raman.sig_request_mea_stop.emit()
        self._mea_worker.remove_queue_observer_measurement(self._queue_mea)
        
        self._wdg.btn_start.setEnabled(True)
        self._wdg.btn_stop.setEnabled(False)
        self._wdg.btn_restart.setEnabled(False)
        self._wdg.rad_plotOneWavenumber.setEnabled(True)
        self._wdg.rad_plotAUC.setEnabled(True)