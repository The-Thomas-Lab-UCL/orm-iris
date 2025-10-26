"""
A controller to take in a video feed and display 

Made on: 04 March 2024
"""
import numpy as np
import cv2
import time
from PIL import Image

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))
    

from iris.controllers.class_camera_controller import Class_CameraController

class CameraController_Dummy(Class_CameraController):
    """
    A class that operates the camera, takes and stores the current frame for a webcam.
    """
    def __init__(self,**kwargs) -> None:
        self._size = (640,480)  # Size of the video feed in pixels
        self._frame = np.ones((self._size[1],self._size[0],3),dtype=np.uint8)*255  # Initial frame
        # Convert to a yellow image
        self._frame[:,:,:] = [0,255,255]
        
        self.flg_initialised = True
        
        print('\n>>>>> DUMMY camera controller is used <<<<<')
        
    def get_identifier(self) -> str:
        return "Dummy camera controller"
        
    def camera_intialisation(self):
        self.flg_initialised = True
        
    def camera_termination(self):
        print('Terminating the camera')
        self.flg_initialised = False
    
    def get_initialisation_status(self) -> bool:
        return self.flg_initialised
    
    def frame_capture(self) -> (np.ndarray|None):
        return self._frame
    
    def img_capture(self) -> Image.Image:
        frame = self.frame_capture()
        self.img = Image.fromarray(frame)
        return self.img
    
    def vidcapture_show(self):
        self.status = "video capture on-going"
        self.vidcap_flag = True
        self.win_name = 'preview'
        
        while self.vidcap_flag:
            self.vidshow(self.win_name,self._frame)
            self.frame_capture()
            key = cv2.waitKey(20)
            if key == 27: # exit on ESC
                self.vidcap_flag = False
                time.sleep(0.5)
        self.status = "video capture stopped"
        self.quit()
    
    def vidshow(self,win_name,frame):
        cv2.imshow(win_name, frame)
    
    def quit(self):
        print('video stopped')
        cv2.destroyWindow(self.win_name)
        self.camera_termination()
        
if __name__ == '__main__':
    vid = Class_CameraController(show=True)
    vid.vidcapture_show()
    