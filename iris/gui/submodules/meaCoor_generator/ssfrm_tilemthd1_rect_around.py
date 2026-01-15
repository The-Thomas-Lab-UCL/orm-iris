import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread

from typing import Callable


import numpy as np
from math import ceil
from scipy.interpolate import griddata

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.gui.motion_video import Wdg_MotionController
from iris.gui.hilvl_coorGen import Wdg_Treeview_MappingCoordinates

from iris.data.calibration_objective import ImgMea_Cal, generate_dummy_calibrationHub
from iris.data.measurement_coordinates import List_MeaCoor_Hub, MeaCoor_mm

from iris.resources.tiling_method_control_ui import Ui_tiling_method_control

class TilingMethodControl_Design(Ui_tiling_method_control, qw.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)

OVERLAP = 0.00   # Overlap between each tile (ratio to the image size)

class worker_zcoor_getter(QObject):
    """
    A worker class to get the current Z coordinate in a separate thread
    """
    sig_return_zcoor = Signal(float)  # Signal to return the Z coordinate
    
    def __init__(self, motion_controller:Wdg_MotionController):
        super().__init__()
        self._motion_controller = motion_controller
        
    @Slot()
    def get_current_zcoor(self):
        """Gets the current Z coordinate from the motion controller and emits it
        """
        try:
            z_mm = self._motion_controller.get_coordinates_closest_mm()[2]
            self.sig_return_zcoor.emit(z_mm)
        except Exception as e:
            print('worker_zcoor_getter >> Error getting current Z coordinate:',e)

