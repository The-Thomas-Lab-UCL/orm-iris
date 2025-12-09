"""
An instance that manages a basic mapping method in tkinter
"""
import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QTimer, QThread, QObject

import numpy as np
from math import floor

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.gui.motion_video import Wdg_MotionController
from iris.utils.general import *

from iris.resources.coordinate_generators.point_zScanLinear_ui import Ui_singlePointZScan

class MotionControllerComm_Worker(QObject):
    sig_currentCoorX_mm = Signal(float)
    sig_currentCoorY_mm = Signal(float)
    sig_currentCoorZStart_mm = Signal(float)
    sig_currentCoorZEnd_mm = Signal(float)
    
    sig_error = Signal(str)
    
    def __init__(self,motion_controller:Wdg_MotionController):
        super().__init__()
        self._motion_controller = motion_controller
        
    @Slot()
    def get_current_coor_xy(self):
        coor = self._motion_controller.get_coordinates_closest_mm()
        if not all((isinstance(c, (int,float)) for c in coor)):
            self.sig_error.emit('Could not retrieve current XY coordinates from motion controller.')
            return
        
        self.sig_currentCoorX_mm.emit(coor[0])
        self.sig_currentCoorY_mm.emit(coor[1])
        
    @Slot()
    def get_current_coor_zStart(self):
        coor = self._motion_controller.get_coordinates_closest_mm()
        if not isinstance(coor[2], (int,float)):
            self.sig_error.emit('Could not retrieve current Z coordinate from motion controller.')
            return
        
        self.sig_currentCoorZStart_mm.emit(coor[2])
        
    @Slot()
    def get_current_coor_zEnd(self):
        coor = self._motion_controller.get_coordinates_closest_mm()
        if not isinstance(coor[2], (int,float)):
            self.sig_error.emit('Could not retrieve current Z coordinate from motion controller.')
            return
        
        self.sig_currentCoorZEnd_mm.emit(coor[2])

class singlePoint_zScan(Ui_singlePointZScan, qw.QWidget):
    sig_request_currentCoorXY = Signal()
    sig_request_currentCoorZStart = Signal()
    sig_request_currentCoorZEnd = Signal()
    
    sig_updateResPt = Signal()
    sig_updateResUm = Signal()
    
    def __init__(self,parent,motion_controller:Wdg_MotionController,
                 *args, **kwargs) -> None:
        """Initializes the mapping method
        
        Args:
            parent (qw.QWidget): The widget to place the mapping method
            motion_controller (Frm_MotionController): The motion controller to control the stage
            status_bar (tk.Label, optional): The status bar to show the status of the mapping method. Defaults to None.
        """
        # Place itself in the given master widget (container)
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
        # Sets up the other controllers
        self._motion_controller = motion_controller
        
        # Make the widgets to store the coordinates
        self.btn_storeXY.clicked.connect(self.sig_request_currentCoorXY.emit)
        self.btn_storeZStart.clicked.connect(self.sig_request_currentCoorZStart.emit)
        self.btn_storeZEnd.clicked.connect(self.sig_request_currentCoorZEnd.emit)
        
        self._init_workers()
        self._init_signals()
    
    def _init_workers(self) -> None:
        """
        Initialises the worker threads for communication with the motion controller
        """
        self._thread = QThread()
        self._worker = MotionControllerComm_Worker(self._motion_controller)
        self._worker.moveToThread(self._thread)
        
        self._worker.sig_currentCoorX_mm.connect(lambda x: self.spin_coorx.setValue(x*1e3))
        self._worker.sig_currentCoorY_mm.connect(lambda y: self.spin_coory.setValue(y*1e3))
        self._worker.sig_currentCoorZStart_mm.connect(lambda z: self.spin_coorZStart.setValue(z*1e3))
        self._worker.sig_currentCoorZEnd_mm.connect(lambda z: self.spin_coorZEnd.setValue(z*1e3))
        self._worker.sig_error.connect(lambda msg: qw.QMessageBox.warning(self,'Error',msg))
        
        self.sig_request_currentCoorXY.connect(self._worker.get_current_coor_xy)
        self.sig_request_currentCoorZStart.connect(self._worker.get_current_coor_zStart)
        self.sig_request_currentCoorZEnd.connect(self._worker.get_current_coor_zEnd)
        
        self._thread.start()
    
    def _init_signals(self) -> None:
        """
        Initialises the signals for the widgets
        """
        self.spin_resPt.valueChanged.connect(self._update_resolution_um)
        self.spin_resUm.valueChanged.connect(self._update_resolution_points)
        
        self.spin_coorZStart.valueChanged.connect(self._update_resolution_points)
        self.spin_coorZEnd.valueChanged.connect(self._update_resolution_points)
    
    def _block_signals_resolution(self,block:bool):
        """
        Blocks the signals for the resolution widgets
        
        Args:
            block (bool): Whether to block the signals
        """
        self.spin_resPt.blockSignals(block)
        self.spin_resUm.blockSignals(block)
    
    @Slot()
    def _update_resolution_points(self):
        """
        Updates the resolution in points based on the resolution in micrometers
        """
        self._block_signals_resolution(True)
        
        coor_z1_um = self.spin_coorZStart.value()
        coor_z2_um = self.spin_coorZEnd.value()
        res_um = self.spin_resUm.value()
        
        num_points = int(abs(coor_z2_um - coor_z1_um) / res_um) + 1 if res_um != 0 else 1
        self.spin_resPt.setValue(num_points)
        
        self._block_signals_resolution(False)
        
    @Slot()
    def _update_resolution_um(self):
        """
        Updates the resolution in micrometers based on the resolution in points
        """
        self._block_signals_resolution(True)
        
        coor_z1_um = self.spin_coorZStart.value()
        coor_z2_um = self.spin_coorZEnd.value()
        res_pt = self.spin_resPt.value()
        
        if res_pt > 1:
            res_um = abs(coor_z2_um - coor_z1_um) / (res_pt - 1)
        else:
            res_um = abs(coor_z2_um - coor_z1_um)
        
        self.spin_resUm.setValue(res_um)
        
        self._block_signals_resolution(False)
    
    def get_mapping_coordinates_mm(self):
        """ 
        Returns the mapping coordinates
        
        Returns:
            list: List of tuple (x,y,z) coordinates
        """
        coor_xy_um = self.spin_coorx.value(), self.spin_coory.value()
        coor_z1_um = self.spin_coorZStart.value()
        coor_z2_um = self.spin_coorZEnd.value()
        res_z_um = self.spin_resPt.value()
        
        # Generate the mapping coordinates
        list_z_um = np.linspace(coor_z1_um,coor_z2_um,num=int(abs(coor_z2_um-coor_z1_um)/res_z_um)+1)
        list_mapping_coor_mm = [(coor_xy_um[0]/1e3,coor_xy_um[1]/1e3,z/1e3) for z in list_z_um]
        
        return list_mapping_coor_mm
        
    
def test_rect1():
    from iris.gui.motion_video import generate_dummy_motion_controller
    import sys
    
    app = qw.QApplication([])
    mw = qw.QMainWindow()
    mwdg = qw.QWidget()
    mw.setCentralWidget(mwdg)
    lyt = qw.QHBoxLayout()
    mwdg.setLayout(lyt)
    
    motion_controller = generate_dummy_motion_controller(mwdg)
    mapping_method = singlePoint_zScan(mwdg,motion_controller)
    
    lyt.addWidget(motion_controller)
    lyt.addWidget(mapping_method)
    
    mw.show()
    
    sys.exit(app.exec())
    
if __name__ == '__main__':
    test_rect1()