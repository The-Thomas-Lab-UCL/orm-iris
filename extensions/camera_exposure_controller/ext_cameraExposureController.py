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

import math

import numpy as np

import PySide6.QtWidgets as qw
from PySide6.QtCore import Qt, Slot, Signal, QObject, QThread, QTimer

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from extensions.extension_template import Extension_MainWindow
from extensions.extension_intermediary import Ext_DataIntermediary as Intermediary

from iris.controllers.class_camera_controller import Class_CameraController as Camera

from extensions.camera_exposure_controller.camera_exposure_controller_ui import Ui_camera_exposure_controller


class _HistogramWorker(QObject):
    sig_histogram = Signal(np.ndarray)

    def __init__(self, camera: Camera):
        super().__init__()
        self._camera = camera
        self._timer: QTimer | None = None

    @Slot()
    def start(self):
        self._timer = QTimer()
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._capture_and_emit)
        self._timer.start()

    @Slot()
    def stop(self):
        if self._timer:
            self._timer.stop()

    @Slot()
    def _capture_and_emit(self):
        try:
            frame = self._camera.frame_capture()
            if frame is None:
                return
            gray = np.mean(frame, axis=2).astype(np.uint8) if frame.ndim == 3 else frame.astype(np.uint8)
            counts, _ = np.histogram(gray, bins=256, range=(0, 255))
            self.sig_histogram.emit(counts)
        except Exception:
            pass


class Ext_CameraExposureController(Ui_camera_exposure_controller, Extension_MainWindow):
    
    msg_instruction = 'Set the exposure time using the slider or the spin boxes. The current exposure time is displayed in the middle spin box.'

    _sig_hist_start = Signal()
    _sig_hist_stop = Signal()
    
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
        self._init_histogram()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, '_hist_worker') and self.chk_histogram.isChecked():
            self._sig_hist_start.emit()

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, '_hist_worker'):
            self._sig_hist_stop.emit()
        
    def _show_instruction(self):
        qw.QMessageBox.information(self,'Camera Exposure Controller Instructions',self.msg_instruction)
        
    @Slot()
    def _toggle_always_on_top(self) -> None:
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.chk_stayOnTop.isChecked()) # pyright: ignore[reportAttributeAccessIssue] ; WindowStaysOnTopHint exists
        self.show()

    @Slot()
    def _toggle_histogram(self) -> None:
        if self.chk_histogram.isChecked():
            self._sig_hist_start.emit()
        else:
            self._sig_hist_stop.emit()
        
    def _init_signals(self):
        self.slider_relative.sliderReleased.connect(self._set_current_spin_time)
        self.spin_curr_ms.editingFinished.connect(self._set_current_slider_time)

        self.btn_preset1.clicked.connect(self._set_preset1_time)
        self.btn_preset2.clicked.connect(self._set_preset2_time)

        self.chk_histogram.stateChanged.connect(self._toggle_histogram)
        self.chk_logarithmic.stateChanged.connect(self._set_current_slider_time)
        
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
        min = self.spin_min_ms.value() or 0.0001
        exposure_time_percent = self.slider_relative.value()

        if self.chk_logarithmic.isChecked():
            curr = min * (max / min) ** (exposure_time_percent / 100)
        else:
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
        min = self.spin_min_ms.value() or 0.0001
        exposure_time_ms = self.spin_curr_ms.value()

        if self.chk_logarithmic.isChecked():
            curr_rel = int(math.log(exposure_time_ms / min) / math.log(max / min) * 100)
        else:
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

    def _init_histogram(self):
        fig = Figure(figsize=(2, 1.2), tight_layout=True)
        self._hist_ax = fig.add_subplot(111)
        self._hist_canvas = FigureCanvas(fig)
        self._hist_canvas.setMinimumHeight(120)
        self.lyt_histogram.addWidget(self._hist_canvas)

        self._hist_bars = self._hist_ax.bar(range(256), np.zeros(256), width=1, color='steelblue', linewidth=0)
        self._hist_ax.set_xlim(0, 255)
        self._hist_ax.set_xlabel('Brightness', fontsize=7)
        self._hist_ax.set_ylabel('Count', fontsize=7)
        self._hist_ax.tick_params(labelsize=6)

        self._hist_worker = _HistogramWorker(self._camera)
        self._hist_thread = QThread(self)
        self._hist_worker.moveToThread(self._hist_thread)
        self._hist_thread.finished.connect(self._hist_worker.deleteLater)
        self._hist_worker.sig_histogram.connect(self._update_histogram)
        self._sig_hist_start.connect(self._hist_worker.start)
        self._sig_hist_stop.connect(self._hist_worker.stop)
        self._hist_thread.start()

    @Slot(np.ndarray)
    def _update_histogram(self, counts: np.ndarray):
        for bar, h in zip(self._hist_bars, counts):
            bar.set_height(h)
        self._hist_ax.relim()
        self._hist_ax.autoscale_view(scalex=False)
        self._hist_canvas.draw_idle()

        total = int(np.dot(counts, np.arange(256)))
        mantissa, exp = f'{total:.2e}'.split('e')
        self.lbl_total.setText(f'Total: {mantissa} x 10^{int(exp)} counts')

