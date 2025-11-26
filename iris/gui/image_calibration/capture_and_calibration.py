import sys
import os
from typing import Callable
from copy import deepcopy

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

import tkinter as tk
from tkinter import messagebox
import numpy as np
from PIL import Image

import multiprocessing.pool as mpp
import threading

from iris.utils.general import *


from iris.data.measurement_image import MeaImg_Unit, MeaImg_Handler
from iris.data.calibration_objective import ImgMea_Cal

from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image,Wdg_DataHub_ImgCal
from iris.gui.image_calibration.Canvas_ROIdefinition import ImageCalibration_canvas_calibration

from iris.data import SaveParamsEnum
from iris.gui import AppPlotEnum

class sFrm_CaptureAndCalibration(tk.Frame):
    """
    Sub-frame to form the calibration file of an ImageMeasurement object.
    I.e., to perform an objective calibration.
    
    Note:
        initialise_auto_updaters must be called after the object is created
    """
    def __init__(self,
                 master,
                 top_level:tk.Toplevel,
                 processor:mpp.Pool,
                 dataHub_img:Wdg_DataHub_Image,
                 dataHub_imgcal:Wdg_DataHub_ImgCal,
                 getter_coor:Callable[[],tuple[float,float,float]],
                 getter_cameraImage:Callable[[],Image.Image],
                 update_statbar:Callable[['str','str',int],None]):
        """
        Args:
            main (tk.Frame): Main frame to put the sub-frame in
            top_level (tk.Toplevel): Top-level window to put the sub-frame in
            mea_img_getter (Callable): Callable to get the measurement image
            getter_coor (Callable): Callable to get the stage coordinate
            getter_cameraFrame (Callable): Callable to get the camera frame
            update_statbar (Callable[['str','str',int], None]): Callable to update the status bar
        """
        super().__init__(master)
        self._window = top_level
        self._processor = processor
        self._getter_cameraImage = getter_cameraImage
        self._getter_coordinate = getter_coor
        self._update_status_bar = update_statbar
        
        self._dataHub_img = dataHub_img
        self._dataHub_imgcal = dataHub_imgcal
        
        self._showHints = AppPlotEnum.IMGCAL_SHOWHINTS.value
        
    # >>> Main parameters <<<
        self._getter_calibration = self._dataHub_imgcal.get_selected_calibration
        self._meaImgUnit = MeaImg_Unit(
            unit_name='Calibration',
            calibration=self._getter_calibration(),
            reconstruct=True
        )
        
    # >>> Subframe setup <<<
        frm_disp = tk.Frame(self)
        frm_control_capture = tk.Frame(self)
        frm_control_calibrate = tk.Frame(self)
        
        frm_disp.grid(row=0, column=0,sticky='ew')
        frm_control_capture.grid(row=1, column=0,sticky='ew')
        frm_control_calibrate.grid(row=0, column=1,rowspan=2,sticky='nsew')
        
    # >>> Display widget <<<
        # Canvas to display the image and button to show current image
        self._canvas_img = ImageCalibration_canvas_calibration(frm_disp)
        self._bool_lowResImg = tk.BooleanVar(value=False)
        chk_lowResImg = tk.Checkbutton(frm_disp, text='Show low resolution image (faster processing)', variable=self._bool_lowResImg)
        self._btn_showImage = tk.Button(frm_disp, text='Show image', command=self._show_stitched_images)
        self._btn_showLiveFeed = tk.Button(frm_disp, text='Refresh live feed', command=self.initialise_auto_updaters)
        
        # Pack the widgets
        col=0
        self._canvas_img.grid(row=0, column=col,columnspan=2,sticky='ew'); col+=1
        chk_lowResImg.grid(row=1, column=col,sticky='ew'); col+=1
        self._btn_showImage.grid(row=1, column=col,sticky='ew'); col+=1
        self._btn_showLiveFeed.grid(row=1, column=col,sticky='ew'); col+=1
        
    # >>> Capture widgets <<<
        # Buttons for image capture
        self._btn_capture = tk.Button(frm_control_capture, text='Capture image', command=self._capture_image)
        self._btn_resetCapture = tk.Button(frm_control_capture, text='Reset capture', command=self._reset_capture)
        self._btn_save = tk.Button(frm_control_capture, text='Save image to DataHub', command=self._save_image)

        # Pack the widgets
        self._btn_capture.grid(row=0, column=0,padx=(2,0),sticky='ew')
        self._btn_resetCapture.grid(row=0, column=1,padx=(0,2),sticky='ew')
        self._btn_save.grid(row=0, column=2,padx=(0,2),sticky='ew')
        
        frm_control_capture.grid_rowconfigure(0,weight=1)
        frm_control_capture.grid_columnconfigure(0,weight=1)
        frm_control_capture.grid_columnconfigure(1,weight=1)
        frm_control_capture.grid_columnconfigure(2,weight=1)
        
    # >>> Calibration adjustment <<<
        # Sub-frame for calibration adjustment
        self._frm_cal_adj=sFrm_CalibrationAdjustment(
            main=frm_control_calibrate,
            processor=self._processor,
            imgUnit_getter=lambda:self._meaImgUnit
            )
        self._frm_cal_adj.grid(row=0, column=1,sticky='ew')
        self._frm_cal_adj.config_finetune_calibration_button(callback=self._finetune_calibration)
        self._frm_cal_adj.config_calibrate_button(callback=self._perform_calibration)
            
    # >>> Display parameters <<<
        self._videoRefreshRate = 25    # Refresh rate of the video feed in Hz
        
    # Thread for a live video feed
        self._flg_video_pause = threading.Event()
        self._thd_videofeed:threading.Thread = None
    
    def _save_image(self):
        """
        Saves the local image to the Image DataHub
        """
        self._dataHub_img.append_ImageMeasurementUnit(self._meaImgUnit, flg_nameprompt=True)
        self._meaImgUnit = MeaImg_Unit(
            unit_name='Calibration',
            calibration=self._getter_calibration(),
            reconstruct=True
        )
    
    def initialise_auto_updaters(self) -> None:
        """
        Initialises the auto-updaters for the calibration adjustment widgets
        """
        self._thd_videofeed = threading.Thread(target=self._continuous_video_feed)
        self._thd_videofeed.start()
    
    def _continuous_video_feed(self):
        """
        Displays the video feed on the canvas
        """
        while True:
            # Check if the window is minimised then pause the video feed
            if self._window.state() not in ['normal','zoomed']:
                time.sleep(1)
                continue
            
            if self._flg_video_pause.is_set():
                time.sleep(3/self._videoRefreshRate)
                continue
            time1 = time.time()
            
            img_ori = self._getter_cameraImage()
            self._canvas_img.set_image(img_ori)
            
            time2 = time.time()
            if time2-time1 < 1/self._videoRefreshRate:
                time.sleep(1/self._videoRefreshRate - (time2-time1))
    
    def _reset_capture(self):
        """
        Resets the capture process
        """
        result = messagebox.askyesno('Reset capture','This will delete all stored image. Are you sure you want to proceed?')
        if not result: return
        
        self._meaImgUnit.reset_measurement()
        self._update_status_bar('Capture reset',bkg='yellow')
    
    def _capture_image(self):
        """
        Captures the image from the camera and saves it to the image measurement
        """
        try:
            self._update_status_bar('Capturing image...',bkg='yellow')
            img:Image.Image = self._getter_cameraImage()
            coor = self._getter_coordinate()
            
            meaImg = self._meaImgUnit
            cal = self._getter_calibration()
            meaImg.set_calibration_ImageMeasurement_Calibration(cal)
            
            timestamp = get_timestamp_us_str()
            meaImg.add_measurement(
                timestamp=timestamp,
                x_coor=coor[0],
                y_coor=coor[1],
                z_coor=coor[2],
                image=img
            )
            
            self._show_stitched_images()
            
            self._update_status_bar('Image captured',bkg='green')
        except Exception as e:
            self._update_status_bar('Error capturing image: {}'.format(e), 'red')
            print('Error capturing image:')
            print(f'_capture_image: {e}')
        finally:
            self._update_status_bar(delay_sec=5)
    
    @thread_assign
    def _show_stitched_images(self) -> None:
        """
        Shows the stitched images on the canvas
        """
        try:
            self._flg_video_pause.set()
            flg_done=threading.Event()
            self._btn_showImage.config(text='Show live feed',command=flg_done.set)
            
            meaImg = self._meaImgUnit
            flg_lowResImg = self._bool_lowResImg.get()
            stitched_img = meaImg.get_image_all_stitched(low_res=flg_lowResImg)[0]
            self._canvas_img.set_image(stitched_img)
            # self._update_status_bar('Stitched images shown',bkg='green')
            flg_done.wait()
        except Exception as e:
            print('Error showing stitched images:',e)
            # self._update_status_bar('Error showing stitched images: {}'.format(e), 'red')
        finally:
            self._flg_video_pause.clear()
            self._btn_showImage.config(text='Show image',command=self._show_stitched_images)
            # self._update_status_bar(delay_sec=5)
    
    @thread_assign
    def _show_camera_continuous(self,event_process:threading.Event,event_pause:threading.Event,coor_list_mm:list=[],
                                flg_alwaysAnnotate:bool=False):
        """
        Displays the video feed on the canvas
        
        Args:
            event_process (threading.Event): Event to process the video feed
            event_pause (threading.Event): Event to pause the video feed
            coor_list_mm (list): List of coordinates to be annotated on the canvas. Default is []
            flg_alwaysAnnotate (bool): Always annotate the coordinates. Default is False
        """
        assert isinstance(coor_list_mm, (type, list)), 'Coordinates must be a list'
        assert isinstance(event_process, threading.Event), 'Event process must be a threading.Event object'
        assert isinstance(event_pause, threading.Event), 'Event pause must be a threading.Event object'
        
        stage_coor = None
        event_process.set()
        while event_process.is_set():
            if event_pause.is_set():
                time.sleep(3/self._videoRefreshRate)
                continue
            time1 = time.time()
            
            img_ori = self._getter_cameraImage()
            self._canvas_img.set_image(img_ori)
            
            if len(coor_list_mm) > 0:
                try:
                    if stage_coor != self._getter_coordinate() or flg_alwaysAnnotate:
                        stage_coor = self._getter_coordinate()
                        low_res = self._bool_lowResImg.get()
                        list_coor_pixel = [self._meaImgUnit.convert_stg2imgpt(coor_stage_mm=stage_coor,coor_point_mm=coor,\
                            correct_rot=False,low_res=low_res) for coor in coor_list_mm]
                        self._canvas_img.annotate_canvas_multi(list_coor_pixel,scale=True,flg_removePreviousAnnotations=True)
                except Exception as e:
                    print('Error annotating the image:',e)
                    
            time2 = time.time()
            if time2-time1 < 1/self._videoRefreshRate:
                time.sleep(1/self._videoRefreshRate - (time2-time1))
    
    @thread_assign
    def _finetune_calibration(self):
        """
        Finetunes the calibration manually using the spinbox widgets
        """ 
        try:
            self._flg_video_pause.set()
            meaImg = self._meaImgUnit
            current_cal = self._getter_calibration()
            meaImg.set_calibration_ImageMeasurement_Calibration(current_cal)
            assert meaImg.check_calibration_exist(), 'Finetune calibration: Calibration does not exist'
            
        # > Parameters initialisation <
            # # Store the original values
            # scl_x_mmPerPixel,scl_y_mmPerPixel,laser_coor_x_mm,laser_coor_y_mm =\
            #     meaImg.get_calibration()
            
            # Reset the values, enable the spinboxes, and set the button to save the calibration
            self._frm_cal_adj.initialise_fineadjuster()
            
        # > Tracking initialisation <
            # Ask the user to pick some points to track
            stage_coor = self._getter_coordinate()
            img = self._getter_cameraImage()
            self._canvas_img.set_image(img)
            
            flg_recordClicks = threading.Event()
            self._frm_cal_adj.config_finetune_calibration_button(callback=flg_recordClicks.set,
                                                              text='Finish feature selection',enabled=True)
            self._update_status_bar('Click on the features to be tracked and click "Finish feature selection". Right-click to clear the current selections.',
                                    bkg='yellow')
            list_coors_pixel = self._canvas_img.start_recordClicks()
            
            # Wait for the selection to finish and allow the user to finetune the calibration
            flg_recordClicks.wait()
            list_coors_mm = [meaImg.convert_imgpt2stg(stage_coor,coor,False,low_res=self._bool_lowResImg.get()) for coor in list_coors_pixel]
            self._canvas_img.stop_recordClicks()
            self._update_status_bar('Finetune the calibration using the spinboxes and move the stage around to monitor the effect',bkg='yellow')
            
        # > Calibration finetuning by video feed <
            # Enable the spinboxes and start the video feed
            self._frm_cal_adj.enable_finetuneCalibration_widgets(callback=self._frm_cal_adj.apply_temp_fineadjustment,readonly=True)
            
            flg_video_on = threading.Event()
            flg_video_pause = threading.Event()
            thread_video:threading.Thread = \
                self._show_camera_continuous(flg_video_on,flg_video_pause,list_coors_mm,flg_alwaysAnnotate=True)
            
            self._frm_cal_adj.config_finetune_calibration_button(callback=flg_video_on.clear,text='End finetune calibration')
            thread_video.join()
            self._frm_cal_adj.finalise_fineadjustment()
            
            self._update_status_bar('Calibration finetuning finished: Please save the calibration file manually if required',bkg='green')
        
        except Exception as e: messagebox.showerror('Error finetuning calibration',str(e))
        finally:
            self._flg_video_pause.clear()
            self._update_status_bar(delay_sec=5); self._frm_cal_adj.config_finetune_calibration_button(callback=self._finetune_calibration)
    
    
    @thread_assign
    def _perform_calibration(self):
        """
        Perform the calibration to:
        - Calculate the mm/pixel ratio
        - Measure the laser coordinate offset of the image coordinate from the stage coordinate
        """ 
        try:
            self._flg_video_pause.set()
            
            event_videoFeed_process = threading.Event()
            event_videoFeed_pause = threading.Event()
            event_operationDone = threading.Event() # Set: indicate that the operation is done
            list_tracking_coors = []
            thread_video:threading.Thread = self._show_camera_continuous(
                event_videoFeed_process,event_videoFeed_pause,list_tracking_coors)
            
            button_texts = (
                '1. Capture the first state',
                '2. Complete laser selection',
                '3. Complete the first selections',
                '4. Capture the second state',
                '5. Complete the second selection',
                '6. Capture the third state',
                '7. Complete the third selection',
                '8. Complete calibration'
            )
            lines = (
                f'1. Wait for the stage to stage coordinates to stabilise and click "{button_texts[0]}"',
                f'2. Click the center of the laser spot and click "{button_texts[1]}"',
                f'3. Click on some features to be tracked and click "{button_texts[2]}"',
                f'4. Move the stage HORIZONTALLY, ensuring that the features are still visible, and click "{button_texts[3]}"',
                f'5. Click on the features in the same order and click "{button_texts[4]}"',
                f'6. Move the stage VERTICALLY, ensuring that the features are still visible, and click "{button_texts[5]}"',
                f'7. Click on the features in the same order and click "{button_texts[6]}"',
                f'8. Move the stage around, confirm that the features are tracked correctly, and click "{button_texts[7]}"'
            )
            
            if self._showHints:
                message = "\n".join(lines)  
                messagebox.showinfo('Calibration',message)
        
            def capture_state(message:str,button_text:str) -> tuple[float,float]:
                event_operationDone.clear()
                self._frm_cal_adj.config_calibrate_button(callback=event_operationDone.set,text=button_text)
                self._update_status_bar(message,bkg='yellow')
                
                event_operationDone.wait()
                event_videoFeed_pause.set()
                img_ori = self._getter_cameraImage()
                self._canvas_img.set_image(img_ori)
                stage_coor = self._getter_coordinate()
                
                return stage_coor

            def feature_selection(message:str,button_text:str,limit1:bool=False) -> list[tuple[float,float]]:
                event_operationDone.clear()
                self._frm_cal_adj.config_calibrate_button(callback=event_operationDone.set,text=button_text)
                self._update_status_bar(message,bkg='yellow')
                list_coors = self._canvas_img.start_recordClicks()
                
                event_operationDone.wait()
                list_ret = list_coors.copy()
                self._canvas_img.stop_recordClicks()
                if len(list_ret) == 0:
                    raise ValueError('At least one feature must be selected')
                if limit1 and len(list_ret) != 1:
                    raise ValueError('Only laser spot must be selected')
                
                return list_ret
            
        # > 1. Capture initial state <
            v1s = capture_state(lines[0],button_texts[0])
            v1s = np.array(v1s[:2])
            v1s_track = v1s.copy()
            
        # > 2. Select the laser spot <
            vlc = feature_selection(lines[1],button_texts[1],True)[-1]
            vlc = np.array(vlc)
            
        # > 3. Select the first tracking features <
            list_coor_pixel = feature_selection(lines[2],button_texts[2])
            list_coor_pixel_v1 = list_coor_pixel.copy()
            v1c = np.mean(list_coor_pixel,axis=0)
            
        # > 4. Capture second state <
            v2s = capture_state(lines[3],button_texts[3])
            v2s = np.array(v2s[:2])
            y_diff = v2s[1] - v1s[1]
            if not y_diff < 10e-3: raise ValueError('The stage must be moved horizontally') # 10e-3 [mm] is the threshold
            # if not np.allclose(v1s[1],v2s[1]): raise ValueError('The stage must be moved horizontally')
            
        # > 5. Select the tracking features <
            num_features = len(list_coor_pixel)
            list_coor_pixel = feature_selection(lines[4],button_texts[4])
            v2c = np.mean(list_coor_pixel,axis=0)
            if len(list_coor_pixel) != num_features: raise ValueError('The number of selected features must be the same')
            
        # > 6. Capture third state <
            v3s = capture_state(lines[5],button_texts[5])
            v3s = np.array(v3s[:2])
            x_diff = v3s[0] - v2s[0]
            if not x_diff < 10e-3: raise ValueError('The stage must be moved vertically') # 10e-3 [mm] is the threshold
            # if not np.allclose(v2s[0],v3s[0]): raise ValueError('The stage must be moved vertically')
        
        # > 7. Select the tracking features <
            list_coor_pixel = feature_selection(lines[6],button_texts[6])
            v3c = np.mean(list_coor_pixel,axis=0)
            v3c = np.array(v3c[:2])
            if len(list_coor_pixel) != num_features: raise ValueError('The number of selected features must be the same')
            
            # Set the calibration obj
            cal = ImgMea_Cal('calibration')
            cal.set_calibration_vector(v1s,v2s,v3s,v1c,v2c,v3c,vlc)
            
            # Save the calibration parameters (corrects for the image coordinate to the stage coordinate inversion)
            self._meaImgUnit = MeaImg_Unit(unit_name='Calibration',calibration=cal)
            
        # > 8. Show the live feature tracking and complete the calibration
            event_operationDone.clear()
            self._frm_cal_adj.config_calibrate_button(callback=event_operationDone.set,text=button_texts[7])
            self._update_status_bar(lines[7],bkg='yellow')
            # Add the initial tracked features to the list, adjusted for the real coordinates by 
            # adding the initial stage coordinates
            list_tracking_coors.extend([cal.convert_imgpt2stg(coor_img_pixel=np.array(coor_img),\
                coor_stage_mm=v1s_track) for coor_img in list_coor_pixel_v1])
            event_videoFeed_pause.clear()
            
            event_operationDone.wait()
            event_videoFeed_pause.set()
            self._canvas_img.stop_recordClicks()
            
        # > 7. Ask the user to save the calibration file
            flg_save = messagebox.askyesno('Save calibration','Do you want to save the calibration file?')
            if not flg_save: raise ValueError('Calibration not saved')
            
            MeaImg_Handler().save_calibration_json_from_ImgMea(self._meaImgUnit)
            messagebox.showinfo('Calibration saved','Calibration file saved successfully')
        
        except Exception as e: messagebox.showerror('Error performing calibration',e)
        finally:
            # Stop the video feed, reset the button state, and reset the status bar
            event_videoFeed_process.clear()
            thread_video.join()
            self._frm_cal_adj.config_calibrate_button(callback=self._perform_calibration)
            self._update_status_bar()
            self._flg_video_pause.clear()
            return
    
