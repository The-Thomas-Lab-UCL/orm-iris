"""
A class that handles the calibration of RamanMeasurement objects to be used in the main_analyser.py
Calibrations handled: wavelength calibration, intensity calibration
"""
import os
import sys

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\library')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox,filedialog

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

from iris.gui.dataHub_MeaRMap import Frm_DataHub_Mapping, Frm_DataHub_Mapping_Plus
from iris.gui.submodules.peakfinder_plotter_MeaRaman import Frm_RamanMeasurement_Plotter

class sFrm_wavelength_calibration(tk.Frame):
    def __init__(self, parent:tk.Frame, dataHub:Frm_DataHub_Mapping):
        super().__init__(parent)
        self._showInfo = False

    # >> Calibration parameters setup <<
        self._mea_RM:MeaRaman = None    # The selected RamanMeasurement for the calibration
        self._transfer_func_coeff:tuple[float,float,float,float] = None

    # >> Frame setup <<
        frm_RMselection = tk.Frame(self)    # For the dataHub_Plus treeview
        frm_peakfinding = tk.LabelFrame(self, text='Peak finding')    # For the peak finding plot, options
        frm_calibration = tk.LabelFrame(self, text='Calibration')    # For the calibration setting, plot, 
                                            ## and result display (of the transfer function)
        
        frm_RMselection.grid(row=0, column=0, sticky='nsew', columnspan=2)
        frm_peakfinding.grid(row=1, column=0, sticky='nsew')
        frm_calibration.grid(row=1, column=1, sticky='nsew')
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
    # >> DataHub_Plus setup <<
        # Set up the dataHubPlus to be used for the calibration data source
        # and reference selections and link the dataHub from which the data are taken
        self._dataHub = Frm_DataHub_Mapping(frm_RMselection,width_rel=0.7,height_rel=0.4)
        self._dataHub.set_MappingHub(dataHub.get_MappingHub())
        self._dataHub_Plus = Frm_DataHub_Mapping_Plus(frm_RMselection, self._dataHub,
            width_rel=0.7, height_rel=0.4)    # dataHubPlus for the representation measurement selection
        
        self._dataHub.grid(row=0, column=0, sticky='nsew')
        self._dataHub_Plus.grid(row=0, column=1, sticky='nsew')
        
        # Bind the RamanMeasurement selection event to the peak finding plotter
        self._dataHub_Plus.set_RMSelection_interactive(callback=self._RMselection_callback)
        
    # >> Peak finding setup <<
        # Widget setup
        self._frm_peakfinding = Frm_RamanMeasurement_Plotter(frm_peakfinding,tree_columnWidth=300,height=300)

        # Pack the widgets
        self._frm_peakfinding.grid(row=0, column=0,columnspan=2)

    # >> Calibration setup <<
    # > Calibration Raman shift peaks selection (of the representative and reference measurements) <
        # Treeview to show the peaks found vs the reference peaks
        self._tree_peaks = ttk.Treeview(frm_calibration, columns=('sample','reference'),
                                        height=5, show='headings')
        self._tree_peaks.heading('sample', text='Sample peaks [nm]')
        self._tree_peaks.heading('reference', text='Reference peaks [nm]')
        self._tree_peaks.column('sample', width=100, anchor='w')
        self._tree_peaks.column('reference', width=100, anchor='w')
        
        btn_load_reference = tk.Button(frm_calibration, text='Load reference Raman shift', command=self._load_reference_Ramanshift)
        btn_remove_entry = tk.Button(frm_calibration, text='Remove selected peak', command=self._remove_selected_peak)

    # > Calibration setup and result display <
        # Parameters setup
        figsize_pixel = (300,300)
        dpi = matplotlib.rcParams['figure.dpi']
        self._figsize_inch = (int(figsize_pixel[0]/dpi),int(figsize_pixel[1]/dpi))
        
        # Widgets setup
        self._fig,self._ax = plt.subplots(1,1,figsize=self._figsize_inch)
        self._fig_canvas = FigureCanvasTkAgg(self._fig,master=frm_calibration)
        self._fig_canvas.draw()
        self._canvas_transferfunc_widget = self._fig_canvas.get_tk_widget()
        btn_calibrate = tk.Button(frm_calibration, text='Generate transfer function', command=self._generate_transfer_function)

        # Pack the widgets
        self._tree_peaks.grid(row=0, column=0, sticky='nsew', columnspan=2)
        btn_load_reference.grid(row=1, column=0, sticky='ew')
        btn_remove_entry.grid(row=1, column=1, sticky='ew')
        
        btn_calibrate.grid(row=2, column=0, sticky='ew', columnspan=2)
        self._canvas_transferfunc_widget.grid(row=3, column=0, sticky='nsew',columnspan=2)

        frm_calibration.grid_rowconfigure(0, weight=1)
        frm_calibration.grid_columnconfigure(0, weight=1)

    # >> Calibration transfer function application to an entire MappingUnit RamanMeasurements <<
        pass
        
    @thread_assign
    def _RMselection_callback(self):
        """
        Callback for the RamanMeasurement selection event
        """
        # Get the selected RamanMeasurement
        list_RM_selected = self._dataHub_Plus.get_selected_RamanMeasurement()
        
        if len(list_RM_selected) == 0: return
        self._mea_RM = list_RM_selected[0]
        
        # Extract the laser parameters
        laser_wavelength = self._mea_RM.get_laser_params()[1]
        
        # Update the peak finding plotter
        list_peakwavelengths,_ = self._frm_peakfinding.plot_spectra(self._mea_RM)

        # Sort the peaks by wavelength
        list_peakwavelengths = sorted(list_peakwavelengths)
        list_peakRS = [convert_wavelength_to_ramanshift(wavelength,laser_wavelength) for wavelength in list_peakwavelengths]

        # Update the treeview
        self._update_tree_peaks(list_peaksRS_rep=list_peakRS)

    def _update_tree_peaks(self,list_peaksRS_rep:list[float]|None=None,
                           list_peaksRS_ref:list[float]|None=None):
        """
        Updates the treeview of the peaks found
        
        Args:
            list_peaksRS_rep (list[float]): List of the Raman shift peaks of the sample representative
            list_peaksRS_ref (list[float]): List of the Raman shift peaks of the reference
        
        Note:
            If the lists are None, the current values in the treeview will be used for the respective lists
        """
        # Get the list of current peak Raman shifts of the sample
        if list_peaksRS_rep is None:
            list_peakRS_mea = [float(self._tree_peaks.item(child)['values'][0]) for child in self._tree_peaks.get_children()]

        # Get the list of current peak Raman shifts of the reference
        if list_peaksRS_ref is None:
            list_peakRS_ref = [float(self._tree_peaks.item(child)['values'][1]) for child in self._tree_peaks.get_children()]

        if len(list_peakRS_mea) != len(list_peakRS_ref):
            length = max(len(list_peakRS_mea),len(list_peakRS_ref))
            for i in range(length-len(list_peakRS_mea)):
                list_peakRS_mea.append('')
            for i in range(length-len(list_peakRS_ref)):
                list_peakRS_ref.append('')

        # Update the treeview
        self._tree_peaks.delete(*self._tree_peaks.get_children())
        for i in range(len(list_peakRS_mea)):
            self._tree_peaks.insert('', 'end', values=(list_peakRS_mea[i],list_peakRS_ref[i]))

    def _load_reference_Ramanshift(self):
        """
        Loads the reference Raman shift
        """
        if self._showInfo: messagebox.showinfo('Info','Please load a .csv of the reference Raman shift. It has to have 1 columns with the list of Raman shift peaks of the reference.')

        path = filedialog.askopenfilename(title='Load reference Raman shift', filetypes=[('CSV files','*.csv')])
        if path == '': return

        # Load the reference Raman shift
        df = pd.read_csv(path)
        if len(df.columns) != 1: messagebox.showerror('Error','The reference Raman shift must have 1 column'); return
        if not pd.api.types.is_numeric_dtype(df.iloc[:,0]):
            messagebox.showerror('Error','The reference Raman shift must be numeric')
            return
        
        # Update the treeview
        self._update_tree_peaks(list_peaksRS_ref=df.iloc[:,0].tolist())

    def _remove_selected_peak(self):
        """
        Removes the selected peak from the treeview
        """
        selected = self._tree_peaks.selection()
        if len(selected) == 0: return
        self._tree_peaks.delete(selected)

    def _generate_transfer_function(self):
        """
        Generate the transfer function from the peaks found and the reference peaks
        """
        try:
            list_peakRS_mea = [float(self._tree_peaks.item(child)['values'][0]) for child in self._tree_peaks.get_children()]
            list_peakRS_ref = [float(self._tree_peaks.item(child)['values'][1]) for child in self._tree_peaks.get_children()]

            if len(list_peakRS_mea) != len(list_peakRS_ref):
                messagebox.showerror('Error','The number of peaks in the sample and reference must be the same')
                return
            
            # Generate the transfer function
            result = self._calculate_transfer_func_cubic(list_peakRS_mea,list_peakRS_ref)
            if len(result) != 4 or not all([pd.api.types.is_numeric_dtype(i) for i in result]):
                messagebox.showerror('Error','The transfer function could not be generated')
                return
            
            self._transfer_func_coeff = result

            # Plot the transfer function
            self._plot_transfer_func()
        except Exception as e: print('_calibrate:',e)

    def _plot_transfer_func(self,list_peakRS_mea:list[float],list_peakRS_ref:list[float]):
        """
        Plots the transfer function
        
        Args:
            list_peakRS_mea (list[float]): List of the Raman shift peaks of the sample representative
            list_peakRS_ref (list[float]): List of the Raman shift peaks of the reference
        """
        if self._transfer_func_coeff is None:
            messagebox.showerror('Error','The transfer function has not been generated yet')
            return

        mea = self._mea_RM
        if not isinstance(mea,MeaRaman): return

        # Generate the x and y values from the transfer function
        x_min = min(mea.get_measurements()[-1][mea.label_wavelength])
        x_max = max(mea.get_measurements()[-1][mea.label_wavelength])
        x = np.linspace(x_min,x_max,100)
        y = np.polyval(self._transfer_func_coeff,x)

        # Generate the plot
        fig,ax = self._fig, self._ax
        ax.cla()
        ax.plot(x,y,c='b',label='Transfer function')
        ax.scatter(list_peakRS_mea,list_peakRS_ref,c='r',label='Peaks')
        ax.set_xlabel('Measurement Raman shift peaks[cm-1]')
        ax.set_ylabel('Reference Raman shift peaks[cm-1]')
        ax.set_title('Wavenumber calibration transfer function')
        ax.legend()

        # Update the canvas
        self._fig_canvas.draw()


    def _calculate_transfer_func_cubic(self,list_peakRS_mea:list[float],list_peakRS_ref:list[float]) -> tuple[float,float,float,float]:
        """
        Generates the transfer function from the peaks found and the reference peaks
        
        Args:
            list_peakRS_mea (list[float]): List of the Raman shift peaks of the sample representative
            list_peakRS_ref (list[float]): List of the Raman shift peaks of the reference
        
        Returns:
            tuple[float,float,float,float]: The coefficients of the transfer function (a,b,c,d) for the cubic function of a*x**3 + b*x**2 + c*x + d
        """
        def cubic(x,a,b,c,d):
            return a*x**3 + b*x**2 + c*x + d
        
        # Fit the transfer function
        popt,_ = curve_fit(cubic,xdata=list_peakRS_mea,ydata=list_peakRS_ref)
        return popt

if __name__ == '__main__':
    pass