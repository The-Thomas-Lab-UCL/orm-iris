"""
A controller to take in a video feed and display
"""
import numpy as np
import cv2
import time
from PIL import Image
import os
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, OPERATION_MODE, TLCamera
import thorlabs_tsi_sdk.tl_camera as TL_Cam

import multiprocessing as mp

from thorlabs_tsi_sdk.tl_mono_to_color_processor import MonoToColorProcessorSDK as TL_MTC
from thorlabs_tsi_sdk.tl_mono_to_color_processor import MonoToColorProcessor
from thorlabs_tsi_sdk.tl_mono_to_color_enums import COLOR_SPACE as TL_ClrSpc
from thorlabs_tsi_sdk.tl_color_enums import FORMAT as TL_Fmt

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))


from iris.controllers.class_camera_controller import Class_CameraController

from iris.controllers import ControllerConfigEnum, ControllerSpecificConfigEnum

absolute_path_to_dlls = ControllerSpecificConfigEnum.THORLABS_CAMERA_DLL_PATH.value
os.environ['PATH'] = absolute_path_to_dlls + os.pathsep + os.environ['PATH']
os.add_dll_directory(absolute_path_to_dlls)

class CameraController_ThorlabsColor(Class_CameraController):
    """
    A class that operates the camera, takes and stores the current frame for Thorlabs colour camera.
    """
    def __init__(self,show:bool=False) -> None:
        self.controller:TLCameraSDK = None
        
        self._lock = mp.Lock()
        
        self.camera_index = 0           # Takes the 1st capture device as the source
                                        # it is possible that the desired device is NOT the 1st one
                                        # in this case, a different index should be chosen by trial and error
                                        # index = 0,1,2,3,... etc.
        
        self._colour_processor:TL_MTC = None
        self._clrprc_monoToColour:MonoToColorProcessor = None        
        
        self._frame_width:int = None
        self._frame_height:int = None
        
        self._flg_show_preview = show
        self.win_name = 'preview'
            
        # Post processing parameters
        self._mirrorx:bool = None
        self._mirrory:bool = None
        
        self.flg_initialised = False
        
        try: self._initialisation()
        except Exception as e: print('CameraController_ThorlabsColor initialisation error:\n{}'.format(e))
        
    def reinitialise_connection(self) -> None:
        """
        Reinitialise the camera connection
        """
        try: self.camera_termination()
        except Exception as e: print('CameraController_ThorlabsColor reinitialise_connection error:\n{}'.format(e))
        
        try: self._initialisation()
        except Exception as e: print('CameraController_ThorlabsColor reinitialise_connection error:\n{}'.format(e))
        
    def _initialisation(self) -> bool:
        """
        Initialise the camera connection
        
        Returns:
            bool: True if the camera is initialised
        """
        try: self.controller = TLCameraSDK()
        except Exception as e: print('CameraController_ThorlabsColor initialisation error:\n{}'.format(e))
        
        self._lock = mp.Lock()
        
        self._lock.acquire()
        
        available_cameras = self.controller.discover_available_cameras()
        
        if len(available_cameras) < 1:
            print("no cameras detected")
            return False
                                        
        self.camera = self.controller.open_camera(available_cameras[self.camera_index])
        self.camera.exposure_time_us = ControllerSpecificConfigEnum.THORLABS_CAMERA_EXPOSURE_TIME.value # exposure time in [us]. Default: 10000 (10ms)
        self.camera.frames_per_trigger_zero_for_unlimited = ControllerSpecificConfigEnum.THORLABS_CAMERA_FRAMEPERTRIGGER.value  # number of frames obtained per trigger, 0 for continuous acquisition mode
        self.camera.image_poll_timeout_ms = ControllerSpecificConfigEnum.THORLABS_CAMERA_IMAGEPOLL_TIMEOUT.value    # set image polling timeout in [ms]
        self.camera.gain = int(0)
        
        self._colour_processor = TL_MTC()
        self._clrprc_monoToColour = self._colour_processor.create_mono_to_color_processor(
            self.camera.camera_sensor_type,
            self.camera.color_filter_array_phase,
            self.camera.get_color_correction_matrix(),
            self.camera.get_default_white_balance_matrix(),
            self.camera.bit_depth)
        self._clrprc_monoToColour.color_space = TL_ClrSpc.SRGB  # sRGB color space
        self._clrprc_monoToColour.output_format = TL_Fmt.RGB_PIXEL  # data is returned as sequential RGB values
        
        self._frame_width = self.camera.image_width_pixels
        self._frame_height = self.camera.image_height_pixels
        
        self.camera.arm(2)
        self.camera.issue_software_trigger()
        
        self.status = "video capture initialisation"  # Status message of the class
        
        if self._flg_show_preview == True:
            self.win_name = 'preview'
            cv2.namedWindow(self.win_name)
            
        # Post processing parameters
        self._mirrorx = ControllerConfigEnum.CAMERA_MIRRORX.value
        self._mirrory = ControllerConfigEnum.CAMERA_MIRRORY.value
            
        self.flg_initialised = True
        
        self._lock.release()
        print('>>>>> Thorlabs color camera initialised <<<<<')
        
    def camera_termination(self):
        
        print('Terminating the Thorlabs color camera')
        try:
            with self._lock: self.camera.disarm()
        except Exception as e: print('camera_termiation error:\n{}'.format(e))
        
        try:
            with self._lock: self._clrprc_monoToColour.dispose()
        except Exception as e: print('camera_termiation error:\n{}'.format(e))
            
        try:
            with self._lock: self._colour_processor.dispose()
        except Exception as e: print('camera_termiation error:\n{}'.format(e))
            
        try:
            with self._lock: self.camera.dispose()
        except Exception as e: print('camera_termiation error:\n{}'.format(e))
        
        try:
            with self._lock: self.controller.dispose()
        except Exception as e: print('camera_termiation error:\n{}'.format(e))
        
        self.controller = None
        self.camera = None
        self._colour_processor = None
        
        time.sleep(3)   # Wait for all terminations to complete
        
        self.flg_initialised = False
        
        print('>>>>> Thorlabs color camera terminated <<<<<')
    
    def set_exposure_time(self, exposure_time_us:int|float) -> None:
        """
        Set the exposure time of the camera

        Args:
            exposure_time_us (int | float): Exposure time in microseconds
        """
        with self._lock:
            try: self.camera.exposure_time_us = exposure_time_us
            except Exception as e: print('set_exposure_time error:\n{}'.format(e))
            
    def get_exposure_time(self) -> int|float|None:
        """
        Get the exposure time of the camera

        Returns:
            int | float: Exposure time in microseconds
        """
        with self._lock:
            try: exposure_time = self.camera.exposure_time_us
            except Exception as e: print('get_exposure_time error:\n{}'.format(e)); exposure_time = None
            return exposure_time
    
    def get_initialisation_status(self) -> bool:
        return self.flg_initialised
    
    def frame_capture(self) -> (np.ndarray|None):
        with self._lock: frame = self.camera.get_pending_frame_or_null()
        if frame is not None:
            image_1d:np.ndarray = self._clrprc_monoToColour.transform_to_24(
                frame.image_buffer, self._frame_width, self._frame_height)
            
            with self._lock:
                image_array = image_1d.reshape(self.camera.image_height_pixels, self.camera.image_width_pixels, 3)
            
            if self._mirrorx: image_array = cv2.flip(image_array, 0)
            if self._mirrory: image_array = cv2.flip(image_array, 1)
            
            self.img = image_array
            return self.img
        else:
            return None
    
    def img_capture(self) -> Image.Image:
        frm = self.frame_capture()
        if frm is None:
            return None
        self.img = Image.fromarray(frm)
        return self.img
    
    def vidcapture_show(self):
        self.status = "video capture on-going"
        self.vidcap_flag = True
        
        while self.vidcap_flag:
            key = cv2.waitKey(20)
            if key == 27: # exit on ESC
                self.vidcap_flag = False
                time.sleep(0.1)
                
            img = self.frame_capture()
            
            if img is None:
                time.sleep(0.01)
                continue
            frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
            self.vidshow(self.win_name,frame)
            
        self.status = "video capture stopped"
        self.quit()
    
    def vidshow(self,win_name,frame):
        cv2.imshow(win_name, frame)
    
    def quit(self):
        print('video stopped')
        self.camera_termination()
        cv2.destroyWindow(self.win_name)
        
        
if __name__ == '__main__':
    vid = CameraController_ThorlabsColor(show=True)
    vid.vidcapture_show()
    vid.camera_termination()