class sFrm_CalibrationAdjustment(tk.Frame):
    """
    Sub-frame for calibration adjustment to be used in the ROI_definition_controller
    """
    def __init__(self, main, processor:mpp.Pool, imgUnit_getter:Callable[[],MeaImg_Unit],
        getter_flipx:Callable[[],bool]=lambda:False, getter_flipy:Callable[[],bool]=lambda:False):
        """
        Args:
            main (tk.Frame): Main frame to put the sub-frame in
            imgUnit_getter (Callable): Callable to get the measurement image
        """
        super().__init__(main)
        self._processor = processor
        
    # >>> Image file handler <<<
        assert callable(imgUnit_getter), 'Measurement image getter must be a callable'
        self._getter_measurement_image = imgUnit_getter
        self._getter_flipx = getter_flipx
        self._getter_flipy = getter_flipy
        
        self._handler_img = MeaImg_Handler()
        self._lastDirPath = SaveParamsEnum.DEFAULT_SAVE_PATH.value
        
    # >> Frame setup <<
        self.config(padx=5,pady=5)
        self._frm_calAdjustAuto = tk.LabelFrame(self,text='Calibration')    # Sub-frame for auto calibration adjustment
        self._frm_calAdjustManual = tk.LabelFrame(self,text='Fine-tune calibration')  # Sub-frame for manual calibration adjustment

    # >> Calibration <<
    # Auto calibration process related
        # Calibration objects
        self._cal_ori:ImgMea_Cal = None
        self._cal_temp:ImgMea_Cal = None
        self._cal_final:ImgMea_Cal = None
    
        # Calibration parameters
        self._cal_sclx = tk.DoubleVar(value=0)
        self._cal_scly = tk.DoubleVar(value=0)
        self._cal_offsetx = tk.DoubleVar(value=0)
        self._cal_offsety = tk.DoubleVar(value=0)
        self._cal_rot_deg = tk.DoubleVar(value=0)
        
        self._frm_calAdjustAuto.grid(row=0, column=0,sticky='ew',pady=(0,5))
        self._frm_calAdjustManual.grid(row=1, column=0,sticky='ew',pady=(0,5))
        
        # Buttons for auto calibration
        self._btn_calibrate = tk.Button(self._frm_calAdjustAuto, text='Calibrate')
        self._btn_loadCalibrationFile = tk.Button(self._frm_calAdjustAuto, text='Load calibration file', command=self._load_calibration_file)
        self._btn_saveCalibrationFile = tk.Button(self._frm_calAdjustAuto, text='Save calibration file', command=self._save_calibration_file)
        
        # Label to display the calibration filename
        self._lbl_calibration = tk.Label(self._frm_calAdjustAuto, text='Calibration source: None',anchor='w')
        
        # Pack the widgets
        self._btn_calibrate.grid(row=0, column=0,pady=10,sticky='ew')
        self._btn_loadCalibrationFile.grid(row=1, column=0,sticky='ew')
        self._btn_saveCalibrationFile.grid(row=2, column=0,sticky='ew')
        self._lbl_calibration.grid(row=3, column=0,pady=(0,5),sticky='ew')
    
    # Manual calibration process related
        # Widgets for manual calibration
        self._btn_cal_finetune = tk.Button(self._frm_calAdjustManual, text='Finetune calibration')
        self._lbl_cal_sclx = tk.Label(self._frm_calAdjustManual, text='Scale x [%]:',anchor='e')
        self._scrl_cal_sclx = tk.Spinbox(self._frm_calAdjustManual, from_=-100, to=100,
                                         increment=0.2, width=5,state='disabled',textvariable=self._cal_sclx)
        self._lbl_cal_scly = tk.Label(self._frm_calAdjustManual, text='Scale y [%]:',anchor='e')
        self._scrl_cal_scly = tk.Spinbox(self._frm_calAdjustManual, from_=-100, to=100,
                                         increment=0.2, width=5,state='disabled',textvariable=self._cal_scly)
        
        self._lbl_cal_offsetx = tk.Label(self._frm_calAdjustManual, text='Offset x [%]:',anchor='e')
        self._scrl_cal_offsetx = tk.Spinbox(self._frm_calAdjustManual, from_=-100, to=100,
                                            increment=0.2, width=5,state='disabled',textvariable=self._cal_offsetx)
        self._lbl_cal_offsety = tk.Label(self._frm_calAdjustManual, text='Offset y [%]:',anchor='e')
        self._scrl_cal_offsety = tk.Spinbox(self._frm_calAdjustManual, from_=-100, to=100,
                                            increment=0.2, width=5,state='disabled',textvariable=self._cal_offsety)
        
        self._lbl_rot_deg = tk.Label(self._frm_calAdjustManual, text='Rotation [deg]:',anchor='e')
        self._scrl_rot_deg = tk.Spinbox(self._frm_calAdjustManual, from_=-180, to=180,
                                         increment=0.1, width=5,state='disabled',textvariable=self._cal_rot_deg)
        
        # Pack the widgets
        self._lbl_cal_sclx.grid(row=0, column=0,padx=(2,0),sticky='ew')
        self._scrl_cal_sclx.grid(row=0, column=1,padx=2,sticky='ew')
        self._lbl_cal_scly.grid(row=1, column=0,padx=(2,0),sticky='ew')
        self._scrl_cal_scly.grid(row=1, column=1,padx=2,sticky='ew',pady=(0,5))
        
        self._lbl_cal_offsetx.grid(row=2, column=0,padx=(2,0),sticky='ew')
        self._scrl_cal_offsetx.grid(row=2, column=1,padx=2,sticky='ew')
        self._lbl_cal_offsety.grid(row=3, column=0,padx=(2,0),sticky='ew')
        self._scrl_cal_offsety.grid(row=3, column=1,padx=2,sticky='ew',pady=(0,5))
        
        self._lbl_rot_deg.grid(row=4, column=0,padx=(2,0),sticky='ew')
        self._scrl_rot_deg.grid(row=4, column=1,padx=2,sticky='ew',pady=(0,5))
        
        self._btn_cal_finetune.grid(row=5, column=0,columnspan=2,sticky='ew')
    
    def initialise_fineadjuster(self) -> None:
        """
        Initialises the calibration parameters in the measurement image using
        the calibration parameters stored in the image
        """
        self._cal_ori = deepcopy(self._getter_measurement_image().get_ImageMeasurement_Calibration())
        self._cal_temp = deepcopy(self._cal_ori)
        
        assert isinstance(self._cal_ori, ImgMea_Cal), 'Calibration object not initialised'
        assert self._cal_ori.check_calibration_set() == True, 'Calibration parameters not set'
        
    def get_final_calibration(self) -> ImgMea_Cal|None:
        """
        Returns the final calibration object
        
        Returns:
            ImageMeasurement_Calibration|None: Final calibration object or None if not initialised
        """
        return self._cal_final
        
    def finalise_fineadjustment(self,apply:bool=False) -> None:
        """
        Finalises the calibration parameters in the measurement image using
        the calibration parameters stored in the temporary calibration object
        
        Args:
            apply (bool): Apply the calibration parameters to the measurement image. Default is False
        """
        assert self._cal_temp is not None, 'Temporary calibration not initialised'
        
        if apply:
            meaImg = self._getter_measurement_image()
            meaImg.set_calibration_ImageMeasurement_Calibration(self._cal_temp)
        
        self._cal_final = deepcopy(self._cal_temp)
        self._cal_temp = None
        self._cal_ori = None
        
        self.reset_calibrationSpinbox_values()
        self._disable_finetuneCalibration_widgets()
    
    def apply_temp_fineadjustment(self) -> None:
        """
        Updates the calibration parameters in the measurement image using
        the calibration parameters in the spinbox widgets
        """
        assert self._cal_temp is not None and self._cal_ori is not None, 'Calibration parameters not initialised'
        
        img_cal = self._cal_ori
        sclx = img_cal.scale_x_pixelPerMm
        scly = img_cal.scale_y_pixelPerMm
        offsetx = img_cal.laser_coor_x_mm
        offsety = img_cal.laser_coor_y_mm
        rot_rad = img_cal.rotation_rad
        
        # Get the calibration parameters in percentage and degrees
        sclx_rel,scly_rel,offsetx_rel,offsety_rel,rotdeg_rel = self.get_calibration_params_percent()
        
        # Update the calibration parameters
        sclx += sclx_rel/100 * sclx
        scly += scly_rel/100 * scly
        offsetx += offsetx_rel/100 * offsetx
        offsety += offsety_rel/100 * offsety
        rot_rad += np.deg2rad(rotdeg_rel)
        
        # Setup a new calibration object
        id = img_cal.id + f'_finetuned_{get_timestamp_sec()}'
        self._cal_temp = ImgMea_Cal(id=id)
        self._cal_temp.set_calibration_params(
            scale_x_pixelPerMm=sclx,
            scale_y_pixelPerMm=scly,
            laser_coor_x_mm=offsetx,
            laser_coor_y_mm=offsety,
            rotation_rad=rot_rad,
            flip_y=img_cal.flip_y,
        )
        
        # Update the calibration parameters in the measurement image
        self._getter_measurement_image().set_calibration_ImageMeasurement_Calibration(self._cal_temp)
    
    def _disable_finetuneCalibration_widgets(self) -> None:
        """
        Disables the calibration widgets
        """
        widgets = get_all_widgets(self._frm_calAdjustManual)
        [widget.config(state='disabled') for widget in widgets if isinstance(widget,tk.Spinbox)]
    
    def enable_finetuneCalibration_widgets(self,callback:Callable|None=None,readonly:bool=True) -> None:
        """
        Configures the calibration widgets
        
        Args:
            callback (Callable): Callback function for the finetune calibration button. Default is None
            readonly (bool): Set the calibration widgets to read-only. Default is True
        
        Note:
            - If callback is None, the callback will default to changing the calibration parameters
                in the measurement image from the getter provided in the constructor
        """
        if readonly: state = 'readonly'
        else: state = 'normal'
        if callback is None: callback = self.apply_temp_fineadjustment
        widgets = get_all_widgets(self._frm_calAdjustManual)
        [widget.config(state=state,command=callback) for widget in widgets if isinstance(widget,tk.Spinbox)]
    
    def config_finetune_calibration_button(self,callback:Callable,text:str='Finetune calibration',enabled:bool=True) -> None:
        """
        Sets the text of the finetune calibration button
        
        Args:
            callback (Callable): Callback function for the finetune calibration button
            text (str): Text to be displayed on the finetune calibration button. Default is 'Finetune calibration'
            enabled (bool): Enable the finetune calibration button. Default is True
        """
        assert isinstance(text, str), 'Text must be a string'
        self._btn_cal_finetune.config(text=text,command=callback)
        if enabled: self._btn_cal_finetune.config(state='normal')
        else: self._btn_cal_finetune.config(state='disabled')
    
    def config_calibrate_button(self,callback:Callable,text:str='Calibrate',enabled:bool=True) -> None:
        """
        Sets the text of the calibrate button
        
        Args:
            callback (Callable): Callback function for the calibrate button
            text (str): Text to be displayed on the calibrate button. Default is 'Calibrate'
            enabled (bool): Enable the calibrate button. Default is True
        """
        assert isinstance(text, str), 'Text must be a string'
        self._btn_calibrate.config(text=text,command=callback)
        if enabled: self._btn_calibrate.config(state='normal')
        else: self._btn_calibrate.config(state='disabled')
    
    def get_calibration_params_percent(self) -> tuple[float,float,float,float,float]:
        """
        Returns the calibration parameters in percentage and in degrees
        
        Returns:
            tuple[float,float,float,float,float]: Calibration parameters in the order (scl_x,scl_y,offset_x,offset_y,rot_deg)
        """
        return self._cal_sclx.get(),self._cal_scly.get(),self._cal_offsetx.get(),self._cal_offsety.get(),self._cal_rot_deg.get()
    
    def reset_calibrationSpinbox_values(self) -> None:
        """Resets the calibration parameters"""
        self._cal_sclx.set(0)
        self._cal_scly.set(0)
        self._cal_offsetx.set(0)
        self._cal_offsety.set(0)
        self._cal_rot_deg.set(0)
        
    def _load_calibration_file(self):
        """
        Loads the calibration file
        """
        try:
            self._btn_loadCalibrationFile.config(state='disabled', text='Loading...')
            mea_img = self._getter_measurement_image()
            img_cal = self._handler_img.load_calibration_json()
            if img_cal is None: raise ValueError('No calibration file loaded')
            
            mea_img.set_calibration_ImageMeasurement_Calibration(img_cal)
            
            self._cal_filename = img_cal.id
            self._lbl_calibration.config(text='Objective: {}'.format(self._cal_filename))
        
        except Exception as e: print('_load_calibration_file >> Error loading objective file:',e)
        finally: self._btn_loadCalibrationFile.config(state='normal', text='Load objective file')
    
    @thread_assign
    def _save_calibration_file(self):
        """
        Saves the calibration file
        """
        try:
            self._btn_saveCalibrationFile.config(state='disabled', text='Saving...')
            mea_img = self._getter_measurement_image()
            result = self._processor.apply_async(func=self._handler_img.save_calibration_json_from_ImgMea, kwds={
                'measurement':mea_img})
            self._lastDirPath,self._cal_filename = result.get()
            self._lbl_calibration.config(text='Objective: {}'.format(self._cal_filename))
        
        except Exception as e: print('_save_calibration_file >> Error saving objective file:',e)
        finally: self._btn_saveCalibrationFile.config(state='normal', text='Save objective file')
    