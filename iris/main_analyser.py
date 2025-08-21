""" 
An app to read the measurement files from the main_controller.py, plot, and analyse it.
"""
import sys

import tkinter as tk
from tkinter import filedialog,ttk
from typing import Callable

import multiprocessing as mp
import multiprocessing.pool as mpp
import threading
import queue


from iris.utils.general import *

from iris.gui.submodules.heatmap_plotter_MeaRMap import Frm_MappingMeasurement_Plotter
from iris.gui.submodules.peakfinder_plotter_MeaRaman import Frm_RamanMeasurement_Plotter
from iris.gui.spectrometerCalibration import sFrm_wavelength_calibration
from iris.gui.dataHub_MeaRMap import Frm_DataHub_Mapping, Frm_DataHub_Mapping_Plus, MeaRMap_Hub
from iris.gui.timestamp_coorshift import sFrm_xyCoorTimestampShift

from iris import *

class A2SSM_analyser(tk.Frame):
    def __init__(self, master, processor:mpp.Pool, dataHub:Frm_DataHub_Mapping|None=None):
        """
        Initialises the A2SSM analyser.
        
        Args:
            master (tk.Tk): The master window
            processor (mpp.Pool): The processor for the mapping measurements
            mapping_data (mapping_measurement_data): The mapping data to be fsded. Default is None.
            dataHub (Frm_DataHub): The datahub to grab the mappingHub from. Default is None.
        """
        super().__init__(master)
        self._master:tk.Tk = master
        self._processor = processor
        self._dataHub_local = dataHub
        
    # >>> Frames setup <<<
        notebook = ttk.Notebook(self)
        notebook.grid(row=0,column=0,sticky='nsew')

        frm_datalabel = tk.Frame(self)  # Frame to show the selected RamanMeasurement and MappingMeasurementUnit
        frm_data = tk.Frame(notebook)
        frm_wav_cal = tk.LabelFrame(notebook,text='Wavelength Calibration')
        # frm_int_cal = tk.LabelFrame(notebook,text='Intensity Calibration')
        frm_tsCoorShift = tk.LabelFrame(notebook,text='Timestamp Shift')
        
        frm_datalabel.grid(row=1,column=0,sticky='ew')
        notebook.add(frm_data,text='Data Hub')
        notebook.add(frm_wav_cal,text='Wavelength Calibration')
        # notebook.add(frm_int_cal,text='Intensity Calibration')
        notebook.add(frm_tsCoorShift,text='Timestamp Shift')
        
    # >>> Sub-frame setup for the data hub and the plots <<<
        sfrm_data = tk.LabelFrame(frm_data,text='Data Hub')
        sfrm_plots = tk.Frame(frm_data)
        
        sfrm_data.grid(row=0,column=0,sticky='nsew')
        sfrm_plots.grid(row=0,column=1,sticky='nsew')
        
    # >>> Plots setup <<<
        frm_heatmap = tk.LabelFrame(sfrm_plots,text='Interactive Heatmap Plotter')
        frm_spectraplot = tk.LabelFrame(sfrm_plots,text='Spectra Plotter')
        frm_heatmap.grid(row=0,column=0,sticky='nsew')
        frm_spectraplot.grid(row=0,column=1,sticky='nsew')
        
        sfrm_plots.grid_rowconfigure(0,weight=1)
        sfrm_plots.grid_columnconfigure(0,weight=1)
        sfrm_plots.grid_columnconfigure(1,weight=1)
        
    # >>> Data label setup <<<
        self._strvar_selected_unit = tk.StringVar()
        self._strvar_selected_mea = tk.StringVar()
        self._lbl_selected_unit = tk.Label(frm_datalabel,textvariable=self._strvar_selected_unit,anchor='w')
        self._lbl_selected_mea = tk.Label(frm_datalabel,textvariable=self._strvar_selected_mea,anchor='w')
        
        self._lbl_selected_unit.grid(row=0,column=0,sticky='w')
        self._lbl_selected_mea.grid(row=0,column=1,sticky='w')
        
        frm_datalabel.grid_rowconfigure(0,weight=1)
        frm_datalabel.grid_columnconfigure(0,weight=1)
        
    # >>> Data hub plus setup <<<
        self._dataHub_MainController = dataHub
        self._dataHub_local = Frm_DataHub_Mapping(sfrm_data,width_rel=0.8)
        if not dataHub is None:
            self._dataHub_local.set_MappingHub(dataHub.get_MappingHub())
            self._flg_isconn_ccontroller = True
            controller_widget_state = 'normal'
        else:
            self._flg_isconn_ccontroller = False
            controller_widget_state = 'disabled'
        
        self._dataHubPlus = Frm_DataHub_Mapping_Plus(sfrm_data,self._dataHub_local,width_rel=0.8)
        btn_refresh_dataHubPlus = tk.Button(sfrm_data,text='Refresh dataHub display',command=self.update_trees)
        self._btn_grab_mappingHub = tk.Button(sfrm_data,text='Grab MappingHub from main_controller',command=self.grab_mappingHub,
                                              state=controller_widget_state)
        
        self._btn_grab_mappingHub.grid(row=0,column=0,sticky='ew')
        btn_refresh_dataHubPlus.grid(row=0,column=1,sticky='ew')
        self._dataHub_local.grid(row=1,column=0,columnspan=2)
        self._dataHubPlus.grid(row=2,column=0,columnspan=2)
        
    # >>> Wavelength calibration setup <<<
        self._frm_wav_cal = sFrm_wavelength_calibration(frm_wav_cal,dataHub=self._dataHub_local)
        self._frm_wav_cal.grid(row=0,column=0,sticky='nsew')
        
    # >>> Interactive heatmap plotter setup <<<
        self._heatmapPlotter = Heatmap_InteractivePlotter(frm_heatmap,self._processor,self._dataHubPlus,self._dataHub_local.get_MappingHub())
        self._heatmapPlotter.grid(row=0,column=0)
        
    # >>> Interactive spectra plotter setup <<<
        self._spectraPlotter = Frm_RamanMeasurement_Plotter(frm_spectraplot)
        self._spectraPlotter.grid(row=0,column=0)
        
    # >>> Interaction setup <<<
        self._eventHandler = EventHandler(self._dataHub_local,self._dataHubPlus,self._heatmapPlotter, self._spectraPlotter)
        self._eventHandler.set_callback_unit(self.show_selected_Unit)
        self._eventHandler.set_callback_mea(self.show_selected_RM)
        
    # >>> Timestamp coordinate shift setup <<<
        self._frm_tsCoorShift = sFrm_xyCoorTimestampShift(
            parent=frm_tsCoorShift,
            dataHub=self._dataHub_local,
            callback=self._dataHub_local.update_tree
        )
        self._frm_tsCoorShift.grid(row=0,column=0,sticky='nsew')
        
    def update_trees(self):
        """
        Updates the trees in the dataHub and dataHubPlus
        """
        self._dataHub_local.update_tree()
        self._dataHubPlus.update_tree_unit()
        
    def init_extensions(self,root):
        """
        Initialises the extensions for the analysers
        
        Args:
            root (tk.Tk): The master window
        """
        pass
        
    def show_selected_Unit(self):
        """
        Shows the selected MappingMeasurementUnit in the data label
        """
        unit_name = self._dataHub_local.get_selected_MappingUnit()[0].get_unit_name()
        self._strvar_selected_unit.set('Selected MappingMeasurement_Unit: {}'.format(unit_name))
        
    def show_selected_RM(self):
        """
        Shows the selected RamanMeasurement in the data label
        """
        list_dict_mea = self._dataHubPlus.get_selected_RamanMeasurement_summary()
        dict_mea = list_dict_mea[0]
        str_mea_summary = ''
        for key in dict_mea.keys():
            str_mea_summary += '{}: {}, '.format(key,dict_mea[key])
        str_mea_summary = str_mea_summary[:-2]
        self._strvar_selected_mea.set('Selected RamanMeasurement: {}'.format(str_mea_summary))
        
    def grab_mappingHub(self):
        """
        Grabs the mappingHub from the dataHub
        """
        if self._dataHub_local is not None:
            self._dataHub_local.set_MappingHub(self._dataHub_MainController.get_MappingHub())
            # self._dataHubPlus.set_mappingHub(self._dataHub.get_MappingHub())
            self._eventHandler.trigger_update_hub()
        
