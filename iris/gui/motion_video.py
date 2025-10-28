"""
A class that manages the motion controller aspect for the Thorlabs stages

Made on: 04 March 2024
By: Kevin Uning
For: The Thomas Group, Biochemical Engineering Dept., UCL
"""
import PySide6.QtWidgets as qw
import PySide6.QtCore as qc
from PySide6.QtCore import Qt as qt, Signal, Slot, QObject, QThread, QTimer
from PySide6.QtGui import QPixmap

import threading
import queue

from PIL import Image, ImageDraw, ImageFont, ImageQt
import cv2
import numpy as np

from typing import Callable, Literal, Any

import time

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.utils.general import *

from iris.data.calibration_objective import ImgMea_Cal

from iris.multiprocessing.basemanager import MyManager,get_my_manager
from iris.multiprocessing.dataStreamer_StageCam import DataStreamer_StageCam,initialise_manager_stage,initialise_proxy_stage

from iris.gui import AppPlotEnum, AppVideoEnum
from iris.controllers import ControllerConfigEnum
from iris.controllers import CameraController, Controller_XY, Controller_Z

class CustomButton(qw.QPushButton):
    # Define custom signals for left and right clicks
    rightClicked = Signal()
    leftClicked = Signal()
    leftReleased = Signal()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Connect the custom signals to the provided functions
        
    def set_left_click_function(self, func: Callable[[], Any]):
        """
        Sets the function to be called on left click

        Args:
            func (Callable[[], Any]): The function to be called on left click
        """
        self.leftClicked.connect(func)
        
    def set_left_release_function(self, func: Callable[[], Any]):
        """
        Sets the function to be called on left button release

        Args:
            func (Callable[[], Any]): The function to be called on left button release
        """
        self.leftReleased.connect(func)
        
    def set_right_click_function(self, func: Callable[[], Any]):
        """
        Sets the function to be called on right click

        Args:
            func (Callable[[], Any]): The function to be called on right click
        """
        self.rightClicked.connect(func)
        
    def mousePressEvent(self, event):
        if event.button() == qt.MouseButton.LeftButton:
            self.leftClicked.emit()
        elif event.button() == qt.MouseButton.RightButton:
            self.rightClicked.emit()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        if event.button() == qt.MouseButton.LeftButton:
            self.leftReleased.emit()
        super().mouseReleaseEvent(event)

class ResizableQLabel(qw.QLabel):
    def __init__(self, min_width: int=1, min_height: int=1, *args, **kwargs):
        assert isinstance(min_width,int) and min_width > 0, 'min_width must be a positive integer'
        assert isinstance(min_height,int) and min_height > 0, 'min_height must be a positive integer'
        
        super().__init__(*args, **kwargs)
        self._pixmap = QPixmap()
        self.setSizePolicy(qw.QSizePolicy.Policy.Expanding, qw.QSizePolicy.Policy.Expanding)
        self.setMinimumSize(min_width, min_height)
        
    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.resizeEvent(None)
        
    def resizeEvent(self, event):
        if not self._pixmap.isNull():
            # Get the size of the label's content area
            label_size = event.size() if event else self.size()
            scaled_pixmap = self._pixmap.scaled(
                label_size,
                qc.Qt.AspectRatioMode.KeepAspectRatio,
                qc.Qt.TransformationMode.SmoothTransformation
            )
            super().setPixmap(scaled_pixmap)
        super().resizeEvent(event)

class _Worker_move_breathing_z(QObject):
    """
    Moves the z-stage up and down for a few cycles
    
    Args:
        flg_done (threading.Event): A flag to stop the breathing motion
    """
    signal_breathing_finished = Signal()
    
    def __init__(self, ctrl_z: 'Controller_Z', parent=None):
        super().__init__(parent)
        self.ctrl_z = ctrl_z
        self._breathing_timer = QTimer(self)
        self._breathing_timer.timeout.connect(self._do_breathing_step)
        self._breathing_state = 0 # Use a state machine to track the motion
        
    @Slot()
    def start(self):
        self._breathing_timer.start(10) # 50ms interval
        
    @Slot()
    def _do_breathing_step(self):
        # A simple state machine to perform the sequence
        if self._breathing_state == 0:
            self.ctrl_z.move_jog('zfwd')
        elif self._breathing_state == 1:
            self.ctrl_z.move_jog('zrev')
        elif self._breathing_state == 2:
            self.ctrl_z.move_jog('zrev')
        elif self._breathing_state == 3:
            self.ctrl_z.move_jog('zfwd')
            
        self._breathing_state = (self._breathing_state + 1) % 4

    @Slot()
    def stop(self):
        self._breathing_timer.stop()
        self.signal_breathing_finished.emit()

class Frm_MotionController(qw.QGroupBox):
    """
    A class to control the app subwindow for the motion:
    - video output
    - stage control and calibration
    
    Future update:
    - Image recognition of the stage >> auto-detect coordinates
    >> move stage automatically by clicking on the video feed
    >> also show the move distance limitation with a red square
    inlayed on top of the video output
    
    Args:
        tk (None): Nothing needed here
    """
    signal_statbar_message = Signal(str,str)  # A signal to update the status bar message
    signal_breathing_stopped = Signal()
    
    def __init__(
        self,
        parent,
        xy_controller:Controller_XY,
        z_controller:Controller_Z,
        stageHub:DataStreamer_StageCam,
        getter_imgcal:Callable[[],ImgMea_Cal],
        flg_issimulation=True,
        main:bool=False
        ):
        # Initialise the class
        super().__init__(parent)
        self._stageHub:DataStreamer_StageCam = stageHub
        self._getter_imgcal = getter_imgcal   # A getter method to get the image calibration
        
        self._flg_isrunning = threading.Event()
        self._flg_isrunning.set()  # A flag to check if the thread is running
        
    # >>> Simulation setup <<<
        self.flg_issimulation = flg_issimulation    # If True, request the motion controller to do a simulation instead
        
    # >>> Top layout <<<
        main_layout = qw.QVBoxLayout(self)  # The main layout for the entire frame
        wdg_video = qw.QWidget(self)  # Top layout compartment for the video
        tab_motion_ctrl = qw.QTabWidget(self)  # Top layout compartment for the stage controllers
        self._statbar = qw.QStatusBar(self)  # Status bar at the bottom
        self._statbar.showMessage("Video and stage initialisation")
        
        main_layout.addWidget(wdg_video)
        main_layout.addWidget(tab_motion_ctrl)
        main_layout.addWidget(self._statbar)
        
        # Notebook setup
        self._wdg_mctrl = qw.QWidget(self)  # Bottom frame compartment for the stage controllers
        self._wdg_GoToCoord = qw.QWidget(self)  # Bottom frame compartment for the go to coordinate
        
        tab_motion_ctrl.addTab(self._wdg_mctrl,'Directional control')
        tab_motion_ctrl.addTab(self._wdg_GoToCoord,'Go to coordinate')
        tab_motion_ctrl.setCurrentIndex(0)
        
    # >>> Video widgets and parameter setup <<<
        self._camera_ctrl:CameraController = self._stageHub.get_camera_controller()
        self._video_height = ControllerConfigEnum.VIDEOFEED_HEIGHT.value    # Video feed height in pixel
        self._flg_isvideorunning = False         # A flag to turn on/off the video
        self._currentImage:Image.Image|None = None   # The current image to be displayed
        self._currentFrame = None               # The current frame to be displayed
        self._flg_isNewFrmReady = threading.Event()  # A flag to wait for the frame to be captured
        
        # >> Sub-frame setup <<
        self._init_video_widgets(stageHub, wdg_video)
        
    # >>> Motion widgets and parameter setup <<<
        # Set up the variable for the controller later
        self.ctrl_xy = xy_controller    # The xy-stage controller (proxy)
        self.ctrl_z = z_controller      # The z-stage controller (proxy)
        
        self._controller_id_camera = self._stageHub.get_camera_controller().get_identifier()
        self._controller_id_xy = self.ctrl_xy.get_identifier()
        self._controller_id_z = self.ctrl_z.get_identifier()
        
        self._controller_id_camera = self._stageHub.get_camera_controller().get_identifier()
        self._controller_id_xy = self.ctrl_xy.get_identifier()
        self._controller_id_z = self.ctrl_z.get_identifier()
        
        self._current_coor:np.ndarray = np.zeros(3)  # The current coordinates of the stage, only to be used internally!
        self._flg_ontarget_gotocoor = threading.Event() # A flag to check if the stage is on target for the go to coordinates
        
        # Connection flag
        self._flg_connectionReady_xyz = threading.Event()  # A flag to check if the reconnection is in progress
        self._flg_connectionReady_xyz.set()
        
        # Add sub-widgets
        swdg_xyz_stage_setup = qw.QWidget(self._wdg_mctrl)  # Hosts the motor parameter setup
        swdg_xyz_home = qw.QWidget(self._wdg_mctrl)         # Hosts the calibration/home buttons
        swdg_xyz_move = qw.QWidget(self._wdg_mctrl)         # Hosts the xy stage and z stage controller subframes
        swdg_joginfo_setup = qw.QWidget(self._wdg_mctrl)    # Hosts the jogging configuration
        
        # Layout configuration
        layout_xyz = qw.QVBoxLayout()
        self._wdg_mctrl.setLayout(layout_xyz)
        layout_xyz.addWidget(swdg_xyz_stage_setup)
        layout_xyz.addWidget(swdg_xyz_home)
        layout_xyz.addWidget(swdg_xyz_move)
        layout_xyz.addWidget(swdg_joginfo_setup)
        
    # >>> Continuous motion controller widgets <<<
        self._init_xyz_control_widgets(swdg_xyz_home, swdg_xyz_move)
        
    # >>> Jogging configuration widgets <<<
        self._init_xyz_jog_widgets(swdg_joginfo_setup)

    # >>> Go to coordinate widgets <<<
        # Sub-frame setup
        slyt_goto = qw.QGridLayout(self._wdg_GoToCoord) # Hosts the go to coordinate setup
        
        # Add the entry boxes
        self._init_gotocoor_widgets(slyt_goto)
        
    # >>> Motor parameter setup widgets <<<
        self._init_stageparam_widgets(swdg_xyz_stage_setup)
        
    # >>> Status update <<<
        self.signal_statbar_message.connect(self.status_update)
        self.signal_statbar_message.emit('Initialising the motion controllers','yellow')
        self._motion_controller_initialisation()
        
        if main: self.initialise_auto_updater()

    def _init_stageparam_widgets(self, slyt_xyz_stage_setup:qw.QWidget):
        """
        Initialises the widgets for the motor parameter setup

        Args:
            slyt_xyz_stage_setup (qw.QWidget): The widget to add the motor parameter controls to
        """
        # Main layout configuration
        main_layout = qw.QVBoxLayout()
        slyt_xyz_stage_setup.setLayout(main_layout)
        
        # Add the entry boxes, label, and button for the speed parameter setups
        self.lbl_speed_xy = qw.QLabel('XY speed: %')
        self.lbl_speed_z = qw.QLabel('Z speed: %')
        self.ent_speed_xy = qw.QLineEdit()
        self.ent_speed_z = qw.QLineEdit()
        self.btn_SetSpeed = qw.QPushButton('Set speed')
        
        # Bind the functions
        self.ent_speed_xy.returnPressed.connect(lambda: self._set_vel_acc_params())
        self.ent_speed_z.returnPressed.connect(lambda: self._set_vel_acc_params())
        self.btn_SetSpeed.released.connect(lambda: self._set_vel_acc_params())
        
        # Disable the widgets until the controller is initialised
        self.ent_speed_xy.setEnabled(False)
        self.ent_speed_z.setEnabled(False)
        self.btn_SetSpeed.setEnabled(False)
        
        # Layout configuration
        layout_grid = qw.QGridLayout()
        main_layout.addLayout(layout_grid)
        layout_grid.addWidget(self.lbl_speed_xy, 0, 0)
        layout_grid.addWidget(self.ent_speed_xy, 0, 1)
        layout_grid.addWidget(self.lbl_speed_z, 1, 0)
        layout_grid.addWidget(self.ent_speed_z, 1, 1)
        layout_grid.addWidget(self.btn_SetSpeed, 2, 0, 1, 2)

        # Add the entry boxes, label, and button for the jogging parameter setup
        self.lbl_jog_xy = qw.QLabel('XY step size: [µm]')
        self.lbl_jog_z = qw.QLabel('Z step size: [µm]')
        self.ent_jog_xy = qw.QLineEdit()
        self.ent_jog_z = qw.QLineEdit()
        self.btn_SetJog = qw.QPushButton('Set jog')
        
        # Bind the functions
        self.ent_jog_xy.returnPressed.connect(lambda: self._set_jog_params())
        self.ent_jog_z.returnPressed.connect(lambda: self._set_jog_params())
        self.btn_SetJog.released.connect(lambda: self._set_jog_params())
        
        # Disable the widgets until the controller is initialised
        self.ent_jog_xy.setEnabled(False)
        self.ent_jog_z.setEnabled(False)
        self.btn_SetJog.setEnabled(False)
        
        # Add to the layout
        layout_grid = qw.QGridLayout()
        main_layout.addLayout(layout_grid)
        layout_grid.addWidget(self.lbl_jog_xy, 3, 0)
        layout_grid.addWidget(self.ent_jog_xy, 3, 1)
        layout_grid.addWidget(self.lbl_jog_z, 4, 0)
        layout_grid.addWidget(self.ent_jog_z, 4, 1)
        layout_grid.addWidget(self.btn_SetJog, 5, 0, 1, 2)

    def _init_xyz_jog_widgets(self, slyt_joginfo_setup:qw.QWidget):
        """
        Initialises the widgets for the jogging configuration

        Args:
            slyt_joginfo_setup (qw.QWidget): The widget to add the jog controls to
        """
        self._chkbox_jog_enabled = qw.QCheckBox('Jogging mode')
        self._chkbox_jog_enabled.setChecked(False)  # A flag to check if the jogging is enabled
        lbl_info_jog = qw.QLabel('OR right click on the direction buttons to jog')
        lbl_info_jog.setStyleSheet('background-color: yellow')
        
        # Layout configuration
        main_layout_jog = qw.QVBoxLayout()
        slyt_joginfo_setup.setLayout(main_layout_jog)
        
        main_layout_jog.addWidget(self._chkbox_jog_enabled)
        main_layout_jog.addWidget(lbl_info_jog)

    def _init_gotocoor_widgets(self, slyt_goto:qw.QGridLayout):
        """
        Initialises the widgets for the go to coordinate setup

        Args:
            slyt_goto (qw.QGridLayout): The layout to add the widgets to
        """
        self.ent_coor_x = qw.QLineEdit()
        self.ent_coor_y = qw.QLineEdit()
        self.ent_coor_z = qw.QLineEdit()
        
        # Bind: Enter to go to the coordinates
        self.ent_coor_x.returnPressed.connect(lambda: self._move_go_to())
        self.ent_coor_y.returnPressed.connect(lambda: self._move_go_to())
        self.ent_coor_z.returnPressed.connect(lambda: self._move_go_to())

        # Add the labels
        lbl_coor_x = qw.QLabel('X-coordinate: [μm]')
        lbl_coor_y = qw.QLabel('Y-coordinate: [μm]')
        lbl_coor_z = qw.QLabel('Z-coordinate: [μm]')
        
        # Add the go to button
        btn_goto = qw.QPushButton('Go to')
        btn_goto.released.connect(lambda: self._move_go_to())
        btn_goto.setEnabled(False)
        
        # Layout configuration
        slyt_goto.addWidget(lbl_coor_x,0,0)
        slyt_goto.addWidget(self.ent_coor_x,0,1)
        slyt_goto.addWidget(lbl_coor_y,1,0)
        slyt_goto.addWidget(self.ent_coor_y,1,1)
        slyt_goto.addWidget(lbl_coor_z,2,0)
        slyt_goto.addWidget(self.ent_coor_z,2,1)
        slyt_goto.addWidget(btn_goto,3,0,1,2)

    def _init_xyz_control_widgets(self, swdg_xyz_home:qw.QWidget, swdg_xyz_move:qw.QWidget):
        """
        Initialises the widgets for the xyz stage control.

        Args:
            swdg_xyz_home (qw.QWidget): Widget for the home/calibration controls.
            swdg_xyz_move (qw.QWidget): Widget for the movement controls.
        """
        main_layout_move = qw.QHBoxLayout()
        swdg_xyz_move.setLayout(main_layout_move)
        
        sslyt_xy_move = qw.QGridLayout()    # Hosts the xy stage controller
        sslyt_z_move = qw.QVBoxLayout()     # Hosts the z stage controller
        main_layout_move.addLayout(sslyt_xy_move)
        main_layout_move.addLayout(sslyt_z_move)
        
        # Add the buttons (disabled until controller initialisation)
        ## Add the buttons for the xy stage
        self.btn_xy_up = CustomButton('up')
        self.btn_xy_down = CustomButton('down')
        self.btn_xy_right= CustomButton('right')
        self.btn_xy_left = CustomButton('left')
        
        # Disable the buttons until the controller is initialised
        self.btn_xy_up.setEnabled(False)
        self.btn_xy_down.setEnabled(False)
        self.btn_xy_right.setEnabled(False)
        self.btn_xy_left.setEnabled(False)
        
        # Bind the functions
        self.btn_xy_up.set_left_click_function(lambda: self.motion_button_manager('yfwd'))
        self.btn_xy_down.set_left_click_function(lambda: self.motion_button_manager('yrev'))
        self.btn_xy_right.set_left_click_function(lambda: self.motion_button_manager('xfwd'))
        self.btn_xy_left.set_left_click_function(lambda: self.motion_button_manager('xrev'))
        
        self.btn_xy_up.set_left_release_function(lambda: self.motion_button_manager('ystop'))
        self.btn_xy_down.set_left_release_function(lambda: self.motion_button_manager('ystop'))
        self.btn_xy_right.set_left_release_function(lambda: self.motion_button_manager('xstop'))
        self.btn_xy_left.set_left_release_function(lambda: self.motion_button_manager('xstop'))
        
        self.btn_xy_up.set_right_click_function(lambda: self.move_jog('yfwd'))
        self.btn_xy_down.set_right_click_function(lambda: self.move_jog('yrev'))
        self.btn_xy_right.set_right_click_function(lambda: self.move_jog('xfwd'))
        self.btn_xy_left.set_right_click_function(lambda: self.move_jog('xrev'))
        
        # Layout configuration        
        sslyt_xy_move.addWidget(self.btn_xy_up,0,1)
        sslyt_xy_move.addWidget(self.btn_xy_left,1,0)
        sslyt_xy_move.addWidget(self.btn_xy_right,1,2)
        sslyt_xy_move.addWidget(self.btn_xy_down,2,1)
        
        ## Add the buttons for the z stage
        self.btn_z_up = CustomButton('up')
        self.btn_z_down = CustomButton('down')
        self._btn_z_breathing = qw.QPushButton('Breathing')
        
        # Disable the buttons until the controller is initialised
        self.btn_z_up.setEnabled(False)
        self.btn_z_down.setEnabled(False)
        self._btn_z_breathing.setEnabled(False)
        
        # Bind the functions
        self.btn_z_up.set_left_click_function(lambda: self.motion_button_manager('zfwd'))
        self.btn_z_down.set_left_click_function(lambda: self.motion_button_manager('zrev'))
        self._btn_z_breathing.released.connect(lambda: self._start_breathing_z())
        
        self.btn_z_up.set_left_release_function(lambda: self.motion_button_manager('zstop'))
        self.btn_z_down.set_left_release_function(lambda: self.motion_button_manager('zstop'))
        
        self.btn_z_up.set_right_click_function(lambda: self.move_jog('zfwd'))
        self.btn_z_down.set_right_click_function(lambda: self.move_jog('zrev'))
        
        # Layout configuration
        sslyt_z_move.addWidget(self.btn_z_up)
        sslyt_z_move.addWidget(self.btn_z_down)
        sslyt_z_move.addStretch(1)
        sslyt_z_move.addWidget(self._btn_z_breathing)
        
        ## Home/Calibration buttons
        self.btn_xy_home = qw.QPushButton('XY-Home/Calibration')
        self.btn_z_home = qw.QPushButton('Z-Home/Calibration')
        
        self.btn_xy_home.setEnabled(False)
        self.btn_z_home.setEnabled(False)
        
        self.btn_xy_home.released.connect(lambda: self.motion_button_manager('xyhome'))
        self.btn_z_home.released.connect(lambda: self.motion_button_manager('zhome'))
        
        self.btn_xy_reinit = qw.QPushButton('Reset XY connection')
        self.btn_z_reinit = qw.QPushButton('Reset Z connection')
        
        self.btn_xy_reinit.setEnabled(False)
        self.btn_z_reinit.setEnabled(False)
        
        self.btn_xy_reinit.released.connect(lambda: self.reinitialise_connection('xy'))
        self.btn_z_reinit.released.connect(lambda: self.signal_statbar_message.emit('Z re-initialisation is not yet implemented', 'yellow'))
        
        # Layout configuration
        main_layout_home = qw.QHBoxLayout()
        swdg_xyz_home.setLayout(main_layout_home)
        sslyt_xy_home_init = qw.QVBoxLayout()
        sslyt_z_home_init = qw.QVBoxLayout()
        main_layout_home.addLayout(sslyt_xy_home_init)
        main_layout_home.addLayout(sslyt_z_home_init)
        
        sslyt_xy_home_init.addWidget(self.btn_xy_home)
        sslyt_xy_home_init.addWidget(self.btn_xy_reinit)
        
        sslyt_z_home_init.addWidget(self.btn_z_home)
        sslyt_z_home_init.addWidget(self.btn_z_reinit)
        
    def _init_video_widgets(self, stageHub: DataStreamer_StageCam, lyt_video: qw.QWidget):
        """
        Initialises the video widgets and layouts

        Args:
            stageHub (DataStreamer_StageCam): The stage hub for video streaming
            lyt_video (qw.QWidget): The layout widget for the video feed
        """
        main_layout = qw.QVBoxLayout()
        lyt_video.setLayout(main_layout)
        
        slyt_video = qw.QVBoxLayout()  # The layout for the video compartment
        slyt_video_ctrl = qw.QVBoxLayout()  # Hosts the video controller subframe
        slyt_video_coor = qw.QVBoxLayout()  # Hosts the video coordinate reporting subframe
        main_layout.addLayout(slyt_video)
        main_layout.addLayout(slyt_video_ctrl)
        main_layout.addLayout(slyt_video_coor)
        
        # > Video
        self._lbl_video = ResizableQLabel(min_height=self._video_height,parent=lyt_video)    # A label to show the video feed
        
        slyt_video.addWidget(self._lbl_video)
        
        # > Video controllers
        self._btn_videotoggle = qw.QPushButton('Turn camera ON')
        self._btn_reinit_conn = qw.QPushButton('Reset camera connection')
        self._btn_videotoggle.released.connect(lambda: self.video_initialise())
        self._btn_reinit_conn.released.connect(lambda: self.reinitialise_connection('camera'))
        self._btn_videotoggle.setStyleSheet('background-color: yellow')
        self._btn_reinit_conn.setStyleSheet('background-color: yellow')
        
        self._chkbox_crosshair = qw.QCheckBox('Show crosshair')
        self._chkbox_scalebar = qw.QCheckBox('Show scalebar')
        self._chkbox_crosshair.setChecked(False)
        self._chkbox_scalebar.setChecked(True)
        
        btn_set_imgproc_gain = qw.QPushButton('Set flatfield gain')
        btn_set_flatfield = qw.QPushButton('Set flatfield')
        btn_save_flatfield = qw.QPushButton('Save flatfield')
        btn_load_flatfield = qw.QPushButton('Load flatfield')
        btn_set_imgproc_gain.released.connect(lambda: self._set_imageProc_gain())
        btn_set_flatfield.released.connect(lambda: self._set_flatfield_correction_camera())
        btn_save_flatfield.released.connect(lambda: self._save_flatfield_correction())
        btn_load_flatfield.released.connect(lambda: self._load_flatfield_correction())
        
        # Video corrections
        self._dict_vidcorrection = {}
        self._combo_vidcorrection = qw.QComboBox()
        self._combo_vidcorrection.addItems(list(stageHub.Enum_CamCorrectionType.__members__))
        self._combo_vidcorrection.setCurrentIndex(0)
        
        ## Layout setups
        sslyt_video_ctrl1 = qw.QHBoxLayout()
        sslyt_video_ctrl2 = qw.QHBoxLayout()
        sslyt_video_ctrl3 = qw.QGridLayout()
        slyt_video_ctrl.addLayout(sslyt_video_ctrl1)
        slyt_video_ctrl.addLayout(sslyt_video_ctrl2)
        slyt_video_ctrl.addWidget(self._combo_vidcorrection)
        slyt_video_ctrl.addLayout(sslyt_video_ctrl3)
        
        sslyt_video_ctrl1.addWidget(self._chkbox_crosshair)
        sslyt_video_ctrl1.addWidget(self._chkbox_scalebar)
        
        sslyt_video_ctrl2.addWidget(self._btn_videotoggle)
        sslyt_video_ctrl2.addWidget(self._btn_reinit_conn)
        
        sslyt_video_ctrl3.addWidget(btn_set_imgproc_gain,0,0)
        sslyt_video_ctrl3.addWidget(btn_set_flatfield,0,1)
        sslyt_video_ctrl3.addWidget(btn_save_flatfield,1,0)
        sslyt_video_ctrl3.addWidget(btn_load_flatfield,1,1)
        
        # > Coordinate reporting
        self._lbl_coor = qw.QLabel('Stage coordinates (x,y,z): ')
        slyt_video_coor.addWidget(self._lbl_coor)
        
    def _set_imageProc_gain(self):
        """
        Sets the gain for the image processing (not setting the gain of the camera directly but
        through the stage hub). Especially useful for the flatfield correction without overexposing
        the camera.
        """
        try:
            init_gain = self._stageHub.get_flatfield_gain()
            new_gain = messagebox_request_input(
                'Set gain',
                'Set gain for the image processing (not camera gain)',
                str(init_gain))
            
            self._stageHub.set_flatfield_gain(float(new_gain))
            qw.QMessageBox.information(self, 'Gain set', 'Gain set to {}'.format(self._stageHub.get_flatfield_gain()))
        except Exception as e:
            qw.QMessageBox.critical(self, 'Error', 'Failed to set gain:\n' + str(e))
            
    def _set_flatfield_correction_camera(self):
        """
        Sets the flatfield correction using the camera's current image
        """
        try:
            img = self._camera_ctrl.img_capture()
            img_arr = np.array(img)
            
            self._stageHub.set_flatfield_reference(img_arr)
            qw.QMessageBox.information(self, 'Flatfield correction', 'Flatfield correction set to the current camera image')
        except Exception as e:
            qw.QMessageBox.critical(self, 'Error', 'Failed to set flatfield correction:\n' + str(e))
            
    def _save_flatfield_correction(self):
        """
        Saves the flatfield correction to a file
        """
        try:
            filename = qw.QFileDialog.getSaveFileName(
                parent=None,
                caption='Save flatfield correction file',
                filter='Numpy files (*.npy);;All files (*)',
            )[0]
            if filename == '': raise ValueError('No file selected')
            self._stageHub.save_flatfield_reference(filename)
        except Exception as e:
            qw.QMessageBox.critical(self, 'Error', 'Failed to save flatfield correction:\n' + str(e))
            
    def _load_flatfield_correction(self):
        """
        Loads the flatfield correction from a file
        """
        try:
            filename = qw.QFileDialog.getOpenFileName(
                parent=None,
                caption='Select flatfield correction file',
                filter='Numpy files (*.npy);;All files (*)',
            )[0]
            if filename == '': raise ValueError('No file selected')
            
            self._stageHub.load_flatfield_reference(filename)
            qw.QMessageBox.information(self, 'Flatfield correction', 'Flatfield correction loaded from {}'.format(filename))
        except Exception as e:
            qw.QMessageBox.critical(self, 'Error', 'Failed to load flatfield correction:\n' + str(e))

    def set_camera_exposure(self):
        """
        Sets the camera exposure time in microseconds
        """
        if not hasattr(self._camera_ctrl,'set_exposure_time') or not hasattr(self._camera_ctrl,'get_exposure_time'):
            qw.QMessageBox.critical(self, 'Error', 'Camera does not support exposure time setting')
            return
        try:
            init_exposure_time = self._camera_ctrl.get_exposure_time()
            new_exposure_time = messagebox_request_input('Set exposure time',
                                                        'Set exposure time in device unit',
                                                        str(init_exposure_time))
            self._camera_ctrl.set_exposure_time(float(new_exposure_time))
            qw.QMessageBox.information(self, 'Exposure time set', 'Exposure time set to {} ms'.format(self._camera_ctrl.get_exposure_time()))
        except Exception as e:
            qw.QMessageBox.critical(self, 'Error', 'Failed to set exposure time:\n' + str(e))

    @thread_assign
    def reinitialise_connection(self,unit:Literal['xy','z','camera']) -> threading.Thread:
        """
        Reinitialises the connection to the stage or camera
        
        Args:
            unit (Literal['xy','z','camera']): The unit to reinitialise
            
        Returns:
            threading.Thread: The thread started
        """
        if unit == 'xy':
            self.ctrl_xy.reinitialise_connection()
            self.signal_statbar_message.emit('XY stage re-initialised', None)
        elif unit == 'z':
            self.ctrl_z.reinitialise_connection()
            self.signal_statbar_message.emit('Z stage re-initialised', None)
        elif unit == 'camera':
            self._camera_ctrl.reinitialise_connection()
            self.signal_statbar_message.emit('Camera re-initialised', None)
        else:
            raise ValueError('Invalid unit for reinitialisation')
        
    def disable_overlays(self):
        """
        Disables the overlays on the video feed
        """
        self._chkbox_crosshair.setChecked(False)
        self._chkbox_scalebar.setChecked(False)
        return
        
    def initialise_auto_updater(self):
        """
        Initialises the auto-updaters to be used post widget initialisations
        (ALL THREADS) to prevent the main thread from being blocked
        """
        self.video_initialise()
        # For the coordinate status bar
        threading.Thread(target=self.coordinate_updater, daemon=False).start()
    
    def video_terminate(self):
        self._flg_isvideorunning = False
        # By turning this flag off, the video autoupdater should automatically terminate, 
        # disconnect from the camera, and resets all the parameters for next use.
        
        # Turn the button back into a camera on button
        self._btn_videotoggle.released.disconnect()
        self._btn_videotoggle.setText('Turn camera ON')
        self._btn_videotoggle.released.connect(lambda: self.video_initialise())
        self._btn_videotoggle.setStyleSheet('background-color: yellow')
    
    def video_initialise(self):
        """
        Initialises the video:
        1. Define the controller
        2. Sets the first frame
        3. Starts the multi-threading to start the autoupdater
        """
        try:
            if self._flg_isvideorunning: return
            # Initialise the video capture
            ## camera initialisation moved to self.video_update for responsiveness
            # Start multithreading for the video to constantly update the captured frame
            threading.Thread(target=self.video_update, daemon=True).start()
            
            # Turn the button into a video stop button
            self._btn_videotoggle.released.disconnect()
            self._btn_videotoggle.setText('Turn camera OFF')
            self._btn_videotoggle.released.connect(lambda: self.video_terminate())
            self._btn_videotoggle.setStyleSheet('background-color: red')
        except Exception as e:
            print(f'Video feed cannot start:\n{e}')
        
    def _start_breathing_z(self) -> None:
        """
        Moves the z-stage up and down for a few cycles

        Returns:
            threading.Thread: The thread started
        """
        # Store references to prevent premature destruction
        self._breathing_z_worker = _Worker_move_breathing_z(self.ctrl_z)
        self._breathing_z_worker.signal_breathing_finished.connect(self.signal_breathing_stopped)
        self._breathing_z_thread = QThread()
        self._breathing_z_worker.moveToThread(self._breathing_z_thread)
        self._breathing_z_thread.started.connect(self._breathing_z_worker.start)
        self._breathing_z_thread.finished.connect(self._breathing_z_worker.deleteLater)

        # Change the button to a stop button
        self._btn_z_breathing.released.disconnect()
        self._btn_z_breathing.setText('STOP Breathing')
        self._btn_z_breathing.setStyleSheet('background-color: red')
        self._btn_z_breathing.released.connect(self._breathing_z_worker.stop)

        # Connect the breathing stopped signal to the stop function
        self._breathing_z_worker.signal_breathing_finished.connect(self._stop_breathing_and_thread)

        self._breathing_z_thread.start()
        
    def _stop_breathing_and_thread(self) -> None:
        """
        Stops the breathing thread and resets the button
        """
        self._breathing_z_thread.quit()
        self._btn_z_breathing.released.disconnect()
        self._btn_z_breathing.setText('Breathing')
        self._btn_z_breathing.released.connect(self._start_breathing_z)
        self._btn_z_breathing.setStyleSheet('')
            
    def move_jog(self,dir:str):
        """
        Moves the stage per request from the button presses
        
        Args:
            dir (str): 'yfwd', 'xfwd', 'zfwd', 'yrev', 'xrev', 'zrev'
            as described in self.motion_button_manager
        """
        def _move_jog():
            self.signal_statbar_message.emit(f'Jogging to: {dir}', 'yellow')
            
            if dir not in ['yfwd','xfwd','zfwd','yrev','xrev','zrev']:
                raise SyntaxError('move_jog: Invalid direction input')
            elif dir in ['xfwd','xrev','yfwd','yrev']:
                self.ctrl_xy.move_jog(dir)
            elif dir in ['zfwd','zrev']:
                self.ctrl_z.move_jog(dir)
                
            self.signal_statbar_message.emit(None, None)
            
        if hasattr(self,'_thread_jog') and self._thread_jog.is_alive(): return
        self._thread_jog = threading.Thread(target=_move_jog)
        self._thread_jog.start()
        
    def _update_set_jog_labels(self):
        """
        Updates the labels for the jogging parameters obtained from the device controllers
        """
        jog_x_mm,jog_y_mm = self.ctrl_xy.get_jog()[:2]
        jog_z_mm,_,_ = self.ctrl_z.get_jog()
        
        jog_x_um = float(jog_x_mm * 10**3)
        jog_y_um = float(jog_y_mm * 10**3)
        if jog_x_um!=jog_y_um:
            self.signal_statbar_message.emit('Jogging parameters XY are not the same','yellow')
            print('Jogging parameters XY are not the same. Jog x: {:.1f}µm Jog y: {:.1f}µm'.format(jog_x_mm,jog_y_mm))
        jog_xy_um = jog_x_um
        jog_z_um = float(jog_z_mm * 10**3)
        
        self.lbl_jog_xy.setText('XY step size: {:.1f}µm'.format(jog_xy_um))
        self.lbl_jog_z.setText('Z step size: {:.1f}µm'.format(jog_z_um))
        
    def _set_jog_params(self):
        """
        Sets the motors jogging parameters according to the widget entries in [µm]
        """
        # Convert it to mm for the controller
        jog_xy_ent = self.ent_jog_xy.text()
        if jog_xy_ent != '': 
            jog_xy_mm = float(jog_xy_ent)*10**-3
            self.ctrl_xy.set_jog(dist_mm=jog_xy_mm)
        
        jog_z_ent = self.ent_jog_z.text()
        if jog_z_ent != '':
            jog_z_mm = float(jog_z_ent)*10**-3
            self.ctrl_z.set_jog(dist_mm=jog_z_mm)
        
        self._update_set_jog_labels()
        
    def _update_set_vel_labels(self):
        """
        Updates the labels for the motor parameters obtained from the device controllers
        """
        _,xy_speed,_ = self.ctrl_xy.get_vel_acc_relative()
        _,z_speed,_ = self.ctrl_z.get_vel_acc_relative()
        
        xy_speed = float(xy_speed)
        z_speed = float(z_speed)
        
        if isinstance(xy_speed,float) and isinstance(z_speed,float):
            self.lbl_speed_xy.setText('XY speed: {:.2f}%'.format(xy_speed))
            self.lbl_speed_z.setText('Z speed: {:.2f}%'.format(z_speed))
        
    def get_controller_identifiers(self) -> tuple:
        """
        Returns the controller identifiers for the camera, xy-stage, and z-stage
        Returns:
            tuple: (camera-id, xy-stage-id, z-stage-id)
        """
        return (self._controller_id_camera,
                self._controller_id_xy,
                self._controller_id_z)
        
    def get_VelocityParameters(self):
        """
        Returns the velocity parameters for the motors

        Returns:
            tuple: (xy-velocity, z-velocity) Velocity parameters for the xy-stage and z-stage in percentage
        """
        vel_xy = self.ctrl_xy.get_vel_acc_relative()[1]
        vel_z = self.ctrl_z.get_vel_acc_relative()[1]
        
        return (vel_xy,vel_z)
        
    def incrase_decrease_speed(self,stage:str,increase:bool):
        """
        Increase or decrease the velocity of the motors by 5% or 1% for the xy-stage and z-stage
        (5% if speed is >= 10%, 1% if speed is < 10%)

        Args:
            stage (str): 'xy' or 'z' for the stage to be controlled
            increase (bool): True to increase, False to decrease
        """
        assert stage in ['xy','z'], 'Invalid stage input'
        
        mult = 1 if increase else -1
        velxy = self.ctrl_xy.get_vel_acc_relative()[1]
        velz = self.ctrl_z.get_vel_acc_relative()[1]
        if stage == 'xy':
            velxy += 5*mult if velxy >= 10 else 1*mult
            if velxy <= 0: velxy = 1
            elif velxy >= 100: velxy = 100
        elif stage == 'z':
            velz = self.ctrl_z.get_vel_acc_relative()[1]
            velz += 5*mult if velz >= 10 else 1*mult
            if velz <= 0: velz = 1
            elif velz >= 100: velz = 100
        
        self.set_vel_relative(vel_xy=velxy,vel_z=velz)
        
    def calculate_vel_relative(self, vel_xy_mmPerSec:float) -> float:
        """
        Calculates the velocity in percentage based on the given velocity in mm/s
        based on the each device controller's internal method.

        Args:
            vel_xy_mmPerSec (float): The velocity in mm/s

        Returns:
            float: The velocity in percentage, relative to the device's maximum velocity
        """
        return self.ctrl_xy.calculate_vel_relative(vel_xy_mmPerSec)

    def set_vel_relative(self,vel_xy:float|None=None,vel_z:float|None=None):
        """
        Sets the velocity parameters for the motors
        
        Args:
            vel_xy (float, optional): Velocity (percentage) for the xy-stage. Must be between 0[%] and 100[%]. Defaults to None.
            vel_z (float, optional): Velocity (percentage) for the z-stage. Must be between 0[%] and 100[%]. Defaults to None.
        """
        if isinstance(vel_xy,type(None)): vel_xy = self.ctrl_xy.get_vel_acc_relative()[1]
        if isinstance(vel_z,type(None)): vel_z = self.ctrl_z.get_vel_acc_relative()[1]
        
        assert isinstance(vel_xy,(float,int)) and isinstance(vel_z,(float,int)), 'Invalid input type for the velocity parameters'
        
        self.ctrl_xy.set_vel_acc_relative(vel_homing=vel_xy,vel_move=vel_xy)
        self.ctrl_z.set_vel_acc_relative(vel_homing=vel_z,vel_move=vel_z)
        
        speed_xy = self.ctrl_xy.get_vel_acc_relative()[1]
        speed_z = self.ctrl_z.get_vel_acc_relative()[1]
        
        self._update_set_vel_labels()
        
    def _set_vel_acc_params(self):
        """
        Sets the motors velocity and acceleration parameters according to the widget entries
        """
        def clear_status():
            time.sleep(2)
            self.signal_statbar_message.emit('Motor parameters have been set', 'green')
            
        try:
            speed_xy = self.ent_speed_xy.text()
            speed_z = self.ent_speed_z.text()

            if speed_xy == '':
                speed_xy = self.ctrl_xy.get_vel_acc_relative()[1]
            if speed_z == '':
                speed_z = self.ctrl_z.get_vel_acc_relative()[1]
            
            speed_xy = float(speed_xy)
            speed_z = float(speed_z)
            
            self.ctrl_xy.set_vel_acc_relative(vel_homing=speed_xy,vel_move=speed_xy)
            self.ctrl_z.set_vel_acc_relative(vel_homing=speed_z,vel_move=speed_z)
            
            self.signal_statbar_message.emit('Motor parameters have been set', 'green')
        except:
            self.signal_statbar_message.emit('Invalid input for the motor parameters', 'yellow')
        finally:
            self._update_set_vel_labels()
        
    def _move_go_to(self):
        """
        Moves the stage to specific coordinates using the coordinates given in the entry boxes
        """
        coor_x_um_str = self.ent_coor_x.text()
        coor_y_um_str = self.ent_coor_y.text()
        coor_z_um_str = self.ent_coor_z.text()
        
        coor_x_current_mm,coor_y_current_mm = self.ctrl_xy.get_coordinates()
        coor_z_current_mm = self.ctrl_z.get_coordinates()
        
        try: coor_x_mm = float(coor_x_um_str)/1e3
        except: coor_x_mm = coor_x_current_mm
        try: coor_y_mm = float(coor_y_um_str)/1e3
        except: coor_y_mm = coor_y_current_mm
        try: coor_z_mm = float(coor_z_um_str)/1e3
        except: coor_z_mm = coor_z_current_mm
        
        threading.Thread(target=self.go_to_coordinates,args=[coor_x_mm,coor_y_mm,coor_z_mm]).start()
        
        # Empty the entry boxes
        self.ent_coor_x.setText('')
        self.ent_coor_y.setText('')
        self.ent_coor_z.setText('')
        
    def isontarget_gotocoor(self) -> bool:
        """
        Returns the status of the target reached for the go to coordinates
        
        Returns:
            bool: True if the target is reached, False otherwise
        """
        return self._flg_ontarget_gotocoor.is_set()
        
    def check_coordinates(self,coor_mm:tuple[float,float,float]) -> bool:
        """
        Checks if the given coordinates are within the travel range of the stages
        
        Args:
            coor_mm (tuple[float,float,float]): The coordinates to check
            
        Returns:
            bool: True if the coordinates are within the travel range, False otherwise
        """
        # NOTE: Implement this!
        pass
        return True
    
    def go_to_coordinates(self,coor_x_mm = None, coor_y_mm = None, coor_z_mm = None, override_controls:bool=False, timeout=10.0):
        """
        Moves the stage to specific coordinates, except if None is provided

        Args:
            coor_x (Decimal, optional): x-channel xy-stage coordinate. Defaults to None.
            coor_y (Decimal, optional): y-channel xy-stage coordinate. Defaults to None.
            coor_z (Decimal, optional): z-stage coordinate. Defaults to None.
            override_controls (bool, optional): If True, does not automatically disable/enable the controls. Defaults to False.
            timeout (float, optional): Timeout in seconds. Defaults to 10.0.
            
        Raises:
            TimeoutError: If the stage does not move within the timeout
        """
        def wait_for_target():
            """
            Waits for the target to be reached, the coordinate doesn't update within the timeout, raises a TimeoutError
                
            Raises:
                TimeoutError: If the target is not reached within the timeout
            """
            nonlocal self,thread_xy_move,thread_z_move,timeout
            
            start_time = time.time()
            coor = self._current_coor.copy()
            while True:
                if thread_xy_move.is_alive() or thread_z_move.is_alive():
                    thread_xy_move.join(timeout=0.1)
                    thread_z_move.join(timeout=0.1)
                else:
                    self._flg_ontarget_gotocoor.set()
                    break
                
                if time.time() - start_time > timeout:
                    raise TimeoutError('Timeout waiting for the target to be reached')
                
                coor_new = self._current_coor.copy()
                # Resets the timer if the coordinates are not the same
                if np.allclose(coor,coor_new,atol=0.001): start_time = time.time()
                coor = coor_new
        
        if not override_controls: self.disable_controls()
        
        # If None is provided, assign the current coordinates (i.e., do not move)
        if any([coor_x_mm is None,coor_y_mm is None,coor_z_mm is None]):
            res = self.get_coordinates_closest_mm()
            if res is None:
                qw.QMessageBox.critical(self, 'Error', 'Failed to get current coordinates')
                return
            coor_x_current,coor_y_current,coor_z_current = res
            if coor_x_mm is None:
                coor_x_mm = coor_x_current
            if coor_y_mm is None:
                coor_y_mm = coor_y_current
            if coor_z_mm is None:
                coor_z_mm = coor_z_current
        
        # Let the user know that it's currently moving
        self.signal_statbar_message.emit('Going to: {:.0f}X {:.0f}Y {:.0f}Z'
                           .format(coor_x_mm*1e3,coor_y_mm*1e3,coor_z_mm*1e3),'yellow') # type: ignore
        
        # Add a check
        self._flg_ontarget_gotocoor.clear()
        
        # Operate both stages at once
        thread_xy_move = threading.Thread(target=self.ctrl_xy.move_direct,args=((coor_x_mm,coor_y_mm),))
        thread_z_move = threading.Thread(target=self.ctrl_z.move_direct,args=(coor_z_mm,))
        
        thread_xy_move.start()
        thread_z_move.start()
        
        wait_for_target()
        
        if not override_controls: self.enable_controls()
        
        # Resets the statusbar, let the user know that it's done moving
        self.signal_statbar_message.emit('Stage movement complete', None)

    def get_coordinates_closest_mm(self) -> tuple[float|None,float|None,float|None]|None:
        """
        Returns the current coordinate of both channels x, y, and z of the stages.

        Returns:
            float: x, y, and z coordinates of the stage (converted from Thorlabs Decimals)
        """
        timestamp_req = get_timestamp_us_int()
        result = self._stageHub.get_coordinates_closest(timestamp_req)
        
        if result is None: return None
        coor_x,coor_y,coor_z = result
        
        self._current_coor = np.array([coor_x,coor_y,coor_z])
        
        return coor_x,coor_y,coor_z
    
    def motion_button_manager(self,dir):
        """
        Moves the stage per request from the button presses and releases.
        Should be assigned to a worker thread.

        Args:
            dir (str): 'yfwd', 'xfwd', 'zfwd', 'yrev', 'xrev', 'zrev', 'ystop', 'xstop', 'zstop', 'xyhome', 'zhome'
            for x, y and z motors with fwd, rev, and stop for forward, backward, and stop.
            'xyhome' and 'zhome' are for calibrating and homing the xy and z stage respectively.
            Note that 'xstop' and 'ystop' will stop both x and y motors.
        """
        if self._chkbox_jog_enabled.isChecked(): self.move_jog(dir); return
        
        def _move():
            if dir not in ['yfwd','xfwd','zfwd','yrev','xrev','zrev','xyhome','zhome']:
                self.signal_statbar_message.emit(f'Moving: {dir}', 'yellow')
            elif dir in ['xstop','ystop','zstop']:
                self.signal_statbar_message.emit(f'Stopping: {dir}', None)
            
            if dir in ['yfwd','xfwd','yrev','xrev']:
                self.ctrl_xy.move_continuous(dir)
            elif dir in ['zfwd','zrev']:
                self.ctrl_z.move_continuous(dir)
            elif dir in ['xstop','ystop']:
                self.ctrl_xy.stop_move()
            elif dir == 'zstop':
                self.ctrl_z.stop_move()
            elif dir == 'xyhome':
                self.ctrl_xy.homing_n_coor_calibration()
            elif dir == 'zhome':
                self.ctrl_z.homing_n_coor_calibration()
            else: raise SyntaxError('motion_button_manager: Invalid direction input')
            
            self.signal_statbar_message.emit(None, None)
            
        if hasattr(self,'_thread_move') and self._thread_move.is_alive(): return
            
        self._thread_move = threading.Thread(target=_move)
        self._thread_move.start()
    
    def _motion_controller_initialisation(self):
        """
        Initialises the controller and enables the buttons
        """
        # Re-enables the controls
        self._update_set_vel_labels()
        self._update_set_jog_labels()
        self.enable_controls()
        
    def disable_controls(self):
        """
        Disables all stage controls
        """
        all_widgets = get_all_widgets(self._wdg_mctrl)
        all_widgets.extend(get_all_widgets(self._wdg_GoToCoord))
        [widget.setEnabled(False) for widget in all_widgets if isinstance(widget,(qw.QPushButton,qw.QLineEdit))]
        
    def enable_controls(self):
        """
        Enables all stage controls
        """
        all_widgets = get_all_widgets(self._wdg_mctrl)
        all_widgets.extend(get_all_widgets(self._wdg_GoToCoord))
        [widget.setEnabled(True) for widget in all_widgets if isinstance(widget,(qw.QPushButton,qw.QLineEdit))]
        
        # Updates the statusbar
        self.signal_statbar_message.emit('Stage controller ready', None)

    def get_current_image(self, wait_newimage:bool=False) -> Image.Image|None:
        """
        Returns the current frame of the video feed
        
        Returns:
            ImageTk.PhotoImage: The current frame of the video feed
            wait_newimage (bool, optional): Waits for a new image to be taken. Defaults to False.
        """
        if wait_newimage:
            self._flg_isNewFrmReady.clear()
            self._flg_isNewFrmReady.wait()
        return self._currentImage
    
    def _overlay_scalebar(self,img:Image.Image) -> Image.Image:
        """
        Overlays a scalebar on the image based on the image calibration file

        Args:
            img (Image.Image): The image to be overlayed with the scalebar

        Returns:
            Image.Image: The image with the scalebar overlayed
        """
        cal = self._getter_imgcal()
        
        if not isinstance(cal,ImgMea_Cal) or not cal.check_calibration_set():
            return img
        
        if not isinstance(img,Image.Image): return img
        
        scalex = 1/cal.scale_x_pixelPerMm
        scalebar_length = int(ControllerConfigEnum.SCALEBAR_LENGTH_RATIO.value * img.size[0]) # in pixel
        scalebar_height = int(ControllerConfigEnum.SCALEBAR_HEIGHT_RATIO.value * img.size[1]) # in pixel
        
        length_mm = scalebar_length * scalex
        font = ControllerConfigEnum.SCALEBAR_FONT.value
        font_size = int(scalebar_length/10 * ControllerConfigEnum.SCALEBAR_FONT_RATIO.value)
        line_width = int(scalebar_length/50 * ControllerConfigEnum.SCALEBAR_FONT_RATIO.value)
        
        line_offset = scalebar_length/10
        
        box_length = scalebar_length + 2*line_offset
        box_height = scalebar_height + 2*line_offset
        
        draw = ImageDraw.Draw(img)
        # Draw a box around the scalebar, taking consideration of the font size height
        draw.rectangle([(img.size[0]-box_length, img.size[1]-box_height),
                        (img.size[0], img.size[1])], fill=(0,0,0))
        draw.line([(img.size[0]-scalebar_length-line_offset, img.size[1]-line_offset),
                   (img.size[0]-line_offset, img.size[1]-line_offset)],
                  fill=(255,255,255), width=line_width)
        
        text_params = {'text':'{:.0f} µm'.format(length_mm*1e3),
                'font':ImageFont.truetype(font,font_size)}
        
        text_length = draw.textlength(**text_params)
        
        draw.text((img.size[0]-box_length/2-text_length/2, img.size[1]-line_offset*2-line_width-font_size/2),
                  align='left', fill=(255,255,255), **text_params)
        return img
    
    def video_update(self):
        """
        Updates the video feed, taking in mind Tkinter's single thread.
        Use in a worker thread, DO NOT use in the mainthread!!!
        """
        def draw_crosshair(img:Image.Image) -> Image.Image:
            width, height = img.size
            draw = ImageDraw.Draw(img)
            line_color = (255, 0, 0)
            # Draw vertical line
            draw.line([(width/2, 0), (width/2, height)], fill=line_color, width=3)
            # Draw horizontal line
            draw.line([(0, height/2), (width, height/2)], fill=line_color, width=3)
            return img
        
        # Initialise the camera controller and grabs the first image
        if not self._camera_ctrl.get_initialisation_status(): self._camera_ctrl.__init__()
        self._currentFrame = None            # Empties the current frame
        
        # Loops the image updater to create outputs the video capture frame by frame
        self._flg_isvideorunning = True  # Enables the autoupdater
        while self._flg_isvideorunning:
            try:
                time1 = time.time()
                # Triggers the frame capture from the camera
                request = self._combo_vidcorrection.currentText()
                
                if self._stageHub.Enum_CamCorrectionType[request] == self._stageHub.Enum_CamCorrectionType.RAW:
                    img = self._camera_ctrl.img_capture()
                else:
                    img:Image.Image = self._stageHub.get_image(request=self._stageHub.Enum_CamCorrectionType[request])
                video_width = int(img.size[1]/img.size[0]*self._video_height)
                
                # Add a scalebar to it
                img = self._overlay_scalebar(img) if self._chkbox_scalebar.isChecked() else img
                
                # Overlay a crosshair if requested
                if self._chkbox_crosshair.isChecked(): img = draw_crosshair(img)
                new_frame:QPixmap = ImageQt.toqpixmap(img)
                
                # Update the image in the app window
                # Only update if the frame is different. Sometimes the program isn't done taking the new image.
                # In this case, it skips the frame update
                if self._currentFrame != new_frame:
                    self._lbl_video.setPixmap(new_frame)
                    self._currentFrame = new_frame
                    self._currentImage = img
                
                # Let the coordinate updater know that the frame is ready if any is waiting
                self._flg_isNewFrmReady.set()
                time_elapsed = time.time() - time1
                if time_elapsed < 1/AppVideoEnum.VIDEOFEED_REFRESH_RATE.value:
                    time.sleep(1/AppVideoEnum.VIDEOFEED_REFRESH_RATE.value - time_elapsed)
            except Exception as e: print(f'Video feed failed: {e}'); time.sleep(0.02)
        
    def coordinate_updater(self):
        while True:
            try:
                # Get the coordinates
                res = self.get_coordinates_closest_mm()
                if res is None: continue
                coor_x,coor_y,coor_z = res
                coor_x_um = float(coor_x) * 1e3 # type: ignore
                coor_y_um = float(coor_y) * 1e3 # type: ignore
                coor_z_um = float(coor_z) * 1e3 # type: ignore
                self._lbl_coor.setText('x,y,z: {:.1f}, {:.1f}, {:.1f} µm'
                                        .format(coor_x_um,coor_y_um,coor_z_um))
                time.sleep(1/AppPlotEnum.DISPLAY_COORDINATE_REFRESH_RATE.value)
            except Exception as e:
                print(f'Coordinate updater failed: {e}')
                time.sleep(0.005)
    
    @Slot(str,str)
    def status_update(self,message=None,bg_colour=None):
        """
        To update the status bar at the bottom

        Args:
            message (str, optional): The update message. Defualts to None
            bg_colour (str, optional): Background colour. Defaults to 'default'.
        """
        print(f'Status bar update: {message}, bg_colour: {bg_colour}')
        if not message: message = 'Motion controller ready'
        
        try:
            self._statbar.showMessage(message)
            self._statbar.setStyleSheet(f"background-color: {bg_colour}") if bg_colour is not None else self._statbar.setStyleSheet("")
        except Exception as e:
            print(f'Status bar update failed: {e}')
        
        
    def terminate(self):
        """
        Terminates the motion controller
        """
        self._flg_isrunning.clear()
        self.video_terminate()  # Terminates the camera controller as well
        self.ctrl_xy.terminate()
        self.ctrl_z.terminate()
        self._camera_ctrl.camera_termination()

def generate_dummy_motion_controller(parent:qw.QWidget) -> Frm_MotionController:
    """
    Generates a dummy motion controller for testing purposes.
    
    Args:
        parent (qw.QWidget): The parent QWidget to attach the motion controller to.
    
    Returns:
        Frm_MotionController: The dummy motion controller
    """
    from iris.multiprocessing.dataStreamer_StageCam import generate_dummy_stageHub
    
    stagehub, xyproxy, zproxy, camproxy, stage_namespace = generate_dummy_stageHub()
    stagehub.start()

    frm_motion = Frm_MotionController(
        parent=parent,
        xy_controller=xyproxy,
        z_controller=zproxy,
        stageHub=stagehub,
        getter_imgcal=lambda: None
    )
    
    frm_motion.initialise_auto_updater()
    
    return frm_motion

if __name__ == '__main__':
    # Initialize the PySide6 application
    app = qw.QApplication([])
    root = qw.QMainWindow()
    root.setWindowTitle('Dummy Motion Controller')
    
    # Create a central widget for the main window
    central_widget = qw.QWidget()
    root.setCentralWidget(central_widget)
    
    # Create a layout for the central widget
    layout = qw.QVBoxLayout(central_widget)
    
    # Create a dummy motion controller for testing
    frm_motion = generate_dummy_motion_controller(central_widget)
    
    # Add the motion controller widget to the layout
    layout.addWidget(frm_motion)
    
    # Set the size policy to allow the widget to expand
    frm_motion.setSizePolicy(
        qw.QSizePolicy.Policy.Expanding,
        qw.QSizePolicy.Policy.Expanding
    )
    
    # Show the main window
    root.show()
    
    # Start the PySide6 application event loop
    app.exec()
    
    # Terminate the motion controller after the application closes
    frm_motion.terminate()