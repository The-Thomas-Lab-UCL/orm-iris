"""
An instance that manages the linear z-scan method for the mapping methods.
To be used in conjunction with the 2D mapping coordinate generators.
"""
if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot

import numpy as np
from typing import Callable
    
from iris.gui.motion_video import Wdg_MotionController
from iris.utils.general import *

from iris.resources.coordinate_generators.convert_2Dto3D_ui import Ui_converter_2Dto3D

class Converter_2Dto3D_design(Ui_converter_2Dto3D,qw.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.lyt_main)

class Wdg_ZScanMethod_linear(qw.QWidget):
    """
    A class that manages the linear z-scan method for the mapping methods.
    """
    def __init__(self,parent,getter_stagecoor:Callable[[],tuple[float|None,float|None,float|None]],
                 *args, **kwargs) -> None:
        """
        Initialises the class with the necessary parameters.

        Args:
            parent: The parent widget
            getter_stagecoor (Callable[[],tuple[float,float,float]]): A function that returns the current stage coordinates.
        """
        super().__init__(parent)
        
        # Set the motion controller
        self._getter_stagecoor = getter_stagecoor
        
        # Main UI setup
        self._widget = Converter_2Dto3D_design(self)
        self._lyt_main = qw.QVBoxLayout(self)
        self._lyt_main.addWidget(self._widget)
        wdg = self._widget
        
        self._ent_start = wdg.ent_zstart_um
        self._ent_end = wdg.ent_zend_um
        self._ent_res_pt = wdg.ent_res_pt
        self._ent_res_um = wdg.ent_res_um

        wdg.btn_currcoor_start.clicked.connect(lambda: self._updatefield_with_stagecoor(self._ent_start))
        wdg.btn_currcoor_end.clicked.connect(lambda: self._updatefield_with_stagecoor(self._ent_end))
        
        self._ent_start.textChanged.connect(self._updatefield_zres_points)
        self._ent_end.textChanged.connect(self._updatefield_zres_points)
        
        self._ent_res_pt.editingFinished.connect(self._updatefield_zres_um)
        self._ent_res_um.editingFinished.connect(self._updatefield_zres_points)

    @Slot()
    def _updatefield_with_stagecoor(self,field:qw.QLineEdit) -> None:
        """
        Updates the given field with the current stage coordinate.

        Args:
            field (qw.QLineEdit): The field to update.
        """
        try:
            stage_coor = self._getter_stagecoor()
            assert isinstance(stage_coor, (list, tuple)) and len(stage_coor) == 3, 'Invalid stage coordinates'
            assert all(isinstance(c, (int, float)) for c in stage_coor), 'Stage coordinates must be numeric'
            field.setText('{:.3f}'.format(stage_coor[2]*1000))  # Convert to um
        except Exception as e: print('Error in _update_field_with_stagecoor: {}'.format(e))
        
    @Slot()
    def _updatefield_zres_points(self) -> None:
        """
        Updates the z-resolution in points based on the z-resolution in micrometers.
        """
        try:
            z_start = float(self._ent_start.text())
            z_end = float(self._ent_end.text())
            z_res_um = float(self._ent_res_um.text())
            assert z_res_um > 0, 'Z-resolution must be positive'
            num_points = max(2, int(np.ceil(abs(z_end - z_start) / z_res_um)) + 1)
            self._ent_res_pt.setText(str(num_points))
        except Exception as e: pass
        
    @Slot()
    def _updatefield_zres_um(self) -> None:
        """
        Updates the z-resolution in micrometers based on the z-resolution in points.
        """
        try:
            z_start = float(self._ent_start.text())
            z_end = float(self._ent_end.text())
            z_res_pt = int(self._ent_res_pt.text())
            assert z_res_pt >= 2, 'Z-resolution must be at least 2 points'
            z_res_um = abs(z_end - z_start) / (z_res_pt - 1)
            self._ent_res_um.setText('{:.3f}'.format(z_res_um))
        except Exception as e: pass
        
    def get_coordinates_mm(self,mapping_coor:list[tuple[float,float,float]]) -> list[list[tuple[float,float,float]]]|None:
        """
        Converts the 2D mapping coordinates to 3D coordinates for the z-scan method.

        Args:
            mapping_coor (list[tuple[float,float,float]]): The mapping coordinates

        Returns:
            list[list[tuple[float,float,float]]]|None: List of 2D mapping coordinates with varying z-scan coordinates OR
                None if the z-scan parameters are not set.
        """
        try:
            z_start = float(self._ent_start.text())
            z_end = float(self._ent_end.text())
            z_res = int(self._ent_res_pt.text())
            mapping_coor_3D = []
            zcoors = np.linspace(z_start/1000,z_end/1000,z_res)  # Convert to mm
            for z in zcoors:
                mapping_coor_2D = [(coor[0],coor[1],z) for coor in mapping_coor]
                mapping_coor_3D.append(mapping_coor_2D)
            return mapping_coor_3D
        except Exception as e:
            qw.QMessageBox.warning(self,'Z-scan Error',
                                   'An error occurred while generating Z-scan coordinates:\n{}'.format(e))
            return None
            
    def report_params(self) -> None:
        """
        Prints the current parameters to the console.
        """
        try:
            print('Z-scan parameters: {}'.format(get_timestamp_us_str()))
            print(f'Z-start: {self._ent_start.text()} um')
            print(f'Z-end: {self._ent_end.text()} um')
            print(f'Z-resolution: {self._ent_res_um.text()} um')
            print('Z-scan coors: {}'.format(np.linspace(
                float(self._ent_start.text()),float(self._ent_end.text()),int(self._ent_res_pt.text()))))
        except:
            pass
            
if __name__ == '__main__':
    import time
    
    app = qw.QApplication(sys.argv)
    window = qw.QMainWindow()
    window.show()
    wdg = qw.QWidget()
    lyt = qw.QVBoxLayout(wdg)
    window.setCentralWidget(wdg)
    
    def get_stagecoor() -> tuple[float,float,float]:
        return (np.random.rand(),np.random.rand(),np.random.rand())
    
    wdg_zscan = Wdg_ZScanMethod_linear(wdg,get_stagecoor)
    lyt.addWidget(wdg_zscan)
    
    def constant_report():
        while True:
            wdg_zscan.report_params()
            time.sleep(1)
    threading.Thread(target=constant_report).start()
    
    sys.exit(app.exec())