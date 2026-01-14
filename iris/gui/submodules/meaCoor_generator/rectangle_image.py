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
from PySide6.QtCore import Signal, Slot, QThread, QObject

import numpy as np
from PIL.Image import Image

from iris.gui.motion_video import Wdg_MotionController
from iris.utils.general import *

from iris.data.calibration_objective import ImgMea_Cal, ImgMea_Cal_Hub
from iris.data.measurement_image import MeaImg_Unit, MeaImg_Handler
from iris.gui.image_calibration.Canvas_ROIdefinition import Canvas_Image_Annotations
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image

from iris.data import SaveParamsEnum
from iris.gui import AppPlotEnum

from iris.resources.coordinate_generators.rect_image_ui import Ui_Rect_Image

class CanvasUpdater_Worker(QObject):
    """
    A worker class to automatically update the video feed canvas
    with the image unit and the clicked coordinates
    """
    sig_error = Signal(str)
    
    sig_img_stageCoor_mm = Signal(tuple)
    
    sig_updateImage = Signal(Image)
    sig_annotateRectangle = Signal(tuple,tuple,bool)
    
    sig_finished = Signal() # To indicate that the canvas update is finished
    
    def __init__(self, canvas_image:Canvas_Image_Annotations, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._canvas_image = canvas_image
        self.sig_updateImage.connect(self._canvas_image.set_image)
        self.sig_annotateRectangle.connect(self._canvas_image.draw_rectangle_canvas)
        
    @Slot(MeaImg_Unit,bool)
    def _update_image_shown(self, imgUnit:MeaImg_Unit, low_resolution:bool) -> None:
        """
        Updates the image shown on the canvas
        """
        img, stage_coor_mm, _ = imgUnit.get_image_all_stitched(low_res=low_resolution)
        self.sig_updateImage.emit(img)
        self.sig_img_stageCoor_mm.emit(stage_coor_mm)
        self.sig_finished.emit()
    
    @Slot(MeaImg_Unit,bool,list)
    def _update_image_annotation_rectangle(self, imgUnit:MeaImg_Unit, low_resolution:bool,
        list_rect_meaCoors_mm:list[tuple[float,float]]):
        """
        Automatically updates the image shown on the canvas with the rectangle annotations
        
        Args:
            imgUnit (MeaImg_Unit): The image measurement unit
            low_resolution (bool): Whether to use low resolution image
            list_rect_meaCoors_mm (list[tuple[float,float]]): The rectangle coordinates in mm
        """
        assert isinstance(imgUnit,MeaImg_Unit), 'imgUnit must be an instance of MeaImg_Unit'
        assert isinstance(list_rect_meaCoors_mm,list), 'list_rect_meaCoors_mm must be a list'
        assert all(isinstance(coor,(tuple,list)) and len(coor)>=2 for coor in list_rect_meaCoors_mm), \
            'list_rect_meaCoors_mm must be a list of tuples of length 2'
            
        # Clear the click coordinates and the annotations
        self._canvas_image.clear_all_annotations()
        
        _, stage_coor_mm, _ = imgUnit.get_image_all_stitched(low_res=True)
        
        # Draw the rectangle coordinatesf
        if len(list_rect_meaCoors_mm) == 2:
            # Convert the measurement coor back to stage coor
            try:
                coor_pxl_min = imgUnit.convert_stg2imgpt(coor_stage_mm=stage_coor_mm,\
                    coor_point_mm=list_rect_meaCoors_mm[0],correct_rot=True,low_res=low_resolution)
                coor_pxl_max = imgUnit.convert_stg2imgpt(coor_stage_mm=stage_coor_mm,\
                    coor_point_mm=list_rect_meaCoors_mm[1],correct_rot=True,low_res=low_resolution)
                
                # print(f'Annotating rectangle at pixel coords: {coor_pxl_min} to {coor_pxl_max}')
                
                self._canvas_image.stop_recordClicks()
                self.sig_annotateRectangle.emit(coor_pxl_min,coor_pxl_max,True)
                self.sig_finished.emit()
            except Exception as e: self.sig_error.emit(f'Error updating rectangle annotation: {e}')

class Rect_Image(Ui_Rect_Image, qw.QWidget):
    
    sig_updateImageCombobox = Signal()
    sig_updateResPt = Signal()
    sig_updateResUm = Signal()
    
    sig_resetStoredCoors = Signal() # To reset the stored coordinates
    
    sig_updateCanvasRectangle = Signal(MeaImg_Unit,bool,list)
    sig_updateCanvasImage = Signal(MeaImg_Unit,bool)
    
    def __init__(
        self,
        parent: qw.QWidget,
        motion_controller:Wdg_MotionController,
        dataHub_img:Wdg_DataHub_Image,
        *args, **kwargs
        ):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
    # >>> General setup <<<
        self._motion_controller = motion_controller
        self._dataHub_img = dataHub_img
        
        video_feed_size = AppPlotEnum.MAP_METHOD_IMAGE_VIDEO_SIZE.value
        
        # Parameters
        self._imgUnit:MeaImg_Unit|None = None    # The image unit object
        self._img:Image|None = None                  # The image shown on the canvas
        self._img_coor_stage_mm:tuple|None = None    # The stage coordinates corresponding to the self._img camera frame of reference
        
    # >>> Video feed setup <<<
        # Parameters
        self._list_imgunit_names:list[str] = []

        # Canvas setup
        self._canvas_image = Canvas_Image_Annotations(self,size_pixel=video_feed_size)
        self.lyt_canvas.addWidget(self._canvas_image)
        self._canvas_image.start_recordClicks()
        
        self.combo_image.activated.connect(self._update_image_shown)
        
        # Params
        self._list_clickMeaCoor_mm = []     # The list of clicked coordinates in mm
        self._list_rect_meaCoors_mm = []    # The rectangle coordinates for the scan area in mm
        
    # > Z-coordinate setup widgets <
        self.btn_storeZ.clicked.connect(self._store_current_coorz)
        
    # >>> Worker and signals setup <<<
        self._init_signals()
        self._init_workers()

    def _init_signals(self):
        """
        Initialises the signals and slots for the GUI
        """
        # Set scan area button
        self.btn_defineROI.clicked.connect(self._set_scan_area)
        self.btn_instruction.clicked.connect(self._show_instructions)
        
        # Image unit combobox
        self.combo_image.setEnabled(False)
        self._dataHub_img.get_ImageMeasurement_Hub().add_observer(self.sig_updateImageCombobox.emit)
        self.sig_updateImageCombobox.connect(self._update_combobox_imageUnits)
        self.sig_updateImageCombobox.emit()
        
        # Resolution spinbox signals
        self.sig_updateResPt.connect(self._update_resolution_pt)
        self.sig_updateResUm.connect(self._update_resolution_um)
        
        self.spin_resXPt.editingFinished.connect(self.sig_updateResUm.emit)
        self.spin_resYPt.editingFinished.connect(self.sig_updateResUm.emit)
        self.spin_resXum.editingFinished.connect(self.sig_updateResPt.emit)
        self.spin_resYum.editingFinished.connect(self.sig_updateResPt.emit)
        
        # Canvas clear annotations observer
        self._canvas_image.add_observer_rightclick(self.sig_resetStoredCoors.emit)
        self.sig_resetStoredCoors.connect(self._reset_click_coors)
        
        # Resolution checkbox
        self.chk_lres.stateChanged.connect(self._update_image_shown)
        
    def _init_workers(self):
        """
        Initialises the worker threads for automatic image updating
        """
        # Worker thread for automatic image updating
        self._thread_canvas = QThread()
        self._worker_canvas = CanvasUpdater_Worker(self._canvas_image)
        self._worker_canvas.moveToThread(self._thread_canvas)
        
        # Connect signals
        self.sig_updateCanvasImage.connect(self._worker_canvas._update_image_shown)
        self.sig_updateCanvasRectangle.connect(self._worker_canvas._update_image_annotation_rectangle)
        
        self._worker_canvas.sig_error.connect(lambda msg: qw.QMessageBox.warning(self, 'Error', msg))
        self._worker_canvas.sig_img_stageCoor_mm.connect(self._update_img_stageCoor_mm)
        self._thread_canvas.start()
    
    @Slot()
    def _show_instructions(self):
        """
        Shows the instructions for using the rectangle image mapping method
        """
        instructions = (
            "Instructions:\n"
            "1. Select an image to display\n"
            "2. Left-click on the image to include points in the ROI\n"
            "3. Right-click on the image to reset the selected points.\n"
            "4. Click the 'Define ROI' button to finalise the setup."
        )
        qw.QMessageBox.information(self, 'Instructions - Rectangle Image Mapping Method', instructions)
    
    @Slot(tuple)
    def _update_img_stageCoor_mm(self,coor_mm:tuple):
        """
        Updates the image stage coordinates
        
        Args:
            coor_mm (tuple): The stage coordinates in mm
        """
        assert isinstance(coor_mm,tuple), 'coor_mm must be a tuple'
        assert all(isinstance(c,float) for c in coor_mm), 'coor_mm must be a tuple of floats'
        self._img_coor_stage_mm = coor_mm
    
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
    def _set_scan_area(self):
        """
        Sets the scan area by taking the (x_min,y_min) and (x_max,y_max)
        from the list of clicked coordinates
        """
        imgUnit = self._get_selected_ImageUnit()
        if not isinstance(imgUnit,MeaImg_Unit):
            qw.QMessageBox.warning(self, 'Error', 'No image unit selected')
            return
        
        # Get the calibration area
        list_clickCoor_pxl = self._canvas_image.get_clickCoordinates()
        
        # Convert to mm
        list_clickCoor_mm = []
        stage_coor_mm = self._img_coor_stage_mm
        
        if stage_coor_mm is None:
            qw.QMessageBox.warning(self, 'Error', 'Image stage coordinates not available')
            return
        
        list_clickCoor_mm = [
            imgUnit.convert_imgpt2stg(
                frame_coor_mm=stage_coor_mm,
                coor_pixel=coor_pxl,
                correct_rot=True,
                low_res=self.chk_lres.isChecked()
            ) for coor_pxl in list_clickCoor_pxl]
        
        # Get the min and max coordinates
        list_x = [coor[0] for coor in list_clickCoor_mm]
        list_y = [coor[1] for coor in list_clickCoor_mm]
        
        x_min = min(list_x)
        x_max = max(list_x)
        y_min = min(list_y)
        y_max = max(list_y)
        
        coor_min = (x_min,y_min)
        coor_max = (x_max,y_max)
        
        stagecoor_min = imgUnit.convert_mea2stg(coor_min)
        stagecoor_max = imgUnit.convert_mea2stg(coor_max)
        
        self._stagecoor_init_xy_mm = stagecoor_min
        self._stagecoor_final_xy_mm = stagecoor_max
        
        # self.lbl_scanEdges.setText('({:.1f}, {:.1f}) to ({:.1f}, {:.1f}) μm'.format(
        #     x_min*1e3,y_min*1e3,x_max*1e3,y_max*1e3))
        self.lbl_scanEdges.setText('({:.1f}, {:.1f}) to ({:.1f}, {:.1f}) μm'.format(
            stagecoor_min[0]*1e3,stagecoor_min[1]*1e3,
            stagecoor_max[0]*1e3,stagecoor_max[1]*1e3))
        
        try:    # Clear the click coordinates and the annotations except the scan area
            self._list_rect_meaCoors_mm = [coor_min,coor_max]
            
            imgUnit = self._get_selected_ImageUnit()
            if imgUnit is None: raise ValueError('No image unit selected')
            
            self.sig_updateCanvasRectangle.emit(
                imgUnit,
                self.chk_lres.isChecked(),
                self._list_rect_meaCoors_mm)
            
            self.sig_updateResPt.emit()
            
        except Exception as e:
            qw.QMessageBox.warning(self, 'Error', f'Error setting scan area: {e}')
    
    @Slot()
    def _reset_click_coors(self):
        """
        Resets the click coordinates
        """
        self._list_clickMeaCoor_mm.clear()
        self._list_rect_meaCoors_mm.clear()
        self.lbl_scanEdges.setText('None')
        
        self._canvas_image.clear_all_annotations()
        self._canvas_image.start_recordClicks()
    
    @Slot()
    def _update_combobox_imageUnits(self):
        """
        Automatically updates the combobox with the image units
        """
        self.combo_image.setEnabled(False)
        hub = self._dataHub_img.get_ImageMeasurement_Hub()
        list_unit_ids = hub.get_list_ImageUnit_ids()
        dict_idToName = hub.get_dict_IDtoName()
        list_unit_names = [dict_idToName[unit_id] for unit_id in list_unit_ids]
        
        # Only updates when necessary
        if list_unit_names == self._list_imgunit_names: return
        
        self._list_imgunit_names = list_unit_names.copy()
        name = self.combo_image.currentText()
        self.combo_image.clear()
        self.combo_image.addItems(self._list_imgunit_names)
        
        if name in self._list_imgunit_names:
            self.combo_image.setCurrentText(name)
        elif len(self._list_imgunit_names) > 0:
            self.combo_image.setCurrentIndex(0)
        
        self.combo_image.setEnabled(len(self._list_imgunit_names) > 0)
    
    def _get_selected_ImageUnit(self) -> MeaImg_Unit|None:
        """
        Returns the selected image unit in the combobox

        Returns:
            ImageMeasurement_Unit|None: The selected image unit or None
        """
        unit_name = self.combo_image.currentText()
        hub = self._dataHub_img.get_ImageMeasurement_Hub()
        ret = None
        try: ret = hub.get_ImageMeasurementUnit(unit_name=unit_name)
        except Exception as e:
            print(f'Error getting selected ImageUnit: {e}')
        return ret
    
    @Slot()
    def _update_image_shown(self) -> None:
        """
        Updates the image shown on the canvas
        """
        img = self._get_selected_ImageUnit()
        if img is None:
            print('No image unit selected')
            return
        # print(f'Updating image shown: {img.get_IdName()}')
        
        self._reset_click_coors()
        
        self.sig_updateCanvasImage.emit(
            img,
            self.chk_lres.isChecked()
        )
    
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
    
    mapping_method = Rect_Image(
        parent=main_widget,
        motion_controller=motion_controller,
        dataHub_img=imghub,
    )
    
    main_layout.addWidget(motion_controller)
    main_layout.addWidget(mapping_method)
    main_layout.addWidget(imghub)
    
    main_window.show()
    sys.exit(app.exec())
    
if __name__ == '__main__':
    pass
    test()