class Heatmap_InteractivePlotter(tk.Frame):
    def __init__(self, master, processor:mpp.Pool, dataHubPlus:Frm_DataHub_Mapping_Plus,
                 mappingHub:MeaRMap_Hub):
        """
        Initialises the interactive heatmap plotter.
        
        Args:
            master (tk.Tk): The master window
            processor (mpp.Pool): The processor for the mapping measurements
            dataHubPlus (Frm_DataHub_Plus): The datahub plus to grab the mappingHub from.
            mappingHub (MappingMeasurement_Hub): The mapping hub to be used.
        """
        super().__init__(master)
        self._master:tk.Tk = master
        self._processor = processor
        self._dataHubPlus = dataHubPlus
        
        # Plotter setup
        self._q_clickcoor = queue.Queue()
        self._heatmapPlotter = Frm_MappingMeasurement_Plotter(
            self,
            mappingHub=mappingHub,
            queue_click=self._q_clickcoor,
            figsize_pxl=(600,600))
        self._heatmapPlotter.override_unit_combobox('Use the "Data Hub" to select the unit')
        self._heatmapPlotter.grid(row=0,column=0)
        
        # Interaction setup
        self._click_callback:list[Callable] = []
        self._click_meaid = 0
        self._click_coor = (0,0)
        
        # Threads setup
        self._thd_auto_clickcheck = threading.Thread(target=self._auto_clickcheck)
        self._thd_auto_clickcheck.start()
    
    def update_plot(self):
        self._heatmapPlotter.replot_heatmap()
    
    def get_Frm_MappingMeasurement_Plotter(self) -> Frm_MappingMeasurement_Plotter:
        """
        Returns the interactive heatmap plotter
        """
        return self._heatmapPlotter
    
    def set_click_callback(self,callback:Callable):
        """
        Sets the callback function for the click event
        """
        self._click_callback.append(callback)
    
    def get_click_meaId_coor(self) -> tuple[int,tuple[float,float]]:
        """
        Returns the click event data.
        
        Returns:
            tuple[int,tuple[float,float]]: The measurement ID and the coordinate of the click event
        """
        return self._click_meaid,self._click_coor
    
    def _auto_clickcheck(self):
        """
        Automatically checks for the click coordinate from the queue.
        """
        while True:
            try:
                mea_id,coor = self._q_clickcoor.get_nowait()
                assert len(coor) == 2, 'Invalid coordinate'
                assert isinstance(coor[0],(float,int)) and isinstance(coor[1],(float,int)), 'Invalid coordinate'
                
                self._click_meaid = mea_id
                self._click_coor = coor
                for callback in self._click_callback: callback()
            except queue.Empty: time.sleep(0.1)
        
class EventHandler():
    """
    A handler for events such as clicking in the plotter or selecting a unit in the datahub plus that
    needs to be communicated between the classes
    """
    def __init__(self,dataHub:Frm_DataHub_Mapping,dataHubPlus:Frm_DataHub_Mapping_Plus, heatmapPlotterInteractive:Heatmap_InteractivePlotter,
                 spectraPlotter:Frm_RamanMeasurement_Plotter):
        """
        Initialises the event handler.
        
        Args:
            dataHubPlus (Frm_DataHub_Plus): The datahub plus to grab the mappingHub from.
            heatmapPlotter (Frm_MappingMeasurement_Plotter): The interactive heatmap plotter.
        """
        self._dataHub = dataHub
        self._dataHubPlus = dataHubPlus
        self._heatmapPlotterInteractive = heatmapPlotterInteractive
        self._heatmapPlotter = self._heatmapPlotterInteractive.get_Frm_MappingMeasurement_Plotter()
        self._spectraPlotter = spectraPlotter
        
        self._flg_update_hub = threading.Event()    # Flag to update the MappingHub in other classes
        self._flg_update_unit = threading.Event()   # Flag to update the MappingMeasurementUnit in other classes
        self._flg_update_mea = threading.Event()    # Flag to update the RamanMeasurement in other classes
        
        self._flg_update_unit_sel = threading.Event()   # Flag to update the MappingMeasurementUnit selection in the dataHub
        self._flg_update_mea_sel = threading.Event()    # Flag to update the RamanMeasurement selection in the dataHub
        
    # >>> Interaction setup: DataHub to widgets <<<
        # Set callback lists
        self._list_callback_unit = []
        self._list_callback_mea = []
        
        # Set the flags to the respective functions
        self._dataHub.set_MappingHub_load_callback(self._flg_update_hub.set)
        self._dataHubPlus.set_RMSelection_interactive(self._flg_update_mea.set)
        self._dataHubPlus.set_UnitSelection_interactive(self._flg_update_unit.set)
        
        # Set threads to constantly check the flags
        self._thd_AutoUpdate_hubload = threading.Thread(target=self._auto_update_Hub)
        self._thd_AutoUpdate_hubload.start()
        self._thd_AutoUpdate_unit = threading.Thread(target=self._auto_update_Unit)
        self._thd_AutoUpdate_unit.start()
        self._thd_AutoUpdate_mea = threading.Thread(target=self._auto_update_RM)
        self._thd_AutoUpdate_mea.start()
        
    # >>> Interaction setup: Widgets to DataHub <<<
        self._heatmapPlotterInteractive.set_click_callback(self._flg_update_mea_sel.set)
        
        # Set threads to constantly check the flags
        self._thd_AutoUpdate_unit_sel = threading.Thread(target=self._auto_update_Unit_selection)
        self._thd_AutoUpdate_unit_sel.start()
        self._thd_AutoUpdate_mea_sel = threading.Thread(target=self._auto_update_RM_selection)
        self._thd_AutoUpdate_mea_sel.start()
        
    def initialise_callbacks(self):
        # Set the flags to the respective functions
        self._dataHub.set_MappingHub_load_callback(self._flg_update_hub.set)
        self._dataHubPlus.set_RMSelection_interactive(self._flg_update_mea.set)
        self._dataHubPlus.set_UnitSelection_interactive(self._flg_update_unit.set)
        self._heatmapPlotterInteractive.set_click_callback(self._flg_update_mea_sel.set)
        
    def trigger_update_hub(self):
        """
        Triggers the update of the MappingHub in the other classes.
        """
        self._flg_update_hub.set()
        
    def _auto_update_Unit_selection(self):
        """
        Automatically calls the callback functions for the MappingMeasurementUnit selection event.
        """
        while True:
            self._flg_update_unit_sel.wait()
            self._flg_update_unit_sel.clear()
            pass
        
    def _auto_update_RM_selection(self):
        """
        Automatically calls the callback functions for the RamanMeasurement selection event.
        """
        while True:
            self._flg_update_mea_sel.wait()
            self._flg_update_mea_sel.clear()
            
            try:
                mea_id_int,_ = self._heatmapPlotterInteractive.get_click_meaId_coor()
                self._dataHubPlus.set_selected_RamanMeasurement(str(mea_id_int))
                self._flg_update_mea.set()
            except Exception as e: print(f'_auto_update_RM_selection: {e}')
        
    def set_callback_mea(self,callback:Callable):
        """
        Sets the callback function for the Raman measurement selection event.
        
        Args:
            callback (Callable): The callback function
        """
        assert callable(callback), 'Invalid callback'
        self._list_callback_mea.append(callback)
        
    def set_callback_unit(self,callback:Callable):
        """
        Sets the callback function for the unit selection event.
        
        Args:
            callback (Callable): The callback function
        """
        assert callable(callback), 'Invalid callback'
        self._list_callback_unit.append(callback)
        
    def _auto_update_Hub(self):
        """
        Automatically updates the MappingHub in the other classes.
        """
        while True:
            self._flg_update_hub.wait()
            self._flg_update_hub.clear()
            
            try:
                self._heatmapPlotter.refresh_plotter()
                self.initialise_callbacks()
            except Exception as e: (f'_auto_update_Hub: {e}')
        
    def _auto_update_RM(self):
        """
        Automatically updates the RamanMeasurement in the other classes.
        """
        while True:
            self._flg_update_mea.wait()
            self._flg_update_mea.clear()
            
            list_mea = self._dataHubPlus.get_selected_RamanMeasurement()
            list_mea_id = [mea.get_latest_timestamp() for mea in list_mea]
            
            try: self._spectraPlotter.plot_spectra(list_mea[0],list_mea_id[0])
            except Exception as e: (f'_auto_update_RM: {e}')
            
            for callback in self._list_callback_mea:
                try: callback()
                except Exception as e: (f'_auto_update_RM: {e}')
            
    def _auto_update_Unit(self):
        """
        Automatically updates the MappingMeasurementUnit in the other classes.
        """
        while True:
            self._flg_update_unit.wait()
            self._flg_update_unit.clear()
            
            list_unit = self._dataHub.get_selected_MappingUnit()
            list_unitid = [unit.get_unit_id() for unit in list_unit]
            list_unitname = [unit.get_unit_name() for unit in list_unit]
            
            try:
                self._heatmapPlotter.set_plotOptions_selection(list_unitname[0])
            except Exception as e: (f'_auto_update_Unit: {e}')
            
            for callback in self._list_callback_unit:
                try: callback()
                except Exception as e: (f'_auto_update_Unit: {e}')
        

        
if __name__ == '__main__':
    root = tk.Tk()
    root.title('A2SSM Analyser')
    
    processor = mpp.Pool()
    app = A2SSM_analyser(root,processor)
    app.pack(fill='both',expand=True)
    
    app.init_extensions(root)
    
    root.mainloop()
    
    os._exit(0)