"""
A class to automatically take images and tile them into a single image
"""
import os

import multiprocessing.pool as mpp

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread

from PIL import Image
import numpy as np

from copy import deepcopy

from dataclasses import dataclass

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.utils.general import *

from iris.gui.motion_video import Wdg_MotionController
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image, Wdg_DataHub_ImgCal
from iris.gui.hilvl_coorGen import Wdg_Treeview_MappingCoordinates

from iris.gui.submodules.meaCoor_generator.ssfrm_tilemthd1_rect_around import tiling_method_rectxy_scan_constz_around_a_point as TileMethod

from iris.gui.image_calibration.Canvas_ROIdefinition import Canvas_Image_Annotations

from iris.data.measurement_image import MeaImg_Unit
from iris.data.calibration_objective import ImgMea_Cal
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.multiprocessing.dataStreamer_StageCam import DataStreamer_StageCam

from iris.gui import AppPlotEnum

from iris.resources.tiling_method_ui import Ui_tiling_method

class TilingMethod_Design(Ui_tiling_method, qw.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)

@dataclass
class ImageTiling_Params:
    shape:tuple[int,int]
    cropx_pixel:int
    cropy_pixel:int
    cropx_mm:float
    cropy_mm:float
    
    def check_validity(self) -> bool:
        """
        Check if the parameters are valid
        
        Returns:
            bool: True if valid, False otherwise
        """
        assert isinstance(self.shape, tuple) and len(self.shape) == 2, 'shape must be a tuple of length 2'
        assert all(isinstance(i, int) and i > 0 for i in self.shape), 'shape must be positive integers'
        assert isinstance(self.cropx_pixel, int) and self.cropx_pixel >= 0, 'cropx_pixel must be a non-negative integer'
        assert isinstance(self.cropy_pixel, int) and self.cropy_pixel >= 0, 'cropy_pixel must be a non-negative integer'
        assert isinstance(self.cropx_mm, (int, float)), 'cropx_mm must be a number'
        assert isinstance(self.cropy_mm, (int, float)), 'cropy_mm must be a number'
        return True    

class ImageProcessor_Worker(QObject):
    """
    Worker class to process images in a separate thread
    """
    sig_ret_image_processed = Signal(Image.Image)
    sig_gotocoor = Signal(tuple, threading.Event)
    sig_statbar_update = Signal(str)
    
    flg_stop_imgCapture = threading.Event()
    sig_midMea_error = Signal(str)  # Signal to indicate an error during mid-measurement
    sig_finished_msg = Signal(str, MeaImg_Unit)      # Signal to indicate the process has finished (even due to errors)
    
    msg_success = 'Image capture complete'
    msg_error = 'Error in ImageTiling_Worker: '
    
    def __init__(self, motion_controller:Wdg_MotionController):
        super().__init__()
        self._motion_ctrl = motion_controller
        
        self.sig_gotocoor.connect(self._motion_ctrl.get_goto_worker().work)
        
    @Slot(MeaImg_Unit,bool)
    def get_stitched_image(self, imgUnit:MeaImg_Unit, low_res:bool) -> None:
        """
        Get the stitched image from the ImageUnit
        
        Args:
            imgUnit (MeaImg_Unit): Image unit to process
            low_res (bool): Whether to get low resolution image
        """
        try:
            img_stitched = imgUnit.get_image_all_stitched(low_res=low_res)[0]
            self.sig_ret_image_processed.emit(img_stitched)
        except Exception as e:
            print('Error in get_stitched_image:', e)
    
    @Slot(MeaCoor_mm,MeaImg_Unit,ImageTiling_Params)
    def take_image(self, meaCoor_mm:MeaCoor_mm, imgUnit:MeaImg_Unit,
        tiling_params:ImageTiling_Params) -> None:
        """
        Take an image at the given measurement coordinates and store it in the given image unit.
        
        Args:
            meacoor (MeaCoor_mm): Measurement coordinates
            imgUnit (MeaImg_Unit): Image unit to store the captured image
            tiling_params (ImageTiling_Params): Parameters for tiling
        """
        flg_stop = self.flg_stop_imgCapture
        if flg_stop.is_set(): return
        
        # Check that all tiling parameters are valid
        try: tiling_params.check_validity()
        except Exception as e: 
            self.sig_midMea_error.emit(self.msg_error + f'Invalid tiling parameters: {e}')
            return
        
        # Extract tiling parameters
        shape = tiling_params.shape
        cropx_pixel = tiling_params.cropx_pixel
        cropy_pixel = tiling_params.cropy_pixel
        cropx_mm = tiling_params.cropx_mm
        cropy_mm = tiling_params.cropy_mm
        
        totalcoor = len(meaCoor_mm.mapping_coordinates)
        flg_stop.clear()
        self.sig_statbar_update.emit('Taking images: {} of {}'.format(1,totalcoor))
        
        msg = self.msg_success
        for i,coor in enumerate(meaCoor_mm.mapping_coordinates):
            x, y, z = coor
            if flg_stop.is_set():
                msg = self.msg_error + 'Image capture stopped by user'
                break
            
            flg_mvmt_done = threading.Event()
            self.sig_gotocoor.emit(coor, flg_mvmt_done)
            flg_mvmt_done.wait()
            
            img = self._motion_ctrl.get_current_image(wait_newimage=True)
            
            if not isinstance(img,Image.Image):
                self.sig_midMea_error.emit(self.msg_error + 'No image received from the controller')
                continue
            
            img = img.crop((cropx_pixel,cropy_pixel,shape[0]-cropx_pixel,shape[1]-cropy_pixel))
            
            imgUnit.add_measurement(
                    timestamp=get_timestamp_us_str(),
                    x_coor=x-cropx_mm,
                    y_coor=y-cropy_mm,
                    z_coor=z,
                    image=img
                )
                
            self.sig_statbar_update.emit('Taking images: {} of {}'.format(i+1,totalcoor))
            img = imgUnit.get_image_all_stitched(low_res=True)[0]
            self.sig_ret_image_processed.emit(img)
            
        self.sig_finished_msg.emit(msg, imgUnit)

