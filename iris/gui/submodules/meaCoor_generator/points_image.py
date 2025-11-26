"""
An instance that manages a basic mapping method in tkinter.
This is similar to that of the mapping_method_rectxy_scan_image
but instead of generating a grid of scan pionts, it generates a list of points
that are defined by the user.
"""
if __name__ == '__main__':
    import sys
    import os
    SCRIPT_DIR = os.path.abspath(r'.\library')
    EXTENSION_DIR = os.path.abspath(r'.\extensions')
    sys.path.append(os.path.dirname(SCRIPT_DIR))
    sys.path.append(os.path.dirname(EXTENSION_DIR))

import tkinter as tk
from tkinter import ttk
import numpy as np
from PIL.Image import Image
import PIL

from iris.gui.motion_video import Wdg_MotionController
from iris.utils.general import *

from iris.data.calibration_objective import ImgMea_Cal, ImgMea_Cal_Hub
from iris.data.measurement_image import MeaImg_Unit, MeaImg_Handler
from iris.gui.image_calibration.Canvas_ROIdefinition import Canvas_Image_Annotations
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image

from iris.gui.submodules.meaCoor_generator.rectangle_image import Rect_Image

class Points_Image(Rect_Image):
    def __init__(
        self,
        container_frame,
        motion_controller:Wdg_MotionController,
        dataHub_img:Wdg_DataHub_Image,
        status_bar:tk.Label,
        *args, **kwargs
        ):
        super().__init__(
            container_frame=container_frame,
            motion_controller=motion_controller,
            dataHub_img=dataHub_img,
            status_bar=status_bar,
            *args, **kwargs
        )
        self._btn_show_image.configure(text='Define scan area',command=self._start_defining_scan_area)
        self._lbl_res_x.destroy()
        self._lbl_res_y.destroy()
        self._spin_res_x.destroy()
        self._spin_res_y.destroy()
        self._btn_set_res.destroy()
        self._lbl_calArea.destroy()
        
    @thread_assign
    def _start_defining_scan_area(self):
        """
        Automatically updates the image shown on the canvas
        """
        try:
            self._combo_imageUnits.configure(state='disabled')
            self._btn_show_image.configure(state='normal',text='Finalize scan area',command=self._set_scan_area)
            self._update_image_shown()
            thread = threading.Thread(target=self._update_image_annotation)
            thread.start()
            thread.join()
        except Exception as e: print('ERROR _auto_annotate_image:',e)
        finally:
            self._combo_imageUnits.configure(state='readonly')
            self._btn_show_image.configure(state='normal',text='Define scan area',command=self._start_defining_scan_area)
        
    @thread_assign
    def _set_scan_area(self):
        """
        Sets the scan area by taking the (x_min,y_min) and (x_max,y_max)
        from the list of clicked coordinates
        """
        try:    # Clear the click coordinates and the annotations except the scan area
            # Stop the auto update of the image
            self._flg_thd_auto_image.clear()
        except Exception as e: print('ERROR _set_calibration_area:',e)
    
    def get_mapping_coordinates_mm(self):
        # Stop the video feed to conserve resources
        try: self._flg_thd_auto_image.clear(); self._thread_auto_image.join(1)
        except Exception as e: print('ERROR get_mapping_coordinates:',e)
        
        if len(self._list_clickMeaCoor_mm) == 0:
            self._status_update('No coordinates clicked','yellow')
            return
        
        try:
            self._mapping_coordinates = [self._imgUnit.convert_mea2stg(coor) for coor in self._list_clickMeaCoor_mm]
            self._mapping_coordinates = [(coor[0],coor[1],self._coor_z_mm) for coor in self._mapping_coordinates]
            self._status_update('Coordinates generated','green')
        except Exception as e:
            self._status_update('Error converting coordinates','red')
            return
        
        return self._mapping_coordinates
    
def initialise_manager_hub_controllers():
    from iris.multiprocessing.basemanager import MyManager
    from iris.multiprocessing.dataStreamer_Raman import DataStreamer_Raman,initialise_manager_raman,initialise_proxy_raman
    from iris.multiprocessing.dataStreamer_StageCam import DataStreamer_StageCam,initialise_manager_stage,initialise_proxy_stage
    
    base_manager = MyManager()
    initialise_manager_raman(base_manager)
    initialise_manager_stage(base_manager)
    base_manager.start()
    ramanControllerProxy,ramanDictProxy=initialise_proxy_raman(base_manager)
    xyControllerProxy,zControllerProxy,stageDictProxy,stage_namespace=initialise_proxy_stage(base_manager)
    ramanHub = DataStreamer_Raman(ramanControllerProxy,ramanDictProxy)
    stageHub = DataStreamer_StageCam(xyControllerProxy,zControllerProxy,stageDictProxy,stage_namespace)
    ramanHub.start()
    stageHub.start()
    
    return xyControllerProxy, zControllerProxy, stageHub
    
def test():
    xyctrl,zctrl,stageHub = initialise_manager_hub_controllers()
    
    root = tk.Tk()
    root.title('Test')
    toplvl = tk.Toplevel(root)
    toplvl.title('motion controller')
    
    cal = ImgMea_Cal()
    cal.generate_dummy_params()
    
    status_bar = tk.Label(root,text='Ready',bd=1,relief=tk.SUNKEN,anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM,fill=tk.X)
    motion_controller = Wdg_MotionController(
        parent=toplvl,
        xy_controller=xyctrl,
        z_controller=zctrl,
        stageHub=stageHub,
        getter_imgcal=lambda: cal,
    )
    motion_controller._init_workers()
    motion_controller.pack()
    
    imghub = Wdg_DataHub_Image(main=root)
    imghub.test_generate_dummy()
    imghub.pack()
    
    mapping_method = Points_Image(
        container_frame=root,
        motion_controller=motion_controller,
        dataHub_img=imghub,
        status_bar=status_bar,
    )
    mapping_method.pack()
    
    root.mainloop()
    
if __name__ == '__main__':
    pass
    test()