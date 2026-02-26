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

from iris import *

from iris.resources.main_analyser_ui import Ui_main_analyser

class main_analyser(Ui_main_analyser,qw.QMainWindow):
    def __init__(self, processor:mpp.Pool, dataHub:Wdg_DataHub_Mapping|None=None):
        """
        Initialises the IRIS analyser.
        
        Args:
            processor (mpp.Pool): The processor for the mapping measurements
            mapping_data (mapping_measurement_data): The mapping data to be fsded. Default is None.
            dataHub (Frm_DataHub): The datahub to grab the mappingHub from. Default is None.
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
        

        
if __name__ == '__main__':
    app = qw.QApplication([])
    processor = mpp.Pool()
    analyser = main_analyser(processor)
    
    analyser._dataHub_local.get_MappingHub().test_generate_dummy()
    
    analyser.show()
    sys.exit(app.exec())