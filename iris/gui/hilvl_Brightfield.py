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

import PySide6.QtWidgets as qw
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QMouseEvent, QPixmap, QPen, QColor, QFont, QPainter
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer, QCoreApplication, QPointF, QSize, Qt

import multiprocessing as mp
import multiprocessing.pool as mpp

from PIL.Image import Image

from iris.utils.general import *

from iris.gui.motion_video import Wdg_MotionController

from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image, Wdg_DataHub_ImgCal
from iris.gui.hilvl_coorGen import Wdg_Hilvl_CoorGenerator

from iris.gui.image_calibration.plotter_heatmap_overlay import Wdg_HeatmapOverlay
from iris.gui.image_calibration.objective_calibration import Wdg_Calibration
from iris.gui.submodules.image_tiling import Wdg_HiLvlTiling
from iris.multiprocessing.dataStreamer_StageCam import DataStreamer_StageCam

from iris.data.measurement_coordinates import List_MeaCoor_Hub, MeaCoor_mm

from iris.gui import AppPlotEnum

from iris.resources.hilvl_brightfield_ui import Ui_Hilvl_Brightfield

class Hilvl_Brightfield_Design(Ui_Hilvl_Brightfield,qw.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)

class Wdg_HighLvlController_Brightfield(qw.QWidget):
    """
    The controller extension part. Handles image collection and calibration
    """
    def __init__(
        self,
        parent:qw.QWidget,
        processor:mpp.Pool,
        dataHub_map:Wdg_DataHub_Mapping,
        dataHub_img:Wdg_DataHub_Image,
        dataHub_imgcal:Wdg_DataHub_ImgCal,
        motion_controller:Wdg_MotionController,
        stageHub:DataStreamer_StageCam,
        coorHub:List_MeaCoor_Hub,
        main:bool=False):
        """
        Args:
            parent (tk parent): Parent widget
            processor (multiprocessing.pool.Pool): Processor pool
            dataHub_map (Wdg_DataHub_Mapping): Data hub to get the data
            dataHub_image (Wdg_DataHub_Image): Data hub for the image data
            dataHub_imgcal (Wdg_DataHub_ImgCal): Data hub for the image calibration data
            getter_coor (Callable[[],tuple[float,float,float]]): Function to get the stage coordinates
            getter_cameraImage (Callable[[],Image]): Function to get the camera image
            main (bool): Flag to indicate if this is the main script
        """
        assert isinstance(processor, mpp.Pool), 'Processor must be a multiprocessing.pool.Pool object'
        assert isinstance(dataHub_map, Wdg_DataHub_Mapping), 'DataHub must be a Wdg_DataHub object'
        assert isinstance(dataHub_img, Wdg_DataHub_Image), 'DataHub must be a Wdg_DataHub object'
        assert isinstance(dataHub_imgcal, Wdg_DataHub_ImgCal), 'DataHub must be a Wdg_DataHub object'
        assert isinstance(motion_controller, Wdg_MotionController), 'Motion controller must be a Wdg_MotionController object'
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
        
    # >>> Initialise the main widget <<<
        self._widget = Hilvl_Brightfield_Design(self)
        lyt = qw.QVBoxLayout()
        lyt.addWidget(self._widget)
        self.setLayout(lyt)
        wdg = self._widget
        
    # >>> Parameters <<<
        # GUI parameters
        self._showHints = AppPlotEnum.IMGCAL_SHOWHINTS.value
        
    # >>> Capture and calibration widgets <<<
        self._wdg_Calibration = Wdg_Calibration(
            parent=self,
            processor=self._processor,
            dataHub_img=self._dataHub_img,
            dataHub_imgcal=self._dataHub_imgcal,
            getter_coor=self._getter_coor,
            getter_cameraImage=self._getter_cameraImage,
        )
        wdg.lyt_holder_objSetup.addWidget(self._wdg_Calibration)
        
    # >> Overlay frame <<
        # Heatmap plotter widgets setup
        self._wdg_heatmapOverlay = Wdg_HeatmapOverlay(
            parent=self,
            processor=self._processor,
            mappingHub=self._dataHub_map.get_MappingHub(),
            imghub_getter=self._dataHub_img.get_ImageMeasurement_Hub,
            dataHub_imgcal=self._dataHub_imgcal,
            figsize_pxl=AppPlotEnum.IMGCAL_IMG_SIZE.value
        )
        wdg.lyt_heatmapOverlay.addWidget(self._wdg_heatmapOverlay)
        
    # >> Tiling frame <<
        tiling = Wdg_HiLvlTiling(
            parent=self,
            motion_controller=self._motion_ctrl,
            stageHub=self._stageHub,
            dataHub_img=self._dataHub_img,
            dataHub_imgcal=self._dataHub_imgcal,
            coorHub=self._coorHub,
            processor=self._processor
        )
        wdg.lyt_tiling.addWidget(tiling)
        

    
def test_hilvl_Brightfield_app(processor:mpp.Pool|None=None):
    """
    Generates a dummy high-level Raman application for testing purposes.
    """
    import sys
    
    from iris.gui.motion_video import generate_dummy_motion_controller
    from iris.gui.raman import generate_dummy_spectrometer_controller
    
    from iris.gui.hilvl_coorGen import generate_dummy_wdg_hilvlCoorGenerator
    
    if processor is None:
        processor = mpp.Pool()
    
    app = qw.QApplication([])
    main_window = qw.QMainWindow()
    wdg_main = qw.QWidget()
    main_window.setCentralWidget(wdg_main)
    layout = qw.QHBoxLayout()
    wdg_main.setLayout(layout)
    
    from iris.data.measurement_RamanMap import MeaRMap_Hub
    
    mappingHub = MeaRMap_Hub()
    dataHub = Wdg_DataHub_Mapping(wdg_main,mappingHub)
    
    wdg_motion_video = generate_dummy_motion_controller(wdg_main)
    datastreamer_motion = wdg_motion_video._stageHub
    wdg_raman = generate_dummy_spectrometer_controller(wdg_main,processor,dataHub)
    wdg_hilvlcoorgen = generate_dummy_wdg_hilvlCoorGenerator(wdg_main,datahub_map=dataHub)
    wdg_imgcal = Wdg_DataHub_ImgCal(wdg_main)
    
    hilvl_brightfield_app = Wdg_HighLvlController_Brightfield(
        parent=main_window,
        processor=processor,
        motion_controller=wdg_motion_video,
        stageHub=datastreamer_motion,
        dataHub_map=dataHub,
        dataHub_img=Wdg_DataHub_Image(wdg_main),
        dataHub_imgcal=wdg_imgcal,
        coorHub=wdg_hilvlcoorgen._coorHub,
        )
    
    layout.addWidget(wdg_motion_video)
    layout.addWidget(hilvl_brightfield_app)
    layout.addWidget(wdg_imgcal)
    layout.addWidget(wdg_raman)
    layout.addWidget(wdg_hilvlcoorgen)
    layout.addWidget(dataHub)
    
    wdg_hilvlcoorgen._coorHub.generate_dummy_data()
    
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    test_hilvl_Brightfield_app()