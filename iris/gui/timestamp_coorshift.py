"""
A class that handles the coordinate shift of the measurements stored in a mapping measurement unit, calculated using the
timestamps already stored in the measurement unit and the user-provided timestamp shift.
"""
import os
import sys

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\library')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox,filedialog

from typing import Callable

import pandas as pd
from scipy.optimize import curve_fit
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
matplotlib.use('Agg')   # Force matplotlib to use the backend to prevent memory leak

from iris.utils.general import *

from iris.data.measurement_RamanMap import MeaRMap_Hub, MeaRMap_Unit
from iris.data.measurement_Raman import MeaRaman, MeaRaman_Plotter

from iris.gui.dataHub_MeaRMap import Frm_DataHub_Mapping
from iris.gui.submodules.heatmap_plotter_MeaRMap import Frm_MappingMeasurement_Plotter

from iris.gui import AppPlotEnum

class sFrm_xyCoorTimestampShift(tk.Frame):
    def __init__(self, parent: tk.Frame, dataHub:Frm_DataHub_Mapping, callback:Callable|None=None):
        super().__init__(parent)
        self._dataHub = dataHub
        self._callback = callback
        
        # > Top level frames <
        self._frm_heatmap_plotter = Frm_MappingMeasurement_Plotter(
            master=self,
            mappingHub=self._dataHub.get_MappingHub(),
            figsize_pxl=AppPlotEnum.PLT_MAP_SIZE_PIXEL.value
        )
        self._frm_controls = tk.Frame(self)
        
        self._frm_heatmap_plotter.grid(row=0, column=0, sticky='nsew')
        self._frm_controls.grid(row=1, column=0, sticky='nsew')
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)
        
        # > Controls frame <
        self._combo_sourceUnitName = ttk.Combobox(self._frm_controls, state='readonly')
        
        self._lbl_tsShift_ms = tk.Label(self._frm_controls, text='Timestamp shift [ms]:')
        self._ent_tsShift_ms = tk.Entry(self._frm_controls)
        self._ent_tsShift_ms.insert(0, '0')
        self._btn_setShift_ms = tk.Button(self._frm_controls, text='Set shift', command=self._apply_timestamp_shift)
        
        self._combo_sourceUnitName.grid(row=0, column=0, columnspan=3, sticky='w')
        
        self._lbl_tsShift_ms.grid(row=1, column=0, sticky='e')
        self._ent_tsShift_ms.grid(row=1, column=1, sticky='w')
        self._btn_setShift_ms.grid(row=1, column=2, sticky='w')
        
        self._frm_controls.grid_columnconfigure(0, weight=0)
        self._frm_controls.grid_columnconfigure(1, weight=1)
        self._frm_controls.grid_columnconfigure(2, weight=0)
        self._frm_controls.grid_rowconfigure(0, weight=0)
        self._frm_controls.grid_rowconfigure(1, weight=0)
        
        self._ent_tsShift_ms.bind('<Return>', lambda event: self._apply_timestamp_shift())
        
        # > Variables <
        self._dict_nameToID = None
        
        # > Threads <
        self._thread_update = threading.Thread(target=self._auto_update)
        self._thread_update.start()
        
    def _auto_update(self):
        while True:
            self._dict_nameToID = self._dataHub.get_MappingHub().get_dict_nameToID()
            list_unitNames = list(self._dict_nameToID.keys())
            self._combo_sourceUnitName.configure(values=list_unitNames)
            
            time.sleep(0.5)
    
    @thread_assign
    def _apply_timestamp_shift(self):
        """
        Apply the timestamp shift to the unit. Based on the user input, the timestamp shift is applied to the unit.
        """
        try:
            # Disable the button to prevent multiple clicks
            self._btn_setShift_ms.configure(state='disabled')
            self._ent_tsShift_ms.configure(state='disabled')
            
            # Get the unit and its info
            hub = self._dataHub.get_MappingHub()
            unit_name = self._combo_sourceUnitName.get()
            unit_id = self._dict_nameToID[unit_name]
            
            # Apply the shift
            shifted_unitname = hub.shift_xycoordinate_timestamp(
                unit_id=unit_id,
                timeshift_us=int(float(self._ent_tsShift_ms.get())*1e3)
            )
            
            # Update the plotter
            self._frm_heatmap_plotter.refresh_plotter()
            
            self._frm_heatmap_plotter.set_combobox_values(mappingUnit_name=shifted_unitname)
            
            if self._callback is not None:
                self._callback()
            
        except Exception as e:
            messagebox.showerror('Error', f"Error: {e}")
            return
        
        finally:
            self._btn_setShift_ms.configure(state='normal')
            self._ent_tsShift_ms.configure(state='normal')