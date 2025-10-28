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
    sys.path.append(os.path.dirname(SCRIPT_DIR))
    sys.path.append(os.path.dirname(EXT_DIR))

import tkinter as tk
from tkinter import messagebox

import threading
import queue
import time

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

from extensions.extension_template import Extension_TopLevel
from extensions.extension_intermediary import Ext_DataIntermediary as Intermediary

from iris.controllers.class_spectrometer_controller import Class_SpectrometerController as Spectrometer
from iris.gui.raman import Frm_RamanSpectrometerController as Frm_Raman
from iris.data.measurement_Raman import MeaRaman
from iris import DataAnalysisConfigEnum as DAEnum

from iris.utils.general import *

class Ext_OpticsCalibrationAid(Extension_TopLevel):
    def __init__(self,master, intermediary: Intermediary) -> None:
        super().__init__(master, intermediary)
        self.title("Optics Calibration Aid")
        self._spectrometer = Spectrometer()
        self._frm_raman:Frm_Raman = self._intermediary.get_raman_controller_gui()
        
    # > Frames for the plot and the controls
        self._frm_plot = tk.Frame(self)
        self._frm_controls = tk.Frame(self)
        
        self._frm_plot.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._frm_controls.pack(side=tk.BOTTOM, fill=tk.X, expand=True)
        
    # > Initialise the plot
        self._fig, self._ax = plt.subplots()
        self._canvas = FigureCanvasTkAgg(self._fig, master=self._frm_plot)
        self._canvas_widget = self._canvas.get_tk_widget()
        
        self._canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._update_plot()
        
    # > Control widgets
        # Button to start the measurements
        self._btn_start = tk.Button(self._frm_controls, text="Start", command=self.start_measurements)
        self._btn_stop = tk.Button(self._frm_controls, text="Stop", command=self.stop_measurements, state='disabled')
        self._btn_restart = tk.Button(self._frm_controls, text="Restart", command=self.restart_measurements, state='disabled')
        
        self._entry_scan_number = tk.Entry(self._frm_controls, width=10)
        self._bool_plot_max = tk.BooleanVar()
        self._chk_keep_max = tk.Checkbutton(self._frm_controls, text="Keep maximum", variable=self._bool_plot_max)
        self._chk_keep_max.select()
        self._bool_0ymin = tk.BooleanVar()
        self._chk_0ymin = tk.Checkbutton(self._frm_controls, text="y-min limit = 0", variable=self._bool_0ymin)
        self._chk_0ymin.select()
        self._bool_plot_OneRaman = tk.BooleanVar()
        self._chk_plot_specific_RamanNumber = tk.Checkbutton(self._frm_controls, text="Plot specific Raman number", variable=self._bool_plot_OneRaman)
        self._lbl_Raman_number = tk.Label(self._frm_controls, text="Raman number:")
        self._entry_Raman_number = tk.Entry(self._frm_controls, width=10)
        
        self._bool_always_on_top = tk.BooleanVar()
        self._chk_always_on_top = tk.Checkbutton(self._frm_controls, text="Always on top", variable=self._bool_always_on_top)
        self._chk_always_on_top.config(command=lambda: self.wm_attributes("-topmost", self._bool_always_on_top.get()))
        self._chk_always_on_top.select()
        self.wm_attributes("-topmost", self._bool_always_on_top.get())
        
        col=0
        self._btn_start.grid(row=0, column=col, padx=5, pady=5); col+=1
        self._btn_stop.grid(row=0, column=col, padx=5, pady=5); col+=1
        self._btn_restart.grid(row=0, column=col, padx=5, pady=5); col+=1
        self._entry_scan_number.grid(row=0, column=col, padx=5, pady=5); col+=1
        self._chk_keep_max.grid(row=0, column=col, padx=5, pady=5); col+=1
        self._chk_0ymin.grid(row=0, column=col, padx=5, pady=5); col+=1
        colmax = col
        
        col=0
        self._chk_plot_specific_RamanNumber.grid(row=1, column=col, padx=5, pady=5); col+=1
        self._lbl_Raman_number.grid(row=1, column=col, padx=5, pady=5); col+=1
        self._entry_Raman_number.grid(row=1, column=col, padx=5, pady=5); col+=1
        colmax = max(col, colmax)
        
        self._chk_always_on_top.grid(row=2, column=0, padx=5, pady=5, columnspan=colmax, sticky='w');
        
        # Control parameters
        self._flg_isrunning = threading.Event()
        self._thread_measurement:threading.Thread = None
        
    # > Other parameters
        self._default_max_scan:int = 100
        self._entry_scan_number.insert(0, str(self._default_max_scan))
        
    def withdraw(self):
        self._stop_measurements()
        return super().withdraw()
        
    def _update_plot(self, list_measurements:list[float]|None=None, max_auc:float|None=None) -> None:
        """
        Set the plot with the new data.
        
        Args:
            list_measurements (list[float]|None): The list of area under the curve (AUC) values to plot. If None, the plot will be cleared.
            max_auc (float|None): The maximum value to add to the end of the plot. If None, nothing will be added.
        """
        if list_measurements is None:
            self._ax.clear()
            self._ax.set_title("Spectrometer area under the curve over time")
            self._ax.set_xlabel("Scan number [a.u.]")
            self._ax.set_ylabel("Area under the curve [a.u.]")
            self._canvas.draw()
            return
        
        flg_plotOneRaman = self._bool_plot_OneRaman.get()
        if flg_plotOneRaman:
            title = f"Spectrometer area under the curve over time (Raman number {self._entry_Raman_number.get()})"
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
            
        if self._bool_plot_max.get() and max_auc is not None:
            self._ax.scatter([len(list_measurements)], [max_auc], color='red', marker='o', label=f"Max {max_auc:.2f}")
            # Annotate the maximum value from the bottom left
            self._ax.annotate(f"Max {max_auc:.2f}", xy=(len(list_measurements), max_auc), xytext=(len(list_measurements)+1, max_auc+0.1),
                              arrowprops=dict(facecolor='black', arrowstyle='->'), fontsize=8, color='black')
            # set the legend on the bottom center of the plot
            self._ax.legend(loc='lower center')
            
        if self._bool_0ymin.get():
            self._ax.set_ylim(bottom=0)
            
        try: self._canvas.draw()
        except Exception as e: print(f"Error while drawing the canvas: {e}")
        
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
        
        maxlen:int
        try: maxlen = int(self._entry_scan_number.get())
        except: maxlen = self._default_max_scan
        
        if maxlen < 1: maxlen = self._default_max_scan
        
        while len(list_mea) > maxlen: list_mea.pop(0)
        
        flg_plotOneRaman = self._bool_plot_OneRaman.get()
        
        if flg_plotOneRaman:
            try:
                wavelength=convert_ramanshift_to_wavelength(float(self._entry_Raman_number.get()),list_mea[0].get_laser_params()[1])
                wv_idx = list_mea[0].get_wavelength_index(wavelength=wavelength)
                wavelength = list_mea[0].get_raw_list()[0][DAEnum.WAVELENGTH_LABEL.value][wv_idx]
            except:
                messagebox.showerror("Error", "Invalid Raman number. Please enter a valid Raman number.")
                self._entry_Raman_number.delete(0, tk.END)
                self._entry_Raman_number.insert(0, str(0))
                wv_idx = 0
        
        list_y = []
        for mea in list_mea:
            df:pd.DataFrame = mea.get_raw_list()[0]
            list_int = df[DAEnum.INTENSITY_LABEL.value].tolist()
            if flg_plotOneRaman:
                y = df[DAEnum.INTENSITY_LABEL.value][wv_idx]
            else: y = sum(list_int)
            list_y.append(y)
        
        max_y = max(list_y)
        max_y = max(max_y, prev_max_y)
        
        return list_y, max_y
    
    def start_measurements(self) -> None:
        """
        Start the measurements.
        """
        self._thread_measurement = self._start_measurements()
        
    def stop_measurements(self) -> None:
        """
        Stop the measurements.
        """
        self._thread_stop = self._stop_measurements()
    
    @thread_assign
    def restart_measurements(self) -> threading.Thread:
        """
        Restart the measurements.
        """
        self.stop_measurements()
        self._thread_stop.join()
        
        self.start_measurements()
        
    @thread_assign
    def _start_measurements(self) -> threading.Thread:
        """
        Start the measurements.
        """
        list_mea = []
        queue_mea = queue.Queue()
        self._frm_raman.perform_continuous_single_measurements(
            queue_mea=queue_mea,
        )
        
        self._btn_start.config(state='disabled')
        self._btn_stop.config(state='normal')
        self._btn_restart.config(state='normal')
        self._chk_plot_specific_RamanNumber.config(state='disabled')
        
        max_y = 0
        self._flg_isrunning.set()
        while self._flg_isrunning.is_set():
            try:
                mea = queue_mea.get_nowait()
                list_mea.append(mea)
                list_y, max_y = self._process_listMea(list_mea, max_y)
                self._update_plot(list_y, max_y)
            except queue.Empty: time.sleep(10e-3)   # Sleep for 10ms to avoid busy waiting
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")
                self._flg_isrunning.clear()
                break
            
        self._stop_measurements()
        
    @thread_assign
    def _stop_measurements(self) -> threading.Thread:
        """
        Stop the measurements.
        """
        self._flg_isrunning.clear()
        self._frm_raman.force_stop_measurement()
        
        if self._thread_measurement is not None: self._thread_measurement.join()
        
        self._btn_start.config(state='normal')
        self._btn_stop.config(state='disabled')
        self._btn_restart.config(state='disabled')
        self._chk_plot_specific_RamanNumber.config(state='normal')