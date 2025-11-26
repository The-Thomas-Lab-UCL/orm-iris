"""
A class to act as an intermediary (abstraction) to transfer control and data between the main app (controller) and the extensions.
"""
import sys
import os

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\library')
    EXT_DIR = os.path.abspath(r'.\extensions')
    sys.path.append(os.path.dirname(SCRIPT_DIR))
    sys.path.append(os.path.dirname(EXT_DIR))
    
from PIL import Image
import numpy as np
import threading

from iris.utils.general import *

# Basic controllers
from iris.controllers.class_camera_controller import Class_CameraController
from iris.controllers.class_xy_stage_controller import Class_XYController
from iris.controllers.class_z_stage_controller import Class_ZController
from iris.controllers.class_spectrometer_controller import Class_SpectrometerController

# GUI controllers
from iris.gui.motion_video import Wdg_MotionController
from iris.gui.raman import Wdg_SpectrometerController
from iris.gui.hilvl_Raman import Wdg_HighLvlController_Raman
from iris.gui.hilvl_Brightfield import Frm_HighLvlController_Brightfield

# Data containers/managers
from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image, Wdg_DataHub_ImgCal

class Ext_DataIntermediary():
    """
    A class to act as an intermediary (abstraction) to transfer control and data
    between the main app (controller) and the extensions.
    """
    def __init__(
        self,
        # Basic controllers
        raman_controller: Class_SpectrometerController,
        camera_controller: Class_CameraController,
        xy_controller: Class_XYController,
        z_controller: Class_ZController,
        # GUI controllers
        frm_motion_controller: Wdg_MotionController,
        frm_raman_controller: Wdg_SpectrometerController,
        frm_highlvl_raman: Wdg_HighLvlController_Raman,
        frm_highlvl_brightfield: Frm_HighLvlController_Brightfield,
        # Data containers/managers
        frm_datahub_mapping: Wdg_DataHub_Mapping,
        frm_datahub_image: Wdg_DataHub_Image,
        frm_datahub_imgcal: Wdg_DataHub_ImgCal,
        ) -> None:
        """
        Initialise the intermediary class with the required controllers and GUI components.
        """
        # Basic controllers
        self.raman_controller = raman_controller
        self.camera_controller = camera_controller
        self.xy_controller = xy_controller
        self.z_controller = z_controller
        
        # GUI controllers
        self.frm_motion_controller = frm_motion_controller
        self.frm_raman_controller = frm_raman_controller
        self.frm_highlvl_raman = frm_highlvl_raman
        self.frm_highlvl_brightfield = frm_highlvl_brightfield
        
        # Data containers/managers
        self.frm_datahub_mapping = frm_datahub_mapping
        self.frm_datahub_image = frm_datahub_image
        self.frm_datahub_imgcal = frm_datahub_imgcal
        
    def get_spectrometer_controller(self) -> Class_SpectrometerController:
        """
        Get the Raman controller. Note that it is not recommended to control the
        spectrometer as it will interefere with the main app. The spectrometer can be
        controlled the GUI controller instead for most operations (raman controller gui).
        """
        return self.raman_controller
    
    def get_camera_controller(self) -> Class_CameraController:
        """
        Get the camera controller. Note that it is not recommended to control the
        camera as it will interefere with the main app. The the GUI controller can be
        controlled through the GUI controller instead for most operations (video motion controller gui).
        """
        return self.camera_controller
    
    def get_xy_controller(self) -> Class_XYController:
        """
        Get the XY stage controller. Note that it is not recommended to control the
        XY stage as it will interefere with the main app. The XY stage can be controlled
        through the GUI controller instead for most operations (video motion controller gui).
        """
        return self.xy_controller
    
    def get_z_controller(self) -> Class_ZController:
        """
        Get the Z stage controller. Note that it is not recommended to control the
        Z stage as it will interefere with the main app. The Z stage can be controlled
        through the GUI controller instead for most operations (video motion controller gui).
        """
        return self.z_controller
    
    def get_video_motion_controller_gui(self) -> Wdg_MotionController:
        """
        Get the motion controller GUI.
        """
        return self.frm_motion_controller
    
    def get_raman_controller_gui(self) -> Wdg_SpectrometerController:
        """
        Get the Raman controller GUI.
        """
        return self.frm_raman_controller
    
    def get_highlvl_raman_gui(self) -> Wdg_HighLvlController_Raman:
        """
        Get the high level Raman controller GUI.
        """
        return self.frm_highlvl_raman
    
    def get_highlvl_brightfield_gui(self) -> Frm_HighLvlController_Brightfield:
        """
        Get the high level brightfield controller GUI.
        """
        return self.frm_highlvl_brightfield
    
    def get_datahub_mapping_gui(self) -> Wdg_DataHub_Mapping:
        """
        Get the data hub mapping GUI.
        """
        return self.frm_datahub_mapping
    
    def get_datahub_image_gui(self) -> Wdg_DataHub_Image:
        """
        Get the data hub image GUI.
        """
        return self.frm_datahub_image
    
    def get_datahub_imgcal_gui(self) -> Wdg_DataHub_ImgCal:
        """
        Get the data hub image calibration GUI.
        """
        return self.frm_datahub_imgcal