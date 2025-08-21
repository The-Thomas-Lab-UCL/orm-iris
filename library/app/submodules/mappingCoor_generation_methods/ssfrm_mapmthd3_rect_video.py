"""
An instance that manages a basic mapping method in tkinter.
This is similar to that of the mapping_method_rectxy_scan_constz mapping method
but this one can set it using a video feed (with an objective calibration file/params)
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
import numpy as np

from typing import Callable, Literal

from uuid import uuid4

from library.app.sframe_motion_video import Frm_MotionController
from library.general_functions import *

from library.data_related.ObjectiveCalibration import ImageMeasurement_Calibration
from library.data_related.ImageMeasurement import ImageMeasurement_Unit, ImageMeasurement_Handler
from library.app.image_calibration.Canvas_ROIdefinition import ImageCalibration_canvas_calibration

from library.data_related import SaveParamsEnum
from library.app import AppPlotEnum

class mapping_method_rectxy_scan_video(tk.Frame):
    def __init__(self,
                 container_frame,
                 motion_controller:Frm_MotionController,
                 status_bar:tk.Label,
                 getter_imgcal:Callable[[],ImageMeasurement_Calibration],
                 *args, **kwargs):
        super().__init__(container_frame)
        
    # >>> General setup <<<
        self._motion_controller = motion_controller
        self._getter_ImageCalibration = getter_imgcal
        self._statbar = status_bar
        self._bg_colour = self._statbar.cget('background')
        
        video_feed_size = AppPlotEnum.MAP_METHOD_IMAGE_VIDEO_SIZE.value
        
    # >>> Frame setups <<<
        self.frm_video = tk.LabelFrame(self,text='2. Video feed/Coordinate selection')
        self.frm_control = tk.LabelFrame(self,text='Control Panel')
        
        self.frm_video.grid(row=0,column=0)
        self.frm_control.grid(row=0,column=1)
        
    # >>> Video feed setup <<<
        # Frame
        self._canvas_video = ImageCalibration_canvas_calibration(self.frm_video,size_pixel=video_feed_size)
        self._btn_update_video = tk.Button(self.frm_video,text='1. Start video feed',command=self._start_videoFeed)
        self._lbl_coor_click = tk.Label(self.frm_video,text='Selected coordinates: None',wraplength=video_feed_size[0],anchor='w',justify='left')
        lbl_vidinfo = tk.Label(self.frm_video,text="Left click to select coordinates\nRight click to remove all the selected coordinates\n'3. Define scan area' will select an area that includes all the selected points",
                               background='yellow',wraplength=video_feed_size[0],anchor='w',
                               justify='left')
        
        self._canvas_video.bind('<Button-3>',lambda event: self._reset_click_coors())
        
        self._canvas_video.grid(row=0,column=0)
        self._btn_update_video.grid(row=1,column=0)
        self._lbl_coor_click.grid(row=2,column=0,sticky='ew')
        lbl_vidinfo.grid(row=3,column=0,sticky='ew')
        
        # Params
        self._flg_videoFeed = threading.Event()
        self._list_clickCoor_mm = []    # The list of clicked coordinates in mm
        self._list_rect_coors_mm = []        # The rectangle coordinates for the scan area in mm
        
    # >>> Objective calibration setup <<<
        self._ImageUnit:ImageMeasurement_Unit = None
        
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
        self._btn_set_calArea = tk.Button(sfrm_cal,text='3. Define scan area',command=self._set_scan_area)
        self._str_lbl_calArea = tk.StringVar(value='Scan edges: None to None')
        lbl_calArea = tk.Label(sfrm_cal,textvariable=self._str_lbl_calArea,anchor='w',justify='left')
        
        # Grid
        self._btn_set_calArea.grid(row=3,column=0,sticky='ew')
        lbl_calArea.grid(row=4,column=0,sticky='ew')
        
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
        
        self._entry_coorz.bind('<Return>',lambda event: self._set_coor_z(coor=self._var_coorz.get(),unit='um'))
        
        lbl_coorz_entry.grid(row=0,column=0,columnspan=2,sticky='ew')
        self._entry_coorz.grid(row=1,column=0)
        self._btn_setcurr_coorz.grid(row=1,column=1)
        
    # > Resolution setup widgets <
        init_value_res = 2
        self._str_lbl_res_x = tk.StringVar(value=f'Resolution X: {init_value_res}')
        self._str_lbl_res_y = tk.StringVar(value=f'Resolution Y: {init_value_res}')
        lbl_res_x = tk.Label(sfrm_res,textvariable=self._str_lbl_res_x,anchor='w',justify='left',width=17)
        lbl_res_y = tk.Label(sfrm_res,textvariable=self._str_lbl_res_y,anchor='w',justify='left',width=17)
        self._spin_res_x = tk.Spinbox(sfrm_res,from_=1,to=100000,increment=1,values=init_value_res,width=7)
        self._spin_res_y = tk.Spinbox(sfrm_res,from_=1,to=100000,increment=1,values=init_value_res,width=7)
        self._btn_set_res = tk.Button(sfrm_res,text='Set resolution',command=self._set_resolution)
        
        self._spin_res_x.bind('<Return>',lambda event: self._set_resolution())
        self._spin_res_y.bind('<Return>',lambda event: self._set_resolution())
        
        # Grid
        lbl_res_x.grid(row=0,column=0,sticky='ew')
        lbl_res_y.grid(row=1,column=0,sticky='ew')
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
            init_x_mm, init_y_mm = self._stagecoor_init_xy_mm
            final_x_mm, final_y_mm = self._stagecoor_final_xy_mm
            res_x_mm = (final_x_mm - init_x_mm)/(res_x-1)
            res_y_mm = (final_y_mm - init_y_mm)/(res_y-1)
            
            self._str_lbl_res_x.set(f'Res. X: {res_x_mm*1e3:.1f} μm, {self._res_x} pts')
            self._str_lbl_res_y.set(f'Res. Y: {res_y_mm*1e3:.1f} μm, {self._res_y} pts')
        except:
            self._str_lbl_res_x.set(f'Resolution X: {self._res_x} pts')
            self._str_lbl_res_y.set(f'Resolution Y: {self._res_y} pts')
        
        self._btn_set_res.config(state='normal')
        self._spin_res_x.config(state='normal')
        self._spin_res_y.config(state='normal')
    
    @thread_assign
    def _set_coor_z(self,coor:str|None=None,unit:Literal['mm','um']='mm'):
        """
        Sets the Z-coordinate to the given value
        
        Args:
            coor (str, optional): The Z-coordinate to set. Defaults to None.
            unit (Literal['mm','um'], optional): The unit of the coordinate. Defaults to 'mm'.
        
        Note:
            If coor is None, it will get it from the current stage coordinate
        """
        self._btn_setcurr_coorz.config(state='disabled')
        self._entry_coorz.config(state='disabled')
        
        assert isinstance(coor,str) or coor == None, 'Coordinate must be a string or None'
        if coor == None:
            stagecoor = self._motion_controller.get_coordinates_closest_mm()
            coor = stagecoor[2]
        elif isinstance(coor,str):
            try: coor = float(coor)
            except Exception as e: print('ERROR _set_coor_z:',e); return
        
        if unit == 'um':
            coor_mm = coor*1e-3
        else:
            coor_mm = coor
        
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
        try:
            self._btn_set_calArea.config(state='disabled')
            
            if len(self._list_clickCoor_mm) < 2:
                self._status_update('Not enough coordinates selected','yellow')
                return
            
            # Get the calibration area
            list_clickCoor_pixel = [self._ImageUnit.convert_stg2imgpt(coor_stage_mm=(0,0),\
                coor_point_mm=coor_mm,correct_rot=False,low_res=False) for coor_mm in self._list_clickCoor_mm]
            
            x_min_pixel = min([coor[0] for coor in list_clickCoor_pixel])
            x_max_pixel = max([coor[0] for coor in list_clickCoor_pixel])
            y_min_pixel = min([coor[1] for coor in list_clickCoor_pixel])
            y_max_pixel = max([coor[1] for coor in list_clickCoor_pixel])
            
            coor_min_mm = self._ImageUnit.convert_imgpt2stg(
                frame_coor_mm=(0,0),
                coor_pixel=(x_min_pixel,y_min_pixel),
                correct_rot=False,
                low_res=False)
            coor_max_mm = self._ImageUnit.convert_imgpt2stg(
                frame_coor_mm=(0,0),
                coor_pixel=(x_max_pixel,y_max_pixel),
                correct_rot=False,
                low_res=False)
            
            x_min_mm = coor_min_mm[0]
            x_max_mm = coor_max_mm[0]
            y_min_mm = coor_min_mm[1]
            y_max_mm = coor_max_mm[1]
            
            # list_x = [coor[0] for coor in self._list_clickCoor_mm]
            # list_y = [coor[1] for coor in self._list_clickCoor_mm]
            
            # x_min_mm = min(list_x)
            # x_max_mm = max(list_x)
            # y_min_mm = min(list_y)
            # y_max_mm = max(list_y)
            
            coor_min = (x_min_mm,y_min_mm)
            coor_max = (x_max_mm,y_max_mm)
            
            stagecoor_min = self._ImageUnit.convert_mea2stg(coor_min)
            stagecoor_max = self._ImageUnit.convert_mea2stg(coor_max)
            
            self._stagecoor_init_xy_mm = stagecoor_min
            self._stagecoor_final_xy_mm = stagecoor_max
            
            print('Stage coordinates:',self._stagecoor_init_xy_mm,self._stagecoor_final_xy_mm)
            
            self._str_lbl_calArea.set('Scan edges [μm]:\n({:.1f},{:.1f}) to ({:.1f},{:.1f})'.format(x_min_mm*1e3,y_min_mm*1e3,x_max_mm*1e3,y_max_mm*1e3))
            
        # Clear the click coordinates and the annotations except the scan area
            self._list_clickCoor_mm.clear()
            self._canvas_video.clear_all_annotations()
            self._list_clickCoor_mm.extend([(x_min_mm,y_min_mm),(x_max_mm,y_max_mm)])
            self._list_rect_coors_mm = [(x_min_mm,y_min_mm),(x_max_mm,y_max_mm)]
        except Exception as e:
            print('ERROR _set_calibration_area:',e)
        finally:
            self._btn_set_calArea.config(state='normal')
            
    
    def _stop_videoFeed(self):
        self._flg_videoFeed.clear()
        self._btn_update_video.configure(text='1. Start video feed',command=self._start_videoFeed)
        self._status_update('Video feed stopped')
    
    def _start_videoFeed(self):
        img_cal = self._getter_ImageCalibration()
        if not isinstance(img_cal,ImageMeasurement_Calibration):
            self._status_update('No calibration loaded','yellow')
            return
        
        print(img_cal.id)
        self._ImageUnit = ImageMeasurement_Unit(unit_name='Video feed_'+str(uuid4())
                                                ,calibration=img_cal)
        
        # Start the video feed
        threading.Thread(target=self._auto_update_videoFeed).start()
        self._btn_update_video.configure(text='Stop video feed',command=self._stop_videoFeed)
    
    def _reset_click_coors(self):
        """
        Resets the click coordinates
        """
        self._list_clickCoor_mm.clear()
        self._list_rect_coors_mm.clear()
        self._canvas_video.clear_all_annotations()
        self._lbl_coor_click.configure(text='Selected coordinates [μm]: None')
    
    def _auto_update_videoFeed(self):
        """
        Automatically updates the video feed on the canvas
        """
        # Clear the click coordinates and the annotations
        self._list_clickCoor_mm.clear()
        self._list_rect_coors_mm.clear()
        self._canvas_video.clear_all_annotations()
        
        # Set the list recording the clicks (pixel coordinates)
        list_clicks_temp = self._canvas_video.start_recordClicks()
        self._flg_videoFeed.set()
        while self._flg_videoFeed.is_set():
            img = self._motion_controller.get_current_image()
            if img is None: time.sleep(0.1); continue
            
            stage_coor_mm = self._motion_controller.get_coordinates_closest_mm()
            
            self._canvas_video.set_image(img)
            
            # Check if there are any clicks
            if len(list_clicks_temp) > 0:
                # Convert the pixel coordinates to mm
                click_coor_pxl = list_clicks_temp.pop()
                click_coor_mm = self._ImageUnit.convert_imgpt2stg(frame_coor_mm=stage_coor_mm[:2],\
                    coor_pixel=click_coor_pxl,correct_rot=False,low_res=False)
                
                # Append the click coordinates and update the label
                self._list_clickCoor_mm.append(click_coor_mm)
                str_coorlist_um = ', '.join([f'({coor_mm[0]*1e3:.1f},{coor_mm[1]*1e3:.1f})'\
                    for coor_mm in self._list_clickCoor_mm])
                self._lbl_coor_click.configure(text=f'Selected coordinates [μm]: {str_coorlist_um}')
                
            # Annotate the canvas with the stored click coordinates
            self._canvas_video.clear_all_annotations()
            for coor_mm in self._list_clickCoor_mm:
                coor_pxl = self._ImageUnit.convert_stg2imgpt(coor_stage_mm=stage_coor_mm[:2],\
                    coor_point_mm=coor_mm,correct_rot=False,low_res=False)
                self._canvas_video.annotate_canvas(coor_pxl,scale=True)
                
            # Draw the rectangle coordinates
            if len(self._list_rect_coors_mm) == 2:
                try:
                    coor_pxl_min = self._ImageUnit.convert_stg2imgpt(coor_stage_mm=stage_coor_mm[:2],\
                        coor_point_mm=self._list_rect_coors_mm[0],correct_rot=False,low_res=False)
                    coor_pxl_max = self._ImageUnit.convert_stg2imgpt(coor_stage_mm=stage_coor_mm[:2],\
                        coor_point_mm=self._list_rect_coors_mm[1],correct_rot=False,low_res=False)
                    
                    self._canvas_video.draw_rectangle_canvas(coor_pxl_min,coor_pxl_max)
                except Exception as e: print('ERROR _auto_update_videoFeed:',e); self._list_rect_coors_mm.clear()
    
    def get_mapping_coordinates_mm(self):
        # Stop the video feed to conserve resources
        try: self._stop_videoFeed()
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
    from library.multiprocessing.basemanager import MyManager
    from library.multiprocessing.raman_measurement_hub import RamanMeasurementHub,initialise_manager_raman,initialise_proxy_raman
    from library.multiprocessing.stage_measurement_hub import stage_measurement_hub,initialise_manager_stage,initialise_proxy_stage
    
    base_manager = MyManager()
    initialise_manager_raman(base_manager)
    initialise_manager_stage(base_manager)
    base_manager.start()
    ramanControllerProxy,ramanDictProxy=initialise_proxy_raman(base_manager)
    xyControllerProxy,zControllerProxy,stageDictProxy,stage_namespace=initialise_proxy_stage(base_manager)
    ramanHub = RamanMeasurementHub(ramanControllerProxy,ramanDictProxy)
    stageHub = stage_measurement_hub(xyControllerProxy,zControllerProxy,stageDictProxy,stage_namespace)
    ramanHub.start()
    stageHub.start()
    
    return xyControllerProxy, zControllerProxy, stageHub
    
def test():
    xyctrl,zctrl,stageHub = initialise_manager_hub_controllers()
    
    root = tk.Tk()
    root.title('Test')
    toplvl = tk.Toplevel(root)
    toplvl.title('motion controller')
    
    status_bar = tk.Label(root,text='Ready',bd=1,relief=tk.SUNKEN,anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM,fill=tk.X)
    motion_controller = Frm_MotionController(
        parent=toplvl,
        xy_controller=xyctrl,
        z_controller=zctrl,
        stageHub=stageHub
    )
    motion_controller.initialise_auto_updater()
    motion_controller.pack()
    
    mapping_method = mapping_method_rectxy_scan_video(root,motion_controller,status_bar)
    mapping_method.pack()
    
    root.mainloop()
    
if __name__ == '__main__':
    test()