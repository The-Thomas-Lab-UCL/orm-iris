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


# Import image processors
import multiprocessing.pool as mpp
from PIL import Image
    
# Import DataHubs
from iris.gui.dataHub_MeaImg import Wdg_DataHub_ImgCal

# Import measurements
from iris.data.measurement_image import MeaImg_Unit, MeaImg_Hub, MeaImg_Handler
from iris.data.calibration_objective import ImgMea_Cal
from iris.data.measurement_RamanMap import MeaRMap_Hub,MeaRMap_Unit,MeaRMap_Plotter,PlotterOptions,PlotterParams,PlotterExtraParamsBase
from iris.gui.submodules.heatmap_plotter_MeaRMap import XYLimits

# Import processors
from iris.gui.submodules.heatmap_plotter_MeaRMap import Wdg_MappingMeasurement_Plotter

# Import extensions
from iris.gui.image_calibration.objective_calibration import Wdg_Calibration_Finetuning

# Import enums
from iris.gui import AppPlotEnum

from iris.resources.heatmap_plotter_overlay_ui import Ui_heatmapPlotterOverlay

class HeatmapOverlay_Design(Ui_heatmapPlotterOverlay,qw.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)

class MappingPlotter_ImageOverlay(MeaRMap_Plotter):
    """
    A modified version of the raman_plot class to allow image overlay on the heatmap
    plot function
    """
    def __init__(self) -> None:
        super().__init__()
        
    def overlay_image(self, image: Image.Image, extent:tuple[float,float,float,float],
                      callback=None) -> None:
        """
        Overlay an image on the heatmap plot
        
        Args:
            ax (Axes): Axis object to plot the image
            image (Image.Image): Image object to overlay
            extent (tuple): Extent of the image in the plot (left,right,bottom,top) coordinates
        """
        assert isinstance(image,Image.Image), "Invalid image object."
        assert isinstance(extent,tuple) and len(extent)==4, "Invalid extent object."
        
        ax = self._ax
        
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
        
class ImageProcessor_Worker(QObject):
    """
    Worker class to process images in a separate thread
    """
    sig_finished = Signal()
    def __init__(self, plotter:MappingPlotter_ImageOverlay):
        super().__init__()
        self._plotter = plotter
        
    @Slot(MeaImg_Unit,bool)
    def overlay_stitched_image(self, imgUnit:MeaImg_Unit, low_res:bool) -> None:
        """
        Get the stitched image from the ImageUnit
        
        Args:
            imgUnit (MeaImg_Unit): Image unit to process
            low_res (bool): Whether to get low resolution image
        """
        try:
            img_stitched,img_stitched_limit_min,img_stitched_limit_max =\
                imgUnit.get_image_all_stitched(low_res=low_res)
                
            img_stitched_extent = (
                min(img_stitched_limit_min[0],img_stitched_limit_max[0]),
                max(img_stitched_limit_max[0],img_stitched_limit_min[0]),
                min(img_stitched_limit_min[1],img_stitched_limit_max[1]),
                max(img_stitched_limit_max[1],img_stitched_limit_min[1])
            )
            
            self._plotter.overlay_image(image=img_stitched,extent=img_stitched_extent)
            self.sig_finished.emit()
        except Exception as e:
            print('Error in get_stitched_image:', e)
            self.sig_finished.emit()
        
class Wdg_HeatmapOverlay(Wdg_MappingMeasurement_Plotter, qw.QWidget):
    """
    A modified version of the plot_mapping_measurements class to allow image overlay
    on the heatmap
    """
    
    sig_update_img_combobox = Signal()
    sig_update_plot_overlay = Signal()
    
    sig_overlay_stitched_image = Signal(MeaImg_Unit,bool)
    
    def __init__(
        self,
        parent:qw.QWidget,
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
        
        # >>> Main widget setup <<<
        self._widget_overlay = HeatmapOverlay_Design(parent)
        wdg_ovl = self._widget_overlay
        super().__init__(parent=parent, mappingHub=self._mappingHub, layout=wdg_ovl.lyt_holder_plotter)
        
        lyt = qw.QVBoxLayout()
        lyt.addWidget(self._widget_overlay)
        self.setLayout(lyt)
        
        # Parameters to control the plots
        self._alpha = 0.5
        
        # Plotter — must share the same fig/ax that the FigureCanvas was built from
        self._plotter = MappingPlotter_ImageOverlay()
        self._plotter._ax = self._ax   # self._ax / self._fig are set by super().__init__()
        self._plotter._fig = self._fig
        self._pending_overlay: tuple[MeaImg_Unit, bool] | None = None
        self._overlay_in_progress = False
        self._init_worker()

    # >>> Calibration fine-tuning widgets <<<
        self._frm_calAdjust = Wdg_Calibration_Finetuning(
            parent=self,
            processor=self._processor,
            imgUnit_getter=self._get_ImageUnit,
            )
        wdg_ovl.lyt_holder_finetuning.addWidget(self._frm_calAdjust)
        
        # Set the behaviour of the calibration fine-tuning widgets
        self._frm_calAdjust.config_calibrate_button(text='Disabled',enabled=False,callback=lambda:None)
        self._frm_calAdjust.config_finetune_calibration_button(text='Finetune calibration',callback=self._finetune_calibration)
        
    # >>> Control widgets <<<
        self._combo_ImageUnits = wdg_ovl.combo_imgUnit
        self._chk_lres = wdg_ovl.chk_lres
        self._chk_overlay = wdg_ovl.chk_overlay

        self._combo_ImageUnits.currentTextChanged.connect(self.plot_heatmap)
        self._chk_lres.stateChanged.connect(self.plot_heatmap)
        self._chk_overlay.stateChanged.connect(self.plot_heatmap)
        self._combo_plot_mappingUnitName.currentTextChanged.connect(self.plot_heatmap)
        self._combo_plot_SpectralPosition.currentTextChanged.connect(self.plot_heatmap)
        self._entry_plot_clim_min.editingFinished.connect(self.plot_heatmap)
        self._entry_plot_clim_max.editingFinished.connect(self.plot_heatmap)
        self._chk_auto_clim.stateChanged.connect(self.plot_heatmap)
        self._entry_plot_xlim_max.editingFinished.connect(self.plot_heatmap)
        self._entry_plot_xlim_min.editingFinished.connect(self.plot_heatmap)
        self._entry_plot_ylim_max.editingFinished.connect(self.plot_heatmap)
        self._entry_plot_ylim_min.editingFinished.connect(self.plot_heatmap)
        
    # >>> Signal connections <<<
        self._getter_imghub().add_observer(self.sig_update_img_combobox.emit)
        self.sig_update_img_combobox.connect(self._update_img_combobox)
        self.sig_update_plot_overlay.connect(self.plot_heatmap)
        
    # >>> Initialise the widgets <<<
        self._initialise_widgets()
        
    def _initialise_widgets(self):
        """
        Initialise the widgets
        """
        self.sig_update_img_combobox.emit()
        
    def _init_worker(self):
        """
        Initialise the worker thread and object
        """
        self._thread_worker = QThread()
        self._worker = ImageProcessor_Worker(plotter=self._plotter)
        self._worker.moveToThread(self._thread_worker)
        self._thread_worker.start()
        
        # Connect signals
        self._worker.sig_finished.connect(self.handle_plot_overlay_finished)
        self.sig_overlay_stitched_image.connect(self._worker.overlay_stitched_image)
        
    @Slot()
    def _update_img_combobox(self):
        """
        Initialises the ImageMeasurementUnit selection combo box
        """
        # Disable the combo box while updating
        self._combo_ImageUnits.setEnabled(False)
        self._combo_ImageUnits.blockSignals(True)
        
        # Get the list of image units from the image measurement hub
        imghub = self._getter_imghub()
        if not isinstance(imghub,MeaImg_Hub): print('_initialise_img_combobox: Invalid image measurement hub object.'); return
        list_imgUnit_ids = imghub.get_list_ImageUnit_ids()
        dict_IDToName = imghub.get_dict_IDtoName()
        list_imgUnits_name = [dict_IDToName[ID] for ID in list_imgUnit_ids]
        
        # Update the combo box items while retaining the current selection if possible
        current_name = self._combo_ImageUnits.currentText()
        self._combo_ImageUnits.clear()
        self._combo_ImageUnits.addItems(list_imgUnits_name)
        if current_name in list_imgUnits_name:
            self._combo_ImageUnits.setCurrentText(current_name)
        
        # Re-enable the combo box
        self._combo_ImageUnits.blockSignals(False)
        self._combo_ImageUnits.setEnabled(True)
        
    def _finetune_calibration(self) -> None:
        """
        Grabs the calibration fine-tuning data and updates the image measurement object
        """
        meaImg = self._get_ImageUnit()
        if not isinstance(meaImg,MeaImg_Unit): return
        
        def apply_finetune_calibration():
            """Apply the calibration fine-tuning data"""
            self._frm_calAdjust.apply_temp_fineadjustment()
            self.sig_update_plot_overlay.emit()
            
        self._frm_calAdjust.config_calibrate_button(text='Reset calibration',enabled=True,callback=
                                                    self._frm_calAdjust.reset_calibrationSpinbox_values)
        self._frm_calAdjust.config_finetune_calibration_button(text='Finish finetuning',callback=self.handle_finetuning_finished)
        self._frm_calAdjust.initialise_fineadjuster()
        self._frm_calAdjust.enable_finetuneCalibration_widgets(callback=apply_finetune_calibration)
        
    @Slot()
    def handle_finetuning_finished(self) -> None:
        # Ask the user to apply the calibration changes
        flg_apply = qw.QMessageBox.question(self, 'Apply calibration', 'Apply the calibration changes?',
            qw.QMessageBox.Yes | qw.QMessageBox.No) == qw.QMessageBox.Yes # pyright: ignore[reportAttributeAccessIssue] ; QMessageBox.Yes exists
        
        if not flg_apply: qw.QMessageBox.information(self, 'Calibration changes','Calibration changes are not applied.')
        self._frm_calAdjust.finalise_fineadjustment(apply=flg_apply)
        
        # Apply the calibration changes
        flg_save = qw.QMessageBox.question(self, 'Save calibration', 'Save the calibration changes to the local disk?',
            qw.QMessageBox.Yes | qw.QMessageBox.No) == qw.QMessageBox.Yes # pyright: ignore[reportAttributeAccessIssue] ; QMessageBox.Yes exists
        if not flg_save: qw.QMessageBox.information(self, 'Calibration changes','Calibration changes are not saved.')
        else:
            new_cal = self._frm_calAdjust.get_last_calibration()
            if not isinstance(new_cal,ImgMea_Cal):
                qw.QMessageBox.critical(self, 'Save calibration','Failed to get the new calibration object.')
                return
            new_id = qw.QInputDialog.getText(self, 'Save calibration','Enter new calibration ID:', text=new_cal.id)[0]
            if not isinstance(new_id,str) or new_id == '':
                qw.QMessageBox.warning(self, 'Save calibration','Invalid calibration ID.')
                return
            
            new_cal.id = new_id
            MeaImg_Handler().save_calibration_json(new_cal)
            
    def reset_finetune_calibration_button(self) -> None:
        """
        Reset the calibration fine-tuning button to its default state
        """
        self._frm_calAdjust.config_finetune_calibration_button(callback=self._finetune_calibration)
        
    def _get_ImageUnit(self) -> MeaImg_Unit|None:
        """
        Get the ImageMeasurement_Unit object from the combo box selection
        """
        hub = self._getter_imghub()
        if not hub.check_measurement_exist(): return None
        
        imgUnit_name = self._combo_ImageUnits.currentText()
        dict_nameToID = hub.get_dict_nameToID()

        if not imgUnit_name in dict_nameToID: return None
        imgUnit_id = dict_nameToID[imgUnit_name]
        
        return hub.get_ImageMeasurementUnit(unit_id=imgUnit_id)
        
    @Slot()
    def plot_heatmap(self) -> None:
        """
        Plot the heatmap with the image overlay.
        """
        def correct_MappingMeasurementCoordinates(mapping_unit:MeaRMap_Unit,
                measurement_img:MeaImg_Unit) -> MeaRMap_Unit:
            """Correct the mapping measurement coordinates to match the image measurement
            coordinates."""
            label_x,label_y,_,_,_ = mapping_unit.get_labels()
            dict_measurement = mapping_unit.get_dict_measurements(copy=False)

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

        if self._isplotting: return

        mapping_hub = self._mappingHub
        img_unit = self._get_ImageUnit()

        if not isinstance(mapping_hub,MeaRMap_Hub): return
        if not isinstance(img_unit,MeaImg_Unit): return

        try:
            flg_lowResImg = self._chk_lres.isChecked()
        except Exception as e:
            print('plot_heatmap:\n',e)
            return

        mappingUnit_name = self._combo_plot_mappingUnitName.currentText()
        dict_nameToID = mapping_hub.get_dict_nameToID()
        if not mappingUnit_name in dict_nameToID: return
        mappingUnit_id = dict_nameToID[mappingUnit_name]
        wavelength = self.get_current_wavelength()
        if wavelength is None: return

        mapping_unit_corr = mapping_hub.copy_mapping_unit(mappingUnit_id,mappingUnit_name+'_LaserCoorCorrected',appendToHub=False)
        mapping_unit_corr = correct_MappingMeasurementCoordinates(
            mapping_unit=mapping_unit_corr,
            measurement_img=img_unit
        )

        try: clim_min = float(self._entry_plot_clim_min.text())
        except: clim_min = None
        try: clim_max = float(self._entry_plot_clim_max.text())
        except: clim_max = None
        clim = (clim_min,clim_max)
        if self._chk_auto_clim.isChecked(): clim = (None,None)

        self._isplotting = True
        self._pending_overlay = (img_unit, flg_lowResImg) if self._chk_overlay.isChecked() else None

        options = self._get_plotter_option()
        params = PlotterParams(mapping_unit=mapping_unit_corr, wavelength=wavelength, clim=clim)
        params_extra = self._get_plotter_extra_params()
        limits_xy = self._get_plot_xylim()

        self._sig_udpate_plot.emit(options, params, params_extra, limits_xy)

    @Slot()
    def on_plotter_worker_plotready(self) -> None:
        """After the heatmap is drawn, start the image overlay in the worker thread."""
        if self._pending_overlay is not None:
            img_unit, low_res = self._pending_overlay
            self._pending_overlay = None
            self._overlay_in_progress = True
            self.sig_overlay_stitched_image.emit(img_unit, low_res)
        else:
            self._canvas_widget.draw_idle()
            self._isplotting = False

    @Slot()
    def on_plotter_worker_finished(self) -> None:
        """Reset _isplotting if the overlay worker was never started.

        The base worker emits sig_finished_plotting without sig_plotready when it
        takes its early-return error path (invalid mapping unit). In that case
        on_plotter_worker_plotready is never called, so _isplotting would stay True
        forever. Resetting here when no overlay is in progress covers both the
        error path and the no-overlay success path (already False, so harmless).
        """
        if not self._overlay_in_progress:
            self._pending_overlay = None
            self._isplotting = False

    @Slot()
    def handle_plot_overlay_finished(self) -> None:
        """Handle the plot overlay finished signal."""
        self._overlay_in_progress = False
        self._canvas_widget.draw_idle()
        self._isplotting = False


def test_heatmap_overlay():
    """
    Test the Wdg_HeatmapOverlay widget with dummy Raman map and image data.

    Both the Raman map and image measurements use random coordinates in [0, 1] mm,
    so they will naturally overlap. The image calibration applies a small scale
    (~19-24 px/mm), rotation (~0.02 rad) and laser offset (~0.03 mm), which keeps
    the transformed coordinates in a similar range.

    Run directly:
        python -m iris.gui.image_calibration.plotter_heatmap_overlay
    """
    import sys
    import multiprocessing.pool as mpp
    from iris.data.calibration_objective import ImgMea_Cal_Hub

    # --- Data hubs ---
    mappinghub = MeaRMap_Hub()
    imghub = MeaImg_Hub()

    # --- Qt application and main window ---
    app = qw.QApplication(sys.argv)
    window = qw.QMainWindow()
    window.setWindowTitle('Heatmap Overlay Test')
    window.show()

    main_wdg = qw.QWidget()
    window.setCentralWidget(main_wdg)
    lyt = qw.QHBoxLayout(main_wdg)

    # --- Processor (used by calibration fine-tuning sub-widget) ---
    processor = mpp.Pool(processes=1)

    # --- Image calibration data hub ---
    cal_hub = ImgMea_Cal_Hub()
    dataHub_imgcal = Wdg_DataHub_ImgCal(main=window, getter_ImageCalHub=lambda: cal_hub)

    # --- Overlay plotter widget ---
    wdg_overlay = Wdg_HeatmapOverlay(
        parent=main_wdg,
        processor=processor,
        mappingHub=mappinghub,
        imghub_getter=lambda: imghub,
        dataHub_imgcal=dataHub_imgcal,
    )
    lyt.addWidget(wdg_overlay)
    lyt.addWidget(dataHub_imgcal)

    # --- Generate dummy data after the event loop is runnikng ---
    # Both hubs use random coords in [0, 1] mm — they will overlap on the plot.
    # The image unit's calibration (generate_dummy_params) applies scale ~19-24 px/mm
    # and laser offset ~0.03 mm, keeping transformed coords in the same range.
    def generate_data():
        mappinghub.test_generate_dummy(3)
        imghub.test_generate_dummy()

    from PySide6.QtCore import QTimer
    QTimer.singleShot(500, generate_data)

    sys.exit(app.exec())


if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
    test_heatmap_overlay()