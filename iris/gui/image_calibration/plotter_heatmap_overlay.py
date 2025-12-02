import os
import sys
from typing import Callable

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

import PySide6.QtWidgets as qw
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QMouseEvent, QPixmap, QPen, QColor, QFont, QPainter
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer, QCoreApplication, QPointF, QSize, Qt


import matplotlib
from matplotlib.axes import Axes
matplotlib.use('Agg')   # Force matplotlib to use the backend to prevent memory leak

# Import general functions and global parameters
from iris.utils.general import *


# Import image processors
import multiprocessing.pool as mpp
from PIL import Image
    
# Import DataHubs
from iris.gui.dataHub_MeaImg import Wdg_DataHub_ImgCal

# Import measurements
from iris.data.measurement_image import MeaImg_Unit, MeaImg_Hub, MeaImg_Handler
from iris.data.calibration_objective import ImgMea_Cal
from iris.data.measurement_RamanMap import MeaRMap_Hub,MeaRMap_Unit,MeaRMap_Plotter

# Import processors
from iris.gui.submodules.heatmap_plotter_MeaRMap import Wdg_MappingMeasurement_Plotter

# Import extensions
from iris.gui.image_calibration.objective_calibration import Wdg_Calibration_Finetuning

# Import enums
from iris.gui import AppPlotEnum

class MappingPlotter_ImageOverlay(MeaRMap_Plotter):
    """
    A modified version of the raman_plot class to allow image overlay on the heatmap
    plot function
    """
    def __init__(self) -> None:
        super().__init__()
        
    def overlay_image(self, ax: Axes, image: Image.Image, extent:tuple[float,float,float,float],
                      callback=None) -> None:
        """
        Overlay an image on the heatmap plot
        
        Args:
            ax (Axes): Axis object to plot the image
            image (Image.Image): Image object to overlay
            extent (tuple): Extent of the image in the plot (left,right,bottom,top) coordinates
        """
        assert isinstance(image,Image.Image), "Invalid image object."
        assert isinstance(ax,Axes), "Invalid axis object."
        assert isinstance(extent,tuple) and len(extent)==4, "Invalid extent object."
        
        # Get current min and max values
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        
        x_min_all = min(x_min, min(extent[0], extent[1]))
        y_min_all = min(y_min, min(extent[2], extent[3]))
        x_max_all = max(x_max, max(extent[0], extent[1]))
        y_max_all = max(y_max, max(extent[2], extent[3]))
        
        ax.imshow(image, extent=extent, interpolation='lanczos')
        
        ax.set_xlim(x_min_all, x_max_all)
        ax.set_ylim(y_min_all, y_max_all)
        ax.set_aspect(AppPlotEnum.PLT_ASPECT.value)
        
        # Callback function
        if callback is not None: callback()
        
class Frm_HeatmapOverlay(Wdg_MappingMeasurement_Plotter):
    """
    A modified version of the plot_mapping_measurements class to allow image overlay
    on the heatmap
    """
    def __init__(
        self,
        master,
        processor:mpp.Pool,
        mappingHub:MeaRMap_Hub,
        imghub_getter:Callable[[],MeaImg_Hub],
        dataHub_imgcal:Wdg_DataHub_ImgCal,
        figsize_pxl:tuple=(440,400)):
        """
        Args:
            master (tk.Frame): Master frame to put the sub-frames in
            processor (multiprocessing.pool.Pool): Processor to handle the data
            mappingHub (MappingMeasurement_Hub): Mapping measurement hub object
            imghub_getter (Callable): Callable to get the ImageMeasurement_Hub object
            dataHub_imgcal (Frm_DataHub_ImgCal): Image calibration data hub
            figsize_pxl (tuple): Figure size in pixels
            
        Note:
            The mea_img_getter is not implemented yet and will be used along with a DataHub_Image, a 
            class to handle the image measurement management.
        """
        self._processor = processor
        self._getter_imghub = imghub_getter
        self._mappingHub = mappingHub
        self._dataHub_imgcal = dataHub_imgcal
        
        # Generate subframes to separate the core widgets from the extra widgets
        frm_corePlotter = tk.Frame(master)
        frm_options = tk.Frame(master)
        frm_calAdjust = tk.Frame(master)
        frm_control = tk.Frame(master)
        
        frm_corePlotter.grid(row=0,column=0,sticky='nsew')
        frm_options.grid(row=1,column=0,sticky='nsew')
        frm_calAdjust.grid(row=0,column=1,rowspan=2,sticky='nsew')
        frm_control.grid(row=2,column=0,columnspan=2,sticky='nsew')
        
        super().__init__(
            parent=frm_corePlotter,
            mappingHub=self._mappingHub,
            )
        
        # # Parameters to store the measurements
        # self._mea_img:ImageMeasurement = None      # Image measurement object
        
        # Parameters to control the plots
        self._alpha = 0.5
        
        # Plotter
        self._plotter = MappingPlotter_ImageOverlay()
        
    # >>> Calibration fine-tuning widgets <<<
        self._frm_calAdjust = Wdg_Calibration_Finetuning(
            parent=frm_calAdjust,
            processor=self._processor,
            imgUnit_getter=self._get_ImageUnit
            )
        self._frm_calAdjust.grid(row=0,column=0,sticky='nsew')
        
        # Set the behaviour of the calibration fine-tuning widgets
        self._frm_calAdjust.config_calibrate_button(text='Disabled',enabled=False,callback=None)
        self._frm_calAdjust.config_finetune_calibration_button(text='Finetune calibration',callback=self._finetune_calibration)
        
    # >>> Control widgets <<<
        self._combo_listvalues = []
        self._combo_ImageUnits = ttk.Combobox(frm_control,state='disabled',values=self._combo_listvalues)
        self._btn_plotHeatmapOverlay = tk.Button(frm_control,text='Plot heatmap overlay',command=self._btncommand_plot_heatmap)
        self._bool_lowResImg = tk.BooleanVar(value=True)
        chk_show_lowResImg = tk.Checkbutton(frm_control,text='Show low resolution image (faster processing)',variable=self._bool_lowResImg)
        
        self._combo_ImageUnits.grid(row=0,column=0,sticky='ew')
        self._btn_plotHeatmapOverlay.grid(row=1,column=0,sticky='nsew')
        chk_show_lowResImg.grid(row=2,column=0,sticky='nsw')
        
        # Bind a combo box selection to the plot heatmap function
        self._combo_ImageUnits.bind('<<ComboboxSelected>>',lambda event: self._btncommand_plot_heatmap())
        
        frm_control.grid_rowconfigure(0,weight=1)
        frm_control.grid_rowconfigure(1,weight=1)
        frm_control.grid_columnconfigure(0,weight=1)
        
    # >>> Reconfigure reset button <<<
        self._btn_restart_threads.config(command=self._reinitialise_auto_plot)
        
    @thread_assign
    def _reinitialise_auto_plot(self) -> threading.Thread: # pyright: ignore[reportReturnType]
        thread = super()._reinitialise_auto_plot()
        thread.join()
        
        self._reset_img_combobox()
        self._initialise_img_combobox()
        
    def _reset_img_combobox(self):
        """
        Resets the ImageMeasurementUnit combo box
        """
        self._combo_ImageUnits.config(state='disabled')
        self._combo_ImageUnits['values'] = []
        self._combo_listvalues = []
                
    def _initialise_img_combobox(self):
        """
        Initialises the ImageMeasurementUnit selection combo box
        """
        imghub = self._getter_imghub()
        if not isinstance(imghub,MeaImg_Hub): print('_initialise_img_combobox: Invalid image measurement hub object.'); return
        
        list_imgUnit_ids = imghub.get_list_ImageUnit_ids()
        dict_IDToName = imghub.get_dict_IDtoName()
        list_imgUnits_name = [dict_IDToName[ID] for ID in list_imgUnit_ids]
        
        # Only updates if the list has changed
        if list_imgUnits_name == self._combo_listvalues: return
        self._combo_listvalues = list_imgUnits_name
        
        # Set the combo box values
        self._combo_ImageUnits['values'] = list_imgUnits_name
        if len(list_imgUnits_name) > 0: self._combo_ImageUnits.current(0)
        
        self._combo_ImageUnits.config(state='readonly')
        
    @thread_assign
    def _finetune_calibration(self) -> None:
        """
        Grabs the calibration fine-tuning data and updates the image measurement object
        """
        try:
            meaImg = self._get_ImageUnit()
            if not isinstance(meaImg,MeaImg_Unit): return
            
            flg_trigger_heatmapPlot = threading.Event()
            
            def apply_finetune_calibration():
                """Apply the calibration fine-tuning data"""
                self._frm_calAdjust.apply_temp_fineadjustment()
                flg_trigger_heatmapPlot.set()
                
            flg_finetune_done = threading.Event()
            self._frm_calAdjust.config_calibrate_button(text='Reset calibration',enabled=True,callback=
                                                        self._frm_calAdjust.reset_calibrationSpinbox_values)
            self._frm_calAdjust.config_finetune_calibration_button(text='Finish finetuning',callback=flg_finetune_done.set)
            self._frm_calAdjust.initialise_fineadjuster()
            self._frm_calAdjust.enable_finetuneCalibration_widgets(callback=apply_finetune_calibration)
            
            def auto_plot_heatmap(flg_done:threading.Event,trigger:threading.Event) -> None:
                """Automatically plot the heatmap"""
                while not flg_done.is_set():
                    trigger.wait()
                    trigger.clear()
                    self.plot_heatmap()
                    
            thd_autoPlot = threading.Thread(target=auto_plot_heatmap,args=(flg_finetune_done,flg_trigger_heatmapPlot))
            thd_autoPlot.start()
            
            flg_finetune_done.wait()
            
            # Ask the user to apply the calibration changes
            flg_apply = messagebox.askyesno('Apply calibration','Apply the calibration changes?')
            
            if not flg_apply: messagebox.showinfo('Calibration changes','Calibration changes are not applied.')
            self._frm_calAdjust.finalise_fineadjustment(apply=flg_apply)
            
            # Apply the calibration changes
            flg_save = messagebox.askyesno('Save calibration','Save the calibration changes to the local disk?')
            if not flg_save: messagebox.showinfo('Calibration changes','Calibration changes are not saved.')
            else:
                new_cal = self._frm_calAdjust.get_final_calibration()
                new_id = messagebox_request_input('Calibration ID','Enter the new calibration ID to save the calibration changes',default=new_cal.id)
                if not isinstance(new_id,str) or new_id == '': raise ValueError('Invalid calibration ID.')
                new_cal.id = new_id
                MeaImg_Handler().save_calibration_json(new_cal)
            
        except Exception as e:
            print('_finetune_calibration:\n',e)
            flg_retry = messagebox.askretrycancel('Error','An error occurred during the calibration fine-tuning process. Retry?')
            if flg_retry: self._finetune_calibration()
        finally:
            self._frm_calAdjust.config_finetune_calibration_button(text='Finetune calibration',callback=self._finetune_calibration)
            thd_autoPlot.join(timeout=5)
        
    @thread_assign
    def _btncommand_plot_heatmap(self) -> None:
        """
        A method specifically for the button command to plot the heatmap
        """
        try:
            self._btn_plotHeatmapOverlay.config(state=tk.DISABLED,text='Plotting...')
            self.plot_heatmap()
        except Exception as e: print('_btncommand_plot_heatmap:\n',e)
        finally:
            self._btn_plotHeatmapOverlay.config(state=tk.NORMAL,text='Plot heatmap overlay')
        
    def _get_ImageUnit(self) -> MeaImg_Unit|None:
        """
        Get the ImageMeasurement_Unit object from the combo box selection
        """
        hub = self._getter_imghub()
        if not hub.check_measurement_exist(): return None
        
        imgUnit_name = self._combo_ImageUnits.get()
        dict_nameToID = hub.get_dict_nameToID()

        if not imgUnit_name in dict_nameToID: return None
        imgUnit_id = dict_nameToID[imgUnit_name]
        
        return hub.get_ImageMeasurementUnit(imgUnit_id)
        
    def plot_heatmap(self,img_unit:MeaImg_Unit|None=None,autoplot:bool=True) -> None:
        """
        Plot the heatmap with the image overlay.
        
        Args:
            measurement_img (image_measurement): Image measurement object. If none, the getter function will be used
            autoplot (bool): If True, the plot will be displayed
        """
        def correct_MappingMeasurementCoordinates(mapping_unit:MeaRMap_Unit,
                measurement_img:MeaImg_Unit) -> MeaRMap_Unit:
            """Correct the mapping measurement coordinates to match the image measurement
            coordinates."""
            label_x,label_y,_,_,_ = mapping_unit.get_labels()
            dict_measurement = mapping_unit.get_dict_measurements()
            
            list_coorx:list = dict_measurement[label_x]
            list_coory:list = dict_measurement[label_y]
            
            list_coor = [(coorx,coory) for coorx,coory in zip(list_coorx,list_coory)]
            list_coor_corr = [measurement_img.convert_stg2mea(coor) for coor in list_coor]
            
            list_coorx_corr = [coor[0] for coor in list_coor_corr]
            list_coory_corr = [coor[1] for coor in list_coor_corr]
            
            # Update the values in the list, which are referenced by the mapping unit measurement dict
            list_coorx.clear()
            list_coorx.extend(list_coorx_corr)
            list_coory.clear()
            list_coory.extend(list_coory_corr)
            
            return mapping_unit
        
        mapping_hub = self._mappingHub
        if not isinstance(img_unit,MeaImg_Unit): img_unit = self._get_ImageUnit()
        
        if not isinstance(mapping_hub,MeaRMap_Hub): return
        if not isinstance(img_unit,MeaImg_Unit): return
        
        try:    # Get the stitched image, its limit, and rotation
            flg_lowResImg = self._bool_lowResImg.get()
            img_stitched,img_stitched_limit_min,img_stitched_limit_max = img_unit.get_image_all_stitched(low_res=flg_lowResImg)
            img_stitched_extent = (
                min(img_stitched_limit_min[0],img_stitched_limit_max[0]),
                max(img_stitched_limit_max[0],img_stitched_limit_min[0]),
                min(img_stitched_limit_min[1],img_stitched_limit_max[1]),
                max(img_stitched_limit_max[1],img_stitched_limit_min[1])
            )
        except Exception as e:
            print('plot_heatmap:\n',e)
            return None
        
        mappingUnit_name = self._combo_plot_mappingUnitName.get()
        dict_nameToID = mapping_hub.get_dict_nameToID()
        if not mappingUnit_name in dict_nameToID: return
        mappingUnit_id = dict_nameToID[mappingUnit_name]
        mappingUnit = mapping_hub.get_MappingUnit(mappingUnit_id)
        wavelength_idx = self._combo_plot_SpectralPosition.current()
        wavelength_list = mappingUnit.get_list_wavelengths()
        wavelength = wavelength_list[wavelength_idx]
        
        mapping_unit_corr = mapping_hub.copy_mapping_unit(mappingUnit_id,mappingUnit_name+'_LaserCoorCorrected',appendToHub=False)
        
        mapping_unit_corr = correct_MappingMeasurementCoordinates(
            mapping_unit=mapping_unit_corr,
            measurement_img=img_unit
        )
        
        _,laser_wavelength = mapping_unit_corr.get_laser_params()
        
        try: clim_min = float(self._entry_plot_clim_min.get())
        except: clim_min = None
        try: clim_max = float(self._entry_plot_clim_max.get())
        except: clim_max = None
        clim = (clim_min,clim_max)
        if self._bool_auto_clim.get(): clim = (None,None)
        
        try:
            title = mapping_unit_corr.get_unit_name()+'\n{:.0f}cm^-1 [{:.1f}nm]'.format(convert_wavelength_to_ramanshift(float(wavelength),laser_wavelength),
                float(wavelength))
            kwargs = self._get_plotter_kwargs()
            result = self._func_current_plotter(
                mapping_unit=mapping_unit_corr,
                wavelength=wavelength,
                clim=clim,
                title=title,
                fig=self._plt_fig,
                ax=self._plt_ax,
                clrbar=self._plt_cbar,
                **kwargs
            )
        except Exception as e:
            print('plot_heatmap:\n',e)
            return None
        
        self._plt_fig,self._plt_ax,self._plt_cbar = result
        self._plt_ax.set_alpha(self._alpha)
        
        try:
            self._plotter.overlay_image(self._plt_ax,image=img_stitched,extent=img_stitched_extent)
        except Exception as e:
            print('plot_heatmap:\n',e)
        
        self._set_plot_xylim()
        
        self.replot_heatmap()