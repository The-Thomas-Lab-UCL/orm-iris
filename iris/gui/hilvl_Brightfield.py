"""
An extension to define the region of interest (ROI) for the mapping measurements.
It calibrates the ROI based on the stage's movement and the camera's image.

Extension ID: ROIDEF    # To be used as a prefix in global variables

Extension for:
    - main_controller.py
    - main_analyser.py
    
Note:
To set the calibration parameters, take all of them as they are:
        - stage coor shift/image coor shift (be it negative of positive)
        - the image flip/coor flip in reference to the mapping frame of reference will be are handled separately
            in the image_measurement object and the Frm_HeatmapOverlay object, when the flip is required
"""
import sys
import os
from typing import Callable

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

import tkinter as tk
from tkinter import ttk

import multiprocessing as mp
import multiprocessing.pool as mpp

from PIL.Image import Image

from iris.utils.general import *


from iris.gui.motion_video import Wdg_MotionController

from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping
from iris.gui.dataHub_MeaImg import Frm_DataHub_Image, Frm_DataHub_ImgCal
from iris.gui.hilvl_coorGen import Wdg_Hilvl_CoorGenerator

from iris.gui.image_calibration.plotter_heatmap_overlay import Frm_HeatmapOverlay
from iris.gui.image_calibration.capture_and_calibration import sFrm_CaptureAndCalibration
from iris.gui.submodules.image_tiling import Frm_HiLvlTiling
from iris.multiprocessing.dataStreamer_StageCam import DataStreamer_StageCam

from iris.data.measurement_coordinates import List_MeaCoor_Hub, MeaCoor_mm

from iris.gui import AppPlotEnum

