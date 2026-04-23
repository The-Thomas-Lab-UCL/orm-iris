"""
A controller to take in a video feed and display
"""
import numpy as np
import cv2
import time
from PIL import Image

import os
from multiprocessing import Lock

from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, TLCamera

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

class CameraController_ThorlabsMono2(Class_CameraController):
    """
    A class that operates the camera, takes and stores the current frame for Thorlabs monochrome camera.
    """
    def __init__(self,show=False) -> None:
        
        # Check if the SDK is open
        self.controller:TLCameraSDK = None
        
        self._lock = Lock()
        
        self.camera_index = 0           # Takes the 1st capture device as the source
                                        # it is possible that the desired device is NOT the 1st one
                                        # in this case, a different index should be chosen by trial and error
                                        # index = 0,1,2,3,... etc.
                                        
        self.camera:TLCamera = None
        self._intensity_mod = 1/100
        
        self._frame_width:int = None
        self._frame_height:int = None
        self._bit_shift:int = None
                
        self._flg_show_preview = show
        
        self.win_name = 'preview'
            
        # Post processing parameters
        self._mirrorx:bool = None
        self._mirrory:bool = None
        
        self.flg_initialised = False
        
        self._identifier = None
        try: self._initialisation()
        except Exception as e: print('camera_initialisation error:\n{}'.format(e))
        
    def get_identifier(self) -> str:
        """
        Returns the identifier of the camera.

        Returns:
            str: The identifier of the camera
        """
        if self._identifier is None:
            self._identifier = f"Thorlabs_{self.camera.model}, S/N:{self.camera.serial_number}"
        return self._identifier

    def reinitialise_connection(self) -> None:
        """
        Reinitialise the camera connection, preserving the current exposure time.
        Fully disposes and recreates the SDK to guarantee a clean hardware state.
        """
        exposure_time_us = None
        try: exposure_time_us = self.get_exposure_time_us()
        except Exception: pass

        try: self.camera_termination()
        except Exception as e: print('camera_reinitialisation error:\n{}'.format(e))

        try: self._initialisation()
        except Exception as e: print('camera_reinitialisation error:\n{}'.format(e))

        if exposure_time_us is not None:
            try: self.set_exposure_time_us(exposure_time_us)
            except Exception as e: print('camera_reinitialisation exposure restore error:\n{}'.format(e))
        
    def _initialisation(self) -> bool:
        """
        Check if the camera is initialised
        """
        self._lock.acquire()
        try:
            self.controller = TLCameraSDK()

            available_cameras = self.controller.discover_available_cameras()
            if len(available_cameras) < 1:
                raise RuntimeError('No Thorlabs cameras detected')

            self.camera = self.controller.open_camera(available_cameras[self.camera_index])
            self.camera.exposure_time_us = ControllerSpecificConfigEnum.THORLABS_CAMERA_EXPOSURE_TIME.value
            self.camera.frames_per_trigger_zero_for_unlimited = ControllerSpecificConfigEnum.THORLABS_CAMERA_FRAMEPERTRIGGER.value
            self.camera.image_poll_timeout_ms = ControllerSpecificConfigEnum.THORLABS_CAMERA_IMAGEPOLL_TIMEOUT.value

            self._frame_width = self.camera.image_width_pixels
            self._frame_height = self.camera.image_height_pixels
            self._bit_shift = max(0, self.camera.bit_depth - 8)

            self.camera.arm(2)
            self.camera.issue_software_trigger()

            self.status = "video capture initialisation"

            if self._flg_show_preview == True:
                self.win_name = 'preview'
                cv2.namedWindow(self.win_name)

            self._mirrorx = ControllerConfigEnum.CAMERA_MIRRORX.value
            self._mirrory = ControllerConfigEnum.CAMERA_MIRRORY.value

            self.flg_initialised = True
            self._identifier = f"Thorlabs_{self.camera.model}, S/N:{self.camera.serial_number}"
        except Exception as e:
            print('camera_initialisation error:\n{}'.format(e))
            self.flg_initialised = False
        finally:
            self._lock.release()
        
    def camera_termination(self):
        self._lock.acquire()
        
        try: self.camera.disarm()
        except Exception as e: print('camera_disarm error:\n{}'.format(e))
            
        try: self.camera.dispose()
        except Exception as e: print('camera_termiation error:\n{}'.format(e))
            
        try: self.controller.dispose()
        except Exception as e: print('controller_dispose error:\n{}'.format(e))
        
        self.camera = None
        self.controller = None
        
        time.sleep(3)   # Wait for all terminations to complete
        
        self.flg_initialised = False
        
        self._lock.release()
    
    def get_initialisation_status(self) -> bool:
        return self.flg_initialised
    
    def set_exposure_time_us(self, exposure_time_us:int|float) -> None:
        """
        Set the exposure time of the camera

        Args:
            exposure_time_us (int | float): Exposure time in microseconds
        """
        with self._lock:
            if not isinstance(exposure_time_us, (int, float)):
                raise ValueError("Exposure time must be an integer or float")
            exposure_time_us = int(exposure_time_us)
            self.camera.exposure_time_us = exposure_time_us
            
    def get_exposure_time_us(self) -> int|float|None:
        """
        Get the exposure time of the camera

        Returns:
            int | float: Exposure time in microseconds
        """
        with self._lock:
            return self.camera.exposure_time_us
    
    def frame_capture(self) -> (np.ndarray|None):
        with self._lock:
            frame = self.camera.get_pending_frame_or_null()
            if frame is not None:
                # Copy inside the lock before the SDK recycles the buffer
                image_1d: np.ndarray = frame.image_buffer.copy()

        if frame is not None:
            image_array = image_1d.reshape(self._frame_height, self._frame_width)

            if self._mirrorx: image_array = cv2.flip(image_array, 0)
            if self._mirrory: image_array = cv2.flip(image_array, 1)

            self.img = image_array
            return self.img
        else:
            return None

    def img_capture(self) -> Image.Image:
        frm = self.frame_capture()
        if frm is None: return None
        frm_8bit = (frm >> self._bit_shift).astype(np.uint8)
        self.img = Image.fromarray(frm_8bit).convert('RGB')
        return self.img

    def set_single_frame_trigger_mode(self, enabled: bool) -> None:
        """Switch between single-frame software trigger (True) and continuous (False) mode."""
        with self._lock:
            self.camera.disarm()
            self.camera.frames_per_trigger_zero_for_unlimited = 1 if enabled else 0
            self.camera.arm(2)
            if not enabled:
                self.camera.issue_software_trigger()  # restart continuous stream

    def img_capture_fresh(self) -> Image.Image | None:
        """
        Flush buffered frames, issue a software trigger, and wait for the fresh frame.
        Camera must already be in single-frame trigger mode — call
        set_single_frame_trigger_mode(True) once before the tiling loop.
        """
        with self._lock:
            # Flush any stale buffered frames non-blocking
            old_timeout = self.camera.image_poll_timeout_ms
            self.camera.image_poll_timeout_ms = 0
            while self.camera.get_pending_frame_or_null() is not None:
                pass
            # Issue trigger → fresh exposure starts now (stage is already stationary)
            self.camera.issue_software_trigger()
            # Wait for the frame: exposure_time + a fixed margin (no artificial floor)
            self.camera.image_poll_timeout_ms = int(self.camera.exposure_time_us // 1000) + 500
            frame = self.camera.get_pending_frame_or_null()
            self.camera.image_poll_timeout_ms = old_timeout

        if frame is None:
            return None
        image_array = frame.image_buffer.copy().reshape(self._frame_height, self._frame_width)
        if self._mirrorx: image_array = cv2.flip(image_array, 0)
        if self._mirrory: image_array = cv2.flip(image_array, 1)
        self.img = Image.fromarray((image_array >> self._bit_shift).astype(np.uint8)).convert('RGB')
        return self.img
    
    def vidcapture_show(self):
        self.status = "video capture on-going"
        self.vidcap_flag = True
        
        while self.vidcap_flag:
            key = cv2.waitKey(20)
            if key == 27: # exit on ESC
                self.vidcap_flag = False
                time.sleep(0.1)
                
                
            # Adjust exposure time dynamically (example)
            if key == ord('i'):  # Increase exposure
                try: self.camera.exposure_time_us += 10000
                except Exception as e: print(f"Error: {e}")
                print(f"Exposure increased to: {self.camera.exposure_time_us}")
            elif key == ord('d'):  # Decrease exposure
                try: self.camera.exposure_time_us -= 10000
                except Exception as e: print(f"Error: {e}")
                print(f"Exposure decreased to: {self.camera.exposure_time_us}")
                
            # img = self.frame_capture()
            # frame = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGBA)
            
            img = self.img_capture() # RGB Image object
            frame = img
            frame = cv2.cvtColor(np.array(frame), cv2.COLOR_BGR2RGBA)
            
            if img is None:
                time.sleep(0.01)
                continue
            
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
    vid = CameraController_ThorlabsMono2(show=True)
    vid.set_exposure_time_us(100e3)
    vid.vidcapture_show()
    vid.camera_termination()