import sys
import os
from typing import Callable
from copy import deepcopy

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))


import PySide6.QtWidgets as qw
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QMouseEvent, QPixmap, QPen, QColor, QFont, QPainter
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer, QCoreApplication, QPointF, QSize, Qt
from PIL import Image, ImageQt

import numpy as np
from PIL import Image

import multiprocessing.pool as mpp
import threading

from iris.utils.general import *

from iris.data.measurement_image import MeaImg_Unit, MeaImg_Handler
from iris.data.calibration_objective import ImgMea_Cal

from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image,Wdg_DataHub_ImgCal
from iris.gui.image_calibration.Canvas_ROIdefinition import Canvas_Image_Annotations

from iris.data import SaveParamsEnum
from iris.gui import AppPlotEnum

from iris.resources.objective_calibration_main_ui import Ui_calibration_main
from iris.resources.objective_calibration_controls_ui import Ui_calibration_controls

class Calibration_Main_Design(Ui_calibration_main,qw.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
class Calibration_Finetune_Design(Ui_calibration_controls,qw.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)

class ImageProcessor_Worker(QObject):
    
    sig_img = Signal(Image.Image)
    
    def __init__(self):
        super().__init__()
    
    @Slot(MeaImg_Unit,bool)
    def get_stitched_image(self,meaImg:MeaImg_Unit,low_res:bool) -> None:
        """
        Gets the stitched image from the measurement image
        
        Args:
            meaImg (MeaImg_Unit): Measurement image unit
            low_res (bool): Whether to get the low resolution image. Default is False
        
        Returns:
            tuple: Stitched image and list of coordinates
        """
        stitched_img = meaImg.get_image_all_stitched(low_res=low_res)[0]
        self.sig_img.emit(stitched_img)

class Calibration_Worker(QObject):
    # Calibration signals
    event_operationDone = threading.Event()
    sig_set_image = Signal(Image.Image) # Signal to set the image on the canvas
    sig_start_record_clicks = Signal(bool)  # Signal to start recording clicks on the canvas
    sig_stop_record_clicks = Signal(bool)   # Signal to stop recording clicks on the canvas
    sig_set_record_clicks_mm = Signal(list)  # Signal to set the recorded clicks in mm coordinates
    
    sig_pause_vid_norm = Signal()   # Signal to pause the video feed (normal, unannotated)
    sig_resume_vid_norm = Signal()  # Signal to resume the video feed (normal, unannotated)
    
    sig_pause_vid_anno = Signal()   # Signal to pause the annotated video feed
    sig_resume_vid_anno = Signal()  # Signal to resume the annotated video feed
    
    sig_set_btnCal = Signal(str,str)    # Signal to set up the calibration button
    sig_finished = Signal(str)          # Signal to indicate the calibration process is finished
    sig_save_cal = Signal(MeaImg_Unit)  # Signal to save the calibration file (stored in the MeaImg_Unit
    sig_set_imgUnit = Signal(MeaImg_Unit)   # Signal to set the image unit being stored in the main widget
    
    msg_cal_success = 'Calibration completed successfully'
    msg_cal_error = 'Error during calibration: '
    
    button_texts = (
        '1. Capture the first state',
        '2. Complete laser selection',
        '3. Complete the first selections',
        '4. Capture the second state',
        '5. Complete the second selection',
        '6. Capture the third state',
        '7. Complete the third selection',
        '8. Complete calibration'
    )
    lines = (
        f'1. Wait for the stage to stage coordinates to stabilise and click "{button_texts[0]}"',
        f'2. Click the center of the laser spot and click "{button_texts[1]}"',
        f'3. Click on some features to be tracked and click "{button_texts[2]}"',
        f'4. Move the stage HORIZONTALLY, ensuring that the features are still visible, and click "{button_texts[3]}"',
        f'5. Click on the features in the same order and click "{button_texts[4]}"',
        f'6. Move the stage VERTICALLY, ensuring that the features are still visible, and click "{button_texts[5]}"',
        f'7. Click on the features in the same order and click "{button_texts[6]}"',
        f'8. Move the stage around, confirm that the features are tracked correctly, and click "{button_texts[7]}"'
    )
    
    # Finetune calibration signals
    event_operationDone_finetune = threading.Event()
    sig_done_picking_points_finetune = Signal()
    sig_finished_finetune = Signal()
    
    def __init__(
        self,
        getter_coor:Callable[[],tuple[float|None,float|None,float|None]],
        getter_cameraImage:Callable[[],Image.Image|None],
        canvas:Canvas_Image_Annotations,
        ):
        """
        Worker to perform the objective calibration

        Args:
            getter_coor (Callable[[],tuple[float,float,float]]): Getter function to get the stage coordinate
            getter_cameraImage (Callable[[],Image.Image]): Getter function to get the camera image
            canvas (Canvas_Image_Annotations): Canvas to display the image and record clicks
        """
        super().__init__()
        self._getter_coor = getter_coor
        self._getter_img = getter_cameraImage
        self._canvas = canvas
        
    @Slot()
    def perform_calibration(self) -> None:
        """
        Main function to perform the calibration setup, to be used in a separate thread, communicating with the main thread using events for GUI interaction.
        
        Args:
            list_tracking_coors (list): List to store the tracking coordinates to be used throughout the entire calibration process
        """
        try:
            def capture_state(message:str,button_text:str) -> tuple[float|None,float|None,float|None]:
                # print('Capture state: waiting for the user to click the button')
                self.event_operationDone.clear()
                self.sig_set_btnCal.emit(message,button_text)
                self.sig_resume_vid_anno.emit()
                self._canvas.clear_all_annotations()
                
                # Wait for the user to finish the 
                self.event_operationDone.wait()
                self.sig_pause_vid_anno.emit()
                img_ori = self._getter_img()
                self.sig_set_image.emit(img_ori)
                
                stage_coor = self._getter_coor()
                
                # print('Captured state at stage coordinates:',stage_coor)
                
                return stage_coor

            def feature_selection(message:str,button_text:str,limit1:bool=False) -> list[tuple[float,float]]:
                # print('Feature selection: waiting for the user to click the button')
                self.event_operationDone.clear()
                self.sig_set_btnCal.emit(message,button_text)
                self.sig_start_record_clicks.emit(True)
                self.sig_pause_vid_anno.emit()
                
                self.event_operationDone.wait()
                list_ret = self._canvas.get_clickCoordinates().copy()
                self.sig_stop_record_clicks.emit(True)
                if len(list_ret) == 0:
                    raise ValueError('At least one feature must be selected')
                if limit1 and len(list_ret) != 1:
                    raise ValueError('Only laser spot must be selected')
                
                # print('Selected features at image pixel coordinates:',list_ret)
                return list_ret
            
            lines = self.lines
            button_texts = self.button_texts
            
        # > 1. Capture initial state <
            # print('\nCalibration step 1: Capture initial state')
            v1s = capture_state(lines[0],button_texts[0])
            v1s = np.array(v1s[:2])
            v1s_track = v1s.copy()
            
        # > 2. Select the laser spot <
            # print('\nCalibration step 2: Select laser spot')
            vlc = feature_selection(lines[1],button_texts[1],True)[-1]
            vlc = np.array(vlc)
            
        # > 3. Select the first tracking features <
            # print('\nCalibration step 3: Select first tracking features')
            list_coor_pixel = feature_selection(lines[2],button_texts[2])
            list_coor_pixel_v1 = list_coor_pixel.copy()
            v1c = np.mean(list_coor_pixel,axis=0)
            
        # > 4. Capture second state <
            # print('\nCalibration step 4: Capture second state')
            v2s = capture_state(lines[3],button_texts[3])
            v2s = np.array(v2s[:2])
            y_diff = v2s[1] - v1s[1]
            if not y_diff < 10e-3: raise ValueError('The stage must be moved horizontally') # 10e-3 [mm] is the threshold
            
        # > 5. Select the tracking features <
            # print('\nCalibration step 5: Select second tracking features')
            num_features = len(list_coor_pixel)
            list_coor_pixel = feature_selection(lines[4],button_texts[4])
            v2c = np.mean(list_coor_pixel,axis=0)
            if len(list_coor_pixel) != num_features: raise ValueError('The number of selected features must be the same')
            
        # > 6. Capture third state <
            # print('\nCalibration step 6: Capture third state')
            v3s = capture_state(lines[5],button_texts[5])
            v3s = np.array(v3s[:2])
            x_diff = v3s[0] - v2s[0]
            if not x_diff < 10e-3: raise ValueError('The stage must be moved vertically') # 10e-3 [mm] is the threshold
        
        # > 7. Select the tracking features <
            # print('\nCalibration step 7: Select third tracking features')
            list_coor_pixel = feature_selection(lines[6],button_texts[6])
            v3c = np.mean(list_coor_pixel,axis=0)
            v3c = np.array(v3c[:2])
            if len(list_coor_pixel) != num_features: raise ValueError('The number of selected features must be the same')
            
            # Set the calibration object
            cal = ImgMea_Cal('calibration')
            cal.set_calibration_vector(v1s,v2s,v3s,v1c,v2c,v3c,vlc)
            
            # Save the calibration parameters (corrects for the image coordinate to the stage coordinate inversion)
            img_unit = MeaImg_Unit(unit_name=f'Calibration {get_timestamp_us_str()}',calibration=cal)
            
        # > 8. Show the live feature tracking and complete the calibration
            # print('\nCalibration step 8: Show live feature tracking and complete the calibration')
            self.event_operationDone.clear()
            self.sig_set_btnCal.emit(lines[7],button_texts[7])
            
            # Add the initial tracked features to the list, adjusted for the real coordinates by 
            # adding the initial stage coordinates
            list_tracking_coors_mm = [cal.convert_imgpt2stg(coor_img_pixel=np.array(coor_img),\
                coor_stage_mm=v1s_track) for coor_img in list_coor_pixel_v1]
            self.sig_set_imgUnit.emit(img_unit)
            self.sig_set_record_clicks_mm.emit(list_tracking_coors_mm)
            self.sig_resume_vid_anno.emit()
            
            # Wait for the user to finish the calibration
            self.event_operationDone.wait()
            
        # > 7. Ask the user to save the calibration file
            self.sig_save_cal.emit(img_unit)
        
        except Exception as e: self.sig_finished.emit(self.msg_cal_error + str(e))
        finally:
            self.sig_stop_record_clicks.emit(True)
            self.sig_pause_vid_anno.emit()
            self.sig_resume_vid_norm.emit()
            self.sig_finished.emit(self.msg_cal_success)
            
    @Slot(MeaImg_Unit)
    def perform_calibration_finetune(self) -> None:
        """
        Performs a finetune calibration based on the current clicked coordinates on the canvas
        """
        self.event_operationDone_finetune.wait()
        self.event_operationDone_finetune.clear()
        self.sig_done_picking_points_finetune.emit()
        
        self.event_operationDone_finetune.wait()
        self.event_operationDone_finetune.clear()
        self.sig_finished_finetune.emit()
    
class Wdg_Calibration(qw.QWidget):
    """
    Sub-frame to form the calibration file of an ImageMeasurement object.
    I.e., to perform an objective calibration.
    
    Note:
        initialise_auto_updaters must be called after the object is created
    """
    sig_get_stitched_img = Signal(MeaImg_Unit,bool)
    sig_perform_calibration = Signal()
    sig_perform_finetune_calibration = Signal()
    
    def __init__(self,
                 parent:qw.QWidget,
                 processor:mpp.Pool,
                 dataHub_img:Wdg_DataHub_Image,
                 dataHub_imgcal:Wdg_DataHub_ImgCal,
                 getter_coor:Callable[[],tuple[float|None,float|None,float|None]],
                 getter_cameraImage:Callable[[],Image.Image|None],):
        """
        Args:
            parent (qw.QWidget): Main frame to put the sub-frame in
            processor (mpp.Pool): Multiprocessing pool for parallel processing
            dataHub_img (Wdg_DataHub_Image): DataHub for the measurement images
            dataHub_imgcal (Wdg_DataHub_ImgCal): DataHub for the image calibrations
            getter_coor (Callable): Callable to get the stage coordinate
            getter_cameraImage (Callable): Callable to get the camera image
        """
        super().__init__(parent)
        self._processor = processor
        self._getter_cameraImage = getter_cameraImage
        self._getter_coordinate = getter_coor
        
        self._dataHub_img = dataHub_img
        self._dataHub_imgcal = dataHub_imgcal
        
        self._showHints = AppPlotEnum.IMGCAL_SHOWHINTS.value
        
    # >>> Main parameters <<<
        self._getter_calibration = self._dataHub_imgcal.get_selected_calibration
        self._meaImgUnit = MeaImg_Unit(
            unit_name='Calibration',
            calibration=self._getter_calibration(),
            reconstruct=True
        )
        
    # >>> Main widget setup <<<
        self._widget = Calibration_Main_Design(self)
        lyt = qw.QVBoxLayout(self)
        lyt.addWidget(self._widget)
        self.setLayout(lyt)
        wdg = self._widget
        
        # Statusbar setup
        self._statbar = qw.QStatusBar(self)
        lyt.addWidget(self._statbar)
        
        lbl_statbar = qw.QLabel('Ready')
        self._statbar.addWidget(lbl_statbar)
        
    # >>> Display widget <<<
        # Canvas to display the image and button to show current image
        self._canvas_img = Canvas_Image_Annotations(wdg.wdg_holder_canvas)
        self._chk_lowres = wdg.chk_lres
        self._btn_showImage = wdg.btn_showimage
        self._btn_showLiveFeed = wdg.btn_refresh
        self._btn_showLiveFeed.setEnabled(False)
        
        self._btn_showImage.clicked.connect(lambda:self._show_stitched_images())
        # self._btn_showLiveFeed.clicked.connect(lambda:self.initialise_auto_updaters())
        
    # >>> Capture widgets <<<
        # Buttons for image capture
        self._btn_capture = wdg.btn_capture
        self._btn_resetCapture = wdg.btn_resetcapture
        self._btn_save = wdg.btn_savecaptured
        
        self._btn_capture.clicked.connect(lambda:self._capture_image())
        self._btn_resetCapture.clicked.connect(lambda:self._reset_capture())
        self._btn_save.clicked.connect(lambda:self._save_image())
        
    # >>> Calibration adjustment <<<
        # Sub-frame for calibration adjustment
        self._wdg_cal_adj=Wdg_Calibration_Finetuning(
            parent=self,
            processor=self._processor,
            imgUnit_getter=lambda:self._meaImgUnit
            )
        wdg.lyt_holder_calibration_controls.addWidget(self._wdg_cal_adj)
        
        self._wdg_cal_adj.config_finetune_calibration_button(callback=self._initialise_finetune_calibration)
        self._wdg_cal_adj.config_calibrate_button(callback=self._start_calibration)
        
    # >>> Display parameters <<<
        self._videoRefreshRate = 25    # Refresh rate of the video feed in Hz
        
    # Thread for a live video feed
        self._flg_video_pause = threading.Event()
        self._timer_videofeed = QTimer()
        self._timer_videofeed.setInterval(1000//self._videoRefreshRate)
        self._timer_videofeed.timeout.connect(lambda: self._show_camera_feed())
        self.destroyed.connect(self._timer_videofeed.stop)
        self._timer_videofeed.start()
        
    # Thread for an annotated video feed during calibration
        self._flg_video_anno_pause = threading.Event()
        self._anno_vid_custom_coors = False
        self._anno_vid_list_coors_mm = []
        self._anno_vid_annotate = False
        
        self._timer_videofeed_anno = QTimer()
        self._timer_videofeed_anno.setInterval(1000//self._videoRefreshRate)
        self._timer_videofeed_anno.timeout.connect(lambda: self._show_annotated_video_feed())
        self.destroyed.connect(self._timer_videofeed_anno.stop)
        self._timer_videofeed_anno.start()
        
        self._init_worker()
    
    def _init_worker(self) -> None:
        """
        Initialises the worker for image processing
        """
        # Image processing worker
        self._thread_worker_img = QThread()
        self._worker_img = ImageProcessor_Worker()
        self._worker_img.moveToThread(self._thread_worker_img)
        self._thread_worker_img.start()
        
        self.sig_get_stitched_img.connect(self._worker_img.get_stitched_image)
        self._worker_img.sig_img.connect(lambda img:self._canvas_img.set_image(img))
        
        # Calibration worker
        self._thread_worker_cal = QThread()
        self._worker_cal = Calibration_Worker(
            getter_coor=self._getter_coordinate,
            getter_cameraImage=self._getter_cameraImage,
            canvas=self._canvas_img,
        )
        self._worker_cal.moveToThread(self._thread_worker_cal)
        self._thread_worker_cal.start()
        
        self.sig_perform_calibration.connect(self._worker_cal.perform_calibration)
        
        self._worker_cal.sig_set_image.connect(self._canvas_img.set_image)
        self._worker_cal.sig_start_record_clicks.connect(self._canvas_img.start_recordClicks)
        self._worker_cal.sig_stop_record_clicks.connect(self._canvas_img.stop_recordClicks)
        self._worker_cal.sig_set_record_clicks_mm.connect(self._setup_annotated_video_feed)
        
        self._worker_cal.sig_pause_vid_norm.connect(self._pause_video_feed)
        self._worker_cal.sig_resume_vid_norm.connect(self._resume_video_feed)
        
        self._worker_cal.sig_pause_vid_anno.connect(self._flg_video_anno_pause.set)
        self._worker_cal.sig_resume_vid_anno.connect(self._flg_video_anno_pause.clear)
        
        self._worker_cal.sig_set_btnCal.connect(self._calibration_button_setup_duringCalibration)
        self._worker_cal.sig_finished.connect(self._handle_calibration_finished)
        self._worker_cal.sig_save_cal.connect(self._save_calibration_file)
        self._worker_cal.sig_set_imgUnit.connect(self._set_internal_meaImgUnit)
        
        # Finetune calibration connections
        self._worker_cal.sig_finished_finetune.connect(self._finalise_finetune_calibration)
        self.sig_perform_finetune_calibration.connect(self._worker_cal.perform_calibration_finetune)
    
    def _save_image(self):
        """
        Saves the local image to the Image DataHub
        """
        self._dataHub_img.append_ImageMeasurementUnit(self._meaImgUnit, flg_nameprompt=True)
        self._meaImgUnit = MeaImg_Unit(
            unit_name='Calibration',
            calibration=self._getter_calibration(),
            reconstruct=True
        )
    
    def _show_camera_feed(self):
        """
        Updates the video feed on the canvas
        """
        if self._flg_video_pause.is_set(): return
        
        try:
            img_ori = self._getter_cameraImage()
            self._canvas_img.set_image(img_ori)
        except Exception as e:
            print('_update_video_feed error:',e)
    
    def _reset_capture(self):
        """
        Resets the capture process
        """
        result = qw.QMessageBox.question(
            self, 'Reset capture', 'This will delete all stored image. Are you sure you want to proceed?',
            qw.QMessageBox.Yes | qw.QMessageBox.No, qw.QMessageBox.No # pyright: ignore[reportAttributeAccessIssue] ; QMessageBox.Yes, No exist
        )
        if result != qw.QMessageBox.Yes: # pyright: ignore[reportAttributeAccessIssue] ; QMessageBox.Yes exists
            return
        
        self._meaImgUnit.reset_measurement()
    
    def _capture_image(self):
        """
        Captures the image from the camera and saves it to the image measurement
        """
        try:
            # Set a style to show a yellow background
            style = "QStatusBar{background-color: %s;}" % 'yellow'
            self._statbar.setStyleSheet(style)
            self._statbar.showMessage('Capturing image...')
            img:Image.Image|None = self._getter_cameraImage()
            coor = self._getter_coordinate()
            
            # Validate the inputs
            if img is None: raise ValueError('No image captured from the camera')
            if not all([isinstance(c,float) for c in coor]): raise ValueError('Stage coordinates are not valid')
            
            # Save the image to the measurement image
            meaImg = self._meaImgUnit
            cal = self._getter_calibration()
            meaImg.set_calibration_ImageMeasurement_Calibration(cal)
            
            timestamp = get_timestamp_us_str()
            
            meaImg.add_measurement(
                timestamp=timestamp,
                x_coor=coor[0], # pyright: ignore[reportArgumentType] ; the check is done above to ensure coor is float
                y_coor=coor[1], # pyright: ignore[reportArgumentType] ; the check is done above to ensure coor is float
                z_coor=coor[2], # pyright: ignore[reportArgumentType] ; the check is done above to ensure coor is float
                image=img
            )
            
            self._show_stitched_images()
            
            style = "QStatusBar{background-color: %s;}" % 'green'
            self._statbar.setStyleSheet(style)
            self._statbar.showMessage('Image captured successfully')
        except Exception as e:
            self._statbar.setStyleSheet("QStatusBar{background-color: %s;}" % 'red')
            self._statbar.showMessage('Error capturing image: {}'.format(e))
            print(f'_capture_image error: {e}')
        finally:
            timer = QTimer()
            timer.setSingleShot(True)
            timer.setInterval(5000)
            timer.timeout.connect(self._statbar.clearMessage)
            timer.timeout.connect(lambda: self._statbar.setStyleSheet(""))
            timer.start()
    
    def _show_stitched_images(self) -> None:
        """
        Shows the stitched images on the canvas
        """
        ori_text = self._btn_showImage.text()
        
        self._pause_video_feed()
        self._btn_showImage.clicked.disconnect()
        self._btn_showImage.clicked.connect(lambda: self._reset_btn_showImage(ori_text))
        self._btn_showImage.setText('Show live feed')
        
        meaImg = self._meaImgUnit
        flg_lowResImg = self._chk_lowres.isChecked()
        self.sig_get_stitched_img.emit(meaImg,flg_lowResImg)
    
    def _reset_btn_showImage(self, text:str):
        """
        Resets the show image button to its original state
        """
        self._btn_showImage.setEnabled(True)
        self._btn_showImage.setText(text)
        self._btn_showImage.clicked.disconnect()
        self._btn_showImage.clicked.connect(lambda: self._show_stitched_images())
        
        self._resume_video_feed()
    
    @Slot(list)
    def _setup_annotated_video_feed(self, list_coors_mm:list[tuple[float,float]]|None):
        """
        Sets up the annotated video feed for calibration. If list_coors_mm is None,
        the annotated video feed will use the clicked coordinates on the canvas.
        (Refer to _show_annotated_video_feed for more details)
        
        Args:
            list_coors_mm (list): List of coordinates to be annotated on the canvas
        """
        if list_coors_mm is None:
            self._anno_vid_custom_coors = False
            self._anno_vid_list_coors_mm = []
            self._anno_vid_annotate = False
        else:
            self._anno_vid_custom_coors = True
            self._anno_vid_list_coors_mm = list_coors_mm
            self._anno_vid_annotate = True
    
    def _show_annotated_video_feed(self):
        """
        Displays the video feed on the canvas with annotations. For specific coordinates to be annotated,
        use _setup_annotated_video_feed to specify them up, which will be stored in the _anno_vid_list_coors_mm.
        """
        if self._flg_video_anno_pause.is_set(): return
        
        img_ori = self._getter_cameraImage()
        self._canvas_img.set_image(img_ori)
        
        if self._anno_vid_custom_coors: coor_list_mm = self._anno_vid_list_coors_mm
        else: coor_list_mm = self._canvas_img.get_clickCoordinates().copy()
        
        if len(coor_list_mm) <= 0: return
        
        try:
            if not self._anno_vid_annotate: return
            stage_coor = self._getter_coordinate()
            low_res = self._chk_lowres.isChecked()
            
            assert all([isinstance(c,float) for c in stage_coor]), 'Stage coordinates are not valid'
            
            list_coor_pixel = [self._meaImgUnit.convert_stg2imgpt(coor_stage_mm=stage_coor,coor_point_mm=coor, # pyright: ignore[reportArgumentType]
                correct_rot=False,low_res=low_res) for coor in coor_list_mm]
            list_coor_pixel = [(float(coor[0]),float(coor[1])) for coor in list_coor_pixel]
            
            self._canvas_img.annotate_canvas_multi(list_coor_pixel,scale=True,flg_removePreviousAnnotations=True)
        except Exception as e: print('Error annotating the image:',e)
    
    @Slot()
    def _pause_video_feed(self):
        """
        Pauses the video feed
        """
        self._flg_video_pause.set()
    
    @Slot()
    def _resume_video_feed(self):
        """
        Resumes the video feed
        """
        self._flg_video_pause.clear()
    
    def _initialise_finetune_calibration(self):
        """
        Finetunes the calibration manually using the spinbox widgets
        """ 
        try:
            self._pause_video_feed()
            meaImg = self._meaImgUnit
            current_cal = self._getter_calibration()
            meaImg.set_calibration_ImageMeasurement_Calibration(current_cal)
            if not meaImg.check_calibration_exist(): qw.QMessageBox.warning(self,'Finetune calibration','Calibration does not exist. Please perform calibration first.'); return
            
        # > Parameters initialisation <
            # Reset the values, enable the spinboxes, and set the button to save the calibration
            try: self._wdg_cal_adj.initialise_fineadjuster()
            except Exception as e: qw.QMessageBox.warning(self,'Finetune calibration','Error initialising fineadjuster: {}'.format(e)); return
            
        # > Tracking initialisation <
            # Ask the user to pick some points to track
            stage_coor = self._getter_coordinate()
            img = self._getter_cameraImage()
            self._canvas_img.set_image(img)
            
            self._statbar.setStyleSheet("QStatusBar{background-color: %s;}" % 'yellow')
            self._statbar.showMessage('Click on the features to be tracked and click "Finish feature selection". Right-click to clear the current selections.')
            list_coors_pixel = self._canvas_img.start_recordClicks()
            
            try: self._worker_cal.sig_done_picking_points_finetune.disconnect()
            except Exception: pass
            
            self._worker_cal.sig_done_picking_points_finetune.connect(
                lambda: self._perform_finetune_calibration(
                    meaImg, stage_coor, list_coors_pixel # pyright: ignore[reportArgumentType] ; the error will be catched elsewhere, and is not critical here
                )
            )
            
            self._wdg_cal_adj.config_finetune_calibration_button(
                callback=self._worker_cal.event_operationDone_finetune.set,
                text='Finish feature selection',enabled=True)
            
            self.sig_perform_finetune_calibration.emit()
            
        except Exception as e:
            qw.QMessageBox.warning(self,'Finetune calibration','Error initialising finetune calibration: {}'.format(e))
            self._resume_video_feed()
            self._reset_status_bar(after_sec=5)
            self._wdg_cal_adj.config_finetune_calibration_button(callback=self._initialise_finetune_calibration)
            
    def _perform_finetune_calibration(self, meaImg: MeaImg_Unit, stage_coor: tuple[float, float, float],
            list_coors_pixel: list[tuple[float, float]]):
        """
        Performs the finetuning of the calibration using the selected features
        
        Args:
            meaImg (MeaImg_Unit): Measurement image unit of which the calibration will be used for the finetuning process
            stage_coor (tuple[float, float, float]): Stage coordinate
            list_coors_pixel (list[tuple[float, float]]): List of pixel coordinates of the selected features
        """
        try:
            list_coors_mm = [meaImg.convert_imgpt2stg(stage_coor,coor,False,low_res=self._chk_lowres.isChecked()) for coor in list_coors_pixel]
            self._canvas_img.stop_recordClicks()
            
            self._statbar.setStyleSheet("QStatusBar{background-color: %s;}" % 'yellow')
            self._statbar.showMessage('Finetune the calibration using the spinboxes and move the stage around to monitor the effect')
            
            # > Calibration finetuning by video feed <
                # Enable the spinboxes and start the video feed
            self._wdg_cal_adj.enable_finetuneCalibration_widgets(
                callback=self._wdg_cal_adj.apply_temp_fineadjustment,
                readonly=True)
            
            # > Set up the annotated video feed and the widgets to finalise the finetuning <
            self._flg_video_pause.set()
            self._flg_video_anno_pause.clear()
            self._setup_annotated_video_feed(list_coors_mm)
            
            self._wdg_cal_adj.config_finetune_calibration_button(
                callback=self._worker_cal.event_operationDone_finetune.set,text='End finetune calibration')
        except Exception as e:
            qw.QMessageBox.warning(self,'Error in finetune calibration',str(e))
            self._statbar.setStyleSheet("QStatusBar{background-color: %s;}" % 'red')
            self._statbar.showMessage(f'Error in finetuning: {e}')
            self._reset_status_bar(after_sec=5)
            self._wdg_cal_adj.config_finetune_calibration_button(callback=self._initialise_finetune_calibration)
        
    @Slot()
    def _finalise_finetune_calibration(self):
        """
        Finalise the calibration finetuning
        """
        self._flg_video_anno_pause.set()
        self._resume_video_feed()
        try:
            self._wdg_cal_adj.finalise_fineadjustment()
            self._statbar.setStyleSheet("QStatusBar{background-color: %s;}" % 'green')
            self._statbar.showMessage('Calibration finetuning finished: Please save the calibration file manually if required')
            self._reset_status_bar(after_sec=5)
        except Exception as e:
            qw.QMessageBox.warning(self,'Error in finetune calibration',str(e))
            self._statbar.setStyleSheet("QStatusBar{background-color: %s;}" % 'red')
            self._statbar.showMessage(f'Error in finetuning: {e}')
        finally:
            self._wdg_cal_adj.config_finetune_calibration_button(callback=self._initialise_finetune_calibration)
            
    @Slot(str, str)
    def _calibration_button_setup_duringCalibration(self, msg:str, btn_text:str) -> None:
        """
        Sets up the calibration button to perform the state capture operation (image and coordinate,
        handled by the worker))

        Args:
            msg (str): Message to display on the status bar
            btn_text (str): Text to display on the button
        """
        callback = self._worker_cal.event_operationDone.set
        self._wdg_cal_adj.config_calibrate_button(callback=callback,text=btn_text)
        self._statbar.setStyleSheet("QStatusBar{background-color: %s;}" % 'yellow')
        self._statbar.showMessage(msg)
    
    @Slot(MeaImg_Unit)
    def _save_calibration_file(self, meaImg:MeaImg_Unit) -> None:
        """
        Saves the calibration file from the measurement image unit

        Args:
            meaImg (MeaImg_Unit): Measurement image unit containing the calibration to be saved
        """
        self._meaImgUnit = meaImg
        flg_save = qw.QMessageBox.question(self,'Save calibration','Do you want to save the calibration file?',
            qw.QMessageBox.Yes | qw.QMessageBox.No, qw.QMessageBox.No) == qw.QMessageBox.Yes # pyright: ignore[reportAttributeAccessIssue] ; QMessageBox.Yes, No exist
        if not flg_save: raise ValueError('Calibration not saved')
        
        MeaImg_Handler().save_calibration_json_from_ImgMea(meaImg)
        qw.QMessageBox.information(self,'Calibration saved','Calibration file saved successfully')
    
    @Slot()
    def _set_internal_meaImgUnit(self, imgunit:MeaImg_Unit):
        """
        Sets the MeaIng_Unit being stored internally (e.g., for the pixel -> mm coordinate conversion)

        Args:
            imgunit (MeaImg_Unit): The image unit to be stored
        """
        self._meaImgUnit = imgunit
    
    @Slot(str)
    def _handle_calibration_finished(self, message:str) -> None:
        """
        Handles the calibration finished signal
        
        Args:
            message (str): Message to display on the status bar
        """
        colour = 'green' if message.startswith(self._worker_cal.msg_cal_success) else 'red'
        self._statbar.setStyleSheet("QStatusBar{background-color: %s;}" % colour)
        self._statbar.showMessage(message)
        self._reset_status_bar(after_sec=5)
        
        # Reset the button state
        self._wdg_cal_adj.config_calibrate_button(callback=self._start_calibration)
    
    def _start_calibration(self):
        """
        Perform the calibration to:
            - Calculate the mm/pixel ratio
            - Measure the laser coordinate offset of the image coordinate from the stage coordinate
        """
        self._pause_video_feed()
        
        timer_vid_anno = QTimer()
        timer_vid_anno.setInterval(1000//self._videoRefreshRate)
        timer_vid_anno.timeout.connect(lambda: self._show_annotated_video_feed())
        timer_vid_anno.start()
        
        if self._showHints:
            message = "\n".join(self._worker_cal.lines)
            qw.QMessageBox.information(self,'Calibration procedure',message)
            
        self._setup_annotated_video_feed(None)
        self.sig_perform_calibration.emit()
    
    def _reset_status_bar(self, after_sec:float=0):
        """
        Resets the status bar after a delay
        
        Args:
            after_sec (float): Delay in seconds before resetting the status bar
        """
        if after_sec <= 0:
            self._statbar.clearMessage()
            self._statbar.setStyleSheet("")
        else:
            timer = QTimer()
            timer.setSingleShot(True)
            timer.setInterval(int(after_sec*1000))
            timer.timeout.connect(self._statbar.clearMessage)
            timer.timeout.connect(lambda: self._statbar.setStyleSheet(""))
            timer.start()
    

class Wdg_Calibration_Finetuning(qw.QWidget):
    """
    Sub-frame for calibration adjustment to be used in the ROI_definition_controller
    """
    def __init__(self, parent, processor:mpp.Pool, imgUnit_getter:Callable[[],MeaImg_Unit|None],
        getter_flipx:Callable[[],bool]=lambda:False, getter_flipy:Callable[[],bool]=lambda:False):
        """
        Args:
            main (tk.Frame): Main frame to put the sub-frame in
            imgUnit_getter (Callable): Callable to get the measurement image
        """
        super().__init__(parent)
        self._processor = processor
        
    # >>> Image file handler <<<
        assert callable(imgUnit_getter), 'Measurement image getter must be a callable'
        self._getter_measurement_image = imgUnit_getter
        self._getter_flipx = getter_flipx
        self._getter_flipy = getter_flipy
        
        self._handler_img = MeaImg_Handler()
        self._lastDirPath = SaveParamsEnum.DEFAULT_SAVE_PATH.value
        
    # >> Main widget setup <<
        self._widget = Calibration_Finetune_Design(self)
        lyt = qw.QVBoxLayout(self)
        lyt.addWidget(self._widget)
        self.setLayout(lyt)
        wdg = self._widget

    # >> Calibration <<
    # Auto calibration process related
        # Calibration objects
        self._cal_ori:ImgMea_Cal|None = None
        self._cal_temp:ImgMea_Cal|None = None
        self._cal_last:ImgMea_Cal|None = None
    
        # Calibration parameters
        self._cal_sclx = wdg.spin_scalex
        self._cal_scly = wdg.spin_scaley
        self._cal_offsetx = wdg.spin_offsetx
        self._cal_offsety = wdg.spin_offsety
        self._cal_rot_deg = wdg.spin_rotdeg
        
        # Buttons for auto calibration
        self._btn_calibrate = wdg.btn_calibrate
        self._btn_loadCalibrationFile = wdg.btn_loadcal
        self._btn_saveCalibrationFile = wdg.btn_savecal
        
        self._btn_loadCalibrationFile.clicked.connect(lambda: self._load_calibration_file())
        self._btn_saveCalibrationFile.clicked.connect(lambda: self._save_calibration_file())
        
        # Label to display the calibration filename
        self._lbl_calibration = wdg.lbl_calfile
        
    # Manual calibration process related
        # Widgets for manual calibration
        self._btn_cal_finetune = wdg.btn_perform_finetune
        self._spin_sclx = wdg.spin_scalex
        self._spin_scly = wdg.spin_scaley
        self._spin_offsetx = wdg.spin_offsetx
        self._spin_offsety = wdg.spin_offsety
        self._spin_rotdeg = wdg.spin_rotdeg
        
    def initialise_fineadjuster(self) -> None:
        """
        Initialises the calibration parameters in the measurement image using
        the calibration parameters stored in the image
        """
        img_unit = self._getter_measurement_image()
        assert img_unit is not None, 'Measurement image not initialised'
        self._cal_ori = deepcopy(img_unit.get_ImageMeasurement_Calibration())
        self._cal_temp = deepcopy(self._cal_ori)
        
        assert isinstance(self._cal_ori, ImgMea_Cal), 'Calibration object not initialised'
        assert self._cal_ori.check_calibration_set() == True, 'Calibration parameters not set'
        
    def get_last_calibration(self) -> ImgMea_Cal|None:
        """
        Returns the last created calibration object
        
        Returns:
            ImageMeasurement_Calibration|None: Last calibration object or None if not initialised
        """
        return self._cal_last
        
    def finalise_fineadjustment(self,apply:bool=False) -> None:
        """
        Finalises the calibration parameters in the measurement image using
        the calibration parameters stored in the temporary calibration object
        
        Args:
            apply (bool): Apply the calibration parameters to the measurement image. Default is False
        """
        assert self._cal_temp is not None, 'Temporary calibration not initialised'
        
        if apply:
            meaImg = self._getter_measurement_image()
            if not isinstance(meaImg, MeaImg_Unit): raise ValueError('Measurement image not initialised')
            meaImg.set_calibration_ImageMeasurement_Calibration(self._cal_temp)
        
        self._cal_last = deepcopy(self._cal_temp)
        self._cal_temp = None
        self._cal_ori = None
        
        self.reset_calibrationSpinbox_values()
        self._disable_finetuneCalibration_widgets()
    
    def apply_temp_fineadjustment(self) -> None:
        """
        Updates the calibration parameters in the measurement image using
        the calibration parameters in the spinbox widgets
        """
        assert self._cal_temp is not None and self._cal_ori is not None, 'Calibration parameters not initialised'
        
        img_cal = self._cal_ori
        sclx = img_cal.scale_x_pixelPerMm
        scly = img_cal.scale_y_pixelPerMm
        offsetx = img_cal.laser_coor_x_mm
        offsety = img_cal.laser_coor_y_mm
        rot_rad = img_cal.rotation_rad
        
        # Get the calibration parameters in percentage and degrees
        sclx_rel,scly_rel,offsetx_rel,offsety_rel,rotdeg_rel = self.get_calibration_params_percent()
        
        # Update the calibration parameters
        sclx += sclx_rel/100 * sclx
        scly += scly_rel/100 * scly
        offsetx += offsetx_rel/100 * offsetx
        offsety += offsety_rel/100 * offsety
        rot_rad += np.deg2rad(rotdeg_rel)
        
        # Setup a new calibration object
        id = img_cal.id + f'_finetuned_{get_timestamp_sec()}'
        self._cal_temp = ImgMea_Cal(id=id)
        self._cal_temp.set_calibration_params(
            scale_x_pixelPerMm=sclx,
            scale_y_pixelPerMm=scly,
            laser_coor_x_mm=offsetx,
            laser_coor_y_mm=offsety,
            rotation_rad=rot_rad,
            flip_y=img_cal.flip_y,
        )
        
        # Update the calibration parameters in the measurement image
        img_unit = self._getter_measurement_image()
        if not isinstance(img_unit, MeaImg_Unit): raise ValueError('Measurement image not initialised')
        img_unit.set_calibration_ImageMeasurement_Calibration(self._cal_temp)
    
    def _disable_finetuneCalibration_widgets(self) -> None:
        """
        Disables the calibration widgets
        """
        widgets = get_all_widgets_from_layout(self._widget.lyt_finetune_spins)
        [widget.setEnabled(False) for widget in widgets if isinstance(widget, qw.QDoubleSpinBox)]
    
    def enable_finetuneCalibration_widgets(self,callback:Callable|None=None,readonly:bool=True) -> None:
        """
        Configures the calibration widgets
        
        Args:
            callback (Callable): Callback function for the finetune calibration button. Default is None
            readonly (bool): Set the calibration widgets to read-only. Default is True
        
        Note:
            - If callback is None, the callback will default to changing the calibration parameters
                in the measurement image from the getter provided in the constructor
        """
        if callback is None: callback = self.apply_temp_fineadjustment
        
        widgets = get_all_widgets_from_layout(self._widget.lyt_finetune_spins)
        widgets = [widget for widget in widgets if isinstance(widget, qw.QDoubleSpinBox)]
        for widget in widgets:
            widget.setReadOnly(not readonly)
            widget.setEnabled(True)
            widget.valueChanged.connect(callback)
    
    def config_finetune_calibration_button(self,callback:Callable,text:str='Finetune calibration',enabled:bool=True) -> None:
        """
        Sets the text of the finetune calibration button
        
        Args:
            callback (Callable): Callback function for the finetune calibration button
            text (str): Text to be displayed on the finetune calibration button. Default is 'Finetune calibration'
            enabled (bool): Enable the finetune calibration button. Default is True
        """
        assert isinstance(text, str), 'Text must be a string'
        
        try: self._btn_cal_finetune.clicked.disconnect()
        except Exception: pass
        self._btn_cal_finetune.setEnabled(enabled)
        self._btn_cal_finetune.setText(text)
        self._btn_cal_finetune.clicked.connect(callback)
    
    def config_calibrate_button(self,callback:Callable,text:str='Calibrate',enabled:bool=True) -> None:
        """
        Sets the text of the calibrate button
        
        Args:
            callback (Callable): Callback function for the calibrate button
            text (str): Text to be displayed on the calibrate button. Default is 'Calibrate'
            enabled (bool): Enable the calibrate button. Default is True
        """
        if not isinstance(text, str): raise ValueError('Text must be a string')
        
        try: self._btn_calibrate.clicked.disconnect()
        except Exception: pass
        self._btn_calibrate.setEnabled(enabled)
        self._btn_calibrate.setText(text)
        self._btn_calibrate.clicked.connect(callback)
        
    def get_calibration_params_percent(self) -> tuple[float,float,float,float,float]:
        """
        Returns the calibration parameters in percentage and in degrees
        
        Returns:
            tuple[float,float,float,float,float]: Calibration parameters in the order (scl_x,scl_y,offset_x,offset_y,rot_deg)
        """
        
        return self._cal_sclx.value(),self._cal_scly.value(),self._cal_offsetx.value(),self._cal_offsety.value(),self._cal_rot_deg.value()
    
    def reset_calibrationSpinbox_values(self) -> None:
        """Resets the calibration parameters"""
        self._cal_sclx.setValue(0.0)
        self._cal_scly.setValue(0.0)
        self._cal_offsetx.setValue(0.0)
        self._cal_offsety.setValue(0.0)
        self._cal_rot_deg.setValue(0.0)
        
    def _load_calibration_file(self):
        """
        Loads the calibration file
        """
        ori_text = self._btn_loadCalibrationFile.text()
        try:
            self._btn_loadCalibrationFile.setEnabled(False)
            self._btn_loadCalibrationFile.setText('Loading...')
            
            mea_img = self._getter_measurement_image()
            img_cal = self._handler_img.load_calibration_json()
            if img_cal is None: raise ValueError('No calibration file loaded')
            
            if not isinstance(mea_img, MeaImg_Unit): raise ValueError('Measurement image not initialised')
            mea_img.set_calibration_ImageMeasurement_Calibration(img_cal)
            
            self._cal_filename = img_cal.id
            self._lbl_calibration.setText('Objective: {}'.format(self._cal_filename))
            
        except Exception as e:
            qw.QMessageBox.warning(self,'Error loading objective file',str(e))
            print('_load_calibration_file >> Error loading objective file:',e)
        finally:
            self._btn_loadCalibrationFile.setEnabled(True)
            self._btn_loadCalibrationFile.setText(ori_text)
    
    def _save_calibration_file(self):
        """
        Saves the calibration file
        """
        ori_text = self._btn_saveCalibrationFile.text()
        try:
            self._btn_saveCalibrationFile.setEnabled(False)
            self._btn_saveCalibrationFile.setText('Saving...')
            
            mea_img = self._getter_measurement_image()
            assert isinstance(mea_img, MeaImg_Unit), 'Measurement image not initialised'
            
            result = self._handler_img.save_calibration_json_from_ImgMea(mea_img)
            self._lastDirPath,self._cal_filename = result
            self._lbl_calibration.setText('Objective: {}'.format(self._cal_filename))
        
        except Exception as e: print('_save_calibration_file >> Error saving objective file:',e)
        finally:
            self._btn_saveCalibrationFile.setEnabled(True)
            self._btn_saveCalibrationFile.setText(ori_text)
    