class Wdg_HiLvlTiling(qw.QWidget):
    """
    A high level controller to take images, tile them into a single image, and save them 
    as an ImageMeasurement_Unit obj
    """
    sig_req_plot_imgunit = Signal()
    sig_req_takeImage = Signal()
    sig_update_combobox = Signal()
    
    sig_capture_img = Signal(MeaCoor_mm,MeaImg_Unit,ImageTiling_Params)
    
    
    def __init__(
        self,
        parent:qw.QWidget,
        motion_controller:Wdg_MotionController,
        stageHub:DataStreamer_StageCam,
        dataHub_img:Wdg_DataHub_Image,
        dataHub_imgcal:Wdg_DataHub_ImgCal,
        coorHub:List_MeaCoor_Hub,
        processor:mpp.Pool
        ) -> None:
        """
        Args:
            parent (qw.QWidget): Parent widget
            motion_controller (Wdg_MotionController): Motion controller object
            stageHub (DataStreamer_StageCam): Stage measurement hub
            dataHub_img (Wdg_DataHub_Image): Data hub for the image data
            dataHub_imgcal (Wdg_DataHub_ImgCal): Data hub for the image calibration data
            processor (multiprocessing.pool.Pool): Processor pool
        """
        assert isinstance(motion_controller, Wdg_MotionController), 'motion_controller must be a Frm_MotionController object'
        assert isinstance(stageHub, DataStreamer_StageCam), 'stageHub must be a stage_measurement_hub object'
        assert isinstance(dataHub_img, Wdg_DataHub_Image), 'dataHub_img must be a Frm_DataHub_Image object'
        assert isinstance(dataHub_imgcal, Wdg_DataHub_ImgCal), 'dataHub_imgcal must be a Frm_DataHub_ImgCal object'
        assert isinstance(processor, mpp.Pool), 'processor must be a multiprocessing.pool.Pool object'
        
        super().__init__(parent)
        self._motion_controller = motion_controller
        self._stageHub = stageHub
        self._dataHub_img = dataHub_img
        self._dataHub_imgcal = dataHub_imgcal
        self._coorHub = coorHub
        self._processor = processor
        
    # >>> Main parameters <<<
        self._getter_calibration = self._dataHub_imgcal.get_selected_calibration
        
    # >>> Top level layout <<<
        self._widget = TilingMethod_Design(self)
        lyt = qw.QVBoxLayout(self)
        lyt.addWidget(self._widget)
        self.setLayout(lyt)
        wdg = self._widget
        
        self._statbar = qw.QStatusBar(self)
        lyt.addWidget(self._statbar)
        
    # >>> Image frame <<<
        self._canvas_img = Canvas_Image_Annotations(
            parent=wdg,
            size_pixel=AppPlotEnum.IMGCAL_IMG_SIZE.value,
            )
        wdg.lyt_holder_img.addWidget(self._canvas_img)
        self._chk_lres = wdg.chk_lres
        
    # >>> Image control frame <<<
        self._list_imgunit_names = []
        self._img_shown:Image.Image|None = None
        self._combo_imgunits = wdg.combo_img
        
        self._combo_imgunits.currentIndexChanged.connect(self._plot_imgunit_combobox)
        self._btn_takeImages = wdg.btn_capture
        self._btn_takeImages_txt = self._btn_takeImages.text()
        self._btn_takeImages.clicked.connect(self._take_image)
        
    # >>> Coordinate generation frame <<<
        wdg_tree = Wdg_Treeview_MappingCoordinates(parent=self, mappingCoorHub=self._coorHub)
        wdg.lyt_holder_tree.addWidget(wdg_tree)
        
        self._coorgen = TileMethod(
            parent=self,
            motion_controller=self._motion_controller,
            coorHub=self._coorHub,
            tree_coor=wdg_tree,
            getter_cal=self._getter_calibration,
        )
        wdg.lyt_holder_controls.addWidget(self._coorgen)
        
    # >>> Worker setup <<<
        self._init_worker()
        
    def _init_worker(self):
        """
        Initialises the worker for the tiling and the image processing
        """
        # >>> Worker setup <<<
        self._thread = QThread()
        self._worker = ImageProcessor_Worker(self._motion_controller)
        self._worker.moveToThread(self._thread)
        self._thread.start()
        self.destroyed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._worker.deleteLater)
        
        self._worker.sig_ret_image_processed.connect(self._canvas_img.set_image)
        self.sig_req_plot_imgunit.connect(self._worker.get_stitched_image)
        
        # Other signal/connection setups
        self._dataHub_img.get_ImageMeasurement_Hub().add_observer(self.sig_update_combobox.emit)
        self.sig_update_combobox.connect(self._update_combobox)
        
        # Image capture signals
        self.sig_capture_img.connect(self._worker.take_image)
        self._worker.sig_finished_msg.connect(self._handle_imageCapture_finished)
        
    def _plot_imgunit_combobox(self):
        """
        Plot the ImageUnit selected in the combobox
        """
        try:
            self._combo_imgunits.setEnabled(False)
            
            imgUnit = self._get_selected_ImageUnit()
            if not isinstance(imgUnit,MeaImg_Unit): raise ValueError('No ImageUnit found')
            if not(imgUnit.check_measurement_exist() and imgUnit.check_calibration_exist()):
                raise ValueError('No image or calibration found')
            
            self.sig_req_plot_imgunit.emit()
            
            self._img_shown = imgUnit.get_image_all_stitched(low_res=self._chk_lres.isChecked())[0]
            self._canvas_img.set_image(self._img_shown)
        except Exception as e:
            qw.QMessageBox.warning(self,'Error in _plot_imgunit',str(e))
        finally:
            self._combo_imgunits.setEnabled(True)
        
    def _update_combobox(self):
        """
        Update the combobox with the ImageUnits stored in the ImageHub
        using the DataHubImage
        """
        self._combo_imgunits.blockSignals(True)
        self._combo_imgunits.setEnabled(False)
        
        hub = self._dataHub_img.get_ImageMeasurement_Hub()
        list_ids = hub.get_list_ImageUnit_ids()
        dict_idToName = hub.get_dict_IDtoName()
        list_names = [dict_idToName[id] for id in list_ids]
        
        # Only update when needed
        if list_names == self._list_imgunit_names: return
        
        current_name = self._combo_imgunits.currentText()
        
        self._list_imgunit_names = list_names.copy()
        self._combo_imgunits.clear()
        self._combo_imgunits.addItems(list_names)
        
        if current_name in list_names:
            self._combo_imgunits.setCurrentText(current_name)
        else:
            self._combo_imgunits.setCurrentIndex(0)
            self.sig_req_plot_imgunit.emit()
        
        self._combo_imgunits.setEnabled(True)
        self._combo_imgunits.blockSignals(False)
        
    @Slot(str, MeaImg_Unit)
    def _handle_imageCapture_finished(self, msg:str, imgUnit:MeaImg_Unit):
        """
        Handle the image capture finished signal
        
        Args:
            msg (str): Message to display
        """
        # Save the image unit into the hub
        self._dataHub_img.get_ImageMeasurement_Hub().append_ImageMeasurementUnit(imgUnit)
        
        # Handle the GUI
        self._statbar.showMessage(msg,5000)
        self.reset_imgCapture_button()
        self._motion_controller.enable_widgets()
        
        # Plot the image unit
        self._combo_imgunits.setCurrentText(imgUnit.get_IdName()[1])

    def reset_imgCapture_button(self):
        self._btn_takeImages.setText(self._btn_takeImages_txt)
        self._btn_takeImages.setStyleSheet('')
        
        try: self._btn_takeImages.clicked.disconnect()
        except: pass
        self._btn_takeImages.clicked.connect(self._take_image)
        
        self._motion_controller.enable_widgets()
        
    def _get_selected_ImageUnit(self) -> MeaImg_Unit:
        """
        Get the selected ImageUnit from the combobox

        Returns:
            ImageMeasurement_Unit: The selected ImageUnit
        """
        hub = self._dataHub_img.get_ImageMeasurement_Hub()
        dict_nameToID = hub.get_dict_nameToID()
        
        name = self._combo_imgunits.currentText()
        id = dict_nameToID[name]
        return hub.get_ImageMeasurementUnit(id)
        
    def _take_image(self):
        """
        Take images and tile them into a single image
        
        Args:
            flg_stop (threading.Event): Event to stop the function
        """
        # > Setup the button <
        try: self._btn_takeImages.clicked.disconnect()
        except: pass
        self._btn_takeImages.setText('STOP')
        self._btn_takeImages.setStyleSheet('background-color: red; color: white;')
        self._btn_takeImages.clicked.connect(self._worker.flg_stop_imgCapture.set)
        self._motion_controller.disable_widgets()
        
        # > Initial checks <
        cal = deepcopy(self._getter_calibration())
        if not isinstance(cal,ImgMea_Cal) or not cal.check_calibration_set():
            qw.QMessageBox.warning(self,'Error','No calibration found')
            self.reset_imgCapture_button()
            return
        
        try: result = self._coorgen.get_tiling_coordinates_mm_and_cropFactors_rel()
        except Exception as e:
            qw.QMessageBox.warning(self,'Error',f'Error generating coordinates: {e}')
            self.reset_imgCapture_button()
            return
        if result is None:
            qw.QMessageBox.warning(self,'Error','No coordinates generated')
            self.reset_imgCapture_button()
            return
        
        list_meaCoor_mm, cropx_ratio_red, cropy_ratio_red = result
        if not list_meaCoor_mm:
            qw.QMessageBox.warning(self,'Error','No coordinates found')
            self.reset_imgCapture_button()
            return
        
        # > Modify the calibration file
        img_test = self._motion_controller.get_current_image(wait_newimage=True)
        if not isinstance(img_test,Image.Image):
            qw.QMessageBox.warning(self,'Error','No image received from the controller')
            self.reset_imgCapture_button()
            return
        
        shape = img_test.size
        laserx = cal.laser_coor_x_mm
        lasery = cal.laser_coor_y_mm
        cropx_pixel = int(shape[0]*cropx_ratio_red)//2  # Cropped pixel x-distance from the edge (one of the two sides!!)
        cropy_pixel = int(shape[1]*cropy_ratio_red)//2  # Cropped pixel y-distance from the edge (one of the two sides!!)
        cropx_mm,cropy_mm = cal.convert_imgpt2stg(
            coor_img_pixel=np.array((cropx_pixel,cropy_pixel)),
            coor_stage_mm=np.array((0,0)))
        
        laserx -= cropx_mm
        lasery -= cropy_mm
        
        cal.set_calibration_params(
            scale_x_pixelPerMm=cal.scale_x_pixelPerMm,
            scale_y_pixelPerMm=cal.scale_y_pixelPerMm,
            laser_coor_x_mm=laserx,
            laser_coor_y_mm=lasery,
            rotation_rad=cal.rotation_rad,
            flip_y=cal.flip_y,
        )
        
        cal.id += f'_{cropx_ratio_red}X,{cropy_ratio_red}Ycrop'
        
        # > Prep the image storage <
        list_imgUnit = []
        for meaCoor_mm in list_meaCoor_mm:
            list_Hub_names = self._dataHub_img.get_ImageMeasurement_Hub().get_list_ImageUnit_ids()
            # Request for the names and check its validity
            while True:
                result = qw.QInputDialog.getText(
                    self,
                    'Image name',
                    'Enter the name of the image:',
                    qw.QLineEdit.Normal, # pyright: ignore[reportAttributeAccessIssue] ; Normal line edit exists
                    meaCoor_mm.mappingUnit_name
                )
                imgname, ok = result
                if not ok: # User cancelled
                    self.reset_imgCapture_button()
                    return
                if imgname in list_Hub_names:
                    retry = qw.QMessageBox.question(
                        self,
                        'Error',
                        'Image name already exists. Please enter a different name.',
                        qw.QMessageBox.Retry | qw.QMessageBox.Cancel, # pyright: ignore[reportAttributeAccessIssue] ; Retry and Cancel buttons exist
                        qw.QMessageBox.Retry # pyright: ignore[reportAttributeAccessIssue] ; Retry button exists
                    )
                    if retry == qw.QMessageBox.Cancel:  # pyright: ignore[reportAttributeAccessIssue] ; Cancel button exists
                        return
                    else: continue
                break
            list_imgUnit.append(MeaImg_Unit(unit_name=imgname,calibration=cal))
        
        # > Send the coordinates to the worker for the image capture <
        tiling_params = ImageTiling_Params(
            shape=shape,
            cropx_pixel=cropx_pixel,
            cropy_pixel=cropy_pixel,
            cropx_mm=cropx_mm,
            cropy_mm=cropy_mm,
        )
        for imgUnit, meaCoor_mm in zip(list_imgUnit,list_meaCoor_mm):
            self.sig_capture_img.emit(meaCoor_mm, imgUnit, tiling_params)
        
            