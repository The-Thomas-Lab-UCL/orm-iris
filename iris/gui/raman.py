"""
A class that manages the motion controller aspect for the Ocean Direct Raman spectrometer
"""
import PySide6.QtWidgets as qw
import PySide6.QtCore as qc
from PySide6.QtCore import Qt as qt, Signal, Slot, QObject, QThread, QTimer
from PySide6.QtGui import QPixmap

import os
import multiprocessing as mp
from multiprocessing.synchronize import Event as EventClass
import multiprocessing.connection as mpc
import multiprocessing.pool as mpp

import threading
import queue
from typing import Callable, Literal

import time

from PIL import Image, ImageTk
import cv2
import numpy as np
from pandas import DataFrame as df

import matplotlib as mpl
import matplotlib.pyplot as plt
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
from iris.multiprocessing.basemanager import MyManager, get_my_manager

from iris.controllers import Controller_Spectrometer

from iris import DataAnalysisConfigEnum
from iris.gui import AppRamanEnum, AppPlotEnum

class Frm_RamanSpectrometerController(qw.QGroupBox):
    """
    A class defining the app subwindow for the Raman spectrometer.
    """
    def __init__(self, parent,processor:mpp.Pool,controller:Controller_Spectrometer,
                 ramanHub:DataStreamer_Raman, dataHub:Frm_DataHub_Mapping,main:bool=False):
        """
        Initialises the Raman spectrometer controller window
        
        Args:
            parent (tk.Tk): The main tkinter window
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
        self._sgl_measurement:MeaRaman = None   # single measurement
        self._con_measurement:MeaRaman = None   # continuous measurement
        
        # Plotter setup
        self._plotter = MeaRaman_Plotter()
        
        # Plotter data management setup
        self._queue_plot_display = queue.Queue()    # Sets up a queue for plot generation from measurement data
        self._img_size = [400,400]                  # Image size (each) of the plot to be displayed (square to maintain aspect ratio)
        self._current_plot = None                   # ImageTk: current plot being shown in the app window *for buffer use*
        self._queue_plot_display\
            .put(self._plotter.plot_RamanMeasurement(plt_size=self._img_size))        # Puts the empty image in the queue for plotting
        
        # Run multithreading to update the image
        self._flg_plot_autoupdate = True     # Flags if the plot should be automatically updated
        self._thread_plot = threading.Thread(target=lambda: self.update_plot(),daemon=True)
        self._thread_plot.start()
        
# >>> Control frames setup <<<
    # Create the subframes to show the plots and controls
        sfrm_plots = tk.Frame(self)     # Subframe for the plots
        self._sfrm_controls = tk.Frame(self)  # Subframe for the Raman spectrometer controls
        self._sfrm_data = tk.Frame(self)      # Subframe for the data management
        
        ## Pack the subframes for display
        sfrm_plots.grid(row=0,column=0,sticky='nsew')
        self._sfrm_controls.grid(row=1,column=0,sticky='nsew')
        self._sfrm_data.grid(row=2,column=0,sticky='nsew')
        
        # Initialise the statusbar
        self._statbar = tk.Label(self, text="Raman controller initialisation", bd=1,relief=tk.SUNKEN,anchor=tk.W)
        self._statbar.grid(row=3,column=0,sticky='sew')
        self._bg_colour = self._statbar.cget('background') # gets the default bg_colour
        
        # Grid configurations
        # self.rowconfigure(0,weight=1)
        # self.rowconfigure(1,weight=1)
        # self.rowconfigure(2,weight=1)
        self.rowconfigure(3,weight=1)
        self.columnconfigure(0,weight=1)
        
# >>> Measurement control widgets setup <<<
        self._last_plotter_input = {}  # Stores the last input for the plotter
        
    # Setup the widget to show the plot
        # Subframe setups for the plot and control widgets
        ssfrm_plot = tk.Frame(sfrm_plots)
        ssfrm_plot_control_basic = tk.Frame(sfrm_plots) # For basic control widgets
        ssfrm_plot_control_add = tk.Frame(sfrm_plots)   # For additional control widgets
        
        ssfrm_plot.grid(row=0,column=0,sticky='nsew')
        ssfrm_plot_control_basic.grid(row=1,column=0,sticky='nsew')
        ssfrm_plot_control_add.grid(row=2,column=0,sticky='nsew')
        
    # Plot widget setup
        self._lbl_plot = tk.Label(image=None, master=ssfrm_plot)
        
    # Basic plot control widgets
        # Add widgets for additional plot options
        self._bool_PlotRawOnly = tk.BooleanVar()
        self._bool_PlotRamanShift = tk.BooleanVar()
        chk_PlotRawOnly = tk.Checkbutton(ssfrm_plot_control_basic,text='Plot raw only',
            variable=self._bool_PlotRawOnly, onvalue=True, offvalue=False)
        chk_PlotRamanShift = tk.Checkbutton(ssfrm_plot_control_basic,text='Plot Raman-shift',
            variable=self._bool_PlotRamanShift, onvalue=True, offvalue=False)
        self._entry_ExctWavelen = tk.Entry(ssfrm_plot_control_basic)
        
        chk_PlotRawOnly.select()
        chk_PlotRamanShift.select()
        
        # Pack the plot widgets
        self._lbl_plot.grid(row=0,column=0,columnspan=2)
        chk_PlotRawOnly.grid(row=1,column=0)
        chk_PlotRamanShift.grid(row=1,column=1)
        
    # Additional plot control widgets
        # Widgets for the plot limits
        lbl_xmin = tk.Label(ssfrm_plot_control_add,text='x-min: ')
        lbl_xmax = tk.Label(ssfrm_plot_control_add,text='x-max: ')
        lbl_ymin = tk.Label(ssfrm_plot_control_add,text='y-min: ')
        lbl_ymax = tk.Label(ssfrm_plot_control_add,text='y-max: ')
        self._entry_xmin = tk.Entry(ssfrm_plot_control_add)
        self._entry_xmax = tk.Entry(ssfrm_plot_control_add)
        self._entry_ymin = tk.Entry(ssfrm_plot_control_add)
        self._entry_ymax = tk.Entry(ssfrm_plot_control_add)
        btn_reset = tk.Button(ssfrm_plot_control_add,text='Reset plot',command=lambda: self._reset_plot_limits())
        
        lbl_xmin.grid(row=0,column=0)
        lbl_xmax.grid(row=0,column=2)
        lbl_ymin.grid(row=1,column=0)
        lbl_ymax.grid(row=1,column=2)
        
        self._entry_xmin.grid(row=0,column=1)
        self._entry_xmax.grid(row=0,column=3)
        self._entry_ymin.grid(row=1,column=1)
        self._entry_ymax.grid(row=1,column=3)
        
        btn_reset.grid(row=0,column=4,rowspan=2)
        
        [widget.bind('<Return>',lambda event: self._force_update_plot())\
            for widget in ssfrm_plot_control_add.winfo_children() if isinstance(widget,tk.Entry)] 
        
    # Raman controller setups
        start_state = 'normal'
        # Add the buttons for the spectrometer controls
        btn_single_mea = tk.Button(self._sfrm_controls,text='Single measurement',state=start_state,
                                   command=lambda: self.perform_single_measurement(accum='single'))
        self.btn_continuous_mea = tk.Button(self._sfrm_controls,text='Continuous measurement', 
                                               state=start_state, command=lambda: self.perform_continuous_measurement())
        
        
        
    # Add buttons and labels for device parameter setups
        ## Label to notify the users of the current device parameters
        self.lbl_dev_stat_inttime = tk.Label(self._sfrm_controls,
                                            text='Device integration time: {} microsec'
                                            .format(self.integration_time_ms))
        self.lbl_dev_stat_acq = tk.Label(self._sfrm_controls,
                                        text='Device accumulation: {} times/average'
                                        .format(self.contMea_accumulation))
        
        ## Label to show the current setting, spinbox to let the user enter new parameters,
        ## button to call the command and update the label
        ### for single measurement integration time
        lbl_inttime = tk.Label(self._sfrm_controls,text='Set integration time [ms]: ')        # label for the setting
        self.spin_inttime = ttk.Spinbox(self._sfrm_controls,state=start_state)         # spinbox for the input
        self.btn_inttime = tk.Button(self._sfrm_controls,text='Set',state=start_state,
            command=lambda:self._set_integration_time(new_value_ms=int(self.spin_inttime.get())))
        self.spin_inttime.bind('<Return>',lambda event: self._set_integration_time(new_value_ms=int(self.spin_inttime.get())))
        
        ### for single measurement number of accumulation
        lbl_bg_acq = tk.Label(self._sfrm_controls,
                              text='Set the single measurement accumulation: {}'.format(self.singMea_accumulation))
        self.spin_bg_acq = ttk.Spinbox(self._sfrm_controls,state=start_state,from_=1,to=1000,increment=1)             
        self.btn_bg_acq = tk.Button(self._sfrm_controls,text='Set',state=start_state,
                                    command=lambda: self.set_singMea_accumulation(
                                        new_value=int(self.spin_bg_acq.get()),tkcontainer=lbl_bg_acq))
        self.spin_bg_acq.bind('<Return>',lambda event: self.set_singMea_accumulation(new_value=int(self.spin_bg_acq.get()),
                                                              tkcontainer=lbl_bg_acq))
        
        ### for the measurement accumulation
        lbl_mea_acq = tk.Label(self._sfrm_controls,
                              text='Set the continuous measurement accumulation: {}'.format(self.contMea_accumulation))
        self.spin_mea_acq = ttk.Spinbox(self._sfrm_controls,state=start_state,from_=1,to=1000,increment=1)             
        self.btn_mea_acq = tk.Button(self._sfrm_controls,text='Set',state=start_state,
                                    command=lambda: 
                                    self.set_contMea_accumulation(new_value=int(self.spin_mea_acq.get()),
                                                           tkcontainer=lbl_mea_acq))
        self.spin_mea_acq.bind('<Return>',lambda event: self.set_contMea_accumulation(new_value=int(self.spin_mea_acq.get()),
                                                                tkcontainer=lbl_mea_acq))
        
        ## Packs the buttons and other widgets
        row_count=0 # to automatize making new rows
        self.lbl_dev_stat_inttime.grid(row=row_count,column=0)
        
        row_count+=1
        self.lbl_dev_stat_acq.grid(row=row_count,column=0)
        
        row_count+=1
        btn_single_mea.grid(row=row_count,column=0,pady=10)
        self.btn_continuous_mea.grid(row=row_count,column=1,pady=10)
        
        row_count+=1
        lbl_inttime.grid(row=row_count,column=0)
        self.spin_inttime.grid(row=row_count,column=1)
        self.btn_inttime.grid(row=row_count,column=2)
        
        row_count+=1
        lbl_bg_acq.grid(row=row_count,column=0)
        self.spin_bg_acq.grid(row=row_count,column=1)
        self.btn_bg_acq.grid(row=row_count,column=2)
        
        row_count+=1
        lbl_mea_acq.grid(row=row_count,column=0)
        self.spin_mea_acq.grid(row=row_count,column=1)
        self.btn_mea_acq.grid(row=row_count,column=2)
        
        if main: self.initialise_spectrometer_n_analyser()
        
    # >>> Data management widgets setup <<<
        # Datasave widget
        self.btn_saveto_datahub = tk.Button(self._sfrm_data,text="Save 'single measurement' to data hub'",state='normal',
                                           command=lambda: self._dataHub.append_RamanMeasurement_multi(self._sgl_measurement))
        
        # Metadata parameters
        self._laserpower_mW = DataAnalysisConfigEnum.LASER_POWER_MILLIWATT.value
        self._laserwavelength_nm = DataAnalysisConfigEnum.LASER_WAVELENGTH_NM.value
        self._objective_info = DataAnalysisConfigEnum.OBJECTIVE_INFO.value
        
        # Metadata widgets
        self._str_lbl_laserpower = tk.StringVar(value='Laser power: {} mW'.format(self._laserpower_mW))
        self._str_lbl_laserwavelength = tk.StringVar(value='Laser wavelength: {} nm'.format(self._laserwavelength_nm))
        self._str_lbl_objectiveinfo = tk.StringVar(value='Objective info: {}'.format(self._objective_info))
        lbl_laserpower = tk.Label(self._sfrm_data,textvariable=self._str_lbl_laserpower)
        lbl_laserwavelength = tk.Label(self._sfrm_data,textvariable=self._str_lbl_laserwavelength)
        lbl_objectiveinfo = tk.Label(self._sfrm_data,textvariable=self._str_lbl_objectiveinfo)
        
         # Entry widgets and button to set the metadata
        self._entry_laserpower = tk.Entry(self._sfrm_data)
        self._entry_laserwavelength = tk.Entry(self._sfrm_data)
        self._entry_objectiveinfo = tk.Entry(self._sfrm_data)
        btn_set_lasermetadata = tk.Button(self._sfrm_data,text='Set laser metadata',state='normal',
                                            command=lambda: self._set_laserMetadata())
        
        self._entry_laserpower.insert(0,DataAnalysisConfigEnum.LASER_POWER_MILLIWATT.value)
        self._entry_laserwavelength.insert(0,DataAnalysisConfigEnum.LASER_WAVELENGTH_NM.value)
        self._entry_objectiveinfo.insert(0,DataAnalysisConfigEnum.OBJECTIVE_INFO.value)

        self._entry_laserpower.bind('<Return>',lambda event: self._set_laserMetadata())
        self._entry_laserwavelength.bind('<Return>',lambda event: self._set_laserMetadata())
        self._entry_objectiveinfo.bind('<Return>',lambda event: self._set_laserMetadata())
        self._entry_objectiveinfo.bind('<Return>',lambda event: self._set_objectiveMetadata())

        # Grid the widgets
        self.btn_saveto_datahub.grid(row=0,column=0,pady=5,sticky='ew')
        btn_set_lasermetadata.grid(row=0,column=1,pady=5,sticky='ew')
        lbl_laserpower.grid(row=1,column=0,sticky='ew')
        self._entry_laserpower.grid(row=1,column=1,sticky='ew')
        lbl_laserwavelength.grid(row=2,column=0,sticky='ew')
        self._entry_laserwavelength.grid(row=2,column=1,sticky='ew')
        lbl_objectiveinfo.grid(row=3,column=0,sticky='ew')
        self._entry_objectiveinfo.grid(row=3,column=1,sticky='ew')
        
        for row in range(self._sfrm_data.grid_size()[1]):
            self._sfrm_data.grid_rowconfigure(row,weight=1)
        for col in range(self._sfrm_data.grid_size()[0]):
            self._sfrm_data.grid_columnconfigure(col,weight=1)
        
    # >>> Finalise the setup <<<
        # Update the statusbar
        self.status_update('Raman setup ready')
    
    def _set_objectiveMetadata(self):
        """
        Sets the objective metadata based on the entry widgets
        """
        try:
            objective_info = self._entry_objectiveinfo.get()
            self._str_lbl_objectiveinfo.set('Objective info: {}'.format(objective_info))
            
            self._objective_info = objective_info
        except Exception as e: print('_set_objectiveMetadata',e); self.status_update('Objective metadata setup failed',bg_colour='red')
    
    def _set_laserMetadata(self):
        """
        Sets the laser metadata based on the entry widgets
        """
        try:
            laserpower_mW = float(self._entry_laserpower.get())
            laserwavelength_nm = float(self._entry_laserwavelength.get())
            self._str_lbl_laserpower.set('Laser power: {} mW'.format(laserpower_mW))
            self._str_lbl_laserwavelength.set('Laser wavelength: {} nm'.format(laserwavelength_nm))
            
            self._laserpower_mW = laserpower_mW
            self._laserwavelength_nm = laserwavelength_nm
        except Exception as e: print('_set_laserMetadata',e); self.status_update('Laser metadata setup failed',bg_colour='red')
    
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
        return self._sgl_measurement
    
    def update_label_device_parameters(self,accum=None):
        """
        Updates the label showing the device integration time from the device itself
        and accumulation from the input

        Args:
            accum (int): new accumulation to be displayed
        """
        int_time = self._controller.get_integration_time_us() # in microsec
        self.lbl_dev_stat_inttime.configure(text='Device integration time: {} millisec'
                                            .format(int(int_time/1000)))
        if accum != None:
            self.lbl_dev_stat_acq.configure(text='Device accumulation: {} times/average'
                                            .format(accum))
    
    def set_contMea_accumulation(self,new_value,tkcontainer:tk.Label|None=None):
        """
        Set the accumulation for the continuous measurement.

        Args:
            new_value (int): The new accumulation
        """
        self.contMea_accumulation = new_value
        if tkcontainer != None:
            tkcontainer.configure(text= 'Set the continuous measurement accumulation: {}'.format(self.contMea_accumulation))
    
    def set_singMea_accumulation(self,new_value,tkcontainer:tk.Label|None=None):
        """
        Set the accumulation for the single measurement.

        Args:
            new_value (int): The new accumulation value
        """
        self.singMea_accumulation = new_value
        if tkcontainer != None:
            tkcontainer.configure(text= 'Set the single measurement accumulation: {}'.format(self.singMea_accumulation))

    def get_integration_time_ms(self):
        """
        Returns the integration time in milliseconds

        Returns:
            int: Integration time in milliseconds
        """
        return self.integration_time_ms
    
    @thread_assign
    def _set_integration_time(self,new_value_ms):
        """
        Sets the integration time of the spectrometer by taking in a variable. It also updates the variable

        Args:
            new_value_ms (int): New integration time [ms]
            tkcontainer (tk.label): Tkinter label which text is to be updated
        """
        self.btn_inttime.configure(state='disabled')
        self.spin_inttime.configure(state='disabled')

        new_int_time_us = self._controller.set_integration_time_us(new_value_ms*1000)
        self.integration_time_ms = int(new_int_time_us/1000)
        self.update_label_device_parameters()

        self.btn_inttime.configure(state='normal')
        self.spin_inttime.configure(state='normal')
    
    def update_plot(self):
        def request_image_update_tk(img):
            new_figtk = ImageTk.PhotoImage(Image.fromarray(img))
            if self._current_plot != new_figtk:
                self._lbl_plot.configure(image=new_figtk)
                self._current_plot = new_figtk
                
        self._flg_plot_autoupdate = True
        
        while True and self._flg_plot_autoupdate: # Turn off the autoupdater if requested
            try:
                img = self._queue_plot_display.get()
                request_image_update_tk(img)
            except Exception as e: (f'update_plot: {e}')
    
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
        try: xmin = float(self._entry_xmin.get())
        except: xmin = None
        try: xmax = float(self._entry_xmax.get())
        except: xmax = None
        try: ymin = float(self._entry_ymin.get())
        except: ymin = None
        try: ymax = float(self._entry_ymax.get())
        except: ymax = None
        
        return xmin,xmax,ymin,ymax
    
    def Analyse(self,measurement:MeaRaman,raw_list:list):
        """
        Offloads the measurement analyses (averaging)
        to a separate process.
        
        Args:
            storage (raman_measurement): The storage object to store the analysed data
            raw_list (list): The list of raw data to be analysed
        """
        # Gap 1: measure the average ~10ms
        result = self._processor.apply_async(func=measurement.get_average_rawlist,args=(raw_list,))
        spectrum_avg = result.get()
        measurement.set_analysed(spectrum_analysed=spectrum_avg)
        
    def _reset_plot_limits(self):
        """
        Resets the entry inputs for the plot limits
        """
        self._entry_xmin.delete(0,'end')
        self._entry_xmax.delete(0,'end')
        self._entry_ymin.delete(0,'end')
        self._entry_ymax.delete(0,'end')
        
        self._force_update_plot()
        
    def _force_update_plot(self):
        """
        Forces a plot update based on the last stored values for the plot
        """
        try:
            if self._last_plotter_input['type'] == 'raw':
                self.Plot_rawlist_RM(**self._last_plotter_input)
            elif self._last_plotter_input['type'] == 'avg':
                self.AnalyseAndPlot_rawlist(**self._last_plotter_input)
        except Exception as e: print('_force_update_plot',e)
        
    def AnalyseAndPlot_rawlist(self,measurement:MeaRaman,
        raw_list:list,idx:int,plot_add_kwargs:dict={}, **kwargs):
        """
        Calculates the average spectrum from the raw list and plots the raw and averaged spectrum.

        Args:
            measurement_storage (RamanMeasurement): The storage object to store the analysed data
            raw_list (list): The list of raw data to be analysed
            idx (int): The index of the measurement
            plot_add_kwargs (dict, optional): Additional plot kwargs. Defaults to {}.
        """
        self._last_plotter_input = {
            'measurement':measurement,
            'raw_list':raw_list,
            'idx':idx,
            'plot_add_kwargs':plot_add_kwargs,
            'type':'avg'
        }
        
        # Get the plot limits
        limits = self._get_plot_limits()
        
        # Set the dictionary for the plotter
        dict_plotter = {
            'measurement':measurement,
            'title':'Raw measurement',
            'plt_size':(self._img_size[0],int(self._img_size[1]/2)),
            'plot_raw':True,
            'limits':limits
        }
        dict_plotter.update(plot_add_kwargs)
        
        # 1. Generate the raw plot
        result_raw = self._processor.apply_async(func=self._plotter.plot_RamanMeasurement,kwds=dict_plotter)
        
        # 2. Calculate the average spectrum
        result_analysis= self._processor.apply_async(func=measurement.get_average_rawlist,args=(raw_list,))
        spectrum_avg = result_analysis.get()
        measurement.set_analysed(spectrum_analysed=spectrum_avg)
        
        # 3. Generate the averaged plot
        dict_plotter['plot_raw'] = False
        dict_plotter['title'] = 'Averaged measurement'
        result_avg = self._processor.apply_async(func=self._plotter.plot_RamanMeasurement,kwds=dict_plotter)
        
        plot_raw:np.ndarray = result_raw.get()
        plot_avg:np.ndarray = result_avg.get()
        
        # 4. Combine the plots
        plot_combined = np.concatenate((plot_raw,plot_avg),axis=0)
        
        # Gap 4: storing the values ~microsecs
        self._queue_plot_display.put(plot_combined)
        
    def Plot_rawlist_RM(self,measurement:MeaRaman,plot_add_kwargs:dict={}):
        """
        Plots the raw data from the measurement.

        Args:
            measurement (RamanMeasurement): The measurement object
            plot_add_kwargs (dict, optional): Additional plot kwargs. Defaults to {}.
        """
        self._last_plotter_input = {
            'measurement':measurement,
            'plot_add_kwargs':plot_add_kwargs,
            'type':'raw'
        }
        
        # Get the plot limits
        limits = self._get_plot_limits()
        
        # Generate the plot
        # self._plotter.set_plot_size(plt_size_mult=1)
        dict_plotter = {
            'measurement':measurement,
            'title':'Raw measurement',
            'plt_size':self._img_size,
            'plot_raw':True,
            'limits':limits
        }
        dict_plotter.update(plot_add_kwargs)
        
        result = self._processor.apply_async(func=self._plotter.plot_RamanMeasurement,kwds=dict_plotter)
        plot = result.get()
        
        # Storing the values
        self._queue_plot_display.put(plot)
    
    def force_stop_measurement(self):
        """
        Forces any running measurement to stop.
        """
        self._flg_isrunning.clear()
    
    @thread_assign
    def perform_continuous_single_measurements(self,widget_override=False,waitforplot=True,delay:int=0,queue_response:queue.Queue=None):
        """
        Perform continuous measurement until stopped. Generates a single measurement for each iteration, which is put into the queue.
        The measurement is then analysed and plotted. Accumulation is set to 1.
        
        Args:
            widget_override (bool, optional): If True, the widgets are not disabled. Defaults to False.
            waitforplot (bool, optional): If True, the function waits for the plot to be updated. Defaults to True.
            delay (int, optional): Delay between measurements in seconds. Defaults to 0.
            queue_response (queue.Queue, optional): A queue to put the result in. Defaults to None.
        """
        if not self._ramanHub.isrunning_auto_measurement(): self.resume_auto_measurement()
        else: print('!!!!! Auto-measurement is already running, a part of the program did NOT TERMINATE it properly !!!!!')
        
        if not widget_override:
            # Disable the widgets to prevent command overlaps
            self.disable_widgets()
            
        self.status_update("Continuous measurement in progress",bg_colour='yellow')
        
        # Turn the continuous measurement button into a stop button
        self.btn_continuous_mea.configure(state='active',text='STOP',
                                                  command= self._flg_isrunning.clear,bg='red')
        
        int_time_ms = self._controller.set_integration_time_us(int(self.integration_time_ms*1000))/1000
        self.update_label_device_parameters(self.contMea_accumulation)
        
        # Initialise the analyser and plotter
        raw_list = []
        thread = threading.Thread()
        
        # Flag for the running operation status and turn off the plot auto updater
        self._flg_isrunning.set()
        
        dict_metadata_extra = self._generate_metadata_dict()
        while self._flg_isrunning.is_set(): # Run till stopped
            # Initializes the measurement
            measurement = MeaRaman(
                timestamp=get_timestamp_us_int(),
                int_time_ms=int_time_ms,
                laserPower_mW=self._laserpower_mW,
                laserWavelength_nm=self._laserwavelength_nm,
                extra_metadata=dict_metadata_extra,
                )
            
            # Performs a measurement and add it to the storage
            timestamp_request = get_timestamp_us_int()
            result = self._ramanHub.get_measurement(timestamp_request,WaitForMeasurement=False,getNewOnly=True)
            spectrum_raw = result[1][-1]
            
            raw_list = measurement.set_raw_list(df_mea=spectrum_raw,idx=0)
            
            plot_add_kwargs = {'flg_plot_ramanshift':self._bool_PlotRamanShift.get()}
            
            if not thread.is_alive():
                if self._bool_PlotRawOnly.get():
                    thread = threading.Thread(target=self.Plot_rawlist_RM,kwargs={
                        'measurement':measurement,'plot_add_kwargs':plot_add_kwargs})
                    thread.start()
                else:
                    thread = threading.Thread(target=self.AnalyseAndPlot_rawlist,kwargs={
                        'measurement':measurement,
                        'raw_list':raw_list,
                        'idx':0,
                        'plot_add_kwargs':plot_add_kwargs
                        })
                    thread.start()
                    
            if waitforplot: thread.join()
            
            if queue_response: queue_response.put((thread,measurement))
            
            # Delay the next measurement to not over-save
            time.sleep(delay)
            
            # Update the statusbar
            self.status_update("Continuous measurement in progress",bg_colour='yellow')
        
        if not widget_override:
            # Enable the widgets again once done
            self.reset_n_enable_widgets()
            
        self.pause_auto_measurement()
        self.status_update() # Reset the statusbar
    
    @thread_assign
    def perform_continuous_measurement(self,widget_override=False,waitforplot=True,store_all=False,delay:int=0,queue_response:queue.Queue=None):
        """
        Perform continuous measurement until stopped.
        
        Idea:
            clicking the button once should activate the mode and clicking it again should turn it off
        
        Args:
            widget_override (bool, optional): If True, the widgets are not disabled. Defaults to False.
            waitforplot (bool, optional): If True, the function waits for the plot to be updated. Defaults to True.
            store_all (bool, optional): To store all measurement or to store as many as the measurement accumulation. Defaults to False.
            delay (int, optional): Delay between measurements in seconds. Defaults to 0.
            queue_response (queue.Queue, optional): A queue to put the result in. Defaults to None.
        """
        if not self._ramanHub.isrunning_auto_measurement(): self.resume_auto_measurement()
        else: print('!!!!! Auto-measurement is already running, a part of the program did NOT TERMINATE it properly !!!!!')
        
        if not widget_override:
            # Disable the widgets to prevent command overlaps
            self.disable_widgets()
            
        # Disable the widgets to prevent command overlaps
        self.disable_widgets()
        self.status_update("Continuous measurement in progress",bg_colour='yellow')
        
        # Turn the continuous measurement button into a stop button
        self.btn_continuous_mea.configure(state='active',text='STOP',
                                                  command= self._flg_isrunning.clear,bg='red')
        
        int_time_ms = self._controller.set_integration_time_us(int(self.integration_time_ms*1000))/1000
        self.update_label_device_parameters(self.contMea_accumulation)
        
        # Initialise the analyser and plotter
        raw_list = []
        thread = threading.Thread()
        
        dict_metadata_extra = self._generate_metadata_dict()
        # Initializes the measurement
        measurement = MeaRaman(timestamp=get_timestamp_us_int(),int_time_ms=int_time_ms,
                                       laserPower_mW=self._laserpower_mW,laserWavelength_nm=self._laserwavelength_nm,
                                       extra_metadata=dict_metadata_extra)
        acq_count = 0   # Counts the number of measurement done for indexing the result
        
        # Flag for the running operation status and turn off the plot auto updater
        self._flg_isrunning.set()
        
        while self._flg_isrunning.is_set(): # Run till stopped
            # Performs a measurement and add it to the storage
            timestamp_request = get_timestamp_us_int()
            result = self._ramanHub.get_measurement(timestamp_request,WaitForMeasurement=False,getNewOnly=True)
            spectrum_raw = result[1][-1]
            
            raw_list = measurement.set_raw_list(df_mea=spectrum_raw,idx=acq_count)
            
            plot_add_kwargs = {'flg_plot_ramanshift':self._bool_PlotRamanShift.get()}
            
            if not thread.is_alive():
                if self._bool_PlotRawOnly.get():
                    thread = threading.Thread(target=self.Plot_rawlist_RM,kwargs={
                        'measurement':measurement,'plot_add_kwargs':plot_add_kwargs})
                    thread.start()
                else:
                    thread = threading.Thread(target=self.AnalyseAndPlot_rawlist,kwargs={
                        'measurement':measurement,
                        'raw_list':raw_list,
                        'idx':acq_count,
                        'plot_add_kwargs':plot_add_kwargs
                        })
                    thread.start()
                    
            if waitforplot: thread.join()
                
            # Increases the counter and resets it if it reaches the maximum
            acq_count+=1
            if acq_count >= self.contMea_accumulation and not store_all:
                acq_count = 0
            
            # Delay the next measurement to not over-save
            time.sleep(delay)
            
            # Update the statusbar
            self.status_update("Continuous measurement in progress ({} of {})"
                            .format(acq_count+1,self.contMea_accumulation),bg_colour='yellow')

        thread_closer = threading.Thread(target=self.AnalyseAndPlot_rawlist,kwargs={
            'measurement':measurement,
            'raw_list':raw_list,
            'idx':acq_count-1,
            'plot_add_kwargs':plot_add_kwargs
            })
        thread_closer.start()
        
        if queue_response:
            queue_response.put((thread_closer,measurement))
        
        if not widget_override:
            # Enable the widgets again once done
            self.reset_n_enable_widgets()
            
        self.pause_auto_measurement()
        self.status_update() # Reset the statusbar
    
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
    
    @thread_assign
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
        
        # Flag for the running operation status and turn off the plot auto updater
        self.status_update("Continuous measurement in progress",bg_colour='yellow')
        
        # Turn the continuous measurement button into a stop button
        self.btn_continuous_mea.configure(state='active',text='STOP',
                                                  command=self._flg_isrunning.clear,bg='red')
        
        int_time_ms = self._controller.set_integration_time_us(int(self.integration_time_ms*1000))/1000
        self.update_label_device_parameters(self.contMea_accumulation)
        
        # Initialise the analyser and plotter
        dict_metadata_extra = self._generate_metadata_dict()
        measurement = MeaRaman(timestamp=get_timestamp_us_int(),
            int_time_ms=int_time_ms,laserPower_mW=self._laserpower_mW,laserWavelength_nm=self._laserwavelength_nm,
            extra_metadata=dict_metadata_extra)
        
        # Initialise the worker thread
        thread_plot = threading.Thread()
        
        # Initializes the measurement
        self._ramanHub.wait_MeasurementUpdate()
        self.perform_continuous_measurement(widget_override=True) # Turn on continuous acquisition for real-time plotting
        trigger = q_trigger.get()
        list_timestamp_trigger = [get_timestamp_us_int()]
        self._flg_isrunning.set()
        while self._flg_isrunning.is_set(): # Run till stopped
            # Wait for the trigger to start the next measurement or to stop
            trigger = q_trigger.get()
            if trigger == 0:
                self._flg_isrunning.clear()
                break
            
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
            if trigger == 1:
                continue
            
            dict_extra_metadata = self._generate_metadata_dict()
            list_measurement = []
            list_thread = []
            for ts_int,spectrum_raw,int_time_ms in zip(list_timestamp_mea_int,list_spectrum,list_integration_time_ms):
                # print(ts)
                # ts = convert_timestamp_us_int_to_str(ts)
                
                measurement = MeaRaman(timestamp=ts_int,int_time_ms=int_time_ms,
                    laserPower_mW=self._laserpower_mW,laserWavelength_nm=self._laserwavelength_nm,
                    extra_metadata=dict_extra_metadata)
                measurement.set_raw_list(df_mea=spectrum_raw)
                
                list_measurement.append(measurement)
                thread = threading.Thread(target=self.Analyse,kwargs={
                    'measurement':measurement,
                    'raw_list':[spectrum_raw]
                })
                thread.start()
                list_thread.append(thread)
            
            for thread in list_thread:
                thread:threading.Thread
                thread.join()
            
            # Return the measurement result
            for i in range(len(list_measurement)):
                q_return.put((list_timestamp_mea_int[i],list_measurement[i]))
            
            # Try to plot the data
            plot_add_kwargs = {'flg_plot_ramanshift':self._bool_PlotRamanShift.get()}
            
            if not thread_plot.is_alive():
                if self._bool_PlotRawOnly.get():
                    thread_plot = threading.Thread(target=self.Plot_rawlist_RM,kwargs={
                        'measurement':measurement,'plot_add_kwargs':plot_add_kwargs})
                    # thread_plot = threading.Thread(target=self.Plot_rawlist,kwargs={
                    #     'raw_spectrum':spectrum_raw,'plot_add_kwargs':plot_add_kwargs})
                    thread_plot.start()
                else:
                    thread_plot = threading.Thread(target=self.AnalyseAndPlot_rawlist,kwargs={
                        'measurement':measurement,
                        'raw_list':[spectrum_raw],
                        'idx':0,
                        'plot_add_kwargs':plot_add_kwargs
                        })
        
        # Enable the widgets again once done
        self.reset_n_enable_widgets()
            
        self.pause_auto_measurement()
        self.status_update() # Reset the statusbar
    
    def _check_RamanHub_automeasurement(self) -> bool:
        """
        Checks if the RamanHub is in auto-measurement mode.

        Returns:
            bool: True if the RamanHub is in auto-measurement mode
        """
        return self._ramanHub.get_measurement
    
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
    
    @thread_assign
    def perform_single_measurement_manual(self,widget_override=False,queue_response:queue.Queue=None,
                                   accum:Literal['single','continuous']='single',):
        """
        Performs multiple measurements based on the self.measurement_accumulation, averages, and
        updates the displayed figure all the time. Different than the perform_single_measurement,
        it pauses the auto measurement in the RamanMeasurementHub and waits for the user to trigger the measurement.

        Args:
            wait_for_plot (bool, optional): If true, wait for the plot to finish
            widget_override (bool, optional): Overrides the widget enable/disable toggle
            queue_response (queue.Queue, optional): If true, puts the result into the response queue
            accum (str, optional): The type of measurement accumulation to perform. Defaults to 'single'.
            
        Returns:
            threading.Thread: The thread for the measurement
        """
        if self._ramanHub.isrunning_auto_measurement(): self.pause_auto_measurement()
        
        if not widget_override:
            # Disable the widgets to prevent command overlaps
            self.disable_widgets()
        
        # Notify the user that the measurement is starting
        self.status_update("Single measurement in progress",bg_colour='yellow')
        
        # Sets the integration time and accumulation
        int_time_ms = self._controller.set_integration_time_us(int(self.integration_time_ms*1000))/1000
        self.update_label_device_parameters(self.singMea_accumulation)
        
        # Initialise the list and the worker thread
        raw_list = []
        thread = threading.Thread()
        
        # Initialise the measurement
        dict_metadata_extra = self._generate_metadata_dict()
        self._sgl_measurement = MeaRaman(timestamp=get_timestamp_us_int(),
            int_time_ms=int_time_ms, laserPower_mW=self._laserpower_mW,laserWavelength_nm=self._laserwavelength_nm,
            extra_metadata=dict_metadata_extra)
        
        # Performs the measurements
        self._flg_isrunning.set()
        accum = self.singMea_accumulation if accum == 'single' else self.contMea_accumulation
        for i in range(accum):
            # Performs a measurement and add it into the storage
            # timestamp_request = get_timestamp_us_int()
            # result = self._ramanHub.get_measurement(timestamp_request,WaitForMeasurement=False,getNewOnly=True)
            # spectrum_raw = result[1][-1]
            result = self._ramanHub.get_single_measurement()
            spectrum_raw = result[1]
            raw_list = self._sgl_measurement.set_raw_list(df_mea=spectrum_raw)
            
            plot_add_kwargs = {'flg_plot_ramanshift':self._bool_PlotRamanShift.get()}
            
            if not thread.is_alive():
                if self._bool_PlotRawOnly.get():
                    thread = threading.Thread(target=self.Plot_rawlist_RM,kwargs={
                        'measurement':self._sgl_measurement,'plot_add_kwargs':plot_add_kwargs})
                    # thread = threading.Thread(target=self.Plot_rawlist,kwargs={
                    #     'raw_spectrum':spectrum_raw,'plot_add_kwargs':plot_add_kwargs})
                    thread.start()
                else:
                    thread = threading.Thread(target=self.AnalyseAndPlot_rawlist,kwargs={
                        'measurement':self._sgl_measurement,
                        'raw_list':raw_list,
                        'idx':i,
                        'plot_add_kwargs':plot_add_kwargs
                        })
                    thread.start()
            
            # Update the statusbar
            self.status_update("Single measurement in progress ({} of {})"
                            .format(i+1,accum),bg_colour='yellow')
        self._flg_isrunning.clear()
        
        # Update the measurement values stored in the mult_measurement obj
        ## This ensures that the values are updated even if the user didn't wait for the
        ## thread to finish
        self.Analyse(measurement=self._sgl_measurement,raw_list=raw_list)
        # Set up the input for the final plot
        thread_closer = threading.Thread(target=self.AnalyseAndPlot_rawlist,kwargs={
            'measurement':self._sgl_measurement,
            'raw_list':raw_list,
            'idx':i,
            'plot_add_kwargs':plot_add_kwargs
            })
        thread_closer.start()
        
        if queue_response:
            queue_response.put((thread_closer,self._sgl_measurement))
        
        if not widget_override:
            # Enable the widgets again once done
            self.reset_n_enable_widgets()
        
        self.pause_auto_measurement()
        self.status_update() # Reset the statusbar
        
    @thread_assign
    def perform_single_measurement(self,widget_override=False,queue_response:queue.Queue=None,
                                   accum:Literal['single','continuous']='single'):
        """
        Perform multiple measurements based on the self.measurement_accumulation, averages, and 
        updates the displayed figure all the time.
        
        IMPORTANT NOTE: plotting takes a huge amount of time ~0.2s per plot. Use wait_for_plot=True only when 
        necessary
        
        Args:
            wait_for_plot (bool, optional): If true, wait for the plot to finish
            widget_override (bool, optional): Overrides the widget enable/disable toggle
            queue_response (queue.Queue, optional): If true, puts the result into the response queue
            accum (str, optional): The type of measurement accumulation to perform. Defaults to 'single'.
        
        Returns:
            threading.Thread: The thread for the measurement
        """
        if self._ramanHub.isrunning_auto_measurement():
            self.pause_auto_measurement()
            print('!!!!! Auto-measurement is already running, a part of the program did NOT TERMINATE it properly !!!!!')
        
        if not widget_override:
            # Disable the widgets to prevent command overlaps
            self.disable_widgets()
        
        # Notify the user that the measurement is starting
        self.status_update("Single measurement in progress",bg_colour='yellow')
        
        # Sets the integration time and accumulation
        int_time_ms = self._controller.set_integration_time_us(int(self.integration_time_ms*1000))/1000
        self.update_label_device_parameters(self.singMea_accumulation)
        
        # Initialise the list and the worker thread
        raw_list = []
        thread = threading.Thread()
        
        # Initialise the measurement
        dict_metadata_extra = self._generate_metadata_dict()
        self._sgl_measurement = MeaRaman(timestamp=get_timestamp_us_int(),
            int_time_ms=int_time_ms, laserPower_mW=self._laserpower_mW,laserWavelength_nm=self._laserwavelength_nm,
            extra_metadata=dict_metadata_extra)

        # Performs the measurements
        self._flg_isrunning.set()
        accum = self.singMea_accumulation if accum == 'single' else self.contMea_accumulation
        for i in range(accum):
            # Performs a measurement and add it into the storage
            timestamp_request = get_timestamp_us_int()
            result = self._ramanHub.get_measurement(timestamp_request,WaitForMeasurement=False,getNewOnly=True)
            spectrum_raw = result[1][-1]
            raw_list = self._sgl_measurement.set_raw_list(df_mea=spectrum_raw)
            
            plot_add_kwargs = {'flg_plot_ramanshift':self._bool_PlotRamanShift.get()}
            
            if not thread.is_alive():
                if self._bool_PlotRawOnly.get():
                    thread = threading.Thread(target=self.Plot_rawlist_RM,kwargs={
                        'measurement':self._sgl_measurement,'plot_add_kwargs':plot_add_kwargs})
                    # thread = threading.Thread(target=self.Plot_rawlist,kwargs={
                    #     'raw_spectrum':spectrum_raw,'plot_add_kwargs':plot_add_kwargs})
                    thread.start()
                else:
                    thread = threading.Thread(target=self.AnalyseAndPlot_rawlist,kwargs={
                        'measurement':self._sgl_measurement,
                        'raw_list':raw_list,
                        'idx':i,
                        'plot_add_kwargs':plot_add_kwargs
                        })
                    thread.start()
            
            # Update the statusbar
            self.status_update("Single measurement in progress ({} of {})"
                            .format(i+1,accum),bg_colour='yellow')
        self._flg_isrunning.clear()
        
        # Update the measurement values stored in the mult_measurement obj
        ## This ensures that the values are updated even if the user didn't wait for the
        ## thread to finish
        self.Analyse(measurement=self._sgl_measurement,raw_list=raw_list)
        # Set up the input for the final plot
        thread_closer = threading.Thread(target=self.AnalyseAndPlot_rawlist,kwargs={
            'measurement':self._sgl_measurement,
            'raw_list':raw_list,
            'idx':i,
            'plot_add_kwargs':plot_add_kwargs
            })
        thread_closer.start()
        
        if queue_response:
            queue_response.put((thread_closer,self._sgl_measurement))
        
        if not widget_override:
            # Enable the widgets again once done
            self.reset_n_enable_widgets()
        
        self.pause_auto_measurement()
        self.status_update() # Reset the statusbar
        
    def initialise_spectrometer_n_analyser(self):
        """
        Sets up the raman spectrometer controller and analyser in a worker thread
        """
        # Configure the integration time config
        intTime_min,intTime_max,intTime_inc = self._controller.get_integration_time_limits_us()
        self.spin_inttime.configure(from_=intTime_min,to=intTime_max,increment=intTime_inc)
        
        # Set and get the current device integration time
        self._set_integration_time(self.integration_time_ms)
        self.integration_time_ms = int(self._controller.get_integration_time_us()/1000)
        
        # Update the current device integration time being
        self.update_label_device_parameters()
        
        # Activates all spectrometer controls once done with the initialisation
        self.reset_n_enable_widgets()
    
    def disable_widgets(self):
        """
        Disables all widgets in a Tkinter frame and sub-frames
        """
        widget:tk.Widget = None # for typehints
        for widget in get_all_widgets(self._sfrm_controls):
            widget.configure(state='disabled')
            
        for widget in get_all_widgets(self._sfrm_data):
            widget.configure(state='disabled')
    
    def reset_n_enable_widgets(self):
        """
        Enable all widgets in a Tkinter frame and sub-frames
        """
        def get_all_widgets(parent_frame:tk.Widget):
            widget_list = []
            for child_widget in parent_frame.winfo_children():
                widget_list.append(child_widget)
                widget_list.extend(get_all_widgets(child_widget))  # Recursion
            return widget_list
        
        for widget in get_all_widgets(self._sfrm_controls):
            widget:tk.Widget
            widget.configure(state='active')
            
        for widget in get_all_widgets(self._sfrm_data):
            widget:tk.Widget
            widget.configure(state='normal')
        
        # Resets the continuous measurement button
        self.btn_continuous_mea.configure(text='Continuous measurement', 
                                               state='active', command=lambda: self.perform_continuous_measurement(),
                                               bg=self._bg_colour)
    
    def status_update(self,message=None,bg_colour=None):
        """
        To update the status bar at the bottom
        
        Args:
            message (str): The update message
            bg_colour (str, optional): Background colour. Defaults to 'default'.
        """
        if bg_colour == None:
            bg_colour = self._bg_colour
        
        if message == None:
            message = 'Spectrometer ready'
        
        try: self._statbar.configure(text=message,background=bg_colour)
        except: pass
        
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
    root = tk.Tk()

    dataHub = Frm_DataHub_Mapping(master=root)
    raman_frame = Frm_RamanSpectrometerController(
        parent=root,
        processor=processor,
        controller=RamanController_proxy,
        ramanHub=RamanHub,
        dataHub=dataHub
    )
    
    # raman_frame = raman_spectrometer_controller_frame(master=root,processor=processor)
    raman_frame.pack()
    root.mainloop()