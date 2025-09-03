"""
A class to automatically take images and tile them into a single image
"""
import os

import multiprocessing.pool as mpp

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog

from PIL import Image
import numpy as np

from copy import deepcopy

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))

from iris.utils.general import *

from iris.gui.motion_video import Frm_MotionController
from iris.gui.dataHub_MeaImg import Frm_DataHub_Image, Frm_DataHub_ImgCal
from iris.gui.hilvl_coorGen import Frm_Treeview_MappingCoordinates

from iris.gui.submodules.meaCoor_generator.ssfrm_tilemthd1_rect_around import tiling_method_rectxy_scan_constz_around_a_point as TileMethod

from iris.gui.image_calibration.Canvas_ROIdefinition import ImageCalibration_canvas_calibration

from iris.data.measurement_image import MeaImg_Unit
from iris.data.calibration_objective import ImgMea_Cal
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.multiprocessing.dataStreamer_StageCam import DataStreamer_StageCam

from iris.gui import AppPlotEnum

class Frm_HiLvlTiling(tk.Frame):
    """
    A high level controller to take images, tile them into a single image, and save them 
    as an ImageMeasurement_Unit obj
    """
    
    def __init__(
        self,
        master,
        motion_controller:Frm_MotionController,
        stageHub:DataStreamer_StageCam,
        dataHub_img:Frm_DataHub_Image,
        dataHub_imgcal:Frm_DataHub_ImgCal,
        coorHub:List_MeaCoor_Hub,
        processor:mpp.Pool
        ) -> None:
        """
        Args:
            master : Parent widget
            motion_controller (Frm_MotionController): Motion controller object
            stageHub (stage_measurement_hub): Stage measurement hub
            dataHub_img (Frm_DataHub_Image): Data hub for the image data
            dataHub_imgcal (Frm_DataHub_ImgCal): Data hub for the image calibration data
            processor (multiprocessing.pool.Pool): Processor pool
        
        Returns:
            None
        """
        assert isinstance(motion_controller, Frm_MotionController), 'motion_controller must be a Frm_MotionController object'
        assert isinstance(stageHub, DataStreamer_StageCam), 'stageHub must be a stage_measurement_hub object'
        assert isinstance(dataHub_img, Frm_DataHub_Image), 'dataHub_img must be a Frm_DataHub_Image object'
        assert isinstance(dataHub_imgcal, Frm_DataHub_ImgCal), 'dataHub_imgcal must be a Frm_DataHub_ImgCal object'
        assert isinstance(processor, mpp.Pool), 'processor must be a multiprocessing.pool.Pool object'
        
        super().__init__(master)
        self._motion_controller = motion_controller
        self._stageHub = stageHub
        self._dataHub_img = dataHub_img
        self._dataHub_imgcal = dataHub_imgcal
        self._coorHub = coorHub
        self._processor = processor
        
    # >>> Main parameters <<<
        self._getter_calibration = self._dataHub_imgcal.get_selected_calibration
        
    # >>> Top level layout <<<
        frm_img = tk.Frame(self)
        frm_img_control = tk.Frame(self)
        frm_coorGen = tk.Frame(self)
        frm_tiling_control = tk.Frame(self)
        self._statbar = tk.Label(self,anchor='w',relief='sunken',bd=1)
        
        frm_img.grid(row=0,column=0,sticky='nsew')
        frm_img_control.grid(row=1,column=0,sticky='nsew')
        frm_coorGen.grid(row=0,column=1,sticky='nsew')
        frm_tiling_control.grid(row=1,column=1,sticky='nsew')
        self._statbar.grid(row=2,column=0,columnspan=2,sticky='sew')
        
        # Grid weight configurations
        self.grid_rowconfigure(0,weight=1)
        self.grid_rowconfigure(1,weight=1)
        self.grid_rowconfigure(2,weight=1)
        self.grid_columnconfigure(0,weight=1)
        self.grid_columnconfigure(1,weight=1)
        
    # >>> Image frame <<<
        self._canvas_img = ImageCalibration_canvas_calibration(
            main=frm_img,
            size_pixel=AppPlotEnum.IMGCAL_IMG_SIZE.value,
            )
        self._bool_lowResImg = tk.BooleanVar(value=True)
        chk_lowResImg = tk.Checkbutton(frm_img,text='Use low resolution image (faster processing)',variable=self._bool_lowResImg)
        
        self._canvas_img.grid(row=0,column=0)
        chk_lowResImg.grid(row=1,column=0,sticky='ew')
        
    # >>> Image control frame <<<
        self._list_imgunit_names = []
        self._img_shown:Image.Image = None
        self._combo_imgunits = ttk.Combobox(frm_img_control,state='disabled')
        self._btn_plot_imgunit = tk.Button(frm_img_control,text='Show stored image',command=self._plot_imgunit)
        self._btn_save_img_png = tk.Button(frm_img_control,text='Save image as PNG',command=self._save_img_png)
        
        self._combo_imgunits.bind('<<ComboboxSelected>>',lambda event: self._plot_imgunit())
        
        self._combo_imgunits.grid(row=0,column=0,sticky='ew')
        self._btn_plot_imgunit.grid(row=0,column=1,sticky='ew')
        self._btn_save_img_png.grid(row=0,column=2,sticky='ew')
        
        frm_img_control.grid_rowconfigure(0,weight=1)
        frm_img_control.grid_columnconfigure(0,weight=1)
        frm_img_control.grid_columnconfigure(1,weight=0)
        frm_img_control.grid_columnconfigure(2,weight=0)
        
    # >>> Coordinate generation frame <<<
        self._coorgen = TileMethod(
            master=frm_coorGen,
            motion_controller=self._motion_controller,
            coorHub=self._coorHub,
            getter_cal=self._getter_calibration,
        )
        self._coorgen.grid(row=0,column=0)
        
    # >>> Tiling control frame <<<
        self._btn_takeImages = tk.Button(frm_tiling_control,text='Take image',command=self._take_image_thread)
        
        self._btn_takeImages.grid(row=0,column=0,sticky='ew')
        
        frm_tiling_control.grid_rowconfigure(0,weight=1)
        frm_tiling_control.grid_columnconfigure(0,weight=1)
        
    # >>> Other setups <<<
        self._flg_autoupdate = True
        self._thread_autoupdate = threading.Thread(target=self._autoupdate_combobox)
        self._thread_autoupdate.start()
        
    @thread_assign
    def _plot_imgunit(self):
        """
        Plot the ImageUnit selected in the combobox
        """
        try:
            self._flg_autoupdate=False
            self._combo_imgunits.config(state='disabled')
            self._btn_plot_imgunit.config(state='disabled',text='Plotting...')
            
            imgUnit = self._get_selected_ImageUnit()
            if not isinstance(imgUnit,MeaImg_Unit): raise ValueError('No ImageUnit found')
            if not(imgUnit.check_measurement_exist() and imgUnit.check_calibration_exist()):
                raise ValueError('No image or calibration found')
            
            self._img_shown = imgUnit.get_image_all_stitched(low_res=self._bool_lowResImg.get())[0]
            self._canvas_img.set_image(self._img_shown)
            self.update_statusbar('ImageUnit plotted')
        except Exception as e:
            messagebox.showerror('Error in _plot_imgunit: ',str(e))
        finally:
            self._flg_autoupdate=True
            self._combo_imgunits.config(state='readonly')
            self._btn_plot_imgunit.config(state='normal',text='Plot ImageUnit')
        
    @thread_assign
    def _save_img_png(self):
        """
        Save the image being shown as a png file. Prompts the user for the file savepath.
        """
        try:
            self._btn_save_img_png.config(state='disabled')
            
            assert isinstance(self._img_shown,Image.Image), 'No image to save'
            
            init_name = self._get_selected_ImageUnit().get_IdName()[1]
            
            savepath = filedialog.asksaveasfilename(
                title='Save image as PNG',
                filetypes=[('PNG files','*.png')],
                defaultextension='.png',
                initialfile=init_name)
            
            if not savepath.endswith('.png'): savepath+='.png'
            
            self._img_shown.save(savepath)
            messagebox.showinfo('Image saved','Image saved as PNG')
            
        except Exception as e: messagebox.showerror('Error',str(e))
        finally: self._btn_save_img_png.config(state='normal')
        
    def _autoupdate_combobox(self):
        """
        Runs a separate thread to automatically update the combobox
        """
        while True:
            try:
                time.sleep(2)
                if not self._flg_autoupdate: continue
                self._update_combobox()
            except Exception as e:
                print('_autoupdate_combobox Error:',e)
        
    def _update_combobox(self):
        """
        Update the combobox with the ImageUnits stored in the ImageHub
        using the DataHubImage
        """
        hub = self._dataHub_img.get_ImageMeasurement_Hub()
        list_ids = hub.get_list_ImageUnit_ids()
        dict_idToName = hub.get_dict_IDtoName()
        list_names = [dict_idToName[id] for id in list_ids]
        
        # Only update when needed
        if list_names == self._list_imgunit_names: return
        
        self._list_imgunit_names = list_names.copy()
        self._combo_imgunits.config(values=list_names,state='readonly')
        
        if self._combo_imgunits.get() not in self._list_imgunit_names:
            self._combo_imgunits.current(0)
        
    @thread_assign
    def _take_image_thread(self):
        """
        Runs the _take_image function in a separate thread
        """
        try:
            flg_stop = threading.Event()
            self._btn_takeImages.config(text='STOP',command=lambda: flg_stop.set())
            self._motion_controller.disable_overlays()
            self._take_image(flg_stop)
        except Exception as e:
            messagebox.showerror('Error',str(e))
        finally:
            self._btn_takeImages.config(state='normal',text='Take image',command=self._take_image_thread)
        
    def _get_selected_ImageUnit(self) -> MeaImg_Unit:
        """
        Get the selected ImageUnit from the combobox

        Returns:
            ImageMeasurement_Unit: The selected ImageUnit
            
        
        """
        hub = self._dataHub_img.get_ImageMeasurement_Hub()
        dict_nameToID = hub.get_dict_nameToID()
        
        name = self._combo_imgunits.get()
        id = dict_nameToID[name]
        return hub.get_ImageMeasurementUnit(id)
        
    def _take_image(self, flg_stop:threading.Event):
        """
        Take images and tile them into a single image
        
        Args:
            flg_stop (threading.Event): Event to stop the function
        """
        # > Initial checks
        cal = deepcopy(self._getter_calibration())
        if not isinstance(cal,ImgMea_Cal) or not cal.check_calibration_set():
            messagebox.showerror('Error','No calibration found')
            return
        result = self._coorgen.get_tiling_coordinates_mm_and_cropFactors_rel()
        if result is None: messagebox.showerror('Error','No coordinates generated'); return
        map_coor, cropx_ratio_red, cropy_ratio_red = result
        if not map_coor: messagebox.showerror('Error','No coordinates found'); return
        
        # > Modify the calibration file
        img_test = self._motion_controller.get_current_image(wait_newimage=True)
        if not isinstance(img_test,Image.Image): messagebox.showerror('Error','No image received from the controller'); return
        
        shape = img_test.size
        laserx = cal.laser_coor_x_mm
        lasery = cal.laser_coor_y_mm
        cropx_pixel = int(shape[0]*cropx_ratio_red)//2  # Cropped pixel x-distance from the edge (one of the two sides!!)
        cropy_pixel = int(shape[1]*cropy_ratio_red)//2  # Cropped pixel y-distance from the edge (one of the two sides!!)
        cropx_mm,cropy_mm = cal.convert_imgpt2stg(
            coor_img_pixel=np.array((cropx_pixel,cropy_pixel)),
            coor_stage_mm=np.array((0,0)))
        
        laserx -= cropx_mm
        lasery -= cropy_mm
        
        cal.set_calibration_params(
            scale_x_pixelPerMm=cal.scale_x_pixelPerMm,
            scale_y_pixelPerMm=cal.scale_y_pixelPerMm,
            laser_coor_x_mm=laserx,
            laser_coor_y_mm=lasery,
            rotation_rad=cal.rotation_rad,
            flip_y=cal.flip_y,
        )
        
        cal.id += f'_{cropx_ratio_red}X,{cropy_ratio_red}Ycrop'
        
        # > Prep the image storage
        list_names = self._dataHub_img.get_ImageMeasurement_Hub().get_list_ImageUnit_ids()
        while True:
            imgname = messagebox_request_input('Image name','Enter the name of the image:', default=map_coor.mappingUnit_name)
            if not imgname: return
            if imgname in list_names:
                retry = messagebox.askretrycancel('Error','Image name already exists. Please enter a different name.')
                if not retry: return
                else: continue
            break
        
        imgUnit = MeaImg_Unit(unit_name=imgname,calibration=cal)
        
        # > Go through the coordinates to take the images
        totalcoor = len(map_coor.mapping_coordinates)
        flg_stop.clear()
        self.update_statusbar('Taking images: {} of {}'.format(1,totalcoor))
        for i,coor in enumerate(map_coor.mapping_coordinates):
            if flg_stop.is_set(): break
            x,y,z = coor
            self._motion_controller.go_to_coordinates(
                coor_x_mm=x,coor_y_mm=y,coor_z_mm=z)
            img = self._motion_controller.get_current_image(wait_newimage=True)
            
            if not isinstance(img,Image.Image): messagebox.showerror('Error','No image received from the controller'); continue
            
            img = img.crop((cropx_pixel,cropy_pixel,shape[0]-cropx_pixel,shape[1]-cropy_pixel))
            
            imgUnit.add_measurement(
                timestamp=get_timestamp_us_str(),
                x_coor=x-cropx_mm,
                y_coor=y-cropy_mm,
                z_coor=z,
                image=img
            )
            
            self.update_statusbar('Taking images: {} of {}'.format(i+1,totalcoor))
            
            # Show the images
            self._img_shown = imgUnit.get_image_all_stitched(low_res=self._bool_lowResImg.get())[0]
            self._canvas_img.set_image(self._img_shown)
            
        self.update_statusbar('Capture complete')
        
        # > Prompt the user for an image name
        self._dataHub_img.append_ImageMeasurementUnit(imgUnit,flg_nameprompt=False)
        
    def update_statusbar(self,text:str=''):
        """
        Update the status bar
        
        Args:
            text (str): Text to display
            bkg (str): Background colour
        """
        self._statbar.config(text=text)
        
            