"""
The Camera Exposure Controller extension is designed to control the exposure time of the brightfield camera easily.
"""
import sys
import os

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'..\library')
    EXT_DIR = os.path.abspath(r'..\extensions')
    sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
    sys.path.insert(0, os.path.dirname(EXT_DIR))

import PySide6.QtWidgets as qw
from PySide6.QtCore import Qt # For context
from PySide6.QtCore import Slot

from extensions.extension_template import Extension_MainWindow
from extensions.extension_intermediary import Ext_DataIntermediary as Intermediary

from iris.controllers.class_camera_controller import Class_CameraController as Camera

from extensions.camera_exposure_controller.camera_exposure_controller_ui import Ui_camera_exposure_controller

class Ext_CameraExposureController(Ui_camera_exposure_controller, Extension_MainWindow):
    
    msg_instruction = 'Set the exposure time using the slider or the spin boxes. The current exposure time is displayed in the middle spin box.'
    
    def __init__(self, parent, intermediary: Intermediary):
        super().__init__(parent, intermediary)
        self.setupUi(self)
        self.setWindowTitle("Camera Exposure Controller")
        
        self._camera:Camera = intermediary.get_camera_controller()
        
        self.btn_instruction.clicked.connect(self._show_instruction)
        self.btn_preset1.clicked.connect(self._set_preset1_time)
        self.btn_preset2.clicked.connect(self._set_preset2_time)
        
        self.chk_stayOnTop.stateChanged.connect(self._toggle_always_on_top)
        self._toggle_always_on_top() # Set the initial state of the always on top checkbox
        
        try:
            current_exposure_time_us = self._camera.get_exposure_time_us()
            if current_exposure_time_us is None: raise ValueError('Camera returned None for current exposure time')
            self.spin_curr_ms.setValue(current_exposure_time_us/1e3)
        except Exception as e:
            qw.QMessageBox.warning(self,'Error getting current exposure time',f'Error getting the current exposure time from the camera: {e}')
        
        self._init_signals()
        
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        
    def _show_instruction(self):
        qw.QMessageBox.information(self,'Camera Exposure Controller Instructions',self.msg_instruction)
        
    @Slot()
    def _toggle_always_on_top(self) -> None:
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.chk_stayOnTop.isChecked()) # pyright: ignore[reportAttributeAccessIssue] ; WindowStaysOnTopHint exists
        self.show()
        
    def _init_signals(self):
        self.slider_relative.sliderReleased.connect(self._set_current_spin_time)
        self.spin_curr_ms.returnPressed.connect(self._set_current_slider_time)
        
        self.btn_preset1.clicked.connect(self._set_preset1_time)
        self.btn_preset2.clicked.connect(self._set_preset2_time)
        
    def _block_signals(self, block:bool):
        self.slider_relative.blockSignals(block)
        self.spin_curr_ms.blockSignals(block)
        
    @Slot()
    def _set_current_spin_time(self):
        """
        Sets the current exposure time spin box to the value of the slider
        """
        print('Setting current spin time')
        max = self.spin_max_ms.value()
        min = self.spin_min_ms.value()
        exposure_time_percent = self.slider_relative.value()
        
        curr = min + (max - min) * exposure_time_percent / 100
        
        self._block_signals(True)
        self.spin_curr_ms.setValue(curr)
        try:
            self._camera.set_exposure_time_us(curr*1e3)
            current_exposure_time_us = self._camera.get_exposure_time_us()
            self.spin_curr_ms.setValue(current_exposure_time_us/1e3) if current_exposure_time_us is not None else None
        except Exception as e:
            qw.QMessageBox.warning(self,'Error getting current exposure time',f'Error getting the current exposure time from the camera: {e}')
        self._block_signals(False)
        
    @Slot()
    def _set_current_slider_time(self):
        """
        Sets the current exposure time slider to the value of the spin box
        
        Args:
            exposure_time_ms (float | None): The exposure time in milliseconds to set. If None, it will get the value from the spin box
        """
        print('Setting current slider time')
        max = self.spin_max_ms.value()
        min = self.spin_min_ms.value()
        exposure_time_ms = self.spin_curr_ms.value()
        
        curr_rel = int((exposure_time_ms - min) / (max - min) * 100)
        
        self._block_signals(True)        
        self.slider_relative.setValue(curr_rel)
        try:
            self._camera.set_exposure_time_us(exposure_time_ms*1e3)
            current_exposure_time_us = self._camera.get_exposure_time_us()
            self.spin_curr_ms.setValue(current_exposure_time_us/1e3) if current_exposure_time_us is not None else None
        except Exception as e:
            qw.QMessageBox.warning(self,'Error getting current exposure time',f'Error getting the current exposure time from the camera: {e}')
        
        self._block_signals(False)
        
    @Slot()
    def _set_preset1_time(self):
        """
        Sets the current exposure time to the preset time selected by the user
        """ 
        preset1_time_ms = self.spin_preset1_ms.value()
        self.spin_curr_ms.setValue(preset1_time_ms)
        self._set_current_slider_time()
        
    @Slot()
    def _set_preset2_time(self):
        """
        Sets the current exposure time to the preset time selected by the user
        """
        preset2_time_ms = self.spin_preset2_ms.value()
        self.spin_curr_ms.setValue(preset2_time_ms)
        self._set_current_slider_time()
        
    