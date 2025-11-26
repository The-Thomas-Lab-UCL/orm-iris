"""
An instance that manages a basic mapping method in tkinter.
This is similar to that of the mapping_method_rectxy_scan_constz mapping method
but this one can set it using an image (with an objective calibration file/params)
instead.
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

from iris.gui.motion_video import Wdg_MotionController
from iris.utils.general import *

from iris.data.calibration_objective import ImgMea_Cal, ImgMea_Cal_Hub
from iris.data.measurement_image import MeaImg_Unit, MeaImg_Handler
from iris.gui.image_calibration.Canvas_ROIdefinition import ImageCalibration_canvas_calibration
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image

from iris.data import SaveParamsEnum
from iris.gui import AppPlotEnum

class Rect_Image(tk.Frame):
    def __init__(
        self,
        container_frame,
        motion_controller:Wdg_MotionController,
        dataHub_img:Wdg_DataHub_Image,
        status_bar:tk.Label,
        *args, **kwargs
        ):
        super().__init__(container_frame)
        
    # >>> General setup <<<
        self._motion_controller = motion_controller
        self._dataHub_img = dataHub_img
        self._statbar = status_bar
        self._bg_colour = self._statbar.cget('background')
        
        video_feed_size = AppPlotEnum.MAP_METHOD_IMAGE_VIDEO_SIZE.value
        
        # Parameters
        self._imgUnit = None    # The image unit object
        self._img:Image = None                  # The image shown on the canvas
        self._img_coor_stage_mm:tuple = None    # The stage coordinates corresponding to the self._img camera frame of reference
        
    # >>> Frame setups <<<
        self.frm_image = tk.LabelFrame(self,text='1. Video feed/Coordinate selection')
        self.frm_control = tk.LabelFrame(self,text='Control Panel')
        
        self.frm_image.grid(row=0,column=0)
        self.frm_control.grid(row=0,column=1)
        
    # >>> Video feed setup <<<
        # Parameters
        self._list_imgunit_names = []
    
        # Frame
        self._canvas_image = ImageCalibration_canvas_calibration(self.frm_image,size_pixel=video_feed_size)
        self._bool_lowResImg = tk.BooleanVar(value=True)
        chk_lowResImg = tk.Checkbutton(self.frm_image,text='Use low resolution image (faster processing)',variable=self._bool_lowResImg)
        self._combo_imageUnits = ttk.Combobox(self.frm_image,state='disabled')
        self._btn_show_image = tk.Button(self.frm_image,text='Define scan area',command=self._start_defining_scan_area,width=20)
        self._lbl_coor_click = tk.Label(self.frm_image,text='Selected coordinates [μm]: None',wraplength=video_feed_size[0],anchor='w',justify='left')
        lbl_vidinfo = tk.Label(self.frm_image,text="Left click to select coordinates\nRight click to remove all the selected coordinates\n'3. Define scan area' will select an area that includes all the selected points",
                               background='yellow',wraplength=video_feed_size[0],anchor='w',
                               justify='left')
        
        self._canvas_image.bind('<Button-3>',lambda event: self._reset_click_coors())
        
        row=0
        self._canvas_image.grid(row=row,column=0,columnspan=2); row+=1
        chk_lowResImg.grid(row=row,column=0,sticky='w'); row+=1
        self._combo_imageUnits.grid(row=row,column=0,sticky='ew')
        self._btn_show_image.grid(row=row,column=1,sticky='e'); row+=1
        self._lbl_coor_click.grid(row=row,column=0,sticky='ew'); row+=1
        lbl_vidinfo.grid(row=row,column=0,sticky='ew'); row+=1
        
        # Params
        self._list_clickCoor_pxl = []    # The list of clicked coordinates in pixels
        self._list_clickMeaCoor_mm = []    # The list of clicked coordinates in mm
        self._list_rect_meaCoors_mm = []        # The rectangle coordinates for the scan area in mm
        
    # >>> Control panel setup <<<
        # Subframe setup
        sfrm_cal = tk.Frame(self.frm_control)
        sfrm_z = tk.Frame(self.frm_control)
        sfrm_res = tk.Frame(self.frm_control)
        
        sfrm_cal.grid(row=0,column=0)
        sfrm_z.grid(row=1,column=0)
        sfrm_res.grid(row=2,column=0)
        
        self.frm_control.columnconfigure(0,weight=1)
        self.frm_control.rowconfigure(0,weight=1)
        self.frm_control.rowconfigure(1,weight=1)
        self.frm_control.rowconfigure(2,weight=1)
        
    # > Calibration and scan setup widgets <
        self._str_lbl_calArea = tk.StringVar(value='Scan edges: None to None')
        self._lbl_calArea = tk.Label(sfrm_cal,textvariable=self._str_lbl_calArea,anchor='w',justify='left')
        
        # Grid
        self._lbl_calArea.grid(row=4,column=0,sticky='ew')
        
        sfrm_cal.columnconfigure(0,weight=1)
        sfrm_cal.rowconfigure(0,weight=1)
        sfrm_cal.rowconfigure(1,weight=1)
        sfrm_cal.rowconfigure(2,weight=1)
        sfrm_cal.rowconfigure(3,weight=1)
        sfrm_cal.rowconfigure(4,weight=1)
        
        # Params
        self._last_loadpath = SaveParamsEnum.DEFAULT_SAVE_PATH.value
        
    # > Z-coordinate setup widgets <
        self._str_lbl_coorz = tk.StringVar(value='Z-coordinate: None')
        lbl_coorz_entry = tk.Label(sfrm_z,textvariable=self._str_lbl_coorz,anchor='w',justify='left')
        self._var_coorz = tk.StringVar()
        self._entry_coorz = tk.Entry(sfrm_z,textvariable=self._var_coorz)
        self._btn_setcurr_coorz = tk.Button(sfrm_z,text='Set current Z',command=self._set_coor_z)
        
        self._entry_coorz.bind('<Return>',lambda event: self._set_coor_z(coor_mm=self._var_coorz.get()*1e3))
        
        lbl_coorz_entry.grid(row=0,column=0,columnspan=2,sticky='ew')
        self._entry_coorz.grid(row=1,column=0)
        self._btn_setcurr_coorz.grid(row=1,column=1)
        
    # > Resolution setup widgets <
        init_value_res = 2
        self._str_lbl_res_x = tk.StringVar(value=f'Resolution X: {init_value_res}')
        self._str_lbl_res_y = tk.StringVar(value=f'Resolution Y: {init_value_res}')
        self._lbl_res_x = tk.Label(sfrm_res,textvariable=self._str_lbl_res_x,anchor='w',justify='left',width=17)
        self._lbl_res_y = tk.Label(sfrm_res,textvariable=self._str_lbl_res_y,anchor='w',justify='left',width=17)
        self._spin_res_x = tk.Spinbox(sfrm_res,from_=1,to=100000,increment=1,values=init_value_res,width=7)
        self._spin_res_y = tk.Spinbox(sfrm_res,from_=1,to=100000,increment=1,values=init_value_res,width=7)
        self._btn_set_res = tk.Button(sfrm_res,text='Set resolution',command=self._set_resolution)
        
        self._spin_res_x.bind('<Return>',lambda event: self._set_resolution())
        self._spin_res_y.bind('<Return>',lambda event: self._set_resolution())
        
        # Grid
        self._lbl_res_x.grid(row=0,column=0,sticky='ew')
        self._lbl_res_y.grid(row=1,column=0,sticky='ew')
        self._spin_res_x.grid(row=0,column=1)
        self._spin_res_y.grid(row=1,column=1)
        self._btn_set_res.grid(row=2,column=0,columnspan=2,sticky='ew')
        
    # >>> Coordinate generation parameters <<<
        self._mapping_coordinates:list[tuple] = None
        self._res_x = int(float(self._spin_res_x.get()))
        self._res_y = int(float(self._spin_res_y.get()))
        self._stagecoor_init_xy_mm:tuple = None
        self._stagecoor_final_xy_mm:tuple = None
        self._coor_z_mm:float = None
        
    # # ><>< Debugging functions starts ><><
    #     btn_generate_coors = tk.Button(self,text='Generate coordinates',command=self.get_mapping_coordinates)
    #     btn_generate_coors.grid(row=1,column=0,columnspan=2,sticky='ew')
    # # ><>< Debugging functions ends ><><

    # >>> Other setups <<<
        self._flg_thd_auto_image = threading.Event()
        self._thread_auto_image = threading.Thread()
        self._thread_auto_combobox = threading.Thread(target=self._auto_update_combobox_imageUnits)
        self._thread_auto_combobox.start()
    
    @thread_assign
    def _set_resolution(self):
        """
        Sets the resolution of the mapping method
        """
        self._btn_set_res.config(state='disabled')
        self._spin_res_x.config(state='disabled')
        self._spin_res_y.config(state='disabled')
        
        res_x = self._spin_res_x.get()
        res_y = self._spin_res_y.get()
        
        try:
            res_x = int(float(res_x))
            res_y = int(float(res_y))
        except ValueError:
            self._status_update('Resolution must be a number','yellow')
            return
            
        if not res_x > 1 or not res_y > 1:
            self._status_update('Resolution must be greater than 1','yellow')
            return
        
        self._res_x = res_x
        self._res_y = res_y
        
        try:
            init_x,init_y = self._stagecoor_init_xy_mm
            final_x,final_y = self._stagecoor_final_xy_mm
            res_x_mm = (final_x-init_x)/(res_x-1)
            res_y_mm = (final_y-init_y)/(res_y-1)
            
            self._str_lbl_res_x.set(f'Res. X: {res_x_mm*1e3:.1f} μm, {self._res_x} pts')
            self._str_lbl_res_y.set(f'Res. Y: {res_y_mm*1e3:.1f} μm, {self._res_y} pts')
        except:
            self._str_lbl_res_x.set(f'Resolution X: {self._res_x} pts')
            self._str_lbl_res_y.set(f'Resolution Y: {self._res_y} pts')
        
        self._btn_set_res.config(state='normal')
        self._spin_res_x.config(state='normal')
        self._spin_res_y.config(state='normal')
    
    @thread_assign
    def _set_coor_z(self,coor_mm:str|None=None):
        """
        Sets the Z-coordinate to the given value
        
        Args:
            coor (str, optional): The Z-coordinate to set. Defaults to None.
        
        Note:
            If coor is None, it will get it from the current stage coordinate
        """
        self._btn_setcurr_coorz.config(state='disabled')
        self._entry_coorz.config(state='disabled')
        
        assert isinstance(coor_mm,str) or coor_mm == None, 'Coordinate must be a string or None'
        if coor_mm == None:
            stagecoor = self._motion_controller.get_coordinates_closest_mm()
            coor_mm = stagecoor[2]
        else:
            try: coor_mm = float(coor_mm)
            except Exception as e: print('ERROR _set_coor_z:',e); return
        
        self._coor_z_mm = coor_mm
        self._str_lbl_coorz.set('Z-coordinate [μm]: {:.1f}'.format(self._coor_z_mm*1e3))
        self._entry_coorz.delete(0,tk.END)
        self._entry_coorz.insert(0,'{}'.format(self._coor_z_mm))
        
        self._btn_setcurr_coorz.config(state='normal')
        self._entry_coorz.config(state='normal')
    
    @thread_assign
    def _set_scan_area(self):
        """
        Sets the scan area by taking the (x_min,y_min) and (x_max,y_max)
        from the list of clicked coordinates
        """        
        if len(self._list_clickMeaCoor_mm) < 2:
            self._status_update('Not enough coordinates selected','yellow')
            return
        
        # Get the calibration area
        list_x = [coor[0] for coor in self._list_clickMeaCoor_mm]
        list_y = [coor[1] for coor in self._list_clickMeaCoor_mm]
        
        x_min = min(list_x)
        x_max = max(list_x)
        y_min = min(list_y)
        y_max = max(list_y)
        
        coor_min = (x_min,y_min)
        coor_max = (x_max,y_max)
        
        stagecoor_min = self._imgUnit.convert_mea2stg(coor_min)
        stagecoor_max = self._imgUnit.convert_mea2stg(coor_max)
        
        self._stagecoor_init_xy_mm = stagecoor_min
        self._stagecoor_final_xy_mm = stagecoor_max
        
        print('Stage coordinates:',self._stagecoor_init_xy_mm,self._stagecoor_final_xy_mm)
        
        self._str_lbl_calArea.set('Scan edges [μm]:\n({:.1f},{:.1f}) to ({:.1f},{:.1f})'.format(x_min*1e3,y_min*1e3,x_max*1e3,y_max*1e3))
                
        try:    # Clear the click coordinates and the annotations except the scan area
            self._list_clickMeaCoor_mm.clear()
            self._canvas_image.clear_all_annotations()
            self._list_clickMeaCoor_mm.extend([(x_min,y_min),(x_max,y_max)])
            self._list_rect_meaCoors_mm = [(x_min,y_min),(x_max,y_max)]
            
            # Stop the auto update of the image
            self._flg_thd_auto_image.clear()
        except Exception as e: print('ERROR _set_calibration_area:',e)
    
    def _reset_click_coors(self):
        """
        Resets the click coordinates
        """
        self._list_clickMeaCoor_mm.clear()
        self._list_rect_meaCoors_mm.clear()
        self._canvas_image.clear_all_annotations()
        self._lbl_coor_click.configure(text='Selected coordinates [μm]: None')
    
    def _auto_update_combobox_imageUnits(self):
        """
        Automatically updates the combobox with the image units using
        a separate thread
        """
        while True:
            self._update_combobox_imageUnits()
            time.sleep(2)
    
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
    
    def _update_combobox_imageUnits(self):
        """
        Automatically updates the combobox with the image units
        """
        hub = self._dataHub_img.get_ImageMeasurement_Hub()
        list_unit_ids = hub.get_list_ImageUnit_ids()
        dict_idToName = hub.get_dict_IDtoName()
        list_unit_names = [dict_idToName[unit_id] for unit_id in list_unit_ids]
        
        # Only updates when necessary
        if list_unit_names == self._list_imgunit_names: return
        
        self._list_imgunit_names = list_unit_names.copy()
        self._combo_imageUnits.config(values=self._list_imgunit_names,state='readonly')
        
        if not self._combo_imageUnits.get() in self._list_imgunit_names\
            and len(self._list_imgunit_names) > 0:
            self._combo_imageUnits.current(0)
            self._update_image_shown
    
    def _get_selected_ImageUnit(self) -> MeaImg_Unit:
        """
        Returns the selected image unit in the combobox

        Returns:
            ImageMeasurement_Unit: The selected image unit
        """
        unit_name = self._combo_imageUnits.get()
        hub = self._dataHub_img.get_ImageMeasurement_Hub()
        unit_id = hub.get_dict_nameToID()[unit_name]
        return hub.get_ImageMeasurementUnit(unit_id)
    
    def _update_image_shown(self) -> None:
        """
        Updates the image shown on the canvas
        """
        self._imgUnit = self._get_selected_ImageUnit()
        flg_lowResImg = self._bool_lowResImg.get()
        self._img, self._img_coor_stage_mm, _ = self._imgUnit.get_image_all_stitched(low_res=flg_lowResImg)
        self._canvas_image.set_image(self._img)
        return
    
    def _update_image_annotation(self):
        """
        Automatically updates the image shown on the canvas
        """
        # Clear the click coordinates and the annotations
        self._list_clickMeaCoor_mm.clear()
        self._list_rect_meaCoors_mm.clear()
        self._canvas_image.clear_all_annotations()
        
        # Setup the ImageUnit and show it on the canvas
        self._imgUnit = self._get_selected_ImageUnit()
        self._update_image_shown()
        
        # Set the list recording the clicks (pixel coordinates)
        list_clicks_temp = self._canvas_image.start_recordClicks()
        
        # NOTE: Get the top left coordinates of the image for the stage reference
        # because all the calculations will be based on the pixel coordinates
        # that are measured relative to the 0,0 pixel coordinate, which is the
        # top left corner of the image
        stage_coor_mm = self._img_coor_stage_mm
        if stage_coor_mm == None: return
        # stage_coor_mm = self._imgUnit.get_topLeftStageCoor_mm()
        
        
        self._flg_thd_auto_image.set()
        
        while self._flg_thd_auto_image.is_set():
            time.sleep(0.3)   # Sleep to lower resource usage
            
            # Check if there are any clicks
            if len(list_clicks_temp) > 0:
                # Convert the pixel coordinates to mm
                click_coor_pxl = list_clicks_temp.pop()
                click_stageCoor_mm = self._imgUnit.convert_imgpt2stg(frame_coor_mm=stage_coor_mm,
                    coor_pixel=click_coor_pxl,correct_rot=True,low_res=self._bool_lowResImg.get())
                
                click_meaCoor_mm = click_stageCoor_mm
                
                # Append the click coordinates and update the labels
                self._list_clickMeaCoor_mm.append(click_meaCoor_mm)
                str_coorlist_um = ', '.join([f'({coor_mm[0]*1e3:.3f},{coor_mm[1]*1e3:.3f})'\
                    for coor_mm in self._list_clickMeaCoor_mm])
                self._lbl_coor_click.configure(text=f'Selected coordinates [μm]: {str_coorlist_um}')
                
            # Annotate the canvas with the stored click coordinates
            self._canvas_image.clear_all_annotations()
            low_res = self._bool_lowResImg.get()
            for coor_mea_mm in self._list_clickMeaCoor_mm:
                coor_pxl = self._imgUnit.convert_stg2imgpt(coor_stage_mm=stage_coor_mm,\
                    coor_point_mm=coor_mea_mm,correct_rot=True,low_res=low_res)
                self._canvas_image.annotate_canvas(coor_pxl,scale=True)
                
            # Draw the rectangle coordinatesf
            if len(self._list_rect_meaCoors_mm) == 2:
                # Convert the measurement coor back to stage coor
                list_rect_stageCoors_mm = self._list_rect_meaCoors_mm
                
                low_res = self._bool_lowResImg.get()
                try:
                    coor_pxl_min = self._imgUnit.convert_stg2imgpt(coor_stage_mm=stage_coor_mm,\
                        coor_point_mm=list_rect_stageCoors_mm[0],correct_rot=True,low_res=low_res)
                    coor_pxl_max = self._imgUnit.convert_stg2imgpt(coor_stage_mm=stage_coor_mm,\
                        coor_point_mm=list_rect_stageCoors_mm[1],correct_rot=True,low_res=low_res)
                    
                    self._canvas_image.draw_rectangle_canvas(coor_pxl_min,coor_pxl_max)
                except Exception as e: print('ERROR _auto_update_videoFeed:',e); self._list_rect_meaCoors_mm.clear()
    
    def get_mapping_coordinates_mm(self):
        # Stop the video feed to conserve resources
        try: self._flg_thd_auto_image.clear(); self._thread_auto_image.join(1)
        except Exception as e: print('ERROR get_mapping_coordinates:',e)
        
        if self._stagecoor_init_xy_mm == None or self._stagecoor_final_xy_mm == None or self._coor_z_mm == None:
            self._status_update('Not all coordinates set','yellow')
            return
        
        if self._res_x == None or self._res_y == None:
            self._status_update('Resolution not set','yellow')
            return
        
        # Generate the mapping coordinates
        x_min, y_min = self._stagecoor_init_xy_mm
        x_max, y_max = self._stagecoor_final_xy_mm
        
        x = np.linspace(x_min,x_max,self._res_x)
        y = np.linspace(y_min,y_max,self._res_y)
        
        self._mapping_coordinates = [(x_val,y_val,self._coor_z_mm) for x_val in x for y_val in y]
        self._status_update('Coordinates generated','green')
        
        # ><>< Debugging part starts ><><
        print('Mapping coordinates:',self._mapping_coordinates)
        # ><>< Debugging part ends ><><
        
        return self._mapping_coordinates
    
    def _status_update(self,message=None,bg_colour=None):
        """
        To update the status bar at the bottom
        
        Args:
            message (str): The update message
            bg_colour (str, optional): Background colour. Defaults to 'default'.
        """
        if bg_colour == None:
            bg_colour = self._bg_colour
        
        if message == None:
            message = 'Controller ready'
        self._statbar.configure(text=message,background=bg_colour)
    
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
    imghub.pack()
    
    mapping_method = Rect_Image(
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