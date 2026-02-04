"""
Class definition for the Thorlabs colour camera controller and a guide to writing one for the IRIS app.
"""
import numpy as np
import cv2
import time
from PIL import Image
import os

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))


from iris.controllers import ControllerConfigEnum


class Class_CameraController:
    """
    A class that operates the camera, takes and stores the current frame for Thorlabs colour camera.
    """
    def __init__(self,show=False) -> None:
        # <<<<< Insert the device initialisation commands here (connection, parameters, etc.)
        pass
        
        self.status = "video capture initialisation"  # Status message of the class
            
        # Post processing parameters
        self._mirrorx = ControllerConfigEnum.CAMERA_MIRRORX.value
        self._mirrory = ControllerConfigEnum.CAMERA_MIRRORY.value
        
        self.flg_initialised = True
        
    def get_identifier(self) -> str:
        """
        Returns the identifier of the camera.

        Returns:
            str: The identifier of the camera
        """
        # <<<<< Insert the command to get the camera identifier here
        identifier = "CameraController_ID: Not set"
        return identifier
        
    def camera_termination(self) -> None:
        """
        To terminate the connections to the camera prior exit
        """
        try:
            # <<<<< Insert the termination commands here
            pass
        except Exception as e:
            print('camera_termiation error:\n{}'.format(e))
        
        self.flg_initialised = False
            
    def get_initialisation_status(self) -> bool:
        """
        Returns the initialisation status of the camera.

        Returns:
            bool: The initialisation status of the camera
        """
        return self.flg_initialised
    
    
    def set_exposure_time_us(self, exposure_time_us:int|float) -> None:
        """
        Set the exposure time of the camera

        Args:
            exposure_time_us (int | float): Exposure time in microseconds
        """
        raise NotImplementedError("set_exposure_time() does not exist in this controller")
            
    def get_exposure_time_us(self) -> int|float|None:
        """
        Get the exposure time of the camera

        Returns:
            int | float: Exposure time in microseconds
        """
        raise NotImplementedError("get_exposure_time() does not exist in this controller")
    
    def frame_capture(self) -> (np.ndarray|None):
        """
        Captures the frame from the camera and returns it as a numpy array.
        
        Returns:
            np.ndarray|None: The frame as a numpy array or None if no frame is captured
        """
        # <<<<< Insert the command to capture the frame here
        frame = np.ndarray((100,100,3)) # dummy frame
        pass
    
        if frame is not None:
            if self._mirrorx:
                # <<<<< Insert the command to flip the image in the x-axis here
                pass
            if self._mirrory:
                # <<<<< Insert the command to flip the image in the y-axis here
                pass
            # <<<<< Insert the command to convert the frame to a numpy array here
            img = frame # dummy img
            pass
            
            return img
        else:
            return None
    
    def img_capture(self) -> Image.Image|None:
        """
        Captures the frame from the camera and returns it as a PIL Image.

        Returns:
            Image.Image|None: The frame as a PIL Image or None if no frame is captured
        """
        frm = self.frame_capture()
        if frm is None:
            return None
        self.img = Image.fromarray(frm)
        return self.img
    
    def vidcapture_show(self) -> None:
        """
        Tests the video capture and shows the video feed.
        """
        self.vidcap_flag = True
        win_name = 'preview'
        cv2.namedWindow(win_name)
        
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
            self.vidshow(win_name,frame)
            
        self.status = "video capture stopped"
        self.quit(win_name=win_name)
    
    def vidshow(self,win_name,frame) -> None:
        """
        Shows the video feed in a window.

        Args:
            win_name (str): The name of the window
            frame (np.ndarray): The frame to be displayed
        """
        cv2.imshow(win_name, frame)
    
    def quit(self,win_name:str=None) -> None:
        print('video stopped')
        self.camera_termination()
        if win_name: cv2.destroyWindow(win_name)
        
        
if __name__ == '__main__':
    vid = Class_CameraController(show=True)
    vid.vidcapture_show()
    vid.camera_termination()