class tiling_method_rectxy_scan_constz_around_a_point(qw.QWidget):
    """
    A basic class that manage a mapping method

    Args:
        tk (tkinter): tkinter library
    """
    sig_store_currZ = Signal()  # Signal to store the current Z coordinate
    
    def __init__(
        self,
        parent:qw.QWidget,
        motion_controller:Wdg_MotionController,
        tree_coor:Wdg_Treeview_MappingCoordinates,
        getter_cal:Callable[[],ImgMea_Cal],
        *args, **kwargs) -> None:
        # Place itself in the given master frame (container)
        super().__init__(parent)
        
        # Sets up the other controllers
        self._motion_controller = motion_controller
        self._getter_imgCal = getter_cal    # Function to get the image calibration
        
    # >>> Main widget setup <<<
        self._widget = TilingMethodControl_Design(self)
        lyt = qw.QVBoxLayout(self)
        lyt.addWidget(self._widget)
        self.setLayout(lyt)
        wdg = self._widget
        
    # >>> Top level frames <<<
        self._frm_tv_mapCoor = tree_coor
        
    # >>> Widgets <<<
        # Make the widgets to store the coordinates
        self._chk_overrideZ = wdg.chk_ZOverride
        self._entry_coorz = wdg.ent_zcoor
        btn_coorz_set = wdg.btn_currZCoor
        btn_coorz_set.clicked.connect(self.sig_store_currZ.emit)
        
        self._spin_cropx = wdg.spin_cropx
        self._spin_cropy = wdg.spin_cropy
        
    # >>> Signals <<<
        self._worker = worker_zcoor_getter(self._motion_controller)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.start()
        self.destroyed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        
        self.sig_store_currZ.connect(self._worker.get_current_zcoor)
        self._worker.sig_return_zcoor.connect(lambda z: self._entry_coorz.setText(str(float(z*1e3))))
        
    def get_tiling_coordinates_mm_and_cropFactors_rel(self) -> tuple[list[MeaCoor_mm],float,float]|None:
        """
        Returns the mapping coordinates and the cropping factors
        
        Returns:
            tuple[list[MeaCoor_mm], float, float]|None: The mapping coordinates (list of MeaCoor_mm objects), crop factor x, and crop factor y
        """
        # Make sure to keep the generated coordinates up to date
        list_meaCoor_mm = self._generate_tiling_coordinates()
        
        if list_meaCoor_mm is None:
            qw.QMessageBox.warning(self,'Error','No mapping coordinates generated. Please generate the coordinates first.')
            return None
        else:
            cropx_reduction, cropy_reduction = self._get_crop_factors()
            return (list_meaCoor_mm,cropx_reduction,cropy_reduction)
    
    def _get_xy_scales_mmPerPixel(self) -> tuple[float,float]:
        """
        Gets the pixel to um conversion factor for the x and y direction 
        
        Returns:
            tuple: The pixel to um conversion factor for the x and y direction [mm/pixel]
        """
        img_cal:ImgMea_Cal = self._getter_imgCal()
        scl_x = 1/img_cal.scale_x_pixelPerMm
        scl_y = 1/img_cal.scale_y_pixelPerMm
        return (abs(scl_x),abs(scl_y))
    
    def _get_crop_factors(self) -> tuple[float,float]:
        """
        Gets the cropping factors for the x and y direction. (Between 0 and 1)
        
        Returns:
            tuple: The cropping factors for the x and y direction
        """
        try:
            cropx_reduction = self._spin_cropx.value()/100
            cropy_reduction = self._spin_cropy.value()/100
            assert 0 <= cropx_reduction < 1 and 0 <= cropy_reduction < 1, 'Cropping factors must be between 0 and 1'
            return (cropx_reduction,cropy_reduction)
        except Exception as e:
            qw.QMessageBox.warning(self,'Error',f'{e}\nUsing the default cropping factors (0.0, 0.0) instead')
            return (0.0,0.0)
    
    def _generate_tiling_coordinates(self) -> list[MeaCoor_mm]|None:
        """
        Generates the mapping coordinates. Also stores them in its own variable and the main
        operation variable.
        
        Returns:
            list[MeaCoor_mm]|None: The mapping coordinates (list of (x,y,z) tuples) or None if an error occurs
        """
        list_meaCoor_mm = self._frm_tv_mapCoor.get_selected_mappingCoor()
        if len(list_meaCoor_mm) < 1:
            qw.QMessageBox.warning(self,'Error','Please select at least one mapping coordinate')
            return
        
        cropx_reduction, cropy_reduction = self._get_crop_factors()
        
        image_size = self._motion_controller.get_image_shape()
        if image_size is None:
            qw.QMessageBox.warning(self,'Error','No image received from the motion controller')
            return
        
        cal = self._getter_imgCal()
        if not isinstance(cal,ImgMea_Cal):
            qw.QMessageBox.warning(self,'Error','No objective calibration selected. Please set the objective calibration first.')
            return
        
        # Define the grid boundaries
        list_ret_MeaCoor_mm = [self._calculate_tiling_coordinates(meaCoor_mm, cropx_reduction, cropy_reduction, image_size, cal) for meaCoor_mm in list_meaCoor_mm]
        list_ret_MeaCoor_mm = [meaCoor_mm for meaCoor_mm in list_ret_MeaCoor_mm if len(meaCoor_mm.mapping_coordinates) > 0]
        if len(list_ret_MeaCoor_mm) == 0:
            qw.QMessageBox.warning(self,'Error','No valid mapping coordinates generated. Please check the input parameters.')
            return None
        
        return list_ret_MeaCoor_mm

    def _calculate_tiling_coordinates(self, meaCoor_mm: MeaCoor_mm, cropx_reduction: float,
        cropy_reduction: float, image_size: tuple[int, int], cal: ImgMea_Cal) -> MeaCoor_mm:
        """
        Calculates the tiling coordinates based on the input parameters.

        Args:
            meaCoor_mm (MeaCoor_mm): The mapping coordinates to tile.
            cropx_reduction (float): The cropping factor for the x direction.
            cropy_reduction (float): The cropping factor for the y direction.
            image_size (tuple[int, int]): The size of an example image to be used for the size calculation. (Typically this would be\
                an image from the video camera)
            cal (ImgMea_Cal): The objective calibration object.

        Returns:
            MeaCoor_mm: The calculated mapping coordinates with the original MeaCoor_mm mapping unit name.
        """
        list_coor_mm = meaCoor_mm.mapping_coordinates
        x_min = min([coor[0] for coor in list_coor_mm])
        x_max = max([coor[0] for coor in list_coor_mm])
        y_min = min([coor[1] for coor in list_coor_mm])
        y_max = max([coor[1] for coor in list_coor_mm])
        list_coor_xy_mm = [(coor[0], coor[1]) for coor in list_coor_mm]
        list_coor_z_mm = [coor[2] for coor in list_coor_mm]
        
        # Calculate the resolution required
        x_scale, y_scale = self._get_xy_scales_mmPerPixel()
        img_size_x, img_size_y = image_size
        x_size_mm = img_size_x * x_scale
        y_size_mm = img_size_y * y_scale
        
        # Take into account the crop and the overlap
        x_size_mm *= (1 - cropx_reduction)    # Taking into account the: Crop
        y_size_mm *= (1 - cropy_reduction)
        x_size_mm_temp, y_size_mm_temp = x_size_mm, y_size_mm
        x_size_mm -= y_size_mm_temp * abs(np.sin(cal.rotation_rad)) # Taking into account the: Rotation
        y_size_mm -= x_size_mm_temp * abs(np.sin(cal.rotation_rad))
        x_size_mm *= (1 - OVERLAP)  # Taking into account the: Overlap
        y_size_mm *= (1 - OVERLAP)
        
        # Calculate the number of points required
        num_x = ceil((x_max - x_min) / x_size_mm) + 1 # +1 to include the last point
        num_y = ceil((y_max - y_min) / y_size_mm) + 1 # +1 to include the last point
        
        m1_pointsx = num_x
        m1_pointsy = num_y
        
        # Generate linearly spaced points along each axis
        x_points_mm = np.linspace(x_min, x_max, m1_pointsx)
        y_points_mm = np.linspace(y_min, y_max, m1_pointsy)
        
        list_xy_mm = [(x, y) for x in x_points_mm for y in y_points_mm]
        
        # Interpolate the z-coordinates using griddata
        list_z_mm = griddata(
            points=list_coor_xy_mm,
            values=list_coor_z_mm,
            xi=list_xy_mm,
            method='linear',
            fill_value=np.nan
        )
        
        if self._chk_overrideZ.isChecked():
            try:
                z_override = float(self._entry_coorz.text()) * 1e-3
                list_z_mm = [z_override for _ in list_z_mm]
            except Exception as e:
                qw.QMessageBox.warning(self,'Error',f'Invalid Z-coordinate override: {e}\nUsing the interpolated Z-coordinates instead.')
        
        list_xyz_mm = [(x, y, z) for (x, y), z in zip(list_xy_mm, list_z_mm) if not np.isnan(z)]
        ret_mapCoor_mm = MeaCoor_mm(
            mappingUnit_name=meaCoor_mm.mappingUnit_name,
            mapping_coordinates=list_xyz_mm,
        )
        return ret_mapCoor_mm
            
def test_rect2():
    import sys
    from iris.gui.motion_video import generate_dummy_motion_controller
    
    app = qw.QApplication([])
    window = qw.QMainWindow()
    wdg_main = qw.QWidget()
    window.setCentralWidget(wdg_main)
    lyt = qw.QHBoxLayout()
    wdg_main.setLayout(lyt)
    
    motion_controller = generate_dummy_motion_controller(wdg_main)
    coorhub = List_MeaCoor_Hub()
    calhub = generate_dummy_calibrationHub()
    
    tree = Wdg_Treeview_MappingCoordinates(wdg_main,coorhub)
    coorhub.generate_dummy_data()
    
    wdg = tiling_method_rectxy_scan_constz_around_a_point(
        parent=wdg_main,
        motion_controller=motion_controller,
        tree_coor=tree,
        getter_cal=lambda: calhub.get_calibration(calhub.get_calibration_ids()[0])
    )
    
    lyt.addWidget(motion_controller)
    lyt.addWidget(tree)
    lyt.addWidget(wdg)
    
    window.show()
    sys.exit(app.exec())
    
if __name__ == '__main__':
    test_rect2()