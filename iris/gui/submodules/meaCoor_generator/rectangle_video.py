"""
An instance that manages a basic mapping method in tkinter.
This is similar to that of the mapping_method_rectxy_scan_constz mapping method
but this one can set it using an image (with an objective calibration file/params)
instead.
"""
if __name__ == '__main__':
    import sys
    import os
    SCRIPT_DIR = os.path.abspath(r'.\library')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QThread, QObject, QTimer

from uuid import uuid4
from typing import Literal

import numpy as np
from PIL.Image import Image

from iris.gui.motion_video import Wdg_MotionController

from iris.data.calibration_objective import ImgMea_Cal
from iris.data.measurement_image import MeaImg_Unit
from iris.gui.image_calibration.Canvas_ROIdefinition import Canvas_Image_Annotations
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image, Wdg_DataHub_ImgCal

from iris.gui import AppPlotEnum

from iris.resources.coordinate_generators.rect_video_ui import Ui_Rect_Video

class CanvasUpdater_Worker(QObject):
    """
    A worker class to automatically update the video feed canvas
    with the image unit and the clicked coordinates
    """
    sig_error = Signal(str)
    
    _sig_updateImageCalibration = Signal()
    
    sig_updateImage = Signal(Image)
    sig_annotateRectangle = Signal(tuple,tuple,bool)
    sig_annotateMultiPoints = Signal(list,bool,bool)
    
    def __init__(self, canvas_image:Canvas_Image_Annotations, motion_controller:Wdg_MotionController,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._canvas_image = canvas_image
        self._motion_controller = motion_controller
        
        self.sig_updateImage.connect(self._canvas_image.set_image)
        self.sig_annotateRectangle.connect(self._canvas_image.draw_rectangle_canvas)
        self.sig_annotateMultiPoints.connect(self._canvas_image.annotate_canvas_multi)
        
    @Slot(list)
    def _update_image_annotation_points(self, list_clickCoor_pixel:list[tuple[float,float]]) -> None:
        """
        Updates the image shown on the canvas
        """
        # print(f'{get_timestamp_us_str()}: Updating canvas image with {len(list_clickCoor_pixel)} points')
        img = self._motion_controller.get_current_image()
        
        self.sig_updateImage.emit(img)
        self.sig_annotateMultiPoints.emit(list_clickCoor_pixel,True,True)
    
    @Slot(list)
    def _update_image_annotation_rectangle(self, list_rect_meaCoors_pixel:list[tuple[float,float]]):
        """
        Automatically updates the image shown on the canvas with the rectangle annotations
        
        Args:
            list_rect_meaCoors_mm (list[tuple[float,float]]): The rectangle coordinates in mm
        """
        assert isinstance(list_rect_meaCoors_pixel,list), 'list_rect_meaCoors_mm must be a list'
        assert len(list_rect_meaCoors_pixel) == 2, 'list_rect_meaCoors_mm must have 2 coordinates'
        
        # print(f'{get_timestamp_us_str()}: Updating canvas rectangle annotation with coordinates {list_rect_meaCoors_pixel}')
        
        img = self._motion_controller.get_current_image()
        self.sig_updateImage.emit(img)
        self._canvas_image.stop_recordClicks()
        self.sig_annotateRectangle.emit(list_rect_meaCoors_pixel[0],list_rect_meaCoors_pixel[1],True)

class Rect_Video(Ui_Rect_Video, qw.QWidget):
    
    sig_updateResPt = Signal()
    sig_updateResUm = Signal()
    
    sig_resetStoredCoors = Signal()     # To reset the stored coordinates
    sig_updateCalibration = Signal()    # To update the calibration parameters
    
    sig_updateCanvasRectangle = Signal(list)
    sig_updateCanvasImage = Signal(list)
    
    def __init__(
        self,
        parent: qw.QWidget,
        motion_controller:Wdg_MotionController,
        dataHub_img:Wdg_DataHub_Image,
        dataHub_imgCal:Wdg_DataHub_ImgCal,
        *args, **kwargs
        ):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
    # >>> General setup <<<
        self._motion_controller = motion_controller
        self._dataHub_img = dataHub_img
        self._dataHub_imgCal = dataHub_imgCal
        
        video_feed_size = AppPlotEnum.MAP_METHOD_IMAGE_VIDEO_SIZE.value
        
        # Parameters
        self._imgUnit:MeaImg_Unit|None = None       # The image measurement unit used
        self._img:Image|None = None                  # The image shown on the canvas
        self._flg_mode:Literal['point','rectangle'] = 'point'   # The current mode of the coordinate generator
        
    # >>> Video feed setup <<<
        # Parameters
        self._list_imgunit_names:list[str] = []

        # Canvas setup
        self._canvas_video = Canvas_Image_Annotations(self,size_pixel=video_feed_size)
        self.lyt_canvas.addWidget(self._canvas_video)
        self._canvas_video.start_recordClicks()
        
        # Params
        self._list_clickMeaCoor_mm = []     # The list of clicked coordinates in mm
        self._list_rect_meaCoors_mm = []    # The rectangle coordinates for the scan area in mm
        
    # > Z-coordinate setup widgets <
        self.btn_storeZ.clicked.connect(self._store_current_coorz)
        
    # >>> Worker and signals setup <<<
        self._init_signals()
        self._init_workers()
        
    # >>> Initial update <<<
        try: self._update_calibration()
        except Exception as e: print(e)

    def _init_signals(self):
        """
        Initialises the signals and slots for the GUI
        """
        # Set scan area button
        self.btn_defineROI.clicked.connect(self._set_scan_area)
        
        # Resolution spinbox signals
        self.sig_updateResPt.connect(self._update_resolution_pt)
        self.sig_updateResUm.connect(self._update_resolution_um)
        
        self.spin_resXPt.editingFinished.connect(self.sig_updateResUm.emit)
        self.spin_resYPt.editingFinished.connect(self.sig_updateResUm.emit)
        self.spin_resXum.editingFinished.connect(self.sig_updateResPt.emit)
        self.spin_resYum.editingFinished.connect(self.sig_updateResPt.emit)
        
        # Canvas clear annotations observer
        self._canvas_video.add_observer_rightclick(self.sig_resetStoredCoors.emit)
        self.sig_resetStoredCoors.connect(self._reset_click_coors)
        self._canvas_video.sig_leftclick.connect(self._append_clickCoor_mm)
        
        # Calibration update
        self._dataHub_imgCal.add_observer_calibrationChange(self.sig_updateCalibration.emit)
        self.sig_updateCalibration.connect(self._update_calibration)
        
    def _init_workers(self):
        """
        Initialises the worker threads for automatic image updating
        """
        # Worker thread for automatic image updating
        self._thread_canvas = QThread()
        self._worker_canvas = CanvasUpdater_Worker(self._canvas_video,self._motion_controller)
        self._worker_canvas.moveToThread(self._thread_canvas)
        
        # Connect signals
        self.sig_updateCanvasImage.connect(self._worker_canvas._update_image_annotation_points)
        self.sig_updateCanvasRectangle.connect(self._worker_canvas._update_image_annotation_rectangle)
        
        self._worker_canvas.sig_error.connect(lambda msg: qw.QMessageBox.warning(self, 'Error', msg))
        self._thread_canvas.start()
        
        # Set a timer to automatically update the image shown
        freq = 25  # in Hz
        self._timer_updateCanvas = QTimer()
        self._timer_updateCanvas.setInterval(int(1000/freq))
        self._timer_updateCanvas.timeout.connect(self._update_canvas)
        self.destroyed.connect(self._timer_updateCanvas.stop)
        self._timer_updateCanvas.start()
        
    def _block_signals_resolution(self,block:bool):
        """
        Blocks or unblocks the resolution spinbox signals
        
        Args:
            block (bool): True to block, False to unblock
        """
        self.spin_resXPt.blockSignals(block)
        self.spin_resYPt.blockSignals(block)
        self.spin_resXum.blockSignals(block)
        self.spin_resYum.blockSignals(block)
    
    @Slot()
    def _update_resolution_pt(self):
        """
        Sets the point resolution of the mapping method
        """
        self.blockSignals(True)
        resUm_x = self.spin_resXum.value()
        resUm_y = self.spin_resYum.value()
        
        if len(self._list_rect_meaCoors_mm) < 2:
            self.blockSignals(False)
            return
        
        dist_x = abs(self._list_rect_meaCoors_mm[1][0] - self._list_rect_meaCoors_mm[0][0])
        dist_y = abs(self._list_rect_meaCoors_mm[1][1] - self._list_rect_meaCoors_mm[0][1])
        
        points_x = int(dist_x/resUm_x)+1 if resUm_x>0 else 1
        points_y = int(dist_y/resUm_y)+1 if resUm_y>0 else 1
        
        self.spin_resXPt.setValue(points_x)
        self.spin_resYPt.setValue(points_y)
        
        self.blockSignals(False)
    
    @Slot()
    def _update_resolution_um(self):
        """
        Sets the resolution of the mapping method
        """
        self.blockSignals(True)
        res_x_pt = self.spin_resXPt.value()
        res_y_pt = self.spin_resYPt.value()
        
        if len(self._list_rect_meaCoors_mm) < 2:
            self.blockSignals(False)
            return
        
        dist_x = abs(self._list_rect_meaCoors_mm[1][0] - self._list_rect_meaCoors_mm[0][0])
        dist_y = abs(self._list_rect_meaCoors_mm[1][1] - self._list_rect_meaCoors_mm[0][1])
        
        resUm_x = dist_x/(res_x_pt-1) if res_x_pt>1 else 0
        resUm_y = dist_y/(res_y_pt-1) if res_y_pt>1 else 0
        
        self.spin_resXum.setValue(resUm_x)
        self.spin_resYum.setValue(resUm_y)
        
        self.blockSignals(False)
    
    @Slot()
    def _store_current_coorz(self):
        """
        Gets the current stage coordinate and store it as the initial position
        """
        try:
            coor_z_mm = self._motion_controller.get_coordinates_closest_mm()[2]
            if not isinstance(coor_z_mm,float): raise ValueError('Z coordinate is not a float')
        except Exception as e:
            print(e)
            qw.QMessageBox.warning(self, 'Error', str(e))
            return
        
        self.spin_z.setValue(coor_z_mm*1e3)
    
    @Slot()
    def _update_calibration(self):
        """
        Updates the calibration parameters
        """
        # print(f'{get_timestamp_us_str()}: Updating calibration for rectangle video mapping method')
        new_calibration = self._dataHub_imgCal.get_selected_calibration()
        self._imgUnit = MeaImg_Unit(
            unit_name=f'ImgUnit_{uuid4()}',
            calibration=new_calibration
        )
        # print(f'{get_timestamp_us_str()}: Updated calibration to {new_calibration.id}')
    
    @Slot(tuple)
    def _append_clickCoor_mm(self, coor_pixel:tuple):
        """
        Appends the clicked coordinate in mm to the list
        
        Args:
            coor_pixel (tuple): The clicked coordinate in pixels
        """
        # print(f'{get_timestamp_us_str()}: Clicked coordinate in pixels: {coor_pixel}')
        stage_coor_mm = self._motion_controller.get_coordinates_closest_mm()
        
        if not all(isinstance(c,float) for c in stage_coor_mm):
            qw.QMessageBox.warning(self, 'Error', 'Image stage coordinates not available')
            return
        if self._imgUnit is None:
            qw.QMessageBox.warning(self, 'Error', 'No image unit selected')
            return
        
        clickCoor_mm = self._imgUnit.convert_imgpt2stg(
                            frame_coor_mm=stage_coor_mm, # pyright: ignore[reportArgumentType] ; Checked above
                            coor_pixel=coor_pixel,
                            correct_rot=False,
                            low_res=False
                        )
        self._list_clickMeaCoor_mm.append(clickCoor_mm)
    
    @Slot()
    def _set_scan_area(self):
        """
        Sets the scan area by taking the (x_min,y_min) and (x_max,y_max)
        from the list of clicked coordinates
        """
        if not isinstance(self._imgUnit,MeaImg_Unit) or not self._imgUnit.check_calibration_exist():
            try:
                self._update_calibration()
            except Exception as e:
                print(e)
                qw.QMessageBox.warning(self, 'Error', 'Please select an objective first')
            return
        
        if len(self._list_clickMeaCoor_mm) < 2:
            qw.QMessageBox.warning(self, 'Error', 'Please click at least 2 coordinates to define the scan area')
            return
        
        # Get the min and max coordinates
        list_x = [coor[0] for coor in self._list_clickMeaCoor_mm]
        list_y = [coor[1] for coor in self._list_clickMeaCoor_mm]
        
        x_min = min(list_x)
        x_max = max(list_x)
        y_min = min(list_y)
        y_max = max(list_y)
        
        coor_min = (x_min,y_min)
        coor_max = (x_max,y_max)
        
        # Convert to stage coordinates and store it
        stagecoor_min = self._imgUnit.convert_mea2stg(coor_min)
        stagecoor_max = self._imgUnit.convert_mea2stg(coor_max)
        
        self._stagecoor_init_xy_mm = stagecoor_min
        self._stagecoor_final_xy_mm = stagecoor_max
        
        # Update the scan edges label
        self.lbl_scanEdges.setText('({:.1f}, {:.1f}) to ({:.1f}, {:.1f}) μm'.format(
            stagecoor_min[0]*1e3,stagecoor_min[1]*1e3,
            stagecoor_max[0]*1e3,stagecoor_max[1]*1e3))
        
        # Store the rectangle coordinates
        self._list_rect_meaCoors_mm = [coor_min,coor_max]
        self._list_clickMeaCoor_mm.clear()
        self._list_clickMeaCoor_mm.extend([coor_min,coor_max])
        
        # Switch to rectangle mode (to commit the selected ROI) and emit signal to update resolution
        self._flg_mode = 'rectangle'
        self.sig_updateResPt.emit()
    
    @Slot()
    def _reset_click_coors(self):
        """
        Resets the click coordinates
        """
        self._list_clickMeaCoor_mm.clear()
        self._list_rect_meaCoors_mm.clear()
        self.lbl_scanEdges.setText('None')
        self._flg_mode = 'point'
        
        self._canvas_video.clear_all_annotations()
        self._canvas_video.start_recordClicks()
    
    @Slot()
    def _update_canvas(self) -> None:
        """
        Updates the image shown on the canvas
        """
        if not self.isVisible():
            print('Canvas not visible, skipping update')
            return  # Do not update if the widget is not visible
        
        if not isinstance(self._imgUnit,MeaImg_Unit) or not self._imgUnit.check_calibration_exist(): return
        
        stagecoor_mm = self._motion_controller.get_coordinates_closest_mm()
        
        if not isinstance(stagecoor_mm,tuple): return
        if not all(isinstance(c,float) for c in stagecoor_mm): return
        
        self._canvas_video.clear_all_annotations()
        if self._flg_mode == 'point':
            list_clickCoor_pixel = [self._imgUnit.convert_stg2imgpt(
                coor_stage_mm=stagecoor_mm, # pyright: ignore[reportArgumentType] ; Checked above
                coor_point_mm=coor_mm,
                correct_rot=False,
                low_res=False
                )
                for coor_mm in self._list_clickMeaCoor_mm
            ]
            self.sig_updateCanvasImage.emit(list_clickCoor_pixel)
            
        elif self._flg_mode == 'rectangle':
            list_clickCoor_pixel = [self._imgUnit.convert_stg2imgpt(
                coor_stage_mm=stagecoor_mm, # pyright: ignore[reportArgumentType] ; Checked above
                coor_point_mm=coor_mm,
                correct_rot=False,
                low_res=False
                )
                for coor_mm in self._list_rect_meaCoors_mm
            ]
            self.sig_updateCanvasRectangle.emit(list_clickCoor_pixel)
    
    def get_mapping_coordinates_mm(self):
        if self._stagecoor_init_xy_mm == None or self._stagecoor_final_xy_mm == None:
            qw.QMessageBox.warning(self, 'Error', 'Scan area not defined')
            return
        
        # Generate the mapping coordinates
        x_min = self._stagecoor_init_xy_mm[0]
        y_min = self._stagecoor_init_xy_mm[1]
        x_max = self._stagecoor_final_xy_mm[0]
        y_max = self._stagecoor_final_xy_mm[1]
        coor_z_mm = self.spin_z.value()/1e3
        
        res_x = self.spin_resXPt.value()
        res_y = self.spin_resYPt.value()
        
        x = np.linspace(x_min,x_max,res_x)
        y = np.linspace(y_min,y_max,res_y)
        
        return [(x_val,y_val,coor_z_mm) for x_val in x for y_val in y]
    
def initialise_manager_hub_controllers():
    from iris.multiprocessing.basemanager import MyManager
    from iris.multiprocessing.dataStreamer_Raman import DataStreamer_Raman,initialise_manager_raman,initialise_proxy_raman
    from iris.multiprocessing.dataStreamer_StageCam import DataStreamer_StageCam,initialise_manager_stage,initialise_proxy_stage
    
    base_manager = MyManager()
    initialise_manager_raman(base_manager)
    initialise_manager_stage(base_manager)
    base_manager.start()
    ramanControllerProxy,ramanDictProxy=initialise_proxy_raman(base_manager)
    xyControllerProxy,zControllerProxy,stageDictProxy,stage_namespace=initialise_proxy_stage(base_manager)
    ramanHub = DataStreamer_Raman(ramanControllerProxy,ramanDictProxy)
    stageHub = DataStreamer_StageCam(xyControllerProxy,zControllerProxy,stageDictProxy,stage_namespace)
    ramanHub.start()
    stageHub.start()
    
    return xyControllerProxy, zControllerProxy, stageHub
    
def test():
    import sys
    
    app = qw.QApplication([])
    main_window = qw.QMainWindow()
    main_widget = qw.QWidget()
    main_layout = qw.QHBoxLayout()
    main_widget.setLayout(main_layout)
    main_window.setCentralWidget(main_widget)
    
    cal = ImgMea_Cal()
    cal.generate_dummy_params()
    
    from iris.gui.motion_video import generate_dummy_motion_controller
    
    motion_controller = generate_dummy_motion_controller(main_widget)
    
    imghub = Wdg_DataHub_Image(main=main_widget)
    imghub.get_ImageMeasurement_Hub().test_generate_dummy()
    
    imgcalhub = Wdg_DataHub_ImgCal(main=main_widget)
    imgcalhub.get_ImageMeasurement_Calibration_Hub().generate_dummy_calibrations()
    
    mapping_method = Rect_Video(
        parent=main_widget,
        motion_controller=motion_controller,
        dataHub_img=imghub,
        dataHub_imgCal=imgcalhub,
    )
    
    main_layout.addWidget(motion_controller)
    main_layout.addWidget(mapping_method)
    main_layout.addWidget(imghub)
    main_layout.addWidget(imgcalhub)
    
    main_window.show()
    sys.exit(app.exec())
    
if __name__ == '__main__':
    pass
    test()