class Frm_HighLvlController_Brightfield(tk.Frame):
    """
    The controller extension part. Handles image collection and calibration
    """
    def __init__(
        self,
        parent:tk.Tk|tk.Frame|tk.LabelFrame|ttk.Notebook,
        processor:mpp.Pool,
        dataHub_map:Wdg_DataHub_Mapping,
        dataHub_img:Frm_DataHub_Image,
        dataHub_imgcal:Frm_DataHub_ImgCal,
        motion_controller:Wdg_MotionController,
        stageHub:DataStreamer_StageCam,
        coorHub:List_MeaCoor_Hub,
        main:bool=False):
        """
        Args:
            parent (tk parent): Parent widget
            processor (multiprocessing.pool.Pool): Processor pool
            dataHub_map (Frm_DataHub): Data hub to get the data
            dataHub_image (Frm_DataHub_Image): Data hub for the image data
            dataHub_imgcal (Frm_DataHub_ImgCal): Data hub for the image calibration data
            getter_coor (Callable[[],tuple[float,float,float]]): Function to get the stage coordinates
            getter_cameraImage (Callable[[],Image]): Function to get the camera image
            main (bool): Flag to indicate if this is the main script
        """
        assert isinstance(processor, mpp.Pool), 'Processor must be a multiprocessing.pool.Pool object'
        assert isinstance(dataHub_map, Wdg_DataHub_Mapping), 'DataHub must be a Frm_DataHub object'
        assert isinstance(dataHub_img, Frm_DataHub_Image), 'DataHub must be a Frm_DataHub object'
        assert isinstance(dataHub_imgcal, Frm_DataHub_ImgCal), 'DataHub must be a Frm_DataHub object'
        assert isinstance(motion_controller, Wdg_MotionController), 'Motion controller must be a Frm_MotionController object'
        assert isinstance(stageHub, DataStreamer_StageCam), 'StageHub must be a stage_measurement_hub object'
        
        super().__init__(parent)
        # self.title('ROI Definition')
        self._processor = processor
        self._dataHub_map = dataHub_map
        self._dataHub_img = dataHub_img
        self._dataHub_imgcal = dataHub_imgcal
        self._motion_ctrl = motion_controller
        self._getter_coor = self._motion_ctrl.get_coordinates_closest_mm
        self._getter_cameraImage = self._motion_ctrl.get_current_image
        self._stageHub = stageHub
        self._coorHub = coorHub
        
    # >>> Parameters <<<
        # GUI parameters
        self._showHints = AppPlotEnum.IMGCAL_SHOWHINTS.value
        
    # >>> Initialise the subframes <<<
        # Notebooks to separate the calibration and the overlay functionalities
        notebook = ttk.Notebook(self)       # Notebook to separate the calibration and the overlay functionalities
        tfrm_controlpanel = tk.Frame(self)  # Top frame for the control panel (control and data)
        
        notebook.grid(row=0, column=0)
        tfrm_controlpanel.grid(row=0, column=1)
        
        tfrm_tiling = tk.Frame(notebook)         # Top frame for the tiling functionalities
        tfrm_overlay = tk.Frame(notebook)        # Top frame for the calibration functionalities
        tfrm_calibration = tk.Frame(notebook)    # Top frame for the overlay functionalities
        
        notebook.add(tfrm_tiling,text='Image capture and display')
        notebook.add(tfrm_overlay,text='Heatmap overlay')
        notebook.add(tfrm_calibration,text='Objective setup')
        
        # Subframes to put the other widgets in + a status bar
        frm_disp = tk.Frame(tfrm_calibration)
        frm_data = tk.Frame(tfrm_controlpanel)
        self._status_bar = tk.Label(self,anchor='w',relief='sunken',bd=1)
        self._statbar_bkg = self._status_bar.cget('background')
        
        frm_disp.grid(row=0, column=0,rowspan=2)
        frm_data.grid(row=0, column=1,sticky='ew')
        self._status_bar.grid(row=2, column=0, columnspan=2, sticky='ew')
        
    # >>> Capture and calibration widgets <<<
        self._frm_CaptureAndCalibration = sFrm_CaptureAndCalibration(
            master=frm_disp,
            top_level=self,
            processor=self._processor,
            dataHub_img=self._dataHub_img,
            dataHub_imgcal=self._dataHub_imgcal,
            getter_coor=self._getter_coor,
            getter_cameraImage=self._getter_cameraImage,
            update_statbar=self._update_status_bar
        )
        self._frm_CaptureAndCalibration.grid(row=0, column=0,sticky='ew')
        
    # >> Overlay frame <<
        # Heatmap plotter widgets setup
        self._frm_heatmapOverlay = Frm_HeatmapOverlay(
            master=tfrm_overlay,
            processor=self._processor,
            mappingHub=self._dataHub_map.get_MappingHub(),
            imghub_getter=self._dataHub_img.get_ImageMeasurement_Hub,
            dataHub_imgcal=self._dataHub_imgcal,
            figsize_pxl=AppPlotEnum.IMGCAL_IMG_SIZE.value
        )
        
        # Pack the widgets
        self._frm_heatmapOverlay.grid(row=0, column=0)
        
    # >> Tiling frame <<
        tiling = Frm_HiLvlTiling(
            master=tfrm_tiling,
            motion_controller=self._motion_ctrl,
            stageHub=self._stageHub,
            dataHub_img=self._dataHub_img,
            dataHub_imgcal=self._dataHub_imgcal,
            coorHub=self._coorHub,
            processor=self._processor
        )
        
        tiling.grid(row=0,column=0,sticky='nsew')
        
        tfrm_tiling.rowconfigure(0,weight=1)
        tfrm_tiling.columnconfigure(0,weight=1)
        
    # >> Others <<
        self._update_status_bar()
        
        if main: self.initialise()
    
    def initialise(self):
        pass
    
    @thread_assign
    def _update_status_bar(self, message:str='Ready', bkg:str|None=None, delay_sec:int|float=0):
        """
        Updates the status bar with a message
        
        Args:
            message (str): Message to be displayed. Default to 'Ready'
            bkg (str): Background colour of the status bar. Default is the default colour.
            delay_sec (int|float): Delay in seconds before the message is updated. Default is 0.
        """
        assert type(message) == str != '', 'Message must be a string'
        if isinstance(bkg, type(None)): bkg = self._statbar_bkg
        assert (type(delay_sec) == float or type(delay_sec) == int) and delay_sec >= 0,\
        'Delay must be a positive float or integer'
        
        if delay_sec > 0: time.sleep(delay_sec)
        
        if bkg == 'red': foreground = 'white'
        else: foreground = 'black'
        
        try:
            self.after(10,self._status_bar.config(text=message,background=bkg,foreground=foreground))
        except Exception as e: pass
        
def test():
    pass
    stageHub = None
    processor = mp.Pool()
    root = tk.Tk()
    data_save_manager_dummy = ControllerDataIntermediary_dummy(stageHub)
    toplevel = Frm_HighLvlController_Brightfield(root,processor,data_manager=data_save_manager_dummy)
    root.mainloop()

if __name__ == '__main__':
    test()