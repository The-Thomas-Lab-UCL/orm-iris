""" 
An app to read the measurement files from the main_controller.py, plot, and analyse it.
"""
import sys

import PySide6.QtWidgets as qw

import multiprocessing.pool as mpp

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.gui.submodules.heatmap_plotter_MeaRMap import Wdg_MappingMeasurement_Plotter
from iris.gui.submodules.peakfinder_plotter_MeaRaman import Wdg_RamanMeasurement_Peakfinder_Plotter
from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping, Wdg_DataHub_Mapping_Plus, MeaRMap_Hub
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image, Wdg_DataHub_ImgCal
from iris.gui.image_calibration.plotter_heatmap_overlay import Wdg_HeatmapOverlay

from iris import *

from iris.resources.main_analyser_ui import Ui_main_analyser

class main_analyser(Ui_main_analyser,qw.QMainWindow):
    def __init__(self, processor:mpp.Pool, dataHub:Wdg_DataHub_Mapping|None=None,
                 dataHub_img:Wdg_DataHub_Image|None=None, dataHub_imgcal:Wdg_DataHub_ImgCal|None=None):
        """
        Initialises the IRIS analyser.
        
        Args:
            processor (mpp.Pool): The processor for the mapping measurements
            mapping_data (mapping_measurement_data): The mapping data to be fsded. Default is None.
            dataHub (Frm_DataHub): The datahub to grab the mappingHub from. Default is None.
            dataHub_img (Wdg_DataHub_Image): The datahub to grab the ImageHub from. Default is None.
            dataHub_imgcal (Wdg_DataHub_ImgCal): The image calibration datahub. Default is None.
        """
        super().__init__()
        self.setupUi(self)
        
        self._processor = processor
        
    # >>> Data hub plus setup <<<
        if isinstance(dataHub,Wdg_DataHub_Mapping):
            self._dataHub_local = Wdg_DataHub_Mapping(self,dataHub.get_MappingHub())
        else:
            self._dataHub_local = Wdg_DataHub_Mapping(self,MeaRMap_Hub())
        
        self._dataHubPlus = Wdg_DataHub_Mapping_Plus(self,self._dataHub_local)
        self.lyt_dataholder.addWidget(self._dataHub_local)
        self.lyt_dataholder.addWidget(self._dataHubPlus)
        
    # >>> Interactive heatmap plotter setup <<<
        self._heatmapPlotter = Wdg_MappingMeasurement_Plotter(self,self._dataHub_local.get_MappingHub())
        self.lyt_heatmap.addWidget(self._heatmapPlotter)
        
    # >>> Interactive spectra plotter setup <<<
        self._spectraPlotter = Wdg_RamanMeasurement_Peakfinder_Plotter(self)
        self.lyt_peakfinder.addWidget(self._spectraPlotter)
        
    # >>> Image visualiser setup <<<
        # Data hubs (sharing the same underlying hubs as the ones above/in the controller)
        if isinstance(dataHub_img,Wdg_DataHub_Image):
            self._dataHub_img_local = Wdg_DataHub_Image(self,getter_ImageHub=dataHub_img.get_ImageMeasurement_Hub)
        else:
            self._dataHub_img_local = Wdg_DataHub_Image(self)
        self._dataHub_img_local.update_tree()
        self._dataHub_imgcal = dataHub_imgcal if isinstance(dataHub_imgcal,Wdg_DataHub_ImgCal)\
            else Wdg_DataHub_ImgCal(self)
        self._dataHub_map_img = Wdg_DataHub_Mapping(self,self._dataHub_local.get_MappingHub())
        self.lyt_datahubImg.addWidget(self._dataHub_img_local)
        self.lyt_datahubMap.addWidget(self._dataHub_map_img)
        
        # Image/overlay plotter
        self._imgPlotter = Wdg_HeatmapOverlay(
            parent=self,
            processor=self._processor,
            mappingHub=self._dataHub_local.get_MappingHub(),
            imghub_getter=self._dataHub_img_local.get_ImageMeasurement_Hub,
            dataHub_imgcal=self._dataHub_imgcal,
        )
        self.lyt_plotter.addWidget(self._imgPlotter)
        
        # Visualisation mode (the radio buttons replace the plotter's own overlay checkbox)
        self._imgPlotter.set_overlay_checkbox_visible(False)
        self._imgPlotter.set_overlay_enabled(True)
        self._imgPlotter.set_image_only(self.rad_onlyImg.isChecked())
        self.rad_onlyImg.toggled.connect(self._imgPlotter.set_image_only)
        
    # # >>> Timestamp coordinate shift setup <<<
    #     self._frm_tsCoorShift = sFrm_xyCoorTimestampShift(
    #         parent=frm_tsCoorShift,
    #         dataHub=self._dataHub_local,
    #         callback=self._dataHub_local.update_tree
    #     )
    #     self._frm_tsCoorShift.grid(row=0,column=0,sticky='nsew')
        
        self._init_signals()
        
    def _init_signals(self):
        # Heatmap plot
        self._dataHub_local.sig_tree_selection_str.connect(self._heatmapPlotter.set_combobox_name)
        self._dataHub_local.sig_tree_selection.connect(self._heatmapPlotter.sig_request_update_plot.emit)
        self._heatmapPlotter.sig_mappingUnit_changed.connect(self._dataHub_local.set_selection_unitName)
        
        # 1D plot
        self._heatmapPlotter.sig_plotclicked_id.connect(self._dataHubPlus.set_selected_RamanMeasurement)
        self._dataHubPlus.sig_selection_changed_mea.connect(self._spectraPlotter.plot_spectra)
        
        # Image visualiser: mapping unit selection
        self._dataHub_map_img.sig_tree_selection_str.connect(self._imgPlotter.set_combobox_name)
        self._dataHub_map_img.sig_tree_selection.connect(self._imgPlotter.sig_request_update_plot.emit)
        self._imgPlotter.sig_mappingUnit_changed.connect(self._dataHub_map_img.set_selection_unitName)
        
        # Image visualiser: image unit selection
        self._dataHub_img_local.sig_tree_selection_str.connect(self._imgPlotter.set_imgUnit_combobox_name)
        self._imgPlotter.sig_imgUnit_changed.connect(self._dataHub_img_local.set_selection_unitName)
        

        
if __name__ == '__main__':
    app = qw.QApplication([])
    processor = mpp.Pool()
    analyser = main_analyser(processor)
    
    # analyser._dataHub_local.get_MappingHub().test_generate_dummy()
    
    analyser.show()
    sys.exit(app.exec())