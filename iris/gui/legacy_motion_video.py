"""
A class that manages the motion controller aspect for the Thorlabs stages

Made on: 04 March 2024
By: Kevin Uning
For: The Thomas Group, Biochemical Engineering Dept., UCL
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox,filedialog
import threading
import queue

from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import numpy as np

from typing import Callable, Literal

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

class Frm_MotionController(tk.Frame):
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
    
    def __init__(self,parent,xy_controller:Controller_XY,z_controller:Controller_Z,
                 stageHub:DataStreamer_StageCam,getter_imgcal:Callable[[],ImgMea_Cal],
                 flg_issimulation=True, main:bool=False):
        # Initialise the class
        super().__init__(parent)
        self._stageHub:DataStreamer_StageCam = stageHub
        self._getter_imgcal = getter_imgcal   # A getter method to get the image calibration
        
        self._flg_isrunning = threading.Event()
        self._flg_isrunning.set()  # A flag to check if the thread is running
        
    # >>> Simulation setup <<<
        self.flg_issimulation = flg_issimulation    # If True, request the motion controller to do a simulation instead
        
    # >>> Top layout <<<
        frm_video = tk.Frame(self)  # Top frame compartment for the video
        notebook_motion_ctrl = ttk.Notebook(self)  # Top frame compartment for the stage controllers
        self._statbar = tk.Label(self, text="Video and stage initialisation", bd=1, relief=tk.SUNKEN,anchor=tk.W)
        
        # Pack the frames
        row=0; col=0
        frm_video.grid(row=row,column=0,sticky='nsew'); row+=1
        notebook_motion_ctrl.grid(row=row,column=0,sticky='nsew'); row+=1
        self._statbar.grid(row=row,column=0,sticky='sew'); row+=1
        
        self._bg_colour = self._statbar.cget('background')
        
        # Grid configuration
        [self.grid_rowconfigure(i,weight=1) for i in range(row)]
        [self.grid_columnconfigure(i,weight=1) for i in range(col)]
        
        # Notebook setup
        self._frm_mctrl = tk.Frame(self)  # Bottom frame compartment for the stage controllers
        self._frm_GoToCoord = tk.Frame(self)  # Bottom frame compartment for the go to coordinate
        
        notebook_motion_ctrl.add(self._frm_mctrl,text='Directional control')
        notebook_motion_ctrl.add(self._frm_GoToCoord,text='Go to coordinate')
        
    # >>> Inter-class/frame data transfer <<<
        self.queue_response_motion = queue.Queue()  # Sets a queue to store data for other classes to take out and use
        
    # >>> Video widgets and parameter setup <<<
        self._camera_ctrl:CameraController = None   # Controls the camera, will be defined in the video initialise method
        self._video_height = ControllerConfigEnum.VIDEOFEED_HEIGHT.value    # Video feed height in pixel
        self._flg_isvideorunning = False         # A flag to turn on/off the video
        self._currentImage:Image.Image = None   # The current image to be displayed
        self._currentFrame = None               # The current frame to be displayed
        self._flg_isNewFrmReady = threading.Event()  # A flag to wait for the frame to be captured
        
        # >> Sub-frame setup <<
        sfrm_video = tk.Frame(frm_video)  # Hosts the video subframe
        sfrm_video_ctrl = tk.Frame(frm_video)  # Hosts the video controller subframe
        sfrm_video_coor = tk.Frame(frm_video)  # Hosts the video coordinate reporting subframe
        
        row=0; col=0
        sfrm_video.grid(row=row,column=0,sticky='nsew'); row+=1; col+=1
        sfrm_video_ctrl.grid(row=row,column=0,sticky='nsew'); row+=1
        sfrm_video_coor.grid(row=row,column=0,sticky='nsew'); row+=1
        [frm_video.grid_rowconfigure(i,weight=1) for i in range(row)]
        [frm_video.grid_columnconfigure(i,weight=1) for i in range(col)]
        
        # > Video
        self._lbl_video = tk.Label(sfrm_video,image=self._currentFrame)    # A label to show the video
        
        row=0; col=0
        self._lbl_video.grid(row=0,column=0,sticky='nsew')
        [sfrm_video.grid_rowconfigure(i,weight=1) for i in range(row)]
        [sfrm_video.grid_columnconfigure(i,weight=1) for i in range(col)]
        
        # > Video controllers
        self._btn_videotoggle = tk.Button(sfrm_video_ctrl,text='Turn camera ON',command= lambda:self.video_initialise(),bg='yellow')
        self._btn_reinit_conn = tk.Button(sfrm_video_ctrl,text='Reset camera connection',command=lambda: self.reinitialise_connection('camera'),bg='yellow')
        self._bool_crosshair = tk.BooleanVar(value=False)
        self._bool_scalebar = tk.BooleanVar(value=True)
        chk_crosshair = tk.Checkbutton(sfrm_video_ctrl,text='Show crosshair',variable=self._bool_crosshair)
        chk_scalebar = tk.Checkbutton(sfrm_video_ctrl,text='Show scalebar',variable=self._bool_scalebar)
        btn_set_imgproc_gain = tk.Button(sfrm_video_ctrl,text='Set flatfield gain',command=lambda: self._set_imageProc_gain())
        btn_set_flatfield = tk.Button(sfrm_video_ctrl,text='Set flatfield',command=lambda: self._set_flatfield_correction_camera())
        btn_save_flatfield = tk.Button(sfrm_video_ctrl,text='Save flatfield',command=lambda: self._save_flatfield_correction())
        btn_load_flatfield = tk.Button(sfrm_video_ctrl,text='Load flatfield',command=lambda: self._load_flatfield_correction())
        
        # Video corrections
        self._dict_vidcorrection = {}
        self._combo_vidcorrection = ttk.Combobox(sfrm_video_ctrl,values=list(stageHub.Enum_CamCorrectionType.__members__),
                                                 state='readonly')
        self._combo_vidcorrection.current(0)
        
        row=0; col=0
        chk_crosshair.grid(row=row,column=0,sticky='ew'); col+=1
        chk_scalebar.grid(row=row,column=1,sticky='ew'); row+=1
        self._btn_videotoggle.grid(row=row,column=0,sticky='ew')
        self._btn_reinit_conn.grid(row=row,column=1,sticky='ew'); row+=1
        self._combo_vidcorrection.grid(row=row,column=0,columnspan=2,sticky='ew'); row+=1
        
        btn_set_imgproc_gain.grid(row=row,column=0,sticky='ew')
        btn_set_flatfield.grid(row=row,column=1,sticky='ew'); row+=1
        btn_save_flatfield.grid(row=row,column=0,sticky='ew')
        btn_load_flatfield.grid(row=row,column=1,sticky='ew'); row+=1
        
        [sfrm_video_ctrl.grid_rowconfigure(i,weight=0) for i in range(row)]
        [sfrm_video_ctrl.grid_columnconfigure(i,weight=1) for i in range(col+1)]
        
        # > Coordinate reporting
        self._lbl_coor = tk.Label(sfrm_video_coor,text='Stage coordinates (x,y,z): ',anchor='center')
        
        row=0; col=0
        self._lbl_coor.grid(row=0,column=0,sticky='new')
        [sfrm_video_coor.grid_rowconfigure(i,weight=0) for i in range(row)]
        [sfrm_video_coor.grid_columnconfigure(i,weight=1) for i in range(col)]
        
    # >>> Motion widgets and parameter setup <<<
        # Set up the variable for the controller later
        self.ctrl_xy = xy_controller    # The xy-stage controller (proxy)
        self.ctrl_z = z_controller      # The z-stage controller (proxy)
        
        self._current_coor:np.array = np.zeros(3)  # The current coordinates of the stage, only to be used internally!
        self._flg_ontarget_gotocoor = threading.Event() # A flag to check if the stage is on target for the go to coordinates
        
        # Connection flag
        self._flg_connectionReady_xyz = threading.Event()  # A flag to check if the reconnection is in progress
        self._flg_connectionReady_xyz.set()
        
        # Add sub-frames
        sfrm_xyz_ctrl = tk.Frame(self._frm_mctrl)           # Hosts the xy stage and z stage controller ssubframes
        sfrm_xyzhome = tk.Frame(self._frm_mctrl)            # Hosts the calibration/home buttons
        ssfrm_xy_ctrl = tk.Frame(sfrm_xyz_ctrl)             # Hosts the xy stage controller
        ssfrm_z_ctrl = tk.Frame(sfrm_xyz_ctrl)              # Hosts the z stage controller
        sfrm_MotorParamSetup = tk.Frame(self._frm_mctrl)    # Hosts the motor parameter setup
        sfrm_jogConfig = tk.Frame(self._frm_mctrl)          # Hosts the jogging configuration
        
        # Pack the sub-frames
        sfrm_jogConfig.pack(side=tk.BOTTOM,padx=10, pady=5)
        sfrm_xyz_ctrl.pack(side=tk.BOTTOM,padx=10, pady=5)
        sfrm_xyzhome.pack(side=tk.BOTTOM,padx=10, pady=5)
        ssfrm_xy_ctrl.pack(side=tk.LEFT,padx=10, pady=5)
        ssfrm_z_ctrl.pack(side=tk.RIGHT,padx=10, pady=5)
        sfrm_MotorParamSetup.pack(side=tk.BOTTOM,padx=10, pady=5)
        
    # >>> Continuous motion controller widgets <<<
        # Add the buttons (disabled until controller initialisation)
        self.btn_xy_up = tk.Button(ssfrm_xy_ctrl,text='up',state='disabled')
        self.btn_xy_down = tk.Button(ssfrm_xy_ctrl,text='down',state='disabled')
        self.btn_xy_right= tk.Button(ssfrm_xy_ctrl,text='right',state='disabled')
        self.btn_xy_left = tk.Button(ssfrm_xy_ctrl,text='left',state='disabled')
        
        self.btn_z_up = tk.Button(ssfrm_z_ctrl,text='up',state='disabled')
        self.btn_z_down = tk.Button(ssfrm_z_ctrl,text='down',state='disabled')
        
        self._btn_z_breathing = tk.Button(ssfrm_z_ctrl,text='Breathing',state='disabled',command=self._move_breathing_z)
        
        self.btn_xy_home = tk.Button(sfrm_xyzhome,text='XY-Home/Calibration',
                                     state='disabled',command=lambda: self.motion_button_manager('xyhome'))
        self.btn_z_home = tk.Button(sfrm_xyzhome,text='Z-Home/Calibration',state='disabled',
                                    command= lambda: self.motion_button_manager('zhome'))
        
        self.btn_xy_reinit = tk.Button(sfrm_xyzhome,text='Reset XY connection',state='disabled',
                                     command=lambda: self.reinitialise_connection('xy'))
        self.btn_z_reinit = tk.Button(sfrm_xyzhome,text='Reset Z connection',state='disabled',
                                    command=lambda: self.status_update('Z re-initialisation is not yet implemented',bg_colour='yellow'))
        
        # Assign the buttons
        self.btn_xy_up.bind("<Button-1>", lambda event: self.motion_button_manager('yfwd'))
        self.btn_xy_down.bind("<Button-1>", lambda event: self.motion_button_manager('yrev'))
        self.btn_xy_right.bind("<Button-1>", lambda event: self.motion_button_manager('xfwd'))
        self.btn_xy_left.bind("<Button-1>", lambda event: self.motion_button_manager('xrev'))
        
        self.btn_z_up.bind("<Button-1>", lambda event: self.motion_button_manager('zfwd'))
        self.btn_z_down.bind("<Button-1>", lambda event: self.motion_button_manager('zrev'))
        
        self.btn_xy_up.bind("<ButtonRelease-1>", lambda event: self.motion_button_manager('ystop'))
        self.btn_xy_down.bind("<ButtonRelease-1>", lambda event: self.motion_button_manager('ystop'))
        self.btn_xy_right.bind("<ButtonRelease-1>", lambda event: self.motion_button_manager('xstop'))
        self.btn_xy_left.bind("<ButtonRelease-1>", lambda event: self.motion_button_manager('xstop'))
        
        self.btn_z_up.bind("<ButtonRelease-1>", lambda event: self.motion_button_manager('zstop'))
        self.btn_z_down.bind("<ButtonRelease-1>", lambda event: self.motion_button_manager('zstop'))
        
        # Pack the buttons into a layout
        self.btn_xy_up.pack(side=tk.TOP)
        self.btn_xy_down.pack(side=tk.BOTTOM)
        self.btn_xy_left.pack(side=tk.LEFT)
        self.btn_xy_right.pack(side=tk.RIGHT)
        
        self.btn_z_up.pack(side=tk.TOP)
        self.btn_z_down.pack(side=tk.TOP,pady=(0,10))
        self._btn_z_breathing.pack(side=tk.TOP)
        
        row_count=0
        self.btn_xy_home.grid(row=row_count,column=0)
        self.btn_z_home.grid(row=row_count,column=1)
        row_count+=1
        self.btn_xy_reinit.grid(row=row_count,column=0)
        self.btn_z_reinit.grid(row=row_count,column=1)
        
    # >>> Jogging configuration widgets <<<
        self._bool_jog_enabled = tk.BooleanVar(value=False)  # A flag to check if the jogging is enabled
        self.chk_jog_enabled = tk.Checkbutton(sfrm_jogConfig,text='Jogging mode',variable=self._bool_jog_enabled)
        lbl_info_jog = tk.Label(sfrm_jogConfig,text='OR right click on the direction buttons to jog',background='yellow')
        
        self.chk_jog_enabled.grid(row=0,column=0,columnspan=2,sticky='ew')
        lbl_info_jog.grid(row=1,column=0,columnspan=2,sticky='ew')

    # >>> Go to coordinate widgets <<<
        # Sub-frame setup
        sfrm_goto = tk.Frame(self._frm_GoToCoord)            # Hosts the go to coordinate entry
        sfrm_goto.grid(row=0,column=0)
        
        # Add the entry boxes
        self.ent_coor_x = tk.Entry(sfrm_goto)
        self.ent_coor_y = tk.Entry(sfrm_goto)
        self.ent_coor_z = tk.Entry(sfrm_goto)
        
        # Add the labels
        lbl_coor_x = tk.Label(sfrm_goto,text='X-coordinate: [μm]')
        lbl_coor_y = tk.Label(sfrm_goto,text='Y-coordinate: [μm]')
        lbl_coor_z = tk.Label(sfrm_goto,text='Z-coordinate: [μm]')
        
        # Add the go to button
        btn_goto = tk.Button(sfrm_goto,text='Go to',command=lambda: self._move_go_to(),
            state='disabled')
        
        # Bind: Enter to go to the coordinates
        self.ent_coor_x.bind('<Return>',lambda event: self._move_go_to())
        self.ent_coor_y.bind('<Return>',lambda event: self._move_go_to())
        self.ent_coor_z.bind('<Return>',lambda event: self._move_go_to())
        
        # Pack the widgets
        lbl_coor_x.grid(row=0,column=0)
        lbl_coor_y.grid(row=1,column=0)
        lbl_coor_z.grid(row=2,column=0)
        self.ent_coor_x.grid(row=0, column=1)
        self.ent_coor_y.grid(row=1, column=1)
        self.ent_coor_z.grid(row=2, column=1)
        btn_goto.grid(row=3, column=0, columnspan=2, sticky='ew')
        
        # Grid configuration
        self._frm_GoToCoord.grid_rowconfigure(0,weight=0)
        self._frm_GoToCoord.grid_rowconfigure(1,weight=0)
        self._frm_GoToCoord.grid_rowconfigure(2,weight=0)
        self._frm_GoToCoord.grid_columnconfigure(0,weight=1)
        
    # >>> Motor parameter setup widgets <<<
        # Add the entry boxes, label, and button for the speed parameter setups
        self.lbl_speed_xy = tk.Label(sfrm_MotorParamSetup,text='XY speed: %')
        self.lbl_speed_z = tk.Label(sfrm_MotorParamSetup,text='Z speed: %')
        self.ent_speed_xy = tk.Entry(sfrm_MotorParamSetup,state='disabled')
        self.ent_speed_z = tk.Entry(sfrm_MotorParamSetup,state='disabled')
        self.btn_SetSpeed = tk.Button(sfrm_MotorParamSetup,text='Set speed',state='disabled',
                                      command=lambda: self._set_vel_acc_params())
        
        # Bind: Enter to set motor parameters
        self.ent_speed_xy.bind('<Return>',lambda event: self._set_vel_acc_params())
        self.ent_speed_z.bind('<Return>',lambda event: self._set_vel_acc_params())
        
        # Pack the widgets
        self.lbl_speed_xy.grid(row=0,column=0)
        self.lbl_speed_z.grid(row=1,column=0)
        self.ent_speed_xy.grid(row=0,column=1)
        self.ent_speed_z.grid(row=1,column=1)
        self.btn_SetSpeed.grid(row=2,column=0,columnspan=2,sticky='ew')
        
        # Add the entry boxes, label, and button for the jogging parameter setup
        self.lbl_jog_xy = tk.Label(sfrm_MotorParamSetup,text='XY step size: [µm]')
        self.lbl_jog_z = tk.Label(sfrm_MotorParamSetup,text='Z step size: [µm]')
        self.ent_jog_xy = tk.Entry(sfrm_MotorParamSetup,state='disabled')
        self.ent_jog_z = tk.Entry(sfrm_MotorParamSetup,state='disabled')
        self.btn_SetJog = tk.Button(sfrm_MotorParamSetup,text='Set jog',state='disabled',
                                   command=lambda: self._set_jog_params())
        
        # Bind: Enter to set motor parameters
        self.ent_jog_xy.bind('<Return>',lambda event: self._set_jog_params())
        self.ent_jog_z.bind('<Return>',lambda event: self._set_jog_params())
        
        # Pack the widgets
        self.lbl_jog_xy.grid(row=3,column=0)
        self.lbl_jog_z.grid(row=4,column=0)
        self.ent_jog_xy.grid(row=3,column=1)
        self.ent_jog_z.grid(row=4,column=1)
        self.btn_SetJog.grid(row=5,column=0,columnspan=2,sticky='ew')
        
        # Bind the buttons to the jogging method (right click)
        self.btn_xy_up.bind("<Button-3>", lambda event: self.move_jog('yfwd'))
        self.btn_xy_down.bind("<Button-3>", lambda event: self.move_jog('yrev'))
        self.btn_xy_right.bind("<Button-3>", lambda event: self.move_jog('xfwd'))
        self.btn_xy_left.bind("<Button-3>", lambda event: self.move_jog('xrev'))
        
        self.btn_z_up.bind("<Button-3>", lambda event: self.move_jog('zfwd'))
        self.btn_z_down.bind("<Button-3>", lambda event: self.move_jog('zrev'))
        
    # >>> Status update <<<
        self.status_update('Initialising the motion controllers')
        self._motion_controller_initialisation()
        
        if main: self.initialise_auto_updater()
        
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
            messagebox.showinfo('Gain set','Gain set to {}'.format(self._stageHub.get_flatfield_gain()))
        except Exception as e:
            messagebox.showerror('Error','Failed to set gain:\n' + str(e))
        
    def _set_flatfield_correction_camera(self):
        """
        Sets the flatfield correction using the camera's current image
        """
        try:
            img = self._camera_ctrl.img_capture()
            img_arr = np.array(img)
            
            self._stageHub.set_flatfield_reference(img_arr)
            messagebox.showinfo('Flatfield correction','Flatfield correction set to the current camera image')
        except Exception as e:
            messagebox.showerror('Error','Failed to set flatfield correction:\n' + str(e))
            
    def _save_flatfield_correction(self):
        """
        Saves the flatfield correction to a file
        """
        try:
            filename = filedialog.asksaveasfilename(title='Save flatfield correction file',
                                                    defaultextension='.npy',
                                                    filetypes=[('Numpy files', '*.npy'),
                                                               ('All files', '*.*')])
            if filename == '': raise ValueError('No file selected')
            self._stageHub.save_flatfield_reference(filename)
        except Exception as e:
            messagebox.showerror('Error','Failed to save flatfield correction:\n' + str(e))
            
    def _load_flatfield_correction(self):
        """
        Loads the flatfield correction from a file
        """
        try:
            filename = filedialog.askopenfilename(title='Select flatfield correction file',
                                                  filetypes=[('Numpy files', '*.npy'),
                                                                ('All files', '*.*')])
            if filename == '': raise ValueError('No file selected')
            
            self._stageHub.load_flatfield_reference(filename)
            messagebox.showinfo('Flatfield correction','Flatfield correction loaded from {}'.format(filename))
        except Exception as e:
            messagebox.showerror('Error','Failed to load flatfield correction:\n' + str(e))
        
    def set_camera_exposure(self):
        """
        Sets the camera exposure time in microseconds
        """
        if not hasattr(self._camera_ctrl,'set_exposure_time') or not hasattr(self._camera_ctrl,'get_exposure_time'):
            messagebox.showerror('Error','Camera does not support exposure time setting')
            return
        try:
            init_exposure_time = self._camera_ctrl.get_exposure_time()
            new_exposure_time = messagebox_request_input('Set exposure time',
                                                        'Set exposure time in device unit',
                                                        str(init_exposure_time))
            self._camera_ctrl.set_exposure_time(float(new_exposure_time))
            messagebox.showinfo('Exposure time set','Exposure time set to {} ms'.format(self._camera_ctrl.get_exposure_time()))
        except Exception as e:
            messagebox.showerror('Error','Failed to set exposure time:\n' + str(e))
        
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
            self.status_update('XY stage re-initialised')
        elif unit == 'z':
            self.ctrl_z.reinitialise_connection()
            self.status_update('Z stage re-initialised')
        elif unit == 'camera':
            self._camera_ctrl.reinitialise_connection()
            self.status_update('Camera re-initialised')
        else:
            raise ValueError('Invalid unit for reinitialisation')
        
    def disable_overlays(self):
        """
        Disables the overlays on the video feed
        """
        self._bool_crosshair.set(False)
        self._bool_scalebar.set(False)
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
        self._btn_videotoggle.configure(text='Turn camera ON',command=lambda: self.video_initialise(),bg='yellow')
    
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
            self._btn_videotoggle.configure(text='Turn camera OFF',command=lambda: self.video_terminate(),bg='red')
        except Exception as e:
            print('Video feed cannot start:\n' + e)
        
    @thread_assign
    def _move_breathing_z(self) -> threading.Thread:
        """
        Moves the z-stage up and down for a few cycles

        Returns:
            threading.Thread: The thread started
        """
        flg_done = threading.Event()
        self._btn_z_breathing.configure(text='STOP Breathing',command=flg_done.set)
        
        try:
            while True:
                self.ctrl_z.move_jog('zfwd')
                time.sleep(0.01)
                if flg_done.is_set(): break
                self.ctrl_z.move_jog('zrev')
                time.sleep(0.01)
                if flg_done.is_set(): break
                self.ctrl_z.move_jog('zrev')
                time.sleep(0.01)
                if flg_done.is_set(): break
                self.ctrl_z.move_jog('zfwd')
                if flg_done.is_set(): break
        except Exception as e:
            print('Breathing failed: ' + e)
        finally:
            flg_done.set()
            self._btn_z_breathing.configure(text='Breathing',command=self._move_breathing_z)
        
    @thread_assign
    def move_jog(self,dir:str):
        """
        Moves the stage per request from the button presses
        
        Args:
            dir (str): 'yfwd', 'xfwd', 'zfwd', 'yrev', 'xrev', 'zrev'
            as described in self.motion_button_manager
        """
        def clear_status_bar(self:Frm_MotionController):
            time.sleep(2)
            self.status_update()
            
        if dir not in ['yfwd','xfwd','zfwd','yrev','xrev','zrev']:
            self.status_update('Invalid jogging direction','yellow')
            clear_status_bar(self)
            return
        elif dir in ['xfwd','xrev','yfwd','yrev']:
            self.ctrl_xy.move_jog(dir)
        elif dir in ['zfwd','zrev']:
            self.ctrl_z.move_jog(dir)
        
    def _update_set_jog_labels(self):
        """
        Updates the labels for the jogging parameters obtained from the device controllers
        """
        jog_x_mm,jog_y_mm = self.ctrl_xy.get_jog()[:2]
        jog_z_mm,_,_ = self.ctrl_z.get_jog()
        
        jog_x_um = float(jog_x_mm * 10**3)
        jog_y_um = float(jog_y_mm * 10**3)
        if jog_x_um!=jog_y_um:
            self.status_update('Jogging parameters XY are not the same','yellow')
            print('Jogging parameters XY are not the same. Jog x: {:.1f}µm Jog y: {:.1f}µm'.format(jog_x_mm,jog_y_mm))
        jog_xy_um = jog_x_um
        jog_z_um = float(jog_z_mm * 10**3)
        
        self.after(10,self.lbl_jog_xy.configure(text='XY step size: {:.1f}µm'.format(jog_xy_um)))
        self.after(10,self.lbl_jog_z.configure(text='Z step size: {:.1f}µm'.format(jog_z_um)))
        
    def _set_jog_params(self):
        """
        Sets the motors jogging parameters according to the widget entries in [µm]
        """
        # Convert it to mm for the controller
        jog_xy_ent = self.ent_jog_xy.get()
        if jog_xy_ent != '': 
            jog_xy_mm = float(jog_xy_ent)*10**-3
            self.ctrl_xy.set_jog(dist_mm=jog_xy_mm)
        
        jog_z_ent = self.ent_jog_z.get()
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
            self.after(10,self.lbl_speed_xy.configure(text='XY speed: {:.2f}%'.format(xy_speed)))
            self.after(10,self.lbl_speed_z.configure(text='Z speed: {:.2f}%'.format(z_speed)))
        
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
        
    def set_vel_relative(self,vel_xy:float=None,vel_z:float=None):
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
        
        self.after(10,self._update_set_vel_labels())
        
    def _set_vel_acc_params(self):
        """
        Sets the motors velocity and acceleration parameters according to the widget entries
        """
        def clear_status():
            time.sleep(2)
            self.status_update()
            
        try:
            speed_xy = self.ent_speed_xy.get()
            speed_z = self.ent_speed_z.get()
            
            if speed_xy == '':
                speed_xy = self.ctrl_xy.get_vel_acc_relative()[1]
            if speed_z == '':
                speed_z = self.ctrl_z.get_vel_acc_relative()[1]
            
            speed_xy = float(speed_xy)
            speed_z = float(speed_z)
            
            self.ctrl_xy.set_vel_acc_relative(vel_homing=speed_xy,vel_move=speed_xy)
            self.ctrl_z.set_vel_acc_relative(vel_homing=speed_z,vel_move=speed_z)
            
            self.after(10,self.status_update('Motor parameters have been set','green'))
        except:
            self.after(10,self.status_update('Invalid input for the motor parameters','yellow'))
            
        self.after(10,self._update_set_vel_labels())
        
    def _move_go_to(self):
        """
        Moves the stage to specific coordinates using the coordinates given in the entry boxes
        """
        coor_x_um = self.ent_coor_x.get()
        coor_y_um = self.ent_coor_y.get()
        coor_z_um = self.ent_coor_z.get()
        
        coor_x_current,coor_y_current = self.ctrl_xy.get_coordinates()
        coor_z_current = self.ctrl_z.get_coordinates()
        
        if coor_x_um == '':
            coor_x_um = coor_x_current
        if coor_y_um == '':
            coor_y_um = coor_y_current
        if coor_z_um == '':
            coor_z_um = coor_z_current
        
        coor_x_mm = float(coor_x_um)/1e3
        coor_y_mm = float(coor_y_um)/1e3
        coor_z_mm = float(coor_z_um)/1e3
        
        threading.Thread(target=self.go_to_coordinates,args=[coor_x_mm,coor_y_mm,coor_z_mm]).start()
        
        # Empty the entry boxes
        self.ent_coor_x.delete(0,tk.END)
        self.ent_coor_y.delete(0,tk.END)
        self.ent_coor_z.delete(0,tk.END)
    
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
            coor_x_current,coor_y_current,coor_z_current = self.get_coordinates_closest_mm()
            if coor_x_mm is None:
                coor_x_mm = coor_x_current
            if coor_y_mm is None:
                coor_y_mm = coor_y_current
            if coor_z_mm is None:
                coor_z_mm = coor_z_current
        
        # Let the user know that it's currently moving
        self.status_update('Going to: {:.3f}X {:.3f}Y {:.3f}Z'
                           .format(coor_x_mm,coor_y_mm,coor_z_mm),bg_colour='yellow')
        
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
        self.status_update()
        
    def get_coordinates_closest_mm(self) -> tuple[float,float,float]:
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
        
        # list_coor = result[1]
        # coor_x,coor_y,coor_z = list_coor[-1][0],list_coor[-1][1],list_coor[-1][2]
        
        # coor_x,coor_y = self.ctrl_xy.get_coordinates()
        # coor_z = self.ctrl_z.get_coordinates()
        
        return coor_x,coor_y,coor_z
    
    @thread_assign
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
        if self._bool_jog_enabled.get(): self.move_jog(dir); return
        
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
        all_widgets = get_all_widgets(self._frm_mctrl)
        all_widgets.extend(get_all_widgets(self._frm_GoToCoord))
        for button in all_widgets:
            if isinstance(button,tk.Button):
                self.after(10,button.configure(state='disabled'))
        
    def enable_controls(self):
        """
        Enables all stage controls"""
        all_widgets = get_all_widgets(self._frm_mctrl)
        all_widgets.extend(get_all_widgets(self._frm_GoToCoord))
        for widget in all_widgets:
            if isinstance(widget,tk.Button):
                self.after(10,widget.configure(state='active'))
            if isinstance(widget,tk.Entry):
                self.after(10,widget.configure(state='normal'))
        
        # Updates the statusbar
        self.status_update('Motion controller ready')

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
        self._camera_ctrl = self._stageHub.get_camera_controller()
        if not self._camera_ctrl.get_initialisation_status(): self._camera_ctrl.__init__()
        self._currentFrame = None            # Empties the current frame
        
        # Loops the image updater to create outputs the video capture frame by frame
        self._flg_isvideorunning = True  # Enables the autoupdater
        while self._flg_isvideorunning:
            try:
                time1 = time.time()
                # Triggers the frame capture from the camera
                request = self._combo_vidcorrection.get()
                
                if self._stageHub.Enum_CamCorrectionType[request] == self._stageHub.Enum_CamCorrectionType.RAW:
                    img = self._camera_ctrl.img_capture()
                else:
                    img:Image.Image = self._stageHub.get_image(request=self._stageHub.Enum_CamCorrectionType[request])
                video_width = int(img.size[1]/img.size[0]*self._video_height)
                
                # Add a scalebar to it
                img = self._overlay_scalebar(img) if self._bool_scalebar.get() else img
                
                # Overlay a crosshair if requested
                if self._bool_crosshair.get(): img = draw_crosshair(img)
                new_frame = ImageTk.PhotoImage(img.resize([self._video_height,video_width],Image.LANCZOS))
                
                # Update the image in the app window
                # Only update if the frame is different. Sometimes the program isn't done taking the new image.
                # In this case, it skips the frame update
                if self._currentFrame != new_frame:
                    self._lbl_video.configure(image=new_frame)
                    self._currentFrame = new_frame
                    self._currentImage = img
                
                # Let the coordinate updater know that the frame is ready if any is waiting
                self._flg_isNewFrmReady.set()
                time_elapsed = time.time() - time1
                if time_elapsed < 1/AppVideoEnum.VIDEOFEED_REFRESH_RATE.value:
                    time.sleep(1/AppVideoEnum.VIDEOFEED_REFRESH_RATE.value - time_elapsed)
            except Exception as e: print(f'Video feed failed: {e}'); time.sleep(0.02)
        
        # # Once done, terminate the camera and resets the self.videocapture instance
        # self._camera_ctrl.camera_termination()
        
    def coordinate_updater(self):
        while True:
            # try:
                # Get the coordinates
                res = self.get_coordinates_closest_mm()
                if res is None: continue
                coor_x,coor_y,coor_z = res
                coor_x_um = float(coor_x) * 1e3
                coor_y_um = float(coor_y) * 1e3
                coor_z_um = float(coor_z) * 1e3
                self._lbl_coor.configure(text='x,y,z: {:.1f}, {:.1f}, {:.1f} µm'
                                        .format(coor_x_um,coor_y_um,coor_z_um))
                time.sleep(1/AppPlotEnum.DISPLAY_COORDINATE_REFRESH_RATE.value)
            # except Exception as e:
            #     print(f'Coordinate updater failed: {e}')
            #     time.sleep(0.005)
    
    @thread_assign
    def status_update(self,message=None,bg_colour=None):
        """
        To update the status bar at the bottom

        Args:
            message (str, optional): The update message. Defualts to None
            bg_colour (str, optional): Background colour. Defaults to 'default'.
        """
        if not bg_colour:
            bg_colour = self._bg_colour
        
        if not message:
            message = 'Motion controller ready'
        
        try: self.after(10,self._statbar.configure(text=message,background=bg_colour))
        except Exception as e: pass
        
    def terminate(self):
        """
        Terminates the motion controller
        """
        self._flg_isrunning.clear()
        self.video_terminate()  # Terminates the camera controller as well
        self.ctrl_xy.terminate()
        self.ctrl_z.terminate()
        self._camera_ctrl.camera_termination()
        self.quit()

def generate_dummy_motion_controller(parent:tk.Tk|tk.Frame) -> Frm_MotionController:
    """
    Generates a dummy motion controller for testing purposes.
    
    Args:
        parent (tk.Tk|tk.Frame): The parent Tkinter widget to attach the motion controller to.
    
    Returns:
        Frm_MotionController: The dummy motion controller
    """
    from iris.gui.motion_video import Frm_MotionController
    from iris.gui.motion_video import get_my_manager, initialise_manager_stage, initialise_proxy_stage
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
    import tkinter as tk
    from iris.gui.motion_video import generate_dummy_motion_controller
    
    root = tk.Tk()
    root.title('Dummy Motion Controller')
    
    # Create a dummy motion controller for testing
    frm_motion = generate_dummy_motion_controller(root)
    frm_motion.pack(fill=tk.BOTH, expand=True)
    
    # Start the Tkinter main loop
    frm_motion.mainloop()
    
    # Terminate the motion controller
    frm_motion.terminate()