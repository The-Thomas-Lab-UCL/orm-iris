"""
A class to control the plot for SERS mapping measurements. To be used inside the high level controller module.
"""
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox

import matplotlib.backend_bases
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.axes
import matplotlib.colorbar
import matplotlib.figure
matplotlib.use('Agg')   # Force matplotlib to use the backend to prevent memory leak

import time
import numpy as np
import numpy as np
import pandas as pd

import threading
import queue
from typing import Any, Callable, Literal

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))


from iris.utils.general import *
from iris.data.measurement_RamanMap import MeaRMap_Hub,MeaRMap_Unit, MeaRMap_Plotter

from iris.gui import AppPlotEnum
from iris import DataAnalysisConfigEnum as DAEnum

class Frm_MappingMeasurement_Plotter(tk.Frame):
    def __init__(self, master, mappingHub:MeaRMap_Hub,
                 callback_click:Callable[[tuple[str,tuple[float,float]]], None]|None=None,
                 figsize_pxl:tuple=(440,400)):
        """
        Initialise the plot_mapping_measurements class
        
        Args:
            master (tk.Tk): Parent widget
            mappingHub (MappingMeasurement_Hub): Mapping measurement hub to be used for plotting.
            callback_click (Callable[[tuple[str,tuple[float,float]]], None]|None): Callback function to be called on click events,
                it will call the function with the measurement ID and the coordinates of the click.
            figsize_pxl (tuple, optional): Size of the figure in pixels. Defaults to (440,400).
        """
        assert isinstance(mappingHub,MeaRMap_Hub),'mappingHub must be an instance of MappingMeasurement_Hub'
        assert callable(callback_click) or callback_click is None,'callback_click must be a callable or None'
        assert isinstance(figsize_pxl,tuple) and len(figsize_pxl)==2,'figsize_pxl must be a tuple of length 2'
        
        super().__init__(master)
        self._mappingHub:MeaRMap_Hub = mappingHub
        
    # >>> Frames setup <<<
        self._frm_plotter_setup = tk.Frame(self)
        self._frm_plot = tk.Frame(self)
        self._frm_plotControls = tk.Frame(self)
        self._frm_generalControls = tk.Frame(self)
        
        self._frm_plotter_setup.grid(row=0,column=0,sticky='nsew')
        self._frm_plot.grid(row=1,column=0,sticky='nsew')
        self._frm_plotControls.grid(row=2,column=0,sticky='nsew')
        self._frm_generalControls.grid(row=3,column=0,sticky='nsew')
        
    # >>> Store the parameters for re-initialisation <<<
        self._figsize_pxl = figsize_pxl
        self._dpi = plt.rcParams['figure.dpi']
        self._figsize_in = (self._figsize_pxl[0]/self._dpi,self._figsize_pxl[1]/self._dpi)
        
    # >>> Plot widgets and parameters set up <<<
    # > Parameters <
        self._flg_isplotting:threading.Event = threading.Event()
        self._flg_isplotting.clear()
        
        # Analysers for data analysis:
        self._mapping_Plotter = MeaRMap_Plotter(figsize_pxl=self._figsize_pxl)
        
        # Latest measurement data storage for plotting purposes only
        self._current_mappingUnit:MeaRMap_Unit = MeaRMap_Unit()
        self._current_mappingUnit.add_observer(self.replot_heatmap)
        
        # Set up a queue and threading to analyse the data for plotting
        self._callback_click:Callable|None = callback_click
        
    # >>> Plotter selection setup <<<
        self._init_plotter_options_widgets()
    
    # >>> Plotter setup <<<
        
    # > Matplotlib plot setup <
        self._bool_plot_in_RamanShift = tk.BooleanVar(value=True) # Boolean variable to plot Raman shift
        self._plt_fig, self._plt_ax = plt.subplots(1,1,figsize=self._figsize_in) # Figure object for the mapping plot
        
        self._plt_cbar = None  # Colorbar figure object for the mapping plot
        self._canvas_plot = FigureCanvasTkAgg(self._plt_fig,master=self._frm_plot) # Canvas for the plot
        self._canvas_widget = self._canvas_plot.get_tk_widget() # Shows plots depending on the operation mode
        self._canvas_id_interaction = self._plt_fig.canvas.mpl_connect('button_press_event', self._retrieve_click_idxcol) # The plot widget's canvas ID for interaction setups
        
        # Initialise the plot with a dummy plot
        self._plt_fig, self._plt_ax, self._plt_cbar = self._func_current_plotter(fig=self._plt_fig,ax=self._plt_ax,clrbar=self._plt_cbar)
        
        # Pack the plot widget
        row=0
        self._canvas_grid_loc = (row,0,1,4) # Grid location for the canvas widget (row,column,rowspan,columnspan)
        row,col,rowspan,colspan = self._canvas_grid_loc
        self._canvas_widget.grid(row=row,column=col,rowspan=rowspan,columnspan=colspan)
        
    # > Plot control widgets <
        # Subframes
        self._init_plot_control_widgets()
        
    # > General control widgets <
        # Set up the other widgets
        self._btn_restart_threads = tk.Button(self._frm_generalControls,text='Restart auto-updater',command=self._reinitialise_auto_plot)
        self._lbl_coordinates = tk.Label(self._frm_generalControls,text='Clicked:',anchor='w')
        
        # Bind selections to plot the latest measurement_data df
        self._combo_plot_mappingUnitName.bind("<<ComboboxSelected>>",func=lambda event:
            self._update_currentMappingUnit_observer(self._combo_plot_mappingUnitName.get(),replot=True))
        self._combo_plot_SpectralPosition.bind("<<ComboboxSelected>>",func=lambda event:
            self.replot_heatmap())
        self._combo_plot_SpectralPosition.bind("<Return>",func=lambda event:
            self._set_combobox_closest_value())
        
        row=0
        self._btn_restart_threads.grid(row=row,column=0,sticky='we')
        self._lbl_coordinates.grid(row=row,column=1,sticky='we')
        
        # Set the callbacks
        self._mappingHub.add_observer(lambda: self.refresh_comboboxes(
            preserve_unit_name=self._combo_plot_mappingUnitName.get(),
            preserve_wavelength=self.get_current_wavelength(),
        ))

    def _init_plot_control_widgets(self):
        """
        Initializes the widgets for the plot controls (save options, color limits, axis limits)
        """
        frm_plotControl_basic = tk.Frame(self._frm_plotControls)
        frm_plotControl_save = tk.Frame(self._frm_plotControls)
        frm_plotControl_clim = tk.Frame(self._frm_plotControls)
        frm_plotControl_xylim = tk.Frame(self._frm_plotControls)
        
        frm_plotControl_basic.grid(row=0,column=0,sticky='we')
        frm_plotControl_save.grid(row=1,column=0,sticky='we')
        frm_plotControl_clim.grid(row=2,column=0,sticky='we')
        frm_plotControl_xylim.grid(row=3,column=0,sticky='we')
        
        self._frm_plotControls.grid_columnconfigure(0,weight=1)
        self._frm_plotControls.grid_rowconfigure(0,weight=1)
        self._frm_plotControls.grid_rowconfigure(1,weight=1)
        self._frm_plotControls.grid_rowconfigure(2,weight=1)
        self._frm_plotControls.grid_rowconfigure(3,weight=1)
        
        # > Set up the basic widgets
        chk_RamanShiftCombobox = tk.Checkbutton(frm_plotControl_basic,text='Plot Raman-shift',
            variable=self._bool_plot_in_RamanShift,onvalue=True,offvalue=False,
            command=self._switch_plot_RamanShift)
        chk_RamanShiftCombobox.select()
        self._lbl_SpectralPosition = tk.Label(frm_plotControl_basic,text='cm^-1',width=7)
        
        # Set up the comboboxes
        self._combo_plot_mappingUnitName = ttk.Combobox(frm_plotControl_basic,width=25,state='readonly')
        self._combo_plot_SpectralPosition = ttk.Combobox(frm_plotControl_basic,width=10,state='active')
        
        row=0
        chk_RamanShiftCombobox.grid(row=row,column=0)
        self._combo_plot_mappingUnitName.grid(row=row,column=1)
        self._combo_plot_SpectralPosition.grid(row=row,column=2)
        self._lbl_SpectralPosition.grid(row=row,column=3)
        
        # > Set up the save widgets
        btn_save_plot = tk.Button(frm_plotControl_save,text='Save plot',command=self.save_plot)
        btn_save_plot_data = tk.Button(frm_plotControl_save,text='Save data',command=self.save_plot_data)
        
        btn_save_plot.grid(row=0,column=0,sticky='we')
        btn_save_plot_data.grid(row=0,column=1,sticky='we')
        
        frm_plotControl_save.grid_columnconfigure(0,weight=1)
        frm_plotControl_save.grid_columnconfigure(1,weight=1)
        
        # > Set up the colour bar limit widgets
        lbl_clim_min = tk.Label(frm_plotControl_clim,text='Colour bar limits min:',anchor='e')
        lbl_clim_max = tk.Label(frm_plotControl_clim,text='max:',anchor='e')
        self._entry_plot_clim_min = ttk.Entry(frm_plotControl_clim,width=15)
        self._entry_plot_clim_max = ttk.Entry(frm_plotControl_clim,width=15)
        self._bool_auto_clim = tk.BooleanVar(value=True)
        chk_auto_clim = tk.Checkbutton(frm_plotControl_clim,text='Auto',variable=self._bool_auto_clim,
                                       command=self.replot_heatmap)
        
        row=0
        lbl_clim_min.grid(row=row,column=0)
        self._entry_plot_clim_min.grid(row=row,column=1)
        lbl_clim_max.grid(row=row,column=2)
        self._entry_plot_clim_max.grid(row=row,column=3)
        chk_auto_clim.grid(row=row,column=4)
        
        # Bind enter key and changes to replot the heatmap
        def bind_enter_replot(): self.replot_heatmap(); self._bool_auto_clim.set(False)
        self._entry_plot_clim_min.bind("<Return>",func=lambda event: bind_enter_replot())
        self._entry_plot_clim_max.bind("<Return>",func=lambda event: bind_enter_replot())
        
        # > Set up the xy limit widgets
        lbl_xlim_min = tk.Label(frm_plotControl_xylim,text='x-min [mm]:',anchor='e')
        lbl_xlim_max = tk.Label(frm_plotControl_xylim,text='x-max [mm]:',anchor='e')
        lbl_ylim_min = tk.Label(frm_plotControl_xylim,text='y-min [mm]:',anchor='e')
        lbl_ylim_max = tk.Label(frm_plotControl_xylim,text='y-max [mm]:',anchor='e')
        self._entry_plot_xlim_min = ttk.Entry(frm_plotControl_xylim,width=15)
        self._entry_plot_xlim_max = ttk.Entry(frm_plotControl_xylim,width=15)
        self._entry_plot_ylim_min = ttk.Entry(frm_plotControl_xylim,width=15)
        self._entry_plot_ylim_max = ttk.Entry(frm_plotControl_xylim,width=15)
        
        self._entry_plot_xlim_min.bind("<Return>",func=lambda event: self.replot_heatmap())
        self._entry_plot_xlim_max.bind("<Return>",func=lambda event: self.replot_heatmap())
        self._entry_plot_ylim_min.bind("<Return>",func=lambda event: self.replot_heatmap())
        self._entry_plot_ylim_max.bind("<Return>",func=lambda event: self.replot_heatmap())
        
        lbl_xlim_min.grid(row=0,column=0)
        lbl_xlim_max.grid(row=0,column=2)
        lbl_ylim_min.grid(row=1,column=0)
        lbl_ylim_max.grid(row=1,column=2)
        self._entry_plot_xlim_min.grid(row=0,column=1)
        self._entry_plot_xlim_max.grid(row=0,column=3)
        self._entry_plot_ylim_min.grid(row=1,column=1)
        self._entry_plot_ylim_max.grid(row=1,column=3)
        
    def _init_plotter_options_widgets(self):
        """
        Initialize the plotter option widgets
        """
        self._func_current_plotter:Callable = self._mapping_Plotter.plot_typehinting
        self._dict_plotter_kwargs_widgets = {}  # Dictionary to store the plotter options
        self._dict_plotter_opts, self._dict_plotter_opts_kwargs = self._mapping_Plotter.get_plotter_options()
        self._combo_plotter = ttk.Combobox(self._frm_plotter_setup,width=25,state='readonly')
        self._combo_plotter.configure(values=list(self._dict_plotter_opts.keys()))
        self._combo_plotter.current(0)
        
        self._combo_plotter.grid(row=0,column=0,columnspan=2)
        self._combo_plotter.bind("<<ComboboxSelected>>",func=lambda event: self._setup_plotter_options())
        self._setup_plotter_options()

    def _setup_plotter_options(self):
        """
        Set up the plotter options for the current mapping plot
        """
        current_plotter = self._combo_plotter.get()
        self._func_current_plotter = self._dict_plotter_opts[current_plotter]
        kwargs = self._dict_plotter_opts_kwargs[current_plotter]
        
        # Destroy the previous widgets
        for widget in self._frm_plotter_setup.winfo_children():
            if widget != self._combo_plotter: widget.destroy()
        
        row_start = 1
        # Auto generate widgets for the plotter options
        self._dict_plotter_kwargs_widgets.clear()
        for i,key in enumerate(kwargs.keys()):
            lbl = tk.Label(self._frm_plotter_setup,text=key,anchor='w')
            entry = ttk.Entry(self._frm_plotter_setup,width=15)
            
            lbl.grid(row=row_start+i,column=0)
            entry.grid(row=row_start+i,column=1)
            entry.bind("<Return>",func=lambda event: self.replot_heatmap())
            
            self._dict_plotter_kwargs_widgets[key] = entry
            
        # Auto adjust the size of the widgets
        total_widgets = row_start + len(kwargs)
        for i in range(total_widgets):
            self._frm_plotter_setup.grid_rowconfigure(i,weight=1)
            self._frm_plotter_setup.grid_columnconfigure(0,weight=1)
            self._frm_plotter_setup.grid_columnconfigure(1,weight=1)
        self.replot_heatmap(flg_suppress_err=True)
    
    def _get_plotter_kwargs(self) -> dict:
        """
        Get the plotter options for the current mapping plot
        
        Returns:
            dict: Plotter options for the current mapping plot
        """
        kwargs = {}
        for key in self._dict_plotter_kwargs_widgets.keys():
            entry = self._dict_plotter_kwargs_widgets[key]
            try: kwargs[key] = float(entry.get())
            except: kwargs[key] = entry.get()
        return kwargs
    
    @thread_assign
    def _reinitialise_auto_plot(self) -> threading.Thread: # pyright: ignore[reportReturnType]
        """
        Initialise the auto plot for the mapping plot
        """
        pass # work here # Now that we're no longer using the auto-plot, this function should be modified to properly reinitialise the combobox, widgets, plot fig/ax, etc.
        
        # Store the combobox values
        mappingUnit_name = self._combo_plot_mappingUnitName.get()
        spectralPosition = self._combo_plot_SpectralPosition.get()
        
        # Destroy the previous canvas plot and widget to prevent memory leak
        try:
            if isinstance(self._plt_cbar,matplotlib.colorbar.Colorbar):
                self._plt_cbar.remove()
        except Exception as e: print('_reinitialise_auto_plot',e)
        
        try:
            if isinstance(self._plt_ax,matplotlib.axes.Axes):
                self._plt_ax.clear()
        except Exception as e: print('_reinitialise_auto_plot',e)
        
        try:
            if isinstance(self._plt_fig,matplotlib.figure.Figure) and isinstance(self._canvas_id_interaction,int):
                self._plt_fig.canvas.mpl_disconnect(self._canvas_id_interaction)
        except Exception as e: print('_reinitialise_auto_plot',e)
        
        try: plt.close(fig=self._plt_fig)
        except Exception as e: print('_reinitialise_auto_plot',e)
        
        # Reset the plot    
        self._plt_fig,self._plt_ax = plt.subplots(1,1,figsize=self._figsize_in)
        
        # Reset the combo boxes
        self._reset_plot_combobox()
        
        # Destroy the previous canvas plot and widget
        if not isinstance(self._canvas_id_interaction,type(None)):
            self._plt_fig.canvas.mpl_disconnect(self._canvas_id_interaction)
        self._canvas_widget.destroy()
        
        # Reset the canvas plot and widget
        self._canvas_plot = FigureCanvasTkAgg(self._plt_fig,master=self._frm_plot)
        self._canvas_widget = self._canvas_plot.get_tk_widget()
        
        row,col,rowspan,colspan = self._canvas_grid_loc
        self._canvas_widget.grid(row=row,column=col,rowspan=rowspan,columnspan=colspan)
        
        # Reset the label for the clicked coordinates
        self._lbl_coordinates.config(text='Clicked:')
        
        # Reset the click event for the plot
        self._canvas_id_interaction = self._plt_fig.canvas.mpl_connect('button_press_event',self._retrieve_click_idxcol)
        
        # Set the combobox values again
        try:
            if mappingUnit_name in self._combo_plot_mappingUnitName.cget('values'):
                self._combo_plot_mappingUnitName.set(mappingUnit_name)
            if spectralPosition in self._combo_plot_SpectralPosition.cget('values'):
                self._combo_plot_SpectralPosition.set(spectralPosition)
        except Exception as e: print('_reinitialise_auto_plot',e)
        
        self._lbl_coordinates.config(text='Figures are reset')
    
    def _set_current_mappingUnit(self,mappingUnit:MeaRMap_Unit):
        """
        Set a new mappingUnit to be observed

        Args:
            mappingUnit (MeaRMap_Unit): The mapping unit to be set
        """
        assert mappingUnit in self._mappingHub.get_list_MappingUnit(),\
            "This is a private method, only to be used when setting up a new mappingUnit to be observed"\
            "the mappingUnit set must be obtained from the internal self._mappingHub."
        self._current_mappingUnit = mappingUnit
        self._current_mappingUnit.add_observer(self.replot_heatmap)
        
    def _switch_plot_RamanShift(self):
        if not self._current_mappingUnit.check_measurement_and_metadata_exist(): return
        
        current_wavelength = self._get_current_wavelength_reversed()
        
        if self._bool_plot_in_RamanShift.get():
            self._lbl_SpectralPosition.config(text='cm^-1')
        else:
            self._lbl_SpectralPosition.config(text='nm')
        
        self.refresh_comboboxes(
            preserve_unit_name=self._combo_plot_mappingUnitName.get(),
            preserve_wavelength=current_wavelength
        )
        
    def _set_combobox_closest_value(self):
        """
        Set the combobox to the closest wavelength to the entered value
        """
        if not self._current_mappingUnit.check_measurement_and_metadata_exist(): return
        try: current_spectralPosition = float(self._combo_plot_SpectralPosition.get())
        except Exception as e: print('_set_combobox_closest_value', e); return
        
        if self._bool_plot_in_RamanShift.get():
            idx = self._current_mappingUnit.get_raman_shift_idx(current_spectralPosition)
        else:
            idx = self._current_mappingUnit.get_wavelength_idx(current_spectralPosition)
        self._combo_plot_SpectralPosition.current(idx)
        
        self.replot_heatmap()
        
    def _reset_plot_combobox(self):
        """
        Resets the status of the combobox for next use cases
        """
        current_name = self._combo_plot_mappingUnitName.get()
        current_wavelength = self.get_current_wavelength()
        self._combo_plot_mappingUnitName.configure(values=[],state='readonly')
        self._combo_plot_SpectralPosition.configure(values=[],state='active')
        
        self.refresh_comboboxes(
            preserve_unit_name=current_name,
            preserve_wavelength=current_wavelength,
        )
        
    def override_unit_combobox(self, message:str) -> None:
        """
        Override the status of the mappingUnit combobox. The combobox will be set to 'readonly'
        but will not be visible in the GUI, instead, it will show a message
        """
        loc = self._combo_plot_mappingUnitName.grid_info()
        self._combo_plot_mappingUnitName.grid_remove()
        frm = self._combo_plot_mappingUnitName.master
        lbl = tk.Label(frm,text=message,bg='yellow')
        lbl.grid(row=loc['row'],column=loc['column'],columnspan=loc['columnspan'])
        
    def set_combobox_values(self,mappingUnit_name:str|None=None,wavelength:float|None=None) -> None:
        """
        Set the mappingUnit and spectralPosition selection in the combobox
        
        Args:
            mappingUnit_id (str): MappingUnit_ID to be selected. If None, no change is made.
            wavelength (float): Wavelength to be selected. If None, no change is made.
        """
        current_name = self._combo_plot_mappingUnitName.get()
        current_wavelength = self.get_current_wavelength()
        
        if mappingUnit_name is None: mappingUnit_name = current_name
        if wavelength is None: wavelength = current_wavelength
            
        self._update_currentMappingUnit_observer(mappingUnit_name, replot=True)
        
    def refresh_comboboxes(self, preserve_unit_name:str|None=None, preserve_wavelength:float|None=None) -> None:
        """
        Refreshes the plotter's combobox according to the mappingUnits in the mappingHub
        
        Args:
            preserve_unit_name (str|None): Unit name to be selected after the refresh if possible.
            preserve_wavelength (float|None): Wavelength to be selected after the refresh if possible. It will\
                be set to Raman shift automatically according to the checkbox state.
        """
        # Check if there are any measurements in the mappingHub for the refresh. Returns if not
        if not self._mappingHub.check_measurement_exist(): return
        list_valid_names = [unit.get_unit_name() for unit in self._mappingHub.get_list_MappingUnit()\
            if unit.check_measurement_and_metadata_exist()]
        if len(list_valid_names) == 0: return
        
        # Get the mappingUnit to be set
        list_names = self._mappingHub.get_list_MappingUnit_names()
        if preserve_unit_name in list_valid_names:
            mappingUnit = self._mappingHub.get_MappingUnit(unit_name=preserve_unit_name)
        elif self._current_mappingUnit.check_measurement_and_metadata_exist():
            mappingUnit = self._current_mappingUnit
        else: mappingUnit = self._mappingHub.get_MappingUnit(unit_name=list_valid_names[0])
        unit_name = mappingUnit.get_unit_name()
        
        # Get the wavelength or Raman shift list to be set
        current_wavelength = self.get_current_wavelength()
        if isinstance(preserve_wavelength, (int,float)): preserve_wavelength = float(preserve_wavelength)
        elif isinstance(current_wavelength, (int,float)): preserve_wavelength = float(current_wavelength)
        else: preserve_wavelength = 0.0
        
        if self._bool_plot_in_RamanShift.get(): list_spectral_position = mappingUnit.get_list_Raman_shift()
        else: list_spectral_position = mappingUnit.get_list_wavelengths()
        idx_spectral_position = mappingUnit.get_wavelength_idx(preserve_wavelength)
        list_spectral_position = [str(pos) for pos in list_spectral_position]
        
        # Set the obtained lists
        self._combo_plot_mappingUnitName.configure(values=[])
        self._combo_plot_SpectralPosition.configure(values=[])
        self._combo_plot_mappingUnitName.configure(values=list_names)
        self._combo_plot_SpectralPosition.configure(values=list_spectral_position)
        
        # Set the original valies
        self._combo_plot_mappingUnitName.set(unit_name)
        self._combo_plot_SpectralPosition.current(idx_spectral_position)
    
    def replot_heatmap(self,flg_suppress_err:bool=False) -> threading.Thread|None:
        """
        Replot the heatmap using the current mappingHub and the selected mappingUnit_ID and SpectralPosition
        
        Args:
            flg_suppress_err (bool, optional): If True, the function will suppress the error message. Defaults to False.

        Returns:
            threading.Thread|None: The thread object if the heatmap is being replotted, None otherwise.
        """
        try:
            thread = threading.Thread(target=self.plot_heatmap)
            thread.start()
            return thread
        except Exception as e:
            if not flg_suppress_err: print('replot_heatmap',e)
        
    def get_selected_mappingUnit(self) -> MeaRMap_Unit|None:
        """
        Get the currently selected mapping unit from the combo box.
        
        Returns:
            MappingMeasurement_Unit: The currently selected mapping unit.
        """
        return self._current_mappingUnit
    
    def _update_currentMappingUnit_observer(self, mappingUnit_name:str, replot:bool) -> None:
        """
        Update the currently selected mapping unit according to the new combobox selection
        
        Args:
            mappingUnit_name (str): The name of the mapping unit to be set.
            replot (bool): If True, the heatmap will be replotted after updating the mapping unit.
        """
        # Remove observer
        try: self._current_mappingUnit.remove_observer(self.replot_heatmap)
        except: pass
        
        # Get the new mappingUnit
        self._current_mappingUnit = self._mappingHub.get_MappingUnit(unit_name=mappingUnit_name)
        self._current_mappingUnit.add_observer(self.replot_heatmap)
        
        self.refresh_comboboxes()
        
        if replot: self.replot_heatmap()
    
    def plot_heatmap(self):
        """
        Extracts the necessary measurement data to make the heatmap plot and then pass it onto the
        plotting queue
        """
        if self._flg_isplotting.is_set(): return
        assert isinstance(self._mappingHub,MeaRMap_Hub),\
            "plot_heatmap: Measurement data is not of the correct type. Expected: MappingMeasurement_Hub"
        
        mappingUnit = self._current_mappingUnit
        if not isinstance(mappingUnit, MeaRMap_Unit) or not mappingUnit.check_measurement_and_metadata_exist(): return

        self._flg_isplotting.set()
        
        # >>> Find the wavelength
        wavelength, ramanshift = self._get_closest_selected_wavelength(mappingUnit)
        
        try: clim_min = float(self._entry_plot_clim_min.get())
        except: clim_min = None
        try: clim_max = float(self._entry_plot_clim_max.get())
        except: clim_max = None
        clim = (clim_min,clim_max)
        if self._bool_auto_clim.get(): clim = (None,None)
                
        title = mappingUnit.get_unit_name()+'\n{:.0f}cm^-1 [{:.1f}nm]'.format(ramanshift,wavelength)
        kwargs = self._get_plotter_kwargs()
        self._plt_fig, self._plt_ax, self._plt_cbar = self._func_current_plotter(
            mapping_unit=mappingUnit,
            wavelength=wavelength,
            clim=clim,
            title=title,
            fig=self._plt_fig,
            ax=self._plt_ax,
            clrbar=self._plt_cbar,
            **kwargs
        )
        
        self._set_plot_xylim()
        self._current_mappingUnit = mappingUnit
        self.refresh_plotter()
        
        self._flg_isplotting.clear()

    def _get_closest_selected_wavelength(self, mappingUnit:MeaRMap_Unit) -> tuple[float,float]:
        """
        Find the closest wavelength and its corresponding Raman shift for the given mapping unit
        to the currently selected wavelength/Raman shift in the combobox

        Args:
            mappingUnit (MappingMeasurement_Unit): The mapping unit to find the wavelength for.

        Returns:
            tuple[float,float]: (wavelength, ramanshift) where wavelength is the closest wavelength in nm and
                   ramanshift is the corresponding Raman shift in cm^-1.
        """
        list_wavelength = mappingUnit.get_list_wavelengths()
        _,laser_wavelength = mappingUnit.get_laser_params()
        try: spectralPosition = float(self._combo_plot_SpectralPosition.get())
        except ValueError: spectralPosition = 0.0
        
        if not self._bool_plot_in_RamanShift.get(): wavelength = spectralPosition
        else: wavelength = convert_ramanshift_to_wavelength(spectralPosition, laser_wavelength)    
        wavelength = list_wavelength[np.argmin(np.abs(np.array(list_wavelength)-wavelength))]
        ramanshift = convert_wavelength_to_ramanshift(wavelength, laser_wavelength)
        
        spectralPosition = wavelength if not self._bool_plot_in_RamanShift.get() else ramanshift
        self._combo_plot_SpectralPosition.set(f'{spectralPosition:.1f}')
        
        return wavelength, ramanshift
        
    @thread_assign
    def save_plot(self):
        """
        Save the current plot as an image, asks the user for the file path
        """
        try:
            filename = self._combo_plot_mappingUnitName.get()
            filepath = filedialog.asksaveasfilename(initialfile=filename,
                defaultextension='.png',
                filetypes=[('PNG files','*.png')])
            
            if not isinstance(self._plt_fig, matplotlib.figure.Figure): return
            
            self._plt_fig.tight_layout()
            self._canvas_plot.draw_idle()
            self._canvas_widget.update_idletasks() # Process pending idle tasks
            self._canvas_widget.update() # Process pending events
            self._canvas_widget.after_idle(self._canvas_plot.print_png,filepath)
            
            messagebox.showinfo('Save plot','Plot saved successfully')
        except Exception as e: print('save_plot',e); return
        
    @thread_assign
    def save_plot_data(self):
        """
        Save the current plot data as a csv file, asks the user for the file path
        """
        try:
            if not isinstance(self._current_mappingUnit, MeaRMap_Unit) or\
                not self._current_mappingUnit.check_measurement_and_metadata_exist(): return
            filepath = filedialog.asksaveasfilename(defaultextension='.csv',
                filetypes=[('CSV files','*.csv')])
            
            spectralPosition_idx = self._combo_plot_SpectralPosition.current()
            list_wavelength = self._current_mappingUnit.get_list_wavelengths()
            wavelength = list_wavelength[spectralPosition_idx]
            df = self._current_mappingUnit.get_heatmap_table(wavelength)
            df.to_csv(filepath)
            messagebox.showinfo('Save data','Data saved successfully')
        except Exception as e: print('save_plot_data',e); return
        
    def _set_plot_xylim(self):
        """
        Sets the x and y limits of the plot using the values in the widgets
        """
        # Set the x and y limits
        try: xlim_min = float(self._entry_plot_xlim_min.get())
        except: xlim_min = None
        try: xlim_max = float(self._entry_plot_xlim_max.get())
        except: xlim_max = None
        try: ylim_min = float(self._entry_plot_ylim_min.get())
        except: ylim_min = None
        try: ylim_max = float(self._entry_plot_ylim_max.get())
        except: ylim_max = None
        
        try:
            if isinstance(self._plt_ax, matplotlib.axes.Axes):
                self._plt_ax.set_xlim(xlim_min,xlim_max)
                self._plt_ax.set_ylim(ylim_min,ylim_max)
        except: pass
        
    def refresh_plotter(self):
        """
        Update the figure being shown. Has to be used in a WORKER THREAD to save resources
        
        Args:
            spectrum_figures (list): List of figures (Pillow figures) of the same size to be combined
        """
        pass # work here # Remove this method and replace it with a method that updates the plot when the data is available.
        try:
            self._canvas_widget.update_idletasks() # Process pending idle tasks
            self._canvas_widget.update() # Process pending events
            self._canvas_widget.after_idle(self._canvas_plot.draw_idle)
            
            # Reset the click event for the plot
            if not isinstance(self._canvas_id_interaction,type(None)):
                self._plt_fig.canvas.mpl_disconnect(self._canvas_id_interaction)
            self._canvas_id_interaction = self._plt_fig.canvas.mpl_connect('button_press_event',self._retrieve_click_idxcol)
        except TimeoutError: pass
        except Exception as e: print('_auto_update_plot',e)
    
    def _get_current_wavelength_reversed(self) -> float|None:
        """
        Retrieves the current wavelength being plotted. REVERSED LOGIC!!!
        ONLY USED FOR THE SWITCHING OF RAMAN SHIFT AND WAVELENGTH because of 
        how the boolean variable is always switched before this function is called.
        
        Returns:
            float|None: The current wavelength or None if not set.
        """
        if not isinstance(self._current_mappingUnit, MeaRMap_Unit) or\
            not self._current_mappingUnit.check_measurement_and_metadata_exist():
            ret = None
        else:
            try: current_val = float(self._combo_plot_SpectralPosition.get())
            except Exception as e: print('get_current_wavelength',e); return None
            if not self._bool_plot_in_RamanShift.get():
                ret = self._current_mappingUnit.convert(Raman_shift=current_val)
            else: ret = current_val
            ret = self._current_mappingUnit.get_closest_wavelength(ret)
        return ret
    
    def get_current_wavelength(self) -> float|None:
        """
        Retrieves the current wavelength being plotted.
        
        Returns:
            float|None: The current wavelength or None if not set.
        """
        if not isinstance(self._current_mappingUnit, MeaRMap_Unit) or\
            not self._current_mappingUnit.check_measurement_and_metadata_exist():
            ret = None
        else:
            try: current_val = float(self._combo_plot_SpectralPosition.get())
            except Exception as e: print('get_current_wavelength',e); return None
            if self._bool_plot_in_RamanShift.get():
                ret = self._current_mappingUnit.convert(Raman_shift=current_val)
            else: ret = current_val
            ret = self._current_mappingUnit.get_closest_wavelength(ret)
        return ret

    def _retrieve_click_idxcol(self,event:matplotlib.backend_bases.MouseEvent|Any):
        """
        Retrieve the index and the column where the figure is clicked
        """
        if event.inaxes and isinstance(self._current_mappingUnit, MeaRMap_Unit)\
            and self._current_mappingUnit.check_measurement_and_metadata_exist():
            coorx,coory = event.xdata,event.ydata
            if coorx is None or coory is None: return
            
            clicked_measurementId = self._current_mappingUnit.get_measurementId_from_coor(coor=(coorx,coory))
            ramanMea = self._current_mappingUnit.get_RamanMeasurement(clicked_measurementId)
            try: intensity = f'{ramanMea.get_intensity(wavelength=self.get_current_wavelength()):.1f}'
            except Exception as e:
                print('_retrieve_click_idxcol: ',e)
                intensity = 'error'
            
            self._lbl_coordinates.config(text=f"Clicked: x={coorx:.3f}, y={coory:.3f}, intensity={intensity}")

            if self._callback_click:
                self._callback_click((clicked_measurementId,(coorx,coory)))

def test_plotter():
    from iris.data.measurement_RamanMap import generate_dummy_mappingHub, test_datasaveload_system
    
    mappinghub = generate_dummy_mappingHub(numx=3,numy=3,repeat=1)
    mappinghub.test_generate_dummy()
    # test_datasaveload_system(mappinghub)
    
    root = tk.Tk()
    root.title('Test plotter')
    queue_click = queue.Queue()
    plotter = Frm_MappingMeasurement_Plotter(
        root,
        mappingHub=mappinghub,
        callback_click=queue_click.put
        )
    plotter.refresh_plotter()
    plotter.pack(fill=tk.BOTH,expand=True)
    
    def retrieve_click():
        while True:
            print('Clicked:',queue_click.get())
    threading.Thread(target=retrieve_click).start()
    
    root.mainloop()
    
    os._exit(0)
    
if __name__=="__main__":
    test_plotter()