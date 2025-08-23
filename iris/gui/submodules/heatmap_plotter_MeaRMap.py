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

class Frm_MappingMeasurement_Plotter(tk.Frame):
    def __init__(self,master,mappingHub:MeaRMap_Hub,
                 callback_click:Callable[[], tuple[str,tuple[float,float]]]|None=None,
                 figsize_pxl:tuple=(440,400)):
        """
        Initialise the plot_mapping_measurements class
        
        Args:
            master (tk.Tk): Parent widget
            mappingHub (MappingMeasurement_Hub): Mapping measurement hub to be used for plotting.
            callback_click (Callable[[], tuple[str,tuple[float,float]]]|None): Callback function to be called on click events,
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
        self._master = master
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
        self._bool_RamanShiftCombobox = tk.BooleanVar(value=True) # Boolean variable to plot Raman shift
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
            self._update_currentMappingUnit())
        self._combo_plot_SpectralPosition.bind("<<ComboboxSelected>>",func=lambda event:
            self.replot_heatmap())
        self._combo_plot_SpectralPosition.bind("<Return>",func=lambda event:
            self._set_combobox_closest_value())
        
        row=0
        self._btn_restart_threads.grid(row=row,column=0,sticky='we')
        self._lbl_coordinates.grid(row=row,column=1,sticky='we')
        
        # Set the callbacks
        self._mappingHub.add_observer(self.refresh_plotter_options)

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
            variable=self._bool_RamanShiftCombobox,onvalue=True,offvalue=False,
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
        
        self._plt_fig = None
        self._plt_ax = None
        self._plt_cbar = None
        
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
    
    def _switch_plot_RamanShift(self):
        _,laser_wavelength = self._current_mappingUnit.get_laser_params()
        if self._bool_RamanShiftCombobox.get():
            self._lbl_SpectralPosition.config(text='cm^-1')
        else:
            self._lbl_SpectralPosition.config(text='nm')
        
        current_value = self._combo_plot_SpectralPosition.get()
        try: current_value = float(current_value)
        except: current_value = 0
        
        self.refresh_plotter_options()
        self.refresh_plotter()
        
        list_values = [float(val) for val in self._combo_plot_SpectralPosition.cget('values')]
        if self._bool_RamanShiftCombobox.get():
            current_value = convert_wavelength_to_ramanshift(float(current_value), laser_wavelength)
        else:
            current_value = convert_ramanshift_to_wavelength(float(current_value), laser_wavelength)

        current_idx = int(np.argmin(np.abs(np.array(list_values)-float(current_value)))) if current_value else 0
        print(f'Current Spectral Position: {current_value}, Index: {current_idx}')
            
        if current_idx < 0 or current_idx >= len(list_values):
            current_idx = 0
        self._combo_plot_SpectralPosition.current(current_idx)
        
    def _set_combobox_closest_value(self):
        """
        Set the combobox to the closest wavelength to the entered value
        
        Returns:
            tuple: (closest_wavelength,closest_wavelength_idx) of the closest wavelength
        """
        entered_value = self._combo_plot_SpectralPosition.get()
        try: # Check if the entered value is a number
            entered_value = float(entered_value)
        except:
            return
        # Terminology:
        # Spectral Position: Wavelength or Raman shift
        # idx: index
        # tupp: tuple
        
        # Get the list of wavelengths
        tupp_SpecPosition = self._combo_plot_SpectralPosition.cget('values')
        list_SpecPosition = []
        for i in range(len(tupp_SpecPosition)):
            try: list_SpecPosition.append(float(tupp_SpecPosition[i]))
            except Exception as e: print('_set_combobox_closest_value',e)
        
        if len(list_SpecPosition)!=len(tupp_SpecPosition):
            print("Error: Spectral Position are not in the correct format")
            return
        
        # Find the closest wavelength
        distance = np.abs(np.array(list_SpecPosition)-entered_value)
        closest_SpecPos_idx = int(np.argmin(distance))
        closest_SpecPos = tupp_SpecPosition[closest_SpecPos_idx]
        
        # Set the combobox to the closest wavelength and plot the heatmap
        self._combo_plot_SpectralPosition.current(closest_SpecPos_idx)
        self.plot_heatmap()
        return (closest_SpecPos,closest_SpecPos_idx)
        
    def _reset_plot_combobox(self):
        """
        Resets the status of the combobox for next use cases
        """
        self._combo_plot_mappingUnitName.configure(values=[],state='readonly')
        self._combo_plot_SpectralPosition.configure(values=[],state='active')
        self.refresh_plotter_options()
        
    def override_unit_combobox(self, message:str) -> None:
        """
        Override the status of the mappingUnit combobox. The combobox will be set to 'readonly'
        but will not be visible in the GUI, instead, it will show a message
        """
        loc = self._combo_plot_mappingUnitName.grid_info()
        # self._combo_plot_mappingUnitName.grid_forget()
        frm = self._combo_plot_mappingUnitName.master
        lbl = tk.Label(frm,text=message,bg='yellow')
        lbl.grid(row=loc['row'],column=loc['column'],columnspan=loc['columnspan'])
        
    def get_plotOptions_selection(self) -> tuple[str,str]:
        """
        Get the mappingUnit and spectralPosition selection in the combobox
        
        Returns:
            tuple[str,str]: MappingUnit_ID and SpectralPosition selected
        """
        mappingUnit_name = self._combo_plot_mappingUnitName.get()
        spectralPosition = self._combo_plot_SpectralPosition.get()
        return (mappingUnit_name,spectralPosition)
        
    def set_plotOptions_selection(self,mappingUnit_name:str='',spectralPosition:str=''):
        """
        Set the mappingUnit and spectralPosition selection in the combobox
        
        Args:
            mappingUnit_id (str): MappingUnit_ID to be selected
            spectralPosition (str): SpectralPosition to be selected
        """
        if mappingUnit_name in self._combo_plot_mappingUnitName.cget('values'):
            self._combo_plot_mappingUnitName.set(mappingUnit_name)
        if spectralPosition in self._combo_plot_SpectralPosition.cget('values'):
            self._combo_plot_SpectralPosition.set(spectralPosition)
            
        self._update_currentMappingUnit()
        self.replot_heatmap()
        
    def refresh_plotter_options(self) -> bool:
        """
        Refreshes the plotter's combobox according to the mappingUnits in the mappingHub
        
        Returns:
            bool: True if the combobox is updated successfully
        """
    # >>> Get the current mapping unit
        mapping_unit = self.get_selected_mappingUnit()
        list_mappingUnit_name = self._mappingHub.get_list_MappingUnit_names()
        list_mappingUnit = self._mappingHub.get_list_MappingUnit()
        flg_found_valid = False
        if not mapping_unit.check_measurement_and_metadata_exist():
            for mapping_unit in list_mappingUnit:
                if mapping_unit.check_measurement_and_metadata_exist():
                    flg_found_valid = True
                    break
        else: flg_found_valid = True
        if not flg_found_valid: return False
        
    # >>> Build the new list
        _,laser_wavelength = mapping_unit.get_laser_params()
        list_wavelengths = mapping_unit.get_list_wavelengths()
        spectralPosition = self._combo_plot_SpectralPosition.get()
        try:
            float(spectralPosition)
            wavelength_prev = float(spectralPosition) if not self._bool_RamanShiftCombobox.get() else convert_ramanshift_to_wavelength(float(spectralPosition),laser_wavelength)
            ramanshift_prev = convert_wavelength_to_ramanshift(float(wavelength_prev),laser_wavelength)
        except ValueError:
            wavelength_prev,ramanshift_prev = self._get_closest_selected_wavelength(mapping_unit)
        
        if self._bool_RamanShiftCombobox.get():
            list_RamanShift = [convert_wavelength_to_ramanshift(float(wavelength),laser_wavelength) for wavelength in list_wavelengths]
            list_SpectralPosition = list_RamanShift
        else:
            list_SpectralPosition = list_wavelengths
            
        list_SpectralPosition = [f'{pos:.1f}' for pos in list_SpectralPosition]
        self._combo_plot_mappingUnitName.configure(values=list_mappingUnit_name,state='readonly')
        self._combo_plot_SpectralPosition.configure(values=list_SpectralPosition,state='active')
        
        prev_mappingUnit_name = mapping_unit.get_unit_name()

        try:
            if prev_mappingUnit_name in list_mappingUnit_name:
                self._combo_plot_mappingUnitName.set(prev_mappingUnit_name)
            if wavelength_prev in list_wavelengths:
                spectralPosition = wavelength_prev if self._bool_RamanShiftCombobox.get() else ramanshift_prev
                self._combo_plot_SpectralPosition.set(spectralPosition)
        except Exception as e:
            print('Error in refresh_plotter_options: ',e)
            if len(list_mappingUnit_name)>0: self._combo_plot_mappingUnitName.current(0)
            if len(list_SpectralPosition)>0: self._combo_plot_SpectralPosition.current(0)
        
        return True
    
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
        
    def get_selected_mappingUnit(self) -> MeaRMap_Unit:
        """
        Get the currently selected mapping unit from the combo box.
        
        Returns:
            MappingMeasurement_Unit: The currently selected mapping unit.
        """
        return self._current_mappingUnit
    
    def _update_currentMappingUnit(self):
        """
        Update the currently selected mapping unit.
        """
        self._current_mappingUnit.remove_observer(self.replot_heatmap)
        
        mappingUnit_name = self._combo_plot_mappingUnitName.get()
        dict_nameToID = self._mappingHub.get_dict_nameToID()
        
        mappingUnit_id = dict_nameToID[mappingUnit_name]
        mappingUnit = self._mappingHub.get_MappingUnit(mappingUnit_id)
        
        self._current_mappingUnit = mappingUnit
        self._current_mappingUnit.add_observer(self.replot_heatmap)
        
        # Update the spectral position combobox
        self._reset_plot_combobox()
        
        self.replot_heatmap()
    
    def plot_heatmap(self):
        """
        Extracts the necessary measurement data to make the heatmap plot and then pass it onto the
        plotting queue
        """
        if self._flg_isplotting.is_set(): return
        assert isinstance(self._mappingHub,MeaRMap_Hub),\
            "plot_heatmap: Measurement data is not of the correct type. Expected: MappingMeasurement_Hub"
        
        mappingUnit = self._current_mappingUnit
        if not mappingUnit.check_measurement_and_metadata_exist(): return
        
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
        
        if not self._bool_RamanShiftCombobox.get(): wavelength = spectralPosition
        else: wavelength = convert_ramanshift_to_wavelength(spectralPosition, laser_wavelength)    
        wavelength = list_wavelength[np.argmin(np.abs(np.array(list_wavelength)-wavelength))]
        ramanshift = convert_wavelength_to_ramanshift(wavelength, laser_wavelength)
        
        spectralPosition = wavelength if not self._bool_RamanShiftCombobox.get() else ramanshift
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
            if not isinstance(self._current_mappingUnit,MeaRMap_Unit): return
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
    
    def _retrieve_click_idxcol(self,event:matplotlib.backend_bases.MouseEvent|Any):
        """
        Retrieve the index and the column where the figure is clicked
        """
        if event.inaxes and isinstance(self._current_mappingUnit, MeaRMap_Unit):
            coorx,coory = event.xdata,event.ydata
            if coorx is None or coory is None: return
            
            self._lbl_coordinates.config(text=f"Clicked: (x={coorx:.3f}, y={coory:.3f})")
            
            clicked_measurementId = self._current_mappingUnit.get_measurementId_from_coor(coor=(coorx,coory))
            ramanMea = self._current_mappingUnit.get_RamanMeasurement(clicked_measurementId)
            
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
    
if __name__=="__main__":
    test_plotter()