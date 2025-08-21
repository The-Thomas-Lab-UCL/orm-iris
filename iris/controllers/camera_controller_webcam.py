"""
A controller to take in a video feed and display
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
    

from iris.controllers import ControllerConfigEnum
from iris.controllers.class_camera_controller import Class_CameraController

class CameraController_Webcam(Class_CameraController):
    """
    A class that operates the camera, takes and stores the current frame for a webcam.
    """
    def __init__(self,show=False) -> None:
        self.camera_index = ControllerConfigEnum.CAMERA_INDEX.value    # Takes the 1st capture device as the source
                                            # it is possible that the desired device is NOT the 1st one
                                            # in this case, a different index should be chosen by trial and error
                                            # index = 0,1,2,3,... etc.
        self.camera_intialisation()
        self.status = "video capture initialisation"  # Status message of the class
        
        if show == True:
            self.win_name = 'preview'
            cv2.namedWindow(self.win_name)
        
        # try to get the first frame
        self.frame_flag = False # An indicator if there's a frame stored
        if self.vc.isOpened():
            self.frame_flag, self.frame = self.vc.read()
            self.img = Image.fromarray(self.frame)
            
        # Post-processing parameters
        self._mirrorx = ControllerConfigEnum.CAMERA_MIRRORX.value
        self._mirrory = ControllerConfigEnum.CAMERA_MIRRORY.value
        
        self.flg_initialised = True

    def camera_intialisation(self):
        self.vc = cv2.VideoCapture(0)
        self.flg_initialised = True
        
    def camera_termination(self):
        self.vc.release()
        self.flg_initialised = False
    
    def get_initialisation_status(self) -> bool:
        return self.flg_initialised
    
    def frame_capture(self) -> (np.ndarray|None):
        self.frame_flag, self.frame = self.vc.read()
        
        if self._mirrorx: self.frame = cv2.flip(self.frame, 0)
        if self._mirrory: self.frame = cv2.flip(self.frame, 1)
        
        return self.frame
    
    def img_capture(self) -> Image.Image:
        # self.frame_flag, self.frame = self.vc.read()
        img = Image.fromarray(cv2.cvtColor(self.vc.read()[1], cv2.COLOR_BGR2RGBA))
        
        if self._mirrorx: img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if self._mirrory: img = img.transpose(Image.FLIP_TOP_BOTTOM)
        
        self.img = img
        return self.img
    
    def vidcapture_show(self):
        self.status = "video capture on-going"
        self.vidcap_flag = True
        
        while self.vidcap_flag:
            self.vidshow(self.win_name,self.frame)
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
    vid = CameraController_Webcam(show=True)
    vid.vidcapture_show()
    
    vid.camera_termination()
    print('>>>>> Webcam terminated <<<<<')
    time.sleep(2)
    
    vid.__init__()
    vid.vidcapture_show()
    print('>>>>> Webcam re-initialised <<<<<')
    
    