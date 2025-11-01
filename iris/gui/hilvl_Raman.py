import os
from glob import glob

import multiprocessing as mp
import multiprocessing.pool as mpp

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
import queue
from typing import Callable, Literal
from enum import Enum

from copy import deepcopy
from uuid import uuid1

import numpy as np
import math
import random

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.utils.general import *

from iris.gui.motion_video import Wdg_MotionController
from iris.gui.raman import Wdg_SpectrometerController
from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping
# from iris.gui.dataHub_MeaImg import Frm_DataHub_Image, Frm_DataHub_ImgCal
from iris.gui.hilvl_coorGen import Frm_Treeview_MappingCoordinates, Frm_CoorGenerator

from iris.gui.submodules.heatmap_plotter_MeaRMap import Frm_MappingMeasurement_Plotter
# from iris.gui.submodules.image_tiling import Frm_HiLvlTiling

from iris.data.measurement_RamanMap import MeaRMap_Unit, MeaRMap_Hub, MeaRMap_Handler
from iris.data.measurement_Raman import MeaRaman,MeaRaman_Handler
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.multiprocessing.dataStreamer_StageCam import DataStreamer_StageCam
from iris.multiprocessing.dataStreamer_Raman import DataStreamer_Raman

# from iris.gui.image_calibration.plotter_heatmap_overlay import Frm_HeatmapOverlay

from iris.gui import AppRamanEnum, AppPlotEnum

class Enum_ScanMthd(Enum):
    """
    Enum for the scan options for the mapping measurement.
    
    Attributes:
        SNAKE (str): Snake scan option
        RASTER (str): Raster scan option
    """
    SNAKE = 'snake'
    RASTER = 'raster'

class Enum_ScanDir(Enum):
    """
    Enum for the scan direction options for the mapping measurement.
    
    Attributes:
        XDIR (str): X-direction scan option
        YDIR (str): Y-direction scan option
    """
    XDIR = 'x-direction'
    YDIR = 'y-direction'

class Frm_HighLvlController_Raman(tk.Frame):
    """
    A higher level controller ruling over the motion controller and raman spectroscopy controller.
    
    Houses the:
        1. Plot (auto-update)
        2. Mapping functionalities
        3. Raman spectroscopy save functions

    Args:
        tk (tkinter): tkinter library
    """
    def __init__(self,
                 parent:tk.Tk|tk.Frame|tk.LabelFrame|ttk.Notebook,
                 motion_controller:Wdg_MotionController,
                 stageHub:DataStreamer_StageCam,
                 raman_controller:Wdg_SpectrometerController,
                 ramanHub:DataStreamer_Raman,
                 dataHub_map:Wdg_DataHub_Mapping,
                #  dataHub_img:Frm_DataHub_Image,
                #  dataHub_imgcal:Frm_DataHub_ImgCal,
                 coorHub:List_MeaCoor_Hub,
                 frm_coorGen:Frm_CoorGenerator,
                 processor:mpp.Pool):
        """
        Initialises the higher level controller, which needs access to most (if not all)
        other modules used in the app

        Args:
            parent (tk.Tk): The parent widget
            motion_controller (Frm_MotionController): The stage and video controller for motion controls
            stageHub (stage_measurement_hub): The stage measurement hub for coordinate retrievals
            raman_controller (Frm_RamanSpectrometerController): The spectrometer controllers
            ramanHub (RamanMeasurementHub): The Raman measurement hub (NOT the DataHub!) for spectra retrievals
            dataHub_map (Frm_DataHub_Mapping): The mapping data hub
            dataHub_img (Frm_DataHub_Image): The image data hub
            dataHub_imgcal (Frm_DataHub_ImgCal): The image calibration data hub
            coorHub (MappingCoordinatesHub): The mapping coordinates hub
            frm_coorGen (sframe_CoorGenerator): The coordinate generator GUI
            processor (mpp.Pool): The multiprocessing pool
        """
        super().__init__(parent)
        self.processor = processor
        
    # >>> Measurement hubs setup <<<
        self._stageHub = stageHub
        self._ramanHub = ramanHub
        self._dataHub_map = dataHub_map
        # self._dataHub_img = dataHub_img
        # self._dataHub_imgcal = dataHub_imgcal
        self._coorHub = coorHub
        self._frm_coorGen = frm_coorGen
        
        # Add shortcuts to the frm_coorGen
        self._btn_perform_discreteMapping_single = self._frm_coorGen.add_shortcut(
            btn_label='Perform discrete mapping',
            command=self.perform_discreteMapping,)
        
        self._btn_perform_continuousMapping_single = self._frm_coorGen.add_shortcut(
            btn_label='Perform continuous mapping',
            command=self.perform_continuousMapping,
        )
        self._list_shortcut_widgets = [self._btn_perform_discreteMapping_single,self._btn_perform_continuousMapping_single]
        
    # >>> Controller initialisation <<<
        # To gain access to the other 2 controllers and data save manager
        self.motion_controller = motion_controller
        self.raman_controller = raman_controller
        self.save_manager_dot = MeaRaman_Handler()
        self._mappingHub_Handler = MeaRMap_Handler()
        
    # >>> Frame setup: top layout <<<
        notebook_main = ttk.Notebook(self)
        frm_mapping = tk.Frame(notebook_main)        # Houses the mapping controls
        frm_heatmap = tk.Frame(notebook_main)        # Houses the heatmap plotter
        frm_mappingoverlay = tk.Frame(notebook_main) # Houses the heatmap overlay plotter (on captured images)
        
        notebook_main.add(frm_mapping,text='Mapping parameters')
        notebook_main.add(frm_heatmap,text='Heatmap plotter')
        notebook_main.add(frm_mappingoverlay,text='Heatmap overlay plotter')
        
        # Status bar
        self.statbar = tk.Label(self,text = 'Initialising controls', 
                                bd=1, relief=tk.SUNKEN,anchor=tk.W)     # Status bar
        self.bg_colour = self.statbar.cget('background')    # Stores the default background colour
        
        # Packs the frames
        notebook_main.grid(row=0,column=0,sticky='nsew')
        self.statbar.grid(row=1,column=0,columnspan=2,sticky='sew')
        
        # Grid configurations
        self.grid_columnconfigure(0,weight=1)
        self.grid_columnconfigure(1,weight=1)
        self.grid_rowconfigure(0,weight=1)
        self.grid_rowconfigure(1,weight=1)
        
        # Internal frams grid configurations
        
    # >>> Frame setup: Notebook (heatmap and mapping controls) <<<
        # Setup: Heatmap plotter
        self.mdl_plot = Frm_MappingMeasurement_Plotter(frm_heatmap,self._dataHub_map.get_MappingHub(),
                                                       figsize_pxl=AppPlotEnum.PLT_MAP_SIZE_PIXEL.value)
        self.mdl_plot.grid(row=0,column=0)
        
        # Setup: Mapping controls
        self._frm_coorHub_treeview = Frm_Treeview_MappingCoordinates(
            master=frm_mapping,mappingCoorHub=self._coorHub)
        
        self._notebook_mapping = ttk.Notebook(frm_mapping)
        self._sfrm_mapping = tk.Frame(self._notebook_mapping)   # Houses the multi mapping controls
        sfrm_mapping_scrambler = tk.Frame(self._notebook_mapping)     # Houses the mapping scrambler options
        
        self._notebook_mapping.add(self._sfrm_mapping,text='Mapping measurement')
        self._notebook_mapping.add(sfrm_mapping_scrambler,text='Mapping coordinats scrambler')
        
        # Packs the frames
        self._frm_coorHub_treeview.grid(row=0,column=0,sticky='nsew')
        self._notebook_mapping.grid(row=1,column=0,sticky='nsew')
        
        # Grid configurations
        frm_mapping.grid_rowconfigure(0,weight=1)
        frm_mapping.grid_rowconfigure(1,weight=1)
        frm_mapping.grid_columnconfigure(0,weight=1)
                
    # >>> Mapping widgets and parameters setups <<<
        # Parameters
        self._flg_meaCancelled = False # Flag to indicate if the measurement was cancelled
        
        # Storage
        self.measurement_data_0D:MeaRaman = None                # Measurement data class for each measurements
        self.measurement_data_2D_unit:MeaRMap_Unit = None    # Measurement data class for the 2D mapping

    # >>> Multi-mapping sub frames setup <<<<
        ssfrm_tree_mapping_multi = tk.Frame(self._sfrm_mapping)
        self._ssfrm_mapping_options = tk.LabelFrame(self._sfrm_mapping,text='Mapping options')
        self._ssfrm_scan_options = tk.LabelFrame(self._sfrm_mapping,text='Scan options')
        
        # > Grids <
        ssfrm_tree_mapping_multi.grid(row=0,column=0,sticky='nsew')
        self._ssfrm_mapping_options.grid(row=1,column=0,sticky='nsew')
        self._ssfrm_scan_options.grid(row=2,column=0,sticky='nsew')

        # >> Mapping options widgets setup <<
        self._btn_perform_discreteMapping_multi = tk.Button(self._ssfrm_mapping_options,text='Perform multi-discrete mapping\nof the selected coordinates',
                                                            command=lambda: self.perform_discreteMapping_multi())
        self._btn_perform_continuousMapping_multi = tk.Button(self._ssfrm_mapping_options,text='Perform multi-continuous mapping\nof the selected coordinates',
                                                                command=lambda: self.perform_continuousMapping_multi())
        self._init_scanoptions()
                
        self._btn_perform_discreteMapping_multi.grid(row=4,column=0,sticky='ew',pady=(5,0))
        self._btn_perform_continuousMapping_multi.grid(row=4,column=1,sticky='ew',pady=(5,0))
        
    # >>> Mapping scrambler options setup <<<
        self._bool_randomise_mappingCoor = tk.BooleanVar(value=False)
        chk_randomise_mappingCoor = tk.Checkbutton(sfrm_mapping_scrambler,text='Randomise mapping coordinates',
            variable=self._bool_randomise_mappingCoor)
        self._bool_jump_mappingCoor = tk.BooleanVar(value=False)
        chk_jump_mappingCoor = tk.Checkbutton(sfrm_mapping_scrambler,text='Jump mapping coordinates',
            variable=self._bool_jump_mappingCoor)
        lbl_jump_mappingCoor = tk.Label(sfrm_mapping_scrambler,text='Number of "jumped" measurements:')
        self._spin_jump_mappingCoor = tk.Spinbox(sfrm_mapping_scrambler,from_=0,to=1000,increment=1)
        
        row=0
        chk_randomise_mappingCoor.grid(row=0,column=0,sticky='w'); row+=1
        chk_jump_mappingCoor.grid(row=1,column=0,sticky='w'); row+=1
        lbl_jump_mappingCoor.grid(row=2,column=0,sticky='w'); row+=1
        self._spin_jump_mappingCoor.grid(row=3,column=0,sticky='w'); row+=1
        
        [sfrm_mapping_scrambler.grid_rowconfigure(i,weight=0) for i in range(row)]
        sfrm_mapping_scrambler.grid_columnconfigure(0,weight=1)
        
    # >>> Overlay heatmap plotter setup <<<
        # Heatmap plotter widgets setup
        # self._frm_heatmapOverlay = Frm_HeatmapOverlay(
        #     master=frm_mappingoverlay,
        #     processor=self.processor,
        #     mappingHub=self._dataHub_map.get_MappingHub(),
        #     imghub_getter=self._dataHub_img.get_ImageMeasurement_Hub,
        #     dataHub_imgcal=self._dataHub_imgcal,
        #     figsize_pxl=AppPlotEnum.IMGCAL_IMG_SIZE.value
        # )
        
        # # Pack the widgets
        # self._frm_heatmapOverlay.grid(row=0, column=0)
        
    # >>> Controller widgets setup <<<
        self.status_update()
    
    def initialise(self):
        """
        Initialises the controller, loading the last mapping coordinates from the temporary folder.
        """
        pass
        
    def terminate(self):
        """
        Terminates the controller, saving the mapping coordinates to the temporary folder.
        """
        pass
    
    def _init_scanoptions(self):
        """
        Initialises the scan options for the mapping measurement.
        
        Returns:
            None
        """
        # Scan options using the radio buttons
        self._str_scanMethod = tk.StringVar(value=Enum_ScanMthd.SNAKE.value)

        for i, scan_opt in enumerate(Enum_ScanMthd):
            rb_scan_opt = tk.Radiobutton(self._ssfrm_scan_options, text=scan_opt.value.capitalize(),
                                        variable=self._str_scanMethod, value=scan_opt.value)
            rb_scan_opt.grid(row=0,column=i, sticky='w', padx=5, pady=5)

        self._str_scanDir = tk.StringVar(value=Enum_ScanDir.XDIR.value)
        for i, scan_dir in enumerate(Enum_ScanDir):
            rb_scan_dir = tk.Radiobutton(self._ssfrm_scan_options, text=scan_dir.value,
                                        variable=self._str_scanDir, value=scan_dir.value)
            rb_scan_dir.grid(row=1,column=i, sticky='w', padx=5, pady=5)
            
    def _generate_metadata_dict(self, map_method:Literal['discrete', 'continuous']) -> dict:
        """
        Generates extra metadata for the mapping measurement
        
        Returns:
            dict: The extra metadata
        """
        controller_ids = self.motion_controller.get_controller_identifiers()
        extra_metadata = {
            'camera_id': controller_ids[0],
            'xystage_id': controller_ids[1],
            'zstage_id': controller_ids[2],
            'mapping_method': map_method,
            'scan_method': self._str_scanMethod.get(),
            'scan_direction': self._str_scanDir.get(),
            'scramble_random': self._bool_randomise_mappingCoor.get(),
            'scramble_jump': self._bool_jump_mappingCoor.get(),
        }
        return extra_metadata
            
    def get_mappingUnit_data(self) -> MeaRMap_Unit:
        """
        Gets the mapping data from the controller
        
        Returns:
            MappingMeasurement_Hub: The mapping data
        """
        return self.measurement_data_2D_unit
    
    def _map_check_coor_min_max(self,mapping_coor:list):
        """
        Checks if the coordinates are within the minimum and maximum limits
        
        Args:
            mapping_coor (list): The list of coordinates to be checked, should be in the format of [(x1,y1,z1),(x2,y2,z2),...]
        
        Returns:
            bool: True if the coordinates are within the limits
        """
        self.status_update('Checking the coordinates',bg_colour='yellow')
        # Input Validation:
        if not all(len(coord) == 3 for coord in mapping_coor):  # Check for 3D points
            raise ValueError("Input must be a list of 3D coordinates (x, y, z).")
        
        list_x = [float(coor[0]) for coor in mapping_coor]
        list_y = [float(coor[1]) for coor in mapping_coor]
        list_z = [float(coor[2]) for coor in mapping_coor]
        
        x_min = min(list_x)
        x_max = max(list_x)
        y_min = min(list_y)
        y_max = max(list_y)
        z_min = min(list_z)
        z_max = max(list_z)
        
        # try:
        #     self.motion_controller.go_to_coordinates(coor_x_mm=x_min,coor_y_mm=y_min,coor_z_mm=z_min)
        #     self.motion_controller.go_to_coordinates(coor_x_mm=x_max,coor_y_mm=y_max,coor_z_mm=z_max)
        #     self.status_update('Coordinates are OK',bg_colour='green')
        #     self.status_update(wait_time_s=2)
        #     return True
        # except:
        #     self.status_update('Coordinates are out of range',bg_colour='yellow')
        #     return False
        
        print('Mapping coordinate checks are not yet implemented')
        
        return True
    
    def _convertCoor_byScanOptions(self,mapping_coor:list=None,precision:int=4,ends_only:bool=False):
        """
        Converts coordinates to raster scan format.

        Args:
            mapping_coor (list): The list of coordinates to be checked, in the format [(x1, y1, z1), (x2, y2, z2), ...].
            precision (int): The number of decimal places to round the coordinates to. Defaults to 4.
            ends_only (bool): If True, only the ends of the coordinates for every line will be returned. Defaults to False.

        Returns:
            list: The coordinates reordered for the raster scan, or None if the input is None.
        """
        
        flg_snake = self._str_scanMethod.get() == Enum_ScanMthd.SNAKE.value
        dir_scan = self._str_scanDir.get()
        
        if not isinstance(mapping_coor, list) or len(mapping_coor) == 0:
            print('No coordinates to convert')
            return None

        mapping_coor = mapping_coor.copy()  # Create a copy to avoid modifying the original list
        
        # Sort the coordinates based on the scan direction
        group_coor = {}
        if dir_scan == Enum_ScanDir.YDIR.value:
            for coor in mapping_coor:
                x = round(coor[0], precision)
                if x not in group_coor:
                    group_coor[x] = []
                group_coor[x].append(coor)
            sorted_x = sorted(group_coor.keys())
            if flg_snake:
                for x in sorted_x[1::2]: group_coor[x].reverse()
            if ends_only: 
                final_coor =    [(x, coor[1], coor[2]) for x in sorted_x for coor in group_coor[x][:1]] + \
                                [(x, coor[1], coor[2]) for x in sorted_x for coor in group_coor[x][-1:]]
                final_coor = sorted(final_coor, key=lambda c: c[0])  # Sort by x-coordinate
            else: final_coor = [(x, coor[1], coor[2]) for x in sorted_x for coor in group_coor[x]]
        elif dir_scan == Enum_ScanDir.XDIR.value:
            for coor in mapping_coor:
                y = round(coor[1], precision)
                if y not in group_coor:
                    group_coor[y] = []
                group_coor[y].append(coor)
            sorted_y = sorted(group_coor.keys())
            if flg_snake:
                for y in sorted_y[1::2]: group_coor[y].reverse()
            if ends_only:
                final_coor =    [(coor[0], y, coor[2]) for y in sorted_y for coor in group_coor[y][:1]] + \
                                [(coor[0], y, coor[2]) for y in sorted_y for coor in group_coor[y][-1:]]
                final_coor = sorted(final_coor, key=lambda c: c[1])  # Sort by y-coordinate
            else: final_coor = [(coor[0], y, coor[2]) for y in sorted_y for coor in group_coor[y]]
        else:
            raise ValueError("Invalid scan direction. Use 'x-direction' or 'y-direction'.")
        return final_coor

    def _calculate_total_XYdistance(self,mapping_coor:list) -> float:
        """
        Calculates the total distance to be travelled for the mapping measurement 
        (only for the XY plane).
        
        Args:
            mapping_coor (list): The list of coordinates to be checked, in the format [(x1, y1, z1), (x2, y2, z2), ...].
        
        Returns:
            float: The total distance to be travelled
        """
        total_distance = 0
        for i in range(len(mapping_coor)-1):
            total_distance += math.sqrt((mapping_coor[i][0]-mapping_coor[i+1][0])**2+
                                        (mapping_coor[i][1]-mapping_coor[i+1][1])**2)
        return total_distance
    
    def _initialise_mapping_parameters(self, mappingHub:MeaRMap_Hub, mapping_coordinates_mm:MeaCoor_mm,
                                       mappingUnit_name:str|None=None) -> tuple[list,float,str]|bool:
        """
        Performs the initial checks prior to the mapping measurement:
            1. Running status check
            2. Coordinates check
            3.1. Mapping speed calculation
            3.2. Mapping speed modifier check
            4. Mapping ID request and check
        
        Args:
            mappingHub (MappingMeasurement_Hub): The mapping hub to store the mapping data
            mapping_coordinates_mm (MappingCoordinates): The mapping coordinate list.
            mappingUnit_name (str|None): The mapping ID. If None, the user will be prompted to enter it. Defaults to None.
            
        Returns:
            tuple: mapping coordinates, mapping speed, mapping ID
            
        NOTE:
            Assumes that the mapping coordinate will be followed as a pathway
        """
        # Running status check
        if self.raman_controller.get_running_status():
            messagebox.showwarning('Raman controller is running',
                'Please stop/finish the current measurement before starting')
            return False
        
        if not isinstance(mapping_coordinates_mm, MeaCoor_mm):
            self.status_update('Please do the coordinate generation first',bg_colour='yellow')
            return False
        
        list_coor_mm = mapping_coordinates_mm.mapping_coordinates
        
        # Check that the controller can reach the coordinates
        if not self._map_check_coor_min_max(list_coor_mm):
            self.status_update(message='The coordinates are out of range', bg_colour='yellow')
            return False
        
        # Calculates the required speed
        integration_time_ms = self.raman_controller.get_integration_time_ms()
        if not isinstance(integration_time_ms,(int,float)):
            self.status_update('Please enter a valid integration time',bg_colour='yellow')
            return False
        total_scan_time_sec = integration_time_ms * len(list_coor_mm) / 1e3
        total_distance_mm = self._calculate_total_XYdistance(list_coor_mm)
        mapping_speed_mmPerSec = abs(total_distance_mm/total_scan_time_sec)
        
        # Mapping speed modifier check
        if not isinstance(AppRamanEnum.CONTINUOUS_SPEED_MODIFIER.value, (int,float)) and not AppRamanEnum.CONTINUOUS_SPEED_MODIFIER.value > 0:
            messagebox.showerror('Error', f'The speed modifier {AppRamanEnum.CONTINUOUS_SPEED_MODIFIER.name}\
                in the config file must be a positive number. It is currently {AppRamanEnum.CONTINUOUS_SPEED_MODIFIER.value}')
            return False
        
        # Mapping ID request and check
        list_mappingUnit_names = list(mappingHub.get_dict_nameToID().keys())
        if mappingUnit_name is None and mapping_coordinates_mm.mappingUnit_name != '':
            mappingUnit_name = mapping_coordinates_mm.mappingUnit_name
        while mappingUnit_name is None:
            mappingUnit_name = messagebox_request_input('Mapping ID','Enter the ID for the mapping measurement:')
            if mappingUnit_name == '' or not isinstance(mappingUnit_name,str) or mappingUnit_name in list_mappingUnit_names:
                retry = messagebox.askretrycancel('Error',"Invalid 'mappingUnit name'. The name cannot be empty or already exist. Please try again.")
                if not retry: return False
                mappingUnit_name = None
            else: break
        
        return (list_coor_mm, mapping_speed_mmPerSec, mappingUnit_name)
        
        
    def _disable_mapping_widgets(self):
        """
        Disables the mapping widgets
        """
        widgets = get_all_widgets(self._ssfrm_mapping_options)
        widgets.extend(self._list_shortcut_widgets)  # Include the shortcut buttons
        for widget in widgets:
            if isinstance(widget, (tk.Button, ttk.Combobox, tk.Entry, tk.Spinbox)):
                widget.configure(state='disabled')
            
    def _enable_mapping_widgets(self):
        """
        Enables the mapping widgets
        """
        widgets = get_all_widgets(self._ssfrm_mapping_options)
        widgets.extend(self._list_shortcut_widgets)  # Include the shortcut buttons
        for widget in widgets:
            if isinstance(widget, (tk.Button, ttk.Combobox, tk.Entry, tk.Spinbox)):
                widget.configure(state='normal')
    
    def abort_mapping_run(self, btn:tk.Button, text:str, command:Callable):
        """
        Aborts the mapping run and resets the controller status

        Args:
            btn (tk.Button): The button to be reset
            text (str): The text to be reset
            command (Callable): The command to be reset
        """
        self.flg_isrunning_mapping = False
        self.status_update(message='Aborting run',bg_colour='red')
        
        self.after(10,btn.configure(state='active',text=text,command=command,bg=self.bg_colour))
    
    def reset_mapping_widgets(self,btn:tk.Button,text:str,command:Callable):
        """
        Resets the mapping widgets after a mapping run

        Args:
            btn (tk.Button): The button to be reset
            text (str): The text to be reset
            command (Callable): The command to be reset
        """
        self._enable_mapping_widgets()
        self.motion_controller.video_initialise()
        btn.configure(text=text,command=command,bg=self.bg_colour)
        self.status_update()
    
    def _scramble_mapping_coordinates(self, list_mappingCoor:list, mode:Literal['discrete','continuous']) -> list:
        """
        Scrambles the mapping coordinates based on the selected mode.
        
        Args:
            list_mappingCoor (list): The list of coordinates to be scrambled
            mode (str): The mode to scramble the coordinates. Can be 'discrete' or 'continuous'.
            
        Returns:
            list: The scrambled coordinates
            
        Raises:
            ValueError: If the jump value is not a positive integer
            
        NOTE:
            The 'discrete' mode will scramble the coordinates randomly, while the 'continuous' mode will always group the
            start and end coordinates of the lines together.
        """
        list_init = list_mappingCoor.copy()
        if mode == 'continuous':
            # Convert the coordinates to a list of two coordinates (assuming that the coordinates are in pairs)
            list_temp = list_init.copy()
            list_init.clear()
            while len(list_temp)>0:
                list_init.append([list_temp.pop(0),list_temp.pop(0)])
                if len(list_temp)==1:
                    list_init.append([list_temp.pop(0),])
                    
        if self._bool_randomise_mappingCoor.get():
            random.shuffle(list_init)
        
        def list_remap_jump(data_list, skip_interval):
            """Remaps the list by skipping elements based on the skip_interval"""
            # Determine the actual 'step' size for slicing
            # A skip_interval of 0 means a step of 1 (every element)
            # A skip_interval of 1 means a step of 2 (every other element)
            # A skip_interval of N means a step of N+1 (every N+1th element)
            step = skip_interval + 1
            num_passes = step
            mapped_list = []
            n = len(data_list)
            for offset in range(num_passes):
                current_index = offset
                while current_index < n:
                    mapped_list.append(data_list[current_index])
                    current_index += step
            return mapped_list
        
        if self._bool_jump_mappingCoor.get():
            jump = self._spin_jump_mappingCoor.get()
            try:
                jump = int(jump)
                if jump < 0: raise ValueError
            except ValueError:
                raise ValueError("Jump value must be a positive integer")
            
            list_final = list_remap_jump(list_init, jump)
        else:
            list_final = list_init
            
        # Convert the coordinates back to the original format
        if mode == 'continuous':
            list_temp = list_final.copy()
            list_final.clear()
            while len(list_temp)>0:
                list_final.extend(list_temp.pop(0))
            
        print()
            
        return list_final
    
    @thread_assign
    def perform_discreteMapping(self,mapping_coordinates:MeaCoor_mm):
        """
        Performs a discrete mapping based on the information stored in the mapping method
        
        Args:
            mapping_coordinates (MappingCoordinates_mm): The mapping coordinates to be used for the mapping measurement.
        """
        def reset():
            self.reset_mapping_widgets(
                self._btn_perform_discreteMapping_single,
                'Perform discrete mapping',
                lambda: self.perform_discreteMapping(self._frm_coorGen.generate_current_mapping_coordinates())
            )
            
        # >>> Initial checks <<<
        # Disable the mapping widgets
        self._disable_mapping_widgets()
        
        ## Change the 'Perform discrete mapping' button into a stop button
        self.after(10,self._btn_perform_discreteMapping_single.configure(state='active',\
            text='STOP',command=lambda:self.abort_mapping_run(self._btn_perform_discreteMapping_single,\
            'Perform discrete mapping',lambda: self.perform_discreteMapping(self._frm_coorGen.generate_current_mapping_coordinates())),bg='red'))
        
        # Check if the raman controller is currently running
        mapping_hub = self._dataHub_map.get_MappingHub()
        result = self._initialise_mapping_parameters(mappingHub=mapping_hub,mapping_coordinates_mm=mapping_coordinates)
        if not result: reset(); return
        list_coors,_,unit_name = result
        list_coors = self._convertCoor_byScanOptions(list_coors)
        
        try:
            self._perform_discreteMapping(
                mapping_hub=mapping_hub,
                mapping_coordinates=list_coors,
                unit_name=unit_name
            )
        except Exception as e:
            messagebox.showerror('Error',f"Failed to perform mapping: {e}")
            self.status_update('Error in mapping measurement',bg_colour='red')
            self._dataHub_map.update_tree()
            return
        
        messagebox.showinfo('Mapping measurement complete','The mapping measurement is complete and added to the data hub')
        reset()
        
    @thread_assign
    def perform_discreteMapping_multi(self):
        """
        Performs multiple discrete mapping based on the information stored in the dictionary
        """
        def reset():
            self.reset_mapping_widgets(self._btn_perform_discreteMapping_multi,'Perform multi-discrete mapping\nof the selected coordinates',self.perform_discreteMapping_multi)
        # >>> Initial checks <<<
        # Disable the mapping widgets
        self._disable_mapping_widgets()
        
        ## Change the 'Perform discrete mapping' button into a stop button
        self.after(10,self._btn_perform_discreteMapping_multi.configure(state='active',\
            text='STOP',command=lambda:self.abort_mapping_run(self._btn_perform_discreteMapping_multi,\
            'Perform multi-discrete mapping\nof the selected coordinates',self.perform_discreteMapping_multi),bg='red'))
        
        # Check if the raman controller is currently running
        self.flg_isrunning_mapping = True
        mapping_hub = self._dataHub_map.get_MappingHub()
        
        list_sel_mapCoor = self._frm_coorHub_treeview.get_selected_mappingCoor(flg_message=True)
        if len(list_sel_mapCoor) == 0: reset(); return
        
        while len(list_sel_mapCoor)>0:
            mapCoor = list_sel_mapCoor.pop(0)
            mappingUnit_name = mapCoor.mappingUnit_name
            mapping_coordinates = mapCoor
            
            if not self.flg_isrunning_mapping: break
            
            result = self._initialise_mapping_parameters(mapping_hub,mapping_coordinates,mappingUnit_name)
            if not result: reset(); return
            mapping_coordinates,_,unit_name = result
            mapping_coordinates = self._convertCoor_byScanOptions(mapping_coordinates)
            
            try:
                self._perform_discreteMapping(
                    mapping_hub=mapping_hub,
                    mapping_coordinates=mapping_coordinates,
                    unit_name=unit_name
                )
            except Exception as e:
                messagebox.showerror('Error',f"Failed to perform mapping: {e}")
                self.status_update('Error in mapping measurement',bg_colour='red')
                self._dataHub_map.update_tree()
                break
            
            if not self._flg_meaCancelled: self._coorHub.remove_mappingCoor(mappingUnit_name)
            
            self.status_update('Mapping measurement complete')
            
        messagebox.showinfo('Mapping measurement complete','The mapping measurement is complete and added to the data hub')
        reset()
        
    def _perform_discreteMapping(self, mapping_hub:MeaRMap_Hub,mapping_coordinates:list, unit_name:str):
        """
        Performs the mapping with the main coordinates stored in the mapping methods:
            1. Checks if the coordinates for mapping is ready
            2. Checks if background is measured
            3. Prepares the queue for mapping
            4. Saves the background
            5. Prepare the mapping_measurement_data class instance to store the measurements
            6. Initialise the plot module
            7. Initialise the loop and its parameter, to stop immediately if required
            8. Performs the mapping loop
            8.1. Loads the coordinate one at a time and go there
            8.2. Wait for the motors to arrive, then, performs a multi-measurement, and plot it (multi-threading for plotting)
            8.3. offload the measurements into the measurement_data along with the plot queue, requesting it to be plot immediately (also multithreading)
            9. Once finished: Resets the controllers status and let the user know

        Args:
            mapping_hub (MappingMeasurement_Hub): The mapping hub to store the mapping data
            mapping_coordinates (list): The list of coordinates to be checked, in the format [(x1, y1, z1), (x2, y2, z2), ...].
            unit_name (str): The name for the mapping measurement
            
        """
        
    # >>> Initialisations <<<
        # Generate the extra metadata for the mapping measurement
        extra_metadata = self._generate_metadata_dict('discrete')
        
        # Initialise the mapping measurement data class
        self.measurement_data_2D_unit = MeaRMap_Unit(unit_name, extra_metadata=extra_metadata)
        self._dataHub_map.append_MappingUnit(self.measurement_data_2D_unit)
        
        # Scramble the mapping coordinates if requested
        mapping_coordinates = self._scramble_mapping_coordinates(mapping_coordinates,'discrete')
        
        # Set up a flag to abort the mapping measurement if needed
        self.flg_isrunning_mapping = True
        
        # Perform the mapping measurement itself
        thread_plot = self._scan_discrete(mapping_coordinates)
        
        # Update the data hub tree view and request to save the data
        self._dataHub_map.update_tree()
        
    def measurement_autosaver_discrete(self,mapping_unit:MeaRMap_Unit,flg_isrunning:threading.Event
                              ,queue_measurement:queue.Queue):
        """
        A function to automatically grabs the measurement data form the
        measurement queue and stores it in the storage class.
        
        Args:
            mapping_unit (MappingMeasurement_Unit): The mapping unit to store the measurement data
            flg_isrunning (threading.Event): The flag to stop the measurement
            queue_measurement (queue.Queue): The queue to store the measurement data
        """
        while flg_isrunning.is_set() or not queue_measurement.empty():
            # Results is returned from the raman controller frame in the form of
            # a tuple: (timestamp, raman_measurement)
            try:
                result=queue_measurement.get(timeout=0.05)
            except queue.Empty: continue
            except Exception as e: print('Error in autosaver:',e)
            
            try:
                timestamp_mea,coor,measurement = result
                
                timestamp_mea:int
                measurement:MeaRaman
                
                measurement.check_uptodate(autoupdate=True)
                mapping_unit.append_ramanmeasurement_data(
                    timestamp=timestamp_mea,
                    coor=coor,
                    measurement=measurement
                )
            except Exception as e:
                print('Error in autosaver:',e)
                self.status_update('Error in autosaver',bg_colour='red')
    
    def _scan_discrete(self, mapping_coordinates:list):
        total_coordinates = len(mapping_coordinates)  # Total number of coordinates
        list_time_estimation = []   # List to store the time estimation
        # thread_save = threading.Thread()
        thread_plot = threading.Thread()
        self.motion_controller.video_terminate()
        
        # > Prep the autosaver function
        flg_isrunning_autosaver = threading.Event()
        flg_isrunning_autosaver.set()
        queue_measurement = queue.Queue()
        thread_autosaver = threading.Thread(target=self.measurement_autosaver_discrete,kwargs={
            'mapping_unit':self.measurement_data_2D_unit,
            'flg_isrunning':flg_isrunning_autosaver,
            'queue_measurement':queue_measurement
        })
        thread_autosaver.start()
        
        unit_name = self.measurement_data_2D_unit.get_unit_name()
        thread_offload = self._frm_coorHub_treeview.offload_mappingCoor(unit_name,mapping_coordinates,0)
        
        # Go through all the coordinates
        self.status_update('Performing mapping: 1 of {}'.format(total_coordinates),bg_colour='yellow')
        self.motion_controller.disable_controls()
        retry_flag = False
        self._flg_meaCancelled = False
        i=0
        while i < len(mapping_coordinates):
            coor = mapping_coordinates[i]
            try:
                # Wait for the previous batch processing to finish
                q_size = queue_measurement.qsize()
                if q_size > AppRamanEnum.CONTINUOUS_MEASUREMENT_BUFFER_SIZE.value:
                    while not queue_measurement.empty():
                        print(f'Measurement buffer full:\nAdjust [APP - RAMAN MEASUREMENT CONTROLLER] "continuous_measurement_buffer_size"\nin the config.ini file to adjust the buffer size')
                        self.status_update(f'Measurement buffer full: Processing previous measurements {q_size} remaining',bg_colour='yellow')
                        time.sleep(0.1)
                        if queue_measurement.qsize() < q_size: q_size = queue_measurement.qsize(); continue
                            
                        queue_measurement_new = queue.Queue()
                        self.init_measurement_autosaver(
                            mapping_unit=self.measurement_data_2D_unit,
                            flg_isrunning=flg_isrunning_autosaver,
                            q_measurement_old=queue_measurement,
                            q_measurement_new=queue_measurement_new,
                            mode='discrete',
                            thread_autosaver=thread_autosaver,
                        )
                        queue_measurement = queue_measurement_new                    
                
                # Starts a timer
                time_0start = time.time()
                
                if not self.flg_isrunning_mapping: break   # Stops the measurement immediately when required.
                if i%AppRamanEnum.AUTOSAVE_FREQ_DISCRETE.value == 0 and i > 0 and not thread_offload.is_alive():
                    thread_offload = self._frm_coorHub_treeview.offload_mappingCoor(unit_name,mapping_coordinates,i+1)
                
                # Go to the requested coordinates
                thread_movement = threading.Thread(target=self.motion_controller.go_to_coordinates,kwargs=({
                    'coor_x_mm': float(coor[0]),
                    'coor_y_mm': float(coor[1]),
                    'coor_z_mm': float(coor[2]),
                    'override_controls': True,
                    }))
                thread_movement.start()
                thread_movement.join()
                
                # Check if the target is reached and retry the coordinate if not
                if not self.motion_controller.isontarget_gotocoor() and not retry_flag:
                    retry_flag = True
                    print('Target coordinate not reached, retrying once')
                    continue
                retry_flag = False
                
                timestamp = get_timestamp_us_int()
                
                time_1motion = time.time()
                
                # Performs the multi-acquisition measurement
                thread_measurement:threading.Thread=\
                    self.raman_controller.perform_single_measurement(widget_override=True,accum='single')
                # Wait for the measurement to be done and obtain the values form the queue
                thread_measurement.join()
                
                # Retrieves the measurement results
                measurement_multi = self.raman_controller.get_single_measurement()
                
                # Send the measurement data to the autosaver
                queue_measurement.put((timestamp,coor,measurement_multi))
                
                time_2raman = time.time()
                time_total = time_2raman-time_0start
                time_raman = time_2raman-time_1motion
                time_motion = time_1motion-time_0start
                print('Total time: {}s = {}s Motion + {}s Raman\n'.format(time_total,time_motion,time_raman))
                
                # Estimate the time remaining
                list_time_estimation.append(time_total)
                num_points = 100
                if i < num_points:
                    time_permea = np.mean(list_time_estimation)
                else:
                    time_permea = np.mean(list_time_estimation[i-num_points:i])
                
                time_remaining = (total_coordinates-i-1)*time_permea
                tim_rem_hour = math.floor(time_remaining/3600)
                time_rem_min = math.floor((time_remaining-tim_rem_hour*3600)/60)
                time_rem_sec = math.floor(time_remaining%60)
                
                # Updates the data hub and status bar
                self._dataHub_map.update_tree()
                self.status_update('Performing mapping: {} of {}. Est. time rem.: {}h {}m {}s'\
                    .format(i+2,total_coordinates,tim_rem_hour,time_rem_min,time_rem_sec),bg_colour='yellow')
            except Exception as e:
                print('Error in mapping measurement:',e)
                self.status_update('Error in mapping measurement',bg_colour='red')
                
            i+=1
        
        self.motion_controller.enable_controls()
        flg_isrunning_autosaver.clear()   # Stops the autosaver thread
        thread_autosaver.join(timeout=1)
        
        self._frm_coorHub_treeview.delete_offload_mappingCoor(unit_name)  # Deletes the offloaded mapping coordinates
        if i != len(mapping_coordinates):
            ans = messagebox.askyesno('Save mapping coordinates','The measurement was stopped abruptly.\nDo you want to save the mapping coordinates?')
            if ans:
                if self._coorHub.search_mappingCoor(unit_name) != None: unit_name += '_remaining_{}'.format(get_timestamp_us_str())
                self._coorHub.append(MeaCoor_mm(unit_name,mapping_coordinates[i+1:]))
        
        self._flg_meaCancelled = True if i < len(mapping_coordinates) else False
        
        return thread_plot
        
        
        
        
    
    
    
    
    
    
        
        
        
        
    def measurement_autosaver_continuous(self,mapping_unit:MeaRMap_Unit,flg_isrunning:threading.Event
                              ,q_measurement:queue.Queue):
        """
        A function to automatically grabs the measurement data form the
        measurement queue and stores it in the storage class.
        
        Args:
            mapping_unit (MappingMeasurement_Unit): The mapping unit to store the measurement data
            flg_isrunning (threading.Event): The flag to stop the measurement
            q_measurement (queue.Queue): The queue to store the measurement data
        """
        while flg_isrunning.is_set() or not q_measurement.empty():
            # Results is returned from the raman controller frame in the form of
            # a tuple: (timestamp, raman_measurement)
            try:
                result=q_measurement.get(timeout=0.05)
            except queue.Empty: continue
            except Exception as e: print('Error in autosaver:',e)
            
            try:
                timestamp_mea,measurement = result
                
                timestamp_mea:int
                measurement:MeaRaman
                
                measurement.check_uptodate(autoupdate=True)
                coor = self._stageHub.get_coordinates_interpolate(timestamp_mea)
                mapping_unit.append_ramanmeasurement_data(
                    timestamp=timestamp_mea,
                    coor=coor,
                    measurement=measurement
                )
            except Exception as e:
                print('Error in autosaver:',e)
                self.status_update('Error in autosaver',bg_colour='red')
        
    def init_measurement_autosaver(self,mapping_unit:MeaRMap_Unit,flg_isrunning:threading.Event,q_measurement_old:queue.Queue,
        q_measurement_new:queue.Queue,mode:Literal['discrete','continuous'],thread_autosaver:threading.Thread|None=None)\
            -> tuple[threading.Thread,queue.Queue,threading.Event]:
        """
        Initialises the measurement autosaver thread. It will try to wait for the previous autosaver to finish
        or starts one if None is provided

        Args:
            mapping_unit (MappingMeasurement_Unit): The mapping unit to store the measurement data
            flg_isrunning (threading.Event): The flag to stop the measurement
            q_measurement_old (queue.Queue): The old queue to store the measurement data
            q_measurement_new (queue.Queue): The new queue to store the measurement data
            stageHub (stage_measurement_hub): The stage hub to get the coordinates
            flg_autosaver_ready (threading.Event): The flag to indicate that the autosaver is ready
            mode (str): The mode of the measurement, either 'discrete' or 'continuous'
            thread_autosaver (threading.Thread): autosaver thread from the previous measurement
            
        Returns:
            tuple[threading.Thread, queue.Queue, threading.Event]: The new autosaver thread, the new measurement queue,
                and the new autosaver ready flag
        """
        # > Try to finish the previous instance of the autosaver
        if isinstance(thread_autosaver,threading.Thread):
            # Stop the measurement autosaver and wait for it to finish
            flg_isrunning.clear()   # Stops the continuous measurement to allow the autosaver to finish
            thread_autosaver.join(timeout=1)     # Wait for the autosaver to finish
        
        # > Transfer the data from the previous queue to a new queue
        while not q_measurement_old.empty():
            # Transfer the data to a new queue
            q_measurement_new.put(q_measurement_old.get())
        
        # > Initialise the new autosaver thread
        flg_isrunning.set()     # Reset the flag to allow the new autosaver to start
        # Restart the autosaver thread
        if mode == 'discrete':
            thread_autosaver = threading.Thread(target=self.measurement_autosaver_discrete,kwargs=({
                'mapping_unit': mapping_unit,
                'flg_isrunning': flg_isrunning,
                'q_measurement': q_measurement_new,
                }))
        elif mode == 'continuous':
            thread_autosaver = threading.Thread(target=self.measurement_autosaver_continuous,kwargs=({
                'mapping_unit': mapping_unit,
                'flg_isrunning': flg_isrunning,
                'q_measurement': q_measurement_new,
                }))
        thread_autosaver.start()
        
        print(f'\n!!!!!!!!!!! New autosaver thread started !!!!!!!!!!!\n')
        
        return thread_autosaver
        
    @thread_assign
    def perform_continuousMapping(self,mapping_coordinates:MeaCoor_mm):
        """
        Performs the mapping with the main coordinates stored in the mapping methods
        """
        def reset():
            self.reset_mapping_widgets(
                self._btn_perform_continuousMapping_single,
                'Perform continuous mapping',
                lambda: self.perform_continuousMapping(self._frm_coorGen.generate_current_mapping_coordinates())
            )
        # >>> Initial checks <<<
        # Disable the mapping widgets
        self._disable_mapping_widgets()
        
        ## Change the 'Perform continuous mapping' button into a stop button
        self.after(10,self._btn_perform_continuousMapping_single.configure(state='active',\
            text='STOP',command=lambda:self.abort_mapping_run(self._btn_perform_continuousMapping_single,\
            'Perform continuous mapping',lambda: self.perform_continuousMapping(self._frm_coorGen.generate_current_mapping_coordinates())),bg='red'))
        
        # Rest of the checks
        mapping_hub = self._dataHub_map.get_MappingHub()
        result = self._initialise_mapping_parameters(mappingHub=mapping_hub,mapping_coordinates_mm=mapping_coordinates)
        if not result: reset(); return
        list_coors, mapping_speed_mmPerSec, unit_name = result
        
        try:
            self._perform_continuousMapping(
                mapping_hub=mapping_hub,
                mapping_coordinates=list_coors,
                mapping_speed_mmPerSec=mapping_speed_mmPerSec,
                unit_name=unit_name
            )
        except Exception as e:
            messagebox.showerror('Error',f"Failed to perform mapping: {e}")
            self.status_update('Error in mapping measurement',bg_colour='red')
            self._dataHub_map.update_tree()
            return
        
        messagebox.showinfo('Mapping measurement complete','The mapping measurement is complete and added to the data hub')
        reset()
    
    @thread_assign
    def perform_continuousMapping_multi(self):
        """
        Performs multiple continuous mapping based on the information stored in the dictionary
        """
        def reset():
            self.reset_mapping_widgets(self._btn_perform_continuousMapping_multi,'Perform multi-continuous mapping\nof the selected coordinates',self.perform_continuousMapping_multi)
        # >>> Initial checks <<<
        # Disable the mapping widgets
        self._disable_mapping_widgets()
        
        ## Change the 'Perform discrete mapping' button into a stop button
        self.after(10,self._btn_perform_continuousMapping_multi.configure(state='active',\
            text='STOP',command=lambda:self.abort_mapping_run(btn=self._btn_perform_continuousMapping_multi,\
            text='Perform multi-continuous mapping\nof the selected coordinates',command=self.perform_continuousMapping_multi),bg='red'))
        
        # Check if the raman controller is currently running
        self.flg_isrunning_mapping = True
        mapping_hub = self._dataHub_map.get_MappingHub()
        
        list_sel_mapCoor = self._frm_coorHub_treeview.get_selected_mappingCoor(flg_message=True)
        if len(list_sel_mapCoor) == 0: reset(); return
        
        while len(list_sel_mapCoor)>0:
            mapCoor = list_sel_mapCoor.pop(0)
            mappingUnit_name = mapCoor.mappingUnit_name
            mapping_coordinates = mapCoor
            
            if not self.flg_isrunning_mapping: break
            
            result = self._initialise_mapping_parameters(mapping_hub,mapping_coordinates,mappingUnit_name)
            if not result: reset(); return
            mapping_coordinates, mapping_speed_mmPerSec, unit_name = result
            
            try:
                self._perform_continuousMapping(
                    mapping_hub=mapping_hub,
                    mapping_coordinates=mapping_coordinates,
                    mapping_speed_mmPerSec=mapping_speed_mmPerSec,
                    unit_name=unit_name
                )
            except Exception as e:
                messagebox.showerror('Error',f"Failed to perform mapping: {e}")
                self.status_update('Error in mapping measurement',bg_colour='red')
                self._dataHub_map.update_tree()
                break
            
            if not self._flg_meaCancelled: self._coorHub.remove_mappingCoor(mappingUnit_name)
            
        messagebox.showinfo('Mapping measurement complete','The mapping measurement is complete and added to the data hub')
        reset()
    
    def _perform_continuousMapping(self, mapping_hub:MeaRMap_Hub,mapping_coordinates:list,
                                   mapping_speed_mmPerSec:float,unit_name:str):
        """
        Performs the mapping with the main coordinates stored in the mapping methods.
        
        Idea:
            1. Retrieve the mapping coordinates and take the ends of each lines
            2. Move the stage following these end points
            3. As the stage is moving, the Raman controller is continuously measuring the data
                (handled by the raman_controller_frame and the raman_measurement_hub)
            4. Similarly, the coordinates are stored continuously
                (handled by the stage_measurement_hub)
            5. Retrieve the Raman measurements and their coordinates, and store them in the mapping_measurement_data class
            
        Args:
            mapping_hub (MappingMeasurement_Hub): The mapping hub to store the mapping data
            mapping_coordinates (list): The list of coordinates to be checked, in the format [(x1, y1, z1), (x2, y2, z2), ...].
            mapping_speed_mmPerSec (float): The speed of the mapping in mm/s
            unit_name (str): The name for the mapping measurement
        """
        mapping_speed_rel = self.motion_controller.calculate_vel_relative(vel_xy_mmPerSec=mapping_speed_mmPerSec)
        mapping_speed_rel *= AppRamanEnum.CONTINUOUS_SPEED_MODIFIER.value
        
        mapping_coordinates_ends = self._convertCoor_byScanOptions(mapping_coordinates,ends_only=True)
        
    # >>> Initialisations <<<
        # Generate the extra metadata for the mapping measurement
        extra_metadata = self._generate_metadata_dict('continuous')
        
        # Initialise the mapping measurement data class
        self.measurement_data_2D_unit = MeaRMap_Unit(unit_name, extra_metadata=extra_metadata)
        self._dataHub_map.append_MappingUnit(self.measurement_data_2D_unit)
        
        # Scramble the mapping coordinates if requested
        mapping_coordinates_ends = self._scramble_mapping_coordinates(mapping_coordinates_ends,'continuous')
        
        # Set up a flag to abort the mapping measurement if needed
        self.flg_isrunning_mapping = True
        
        # Store the initial speed
        initial_speed_xy,initial_speed_z = self.motion_controller.get_VelocityParameters()
        
    # >>> Perform the mapping measurement <<<
        thread_plot = self._scan_continuous(mapping_coordinates_ends,mapping_speed_rel)
        
    # >>> Finalisations <<<
        self.status_update('Saving the measurement data',bg_colour='yellow')
        # Update the data hub tree view and request to save the data
        self._dataHub_map.update_tree()
        
        # Reset the speed
        self.motion_controller.set_vel_relative(vel_xy=initial_speed_xy,vel_z=initial_speed_z)
        
    def _scan_continuous(self, mapping_coordinates_ends:list,mapping_speed_rel:int):
        """
        Scans the mapping coordinates continuously based on the given scan coordinates.

        Args:
            mapping_coordinates_ends (list): List of scan coordinates (end coordinates of each scan lines)
            mapping_speed_rel (int): The relative speed to move between the coordinates
        """
        # >> Prep the continuous measurement <<
        # Prep the raman controller
        thread_continuous,queue_measurement,func_start_Raman,func_store_Raman,func_ignore_Raman,\
            func_stop_Raman = self.raman_controller.perform_ContinuousMeasurement_trigger()
        
        # Prep the threads for movement and measurement
        flg_isrunning_autosaver = threading.Event()    # clear to stop the continuous measurement
        flg_isrunning_autosaver.set()
        
    # > Prep for the loop Calculate the number of measurements to be done <
        total_coordinates = len(mapping_coordinates_ends)  # Total number of coordinates
        total_lines = int(total_coordinates/2)  # Total number of lines to be scanned
        self.status_update('Performing mapping line: 1 of {}'.format(total_lines),bg_colour='yellow')
        
    # > Start the auto-measurement retrieval <
        thread_movement = threading.Thread()
        thread_plot = threading.Thread()
        
        thread_autosaver = threading.Thread(target=self.measurement_autosaver_continuous,kwargs=({
            'mapping_unit': self.measurement_data_2D_unit,
            'flg_isrunning': flg_isrunning_autosaver,
            'q_measurement': queue_measurement
            }))
        thread_autosaver.start()
        unit_name = self.measurement_data_2D_unit.get_unit_name()
        thread_offload = self._frm_coorHub_treeview.offload_mappingCoor(unit_name,mapping_coordinates_ends,0)
        
        self.motion_controller.video_terminate()
        
    # >>> Perform the mapping measurement <<<
        # self.raman_controller.resume_auto_measurement()
        self.flg_isrunning_mapping = True
        time_start = time.time()
        self.motion_controller.disable_controls()
        retry_flag = False
        self._flg_meaCancelled = False
        i=0
        while i < len(mapping_coordinates_ends):
            coor = mapping_coordinates_ends[i]
            if not self.flg_isrunning_mapping: break   # Stops the measurement immediately when required.
            if i%AppRamanEnum.AUTOSAVE_FREQ_CONTINUOUS.value == 0 and i > 0 and not thread_offload.is_alive():
                thread_offload = self._frm_coorHub_treeview.offload_mappingCoor(unit_name,mapping_coordinates_ends,i+1)
            
            # >> Only perform the continuous measurement for x-rows <<
            # (i.e., skipped whenever moving between 1 y-coor to another)
            if i == 0: func_start_Raman()
            elif i%2 == 1:
                func_ignore_Raman()
                self.motion_controller.set_vel_relative(vel_xy=mapping_speed_rel)   # Set actual speed to move between x-coordinates
            else:
                func_store_Raman()
                self.motion_controller.set_vel_relative(vel_xy=100) # Set actual speed to move between x-coordinates
            
            # Wait for the previous batch processing to finish
            q_size = queue_measurement.qsize()
            flg_restart_Raman = False
            if q_size > AppRamanEnum.CONTINUOUS_MEASUREMENT_BUFFER_SIZE.value:
                while not queue_measurement.empty():
                    print(f'Measurement buffer full:\nAdjust [APP - RAMAN MEASUREMENT CONTROLLER] "continuous_measurement_buffer_size"\nin the config.ini file to adjust the buffer size')
                    self.status_update(f'Measurement buffer full: Processing previous measurements {q_size} remaining',bg_colour='yellow')
                    time.sleep(0.1)
                    if queue_measurement.qsize() < q_size: q_size = queue_measurement.qsize(); continue
                    
                    # Restart the continuous measurement
                    func_store_Raman()
                    func_stop_Raman()
                    thread_continuous.join()
                    flg_restart_Raman = True
                    
                    thread_continuous,queue_measurement_new,func_start_Raman,func_store_Raman,func_ignore_Raman,\
                        func_stop_Raman = self.raman_controller.perform_ContinuousMeasurement_trigger()
                        
                    self.init_measurement_autosaver(
                        mapping_unit=self.measurement_data_2D_unit,
                        flg_isrunning=flg_isrunning_autosaver,
                        q_measurement_old=queue_measurement,
                        q_measurement_new=queue_measurement_new,
                        mode='continuous',
                        thread_autosaver=thread_autosaver,
                    )
                    queue_measurement = queue_measurement_new
                if flg_restart_Raman: func_start_Raman()
                func_ignore_Raman()
                
                
            # Go to the requested coordinates
            thread_movement = threading.Thread(target=self.motion_controller.go_to_coordinates,kwargs=({
                'coor_x_mm': float(coor[0]),
                'coor_y_mm': float(coor[1]),
                'coor_z_mm': float(coor[2]),
                'override_controls': True,
                }))
            thread_movement.start()
            thread_movement.join()
            
            # Check if the target is reached and retry the coordinate if not
            if not self.motion_controller.isontarget_gotocoor() and not retry_flag:
                retry_flag = True
                print('Target coordinate not reached, retrying once')
                continue
            retry_flag = False
            
            # Status update
            self._dataHub_map.update_tree()
            time_elapsed = time.time()-time_start
            self.status_update('Performing mapping line: {} of {}. Elapsed time: {} min {} sec. Queue size: {}'\
                .format(int((i+1)/2),total_lines,math.floor(time_elapsed/60),math.floor(time_elapsed%60),
                        queue_measurement.qsize()),bg_colour='yellow')
            
            i+=1
        
        # Stop raman frame's continuous measurement
        func_store_Raman()
        func_stop_Raman()
        thread_continuous.join(timeout=1)
        
        # Stop the measurement autosaver and wait for it to finish
        self.motion_controller.enable_controls()
        flg_isrunning_autosaver.clear()   # Stops the continuous measurement
        thread_autosaver.join(timeout=1)     # Wait for the autosaver to finish
        
        self._frm_coorHub_treeview.delete_offload_mappingCoor(unit_name)  # Deletes the offloaded mapping coordinates
        if i != len(mapping_coordinates_ends):
            ans = messagebox.askyesno('Save mapping coordinates','The measurement was stopped abruptly.\nDo you want to save the mapping coordinates?')
            if ans:
                if self._coorHub.search_mappingCoor(unit_name) != None: unit_name += '_remaining_{}'.format(get_timestamp_us_str())
                self._coorHub.append(MeaCoor_mm(unit_name,mapping_coordinates_ends[i+1:]))
        
        self._flg_meaCancelled = True if i < len(mapping_coordinates_ends) else False
        
        return thread_plot
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    
    @thread_assign
    def status_update(self,message=None,bg_colour=None,wait_time_s:int=0):
        """
        To update the status bar at the bottom

        Args:
            message (str): The update message
            bg_colour (str, optional): Background colour. Defaults to 'default'.
            wait_time_s (int, optional): The time to wait before updating the status bar. Defaults to 0.
            
        Note:
            - The function should ideally be used in a separate thread if wait_time_s is used.
        """
        if wait_time_s > 0:
            time.sleep(wait_time_s)
        if bg_colour == None:
            bg_colour = self.bg_colour
        
        if message == None:
            message = 'Controller ready'
        
        try: self.after(10,self.statbar.configure(text=message,background=bg_colour))
        except: pass
