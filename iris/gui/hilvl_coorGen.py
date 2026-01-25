import sys
import os

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread, Qt

from glob import glob
from uuid import uuid1
from typing import Literal

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(SCRIPT_DIR))

from iris.gui.submodules.meaCoor_generator.rectangle_endToEnd import Wdg_Rect_StartEnd as Map1
from iris.gui.submodules.meaCoor_generator.rectangle_aroundCentre import Rect_AroundCentre as Map2
from iris.gui.submodules.meaCoor_generator.rectangle_video import Rect_Video as Map3
from iris.gui.submodules.meaCoor_generator.rectangle_image import Rect_Image as Map4
from iris.gui.submodules.meaCoor_generator.points_image import Points_Image as Map5
from iris.gui.submodules.meaCoor_generator.singlePoint_zScan import singlePoint_zScan as Map6
from iris.gui.submodules.meaCoor_generator.line_zScan import Wdg_ZScanMethod_linear as ZScan1

from iris.gui.submodules.meaCoor_modifier.every_z import EveryZ as MapMod1
from iris.gui.submodules.meaCoor_modifier.zInterpolate import ZInterpolate as MapMod2
from iris.gui.submodules.meaCoor_modifier.topology_visualiser import TopologyVisualiser as MapMod3
from iris.gui.submodules.meaCoor_modifier.translateXYZ import TranslateXYZ as MapMod4
from iris.gui.submodules.meaCoor_modifier.gridify import Gridify as MapMod5

from iris.utils.general import messagebox_request_input, get_all_widgets_from_layout
from iris.gui import AppRamanEnum

from iris.gui.motion_video import Wdg_MotionController
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image, Wdg_DataHub_ImgCal
from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping

from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.resources.dataHub_coor_ui import Ui_dataHub_coor
from iris.resources.hilvl_coorGen_ui import Ui_hilvl_coorGen
from iris.resources.hilvl_coorGen_coorMod_ui import Ui_coorMod

class Hilvl_CoorGen_UiDesign(qw.QWidget, Ui_hilvl_coorGen):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

class Coor_saveload_worker(QObject):
    
    sig_save_done = Signal() # Emitted when the mapping coordinates are saved.
    sig_load_done = Signal() # Emitted when the mapping coordinates are loaded.
    
    sig_save_error = Signal(str) # Emitted when there is an error in saving the mapping coordinates.
    sig_load_error = Signal(str) # Emitted when there is an error in loading the mapping coordinates.
    
    message_loaded_lastsession = "Previous unfinished mapping coordinates found and has been loaded"
    
    def __init__(self,mappingCoorHub:List_MeaCoor_Hub):
        """
        Initialises the treeview for the mapping coordinates.
        
        Args:
            mappingCoorHub (MappingCoordinatesHub): The hub for the mapping coordinates.
        """
        super().__init__()
        self._mappingCoorHub = mappingCoorHub
    
    @Slot(list)
    def load_MappingCoordinates(self,list_loadpath:list[str]):
        """
        Loads the mapping coordinates from a pickle file and adds them to the list of mapping coordinates.
        
        Args:
            list_loadpath (list[str]|None): The path to load the coordinates from. Defaults to None.
        
        Returns:
            MappingCoordinates: The loaded mapping coordinates.
        """
        for path in list_loadpath:
            try:
                mappingCoor = MeaCoor_mm(loadpath=path)
                self._mappingCoorHub.append(mappingCoor)
            except Exception as e: self.sig_load_error.emit(f"Failed to load mapping coordinates: {e}")
        return
    
    @Slot(list, str, str)
    def save_MappingCoordinates(self,list_coorNames:list[str],dirpath:str,type:Literal['pickle','csv']='pickle'):
        """
        Saves the selected mapping coordinates to a pickle file.
        
        Args:
            list_coorNames (list[str]): The list of mapping coordinate names to save.
            dirpath (str): The directory path to save the coordinates to.
            type (Literal['pickle','csv']): The type of file to save the coordinates to. Defaults to 'pickle'.
        """
        if type=='pickle': extension = '.pkl'
        elif type=='csv': extension = '.csv'
        
        # Save all selected mapping coordinates
        for unitname in list_coorNames:
            mappingCoor = self._mappingCoorHub.get_mappingCoor(unitname)
            if mappingCoor is None: continue
            filename = os.path.join(dirpath,mappingCoor.mappingUnit_name+extension)
            
            if not os.path.exists(dirpath): os.makedirs(dirpath) # Create directory if it does not exist
            
            while True:
                if os.path.exists(filename):
                    # Remove the extension and add a UUID to the filename
                    filename = os.path.splitext(filename)[0]
                    filename += '_'+str(uuid1())
                else: break
                
            if type == 'csv':
                mappingCoor.save_csv(filename)
            elif type == 'pickle':
                mappingCoor.save_pickle(filename)
        return


class DataHub_Coor_UiDesign(qw.QWidget, Ui_dataHub_coor):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        # lyt = qw.QVBoxLayout(self)
        # self.setLayout(lyt)

class Wdg_Treeview_MappingCoordinates(qw.QWidget):
    """
    A class to create a treeview for the mapping coordinates.
    """
    sig_load_mappingCoor = Signal(list) # Emitted to load the mapping coordinates from the local disk.
    sig_save_mappingCoor = Signal(list, str, str) # Emitted to save the mapping coordinates to the local disk.
    
    _sig_update_tree = Signal() # Emitted when the treeview needs to be updated.
    
    def __init__(self,parent:qw.QWidget,mappingCoorHub:List_MeaCoor_Hub):
        """
        Initialises the treeview for the mapping coordinates.
        
        Args:
            parent (tk.Tk | tk.Frame): The parent frame or window.
            mappingCoorHub (MappingCoordinatesHub): The hub for the mapping coordinates.
        """
        super().__init__(parent)
        self._mappingCoorHub = mappingCoorHub
        
        # > Top level frame setup <
        self._widget = DataHub_Coor_UiDesign(self)
        self._layout_main = qw.QHBoxLayout(self)
        self._layout_main.addWidget(self._widget)
        wdg = self._widget
        
        self._init_multiCoor_tree()
        
        # > Control widgets <
        self._btn_remove = wdg.btn_remove
        self._btn_rename = wdg.btn_rename
        self._btn_load = wdg.btn_load
        self._btn_save = wdg.btn_save
        
        self._btn_remove.clicked.connect(lambda: self._remove_selected_mapping_coordinate())
        self._btn_rename.clicked.connect(lambda: self.rename_MappingCoordinate())
        self._btn_load.clicked.connect(lambda: self._load_MappingCoordinates())
        self._btn_save.clicked.connect(lambda: self.save_MappingCoordinates(type='csv'))
        
        # > Run parameters setup <
        self._sig_update_tree.connect(self._update_multi_mapping_tree)
        self._mappingCoorHub.add_observer(self._sig_update_tree.emit)
        
        # > Worker and thread setup <
        self._worker = Coor_saveload_worker(self._mappingCoorHub)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        
        self.destroyed.connect(self._thread.quit)
        self.destroyed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        
        self._thread.start()
        
        self.sig_load_mappingCoor.connect(self._worker.load_MappingCoordinates)
        self.sig_save_mappingCoor.connect(self._worker.save_MappingCoordinates)
        
        self._worker.sig_save_error.connect(lambda msg: qw.QMessageBox.warning(self, 'Error', msg))
        self._worker.sig_load_error.connect(lambda msg: qw.QMessageBox.warning(self, 'Error', msg))
        
        self._worker.sig_save_done.connect(lambda: self._btn_save.setEnabled(True))
        self._worker.sig_load_done.connect(lambda: self._btn_load.setEnabled(True))
        
    def _init_multiCoor_tree(self):
        """
        Initialises the tree view for the multi-coordinate mapping
        """
        self._tree = self._widget.tree_coor
        
        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels(['Index','ROI name','Number of samplings'])
        
    def get_selected_mappingCoor(self, flg_message:bool=False) -> list[MeaCoor_mm]:
        """
        Gets the selected mapping coordinates from the tree view
        
        Args:
            message (bool): If True, a message box will be shown to notify the user of the selected units. Defaults to False.

        Returns:
            list[MappingCoordinates]: The list of selected mapping coordinates
        """
        list_sels = self._tree.selectedItems()
        list_names = [item.text(1) for item in list_sels]
        
        list_sel_mapCoor = self._mappingCoorHub.get_list_MappingCoordinates(list_names)
        
        if flg_message:
            if len(list_sel_mapCoor) == 0:
                qw.QMessageBox.information(self, 'No selection', 'No mapping coordinates have been selected.')
            list_show_names = [mc.mappingUnit_name for mc in list_sel_mapCoor]
            if len(list_sel_mapCoor) > 3:
                list_show_names = [mc.mappingUnit_name for mc in list_sel_mapCoor[:3]] + ['...']
            qw.QMessageBox.information(self, 'Selected mapping coordinates',
                                f'The following mapping coordinates have been selected:\n\n{list_show_names}')
        return list_sel_mapCoor
    
    def _load_MappingCoordinates(self):
        """
        Loads the mapping coordinates from a pickle file and adds them to the list of mapping coordinates.
        
        Args:
            list_loadpath (list[str]|None): The path to load the coordinates from. Defaults to None.
        
        Returns:
            MappingCoordinates: The loaded mapping coordinates.
        """ 
        self._btn_load.setEnabled(False)
        
        list_loadpath, _ = qw.QFileDialog.getOpenFileNames(
            self,'Select the mapping coordinates files to load',
            filter='Pickle files (*.pkl);;CSV files (*.csv)'
        )
        
        if len(list_loadpath) == 0: return None
        
        if not isinstance(list_loadpath, (list,tuple)):
            qw.QMessageBox.warning(self, 'Error',f"Expected list, got {type(list_loadpath)}")
            return
        if not all(isinstance(path, str) for path in list_loadpath):
            qw.QMessageBox.warning(self, 'Error',f"Expected list of str, got {type(list_loadpath)}")
            return
        if not all(os.path.exists(path) for path in list_loadpath):
            qw.QMessageBox.warning(self, 'Error',f"Some files do not exist")
            return
        
        self.sig_load_mappingCoor.emit(list_loadpath)
        return
    
    def save_MappingCoordinates(self,type:Literal['pickle','csv']='csv'):
        """
        Saves the selected mapping coordinates to a pickle file.
        
        Args:
            autosave (bool): If True, suppresses the message box and uses the temporary folder. Defaults to False.
            type (Literal['pickle','csv']): The type of file to save the coordinates to. Defaults to 'pickle'.
        """
        def reset():
            nonlocal self
        
        list_selection = self._tree.selectedItems()
        
        if len(list_selection) == 0:
            qw.QMessageBox.warning(self, 'Error','No mapping coordinates selected')
            return
        
        dirpath = qw.QFileDialog.getExistingDirectory(
            self,'Select the directory to save the mapping coordinates')
        if not os.path.exists(dirpath):
            qw.QMessageBox.warning(self, 'Error',f"Directory {dirpath} does not exist")
            reset()
            return
        
        # Save all selected mapping coordinates
        list_names = [item.text(1) for item in list_selection]
        self.sig_save_mappingCoor.emit(list_names,dirpath,type)
        qw.QMessageBox.information(self, 'Info','Mapping coordinates saved')
        return
    
    def rename_MappingCoordinate(self):
        """
        Renames the selected mapping coordinate in the list.
        """
        list_names = [item.text(1) for item in self._tree.selectedItems()]
        
        if len(list_names) == 0:
            qw.QMessageBox.information(self, 'No selection', 'No mapping coordinates have been selected.')
        elif len(list_names) > 1:
            qw.QMessageBox.information(self, 'Multiple selection', 'Please select only one mapping coordinate to rename at a time.')
            return
        
        init_name = list_names[0]
        while True:
            try:
                new_name,ok = qw.QInputDialog.getText(self, 'Rename mapping coordinate',
                    f'Enter the new name for the mapping coordinate for\n"{init_name}":',
                    text=init_name)
                if not ok: return
                self._mappingCoorHub.rename_mappingCoor(init_name, new_name)
                break
            except ValueError as e:
                qw.QMessageBox.warning(self, 'Error',f"Invalid unit name: {e}")
    
    def _remove_selected_mapping_coordinate(self):
        """
        Removes the selected mapping coordinate from the list
        """
        list_selection = self._tree.selectedItems()
        list_unitname = [item.text(1) for item in list_selection]
        
        for unitname in list_unitname:
            self._mappingCoorHub.remove_mappingCoor(unitname)
    
    @Slot()
    def _update_multi_mapping_tree(self):
        """
        Refreshes the tree view for the multi-coordinate mapping with the data stored in the dictionary
        """
        self._tree.clear()
        
        for i, mappingCoor in enumerate(self._mappingCoorHub):
            qw.QTreeWidgetItem(self._tree, [str(i+1), mappingCoor.mappingUnit_name, str(len(mappingCoor.mapping_coordinates))])
    
class Wdg_CoorModifier(Ui_coorMod, qw.QWidget):
    def __init__(
        self,
        parent:qw.QWidget,
        motion_controller:Wdg_MotionController,
        coor_Hub:List_MeaCoor_Hub):
        """
        Displays the GUI for the coordinate modifier methods.
        
        Args:
            master (tk.Tk | tk.Frame): The parent frame or window.
            motion_controller (Frm_MotionController): The motion controller to use.
            coor_Hub (MappingCoordinatesHub): The hub for the mapping coordinates.
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
        self._motion_controller = motion_controller
        self._coorHub = coor_Hub
        
        # > Options setup <
        self._dict_mapModMethods_kwargs = {
            'parent': self,
            'motion_controller': self._motion_controller,
            'mappingCoorHub': self._coorHub,
            'motion_controller': self._motion_controller,
        }
        self._dict_mapModMethods = {
            '1. Every Z': MapMod1,
            '2. Z Interpolate': MapMod2,
            '3. Topology visualiser': MapMod3,
            '4. Translate XYZ': MapMod4,
            '5. Gridify': MapMod5
        }   # Mapping methods, to be programmed manually

        self.combo_methods.addItems(list(self._dict_mapModMethods.keys()))
        self.combo_methods.currentTextChanged.connect(
            lambda text: self.show_chosen_mapModMethod(text))
        
        # > Initial map modifier method setup <
        self._current_mapModMethod = MapMod1(**self._dict_mapModMethods_kwargs)
        self.lyt_holder_modifiers.addWidget(self._current_mapModMethod)
        
    @Slot(str)
    def show_chosen_mapModMethod(self, method_name:str):
        """
        Shows the options for the selected mapping method
        
        Args:
            method_name (str): The name of the mapping method to show.
        """
        widgets = get_all_widgets_from_layout(self.lyt_holder_modifiers)
        
        for widget in widgets:
            widget.deleteLater()
        qw.QApplication.processEvents()
        
        self._current_map_method = self._dict_mapModMethods[method_name](**self._dict_mapModMethods_kwargs)
        self.lyt_holder_modifiers.addWidget(self._current_map_method)
    
class Wdg_Hilvl_CoorGenerator(qw.QWidget):
    """
    A class to generate coordinates for the mapping measurement and image tiling.
    """
    def __init__(self,
                 parent:qw.QWidget,
                 coorHub:List_MeaCoor_Hub,
                 motion_controller:Wdg_MotionController,
                 dataHub_map:Wdg_DataHub_Mapping,
                 dataHub_img:Wdg_DataHub_Image,
                 dataHub_imgcal:Wdg_DataHub_ImgCal,
                 ):
        """
        Initialises the coordinate generator frame.
        
        Args:
            parent (qw.QWidget): The parent widget.
            coorHub (List_MeaCoor_Hub): The hub for the mapping coordinates.
            motion_controller (Wdg_MotionController): The motion controller to use.
            dataHub_map (Wdg_DataHub_Mapping): The mapping data hub to use.
            dataHub_img (Wdg_DataHub_Image): The image measurement data hub to use.
            dataHub_imgcal (Wdg_DataHub_ImgCal): The image calibration data hub to use.
        """
    # >>> Initial setup <<<
        super().__init__(parent)
        self.master = parent
        self._coorHub = coorHub
        self._motion_controller = motion_controller
        self._dataHub_map = dataHub_map
        self._dataHub_img = dataHub_img
        self._dataHub_imgcal = dataHub_imgcal
        
    # >>> Main widget/layout setup <<<
        self._widget = Hilvl_CoorGen_UiDesign(self)
        self._layout_main = qw.QHBoxLayout(self)
        self._layout_main.addWidget(self._widget)
        wdg = self._widget
        
    # >>> Top level frame setup <<<
        self._wdg_tv_mapcoor = Wdg_Treeview_MappingCoordinates(
            wdg.wdg_coorHub_holder,self._coorHub)
        wdg.lyt_coorHub_holder.addWidget(self._wdg_tv_mapcoor)
        
        self._wdg_coorMod = Wdg_CoorModifier(
            parent=self,
            motion_controller=self._motion_controller,
            coor_Hub=self._coorHub,
        )
        wdg.lyt_coorMod_holder.addWidget(self._wdg_coorMod)
        
    # >>> Mapping coordinate method widgets<<<
        # > Dictionaries and parameters to set up the mapping methods <
        wdg.wdg_coorGen_holder.setLayout(qw.QVBoxLayout())
        self._dict_mappingmethods_kwargs = {
            'parent':wdg.wdg_coorGen_holder,
            'motion_controller':self._motion_controller,
            'dataHub_img':self._dataHub_img,
            'dataHub_imgCal':self._dataHub_imgcal,
            'getter_imgcal':self._dataHub_imgcal.get_selected_calibration,
        }
        self._dict_mappingmethods = {
            '1. Start/End': Map1,
            '2. Around center': Map2,
            '3. Video': Map3,
            '4. Image': Map4,
            '5. Image points': Map5,
            '6. Single point Z-scan': Map6,
            }   # Mapping methods, to be programmed manually
        self._current_map_method = Map1(**self._dict_mappingmethods_kwargs)
        wdg.lyt_coorGen_holder.addWidget(self._current_map_method)
        
        # > Widget setup <
        # Mapping method selection
        self._combo_mappingmethods = wdg.combo_coorGen
        self._combo_mappingmethods.addItems(list(self._dict_mappingmethods.keys()))
        self._combo_mappingmethods.currentTextChanged.connect(
            lambda text: self.show_chosen_coorGen(text))
        
        # Z-scan method selection
        self._zscan_method = ZScan1(
            parent = wdg.wdg_3Dmod_holder,
            getter_stagecoor = self._motion_controller.get_coordinates_closest_mm)
        wdg.lyt_3Dmod_holder.addWidget(self._zscan_method)
        
        # > Control widgets <
        self._btn_genCoor_2D = wdg.btn_gen_2Dcoor
        self._btn_genCoor_3D = wdg.btn_gen_3Dcoor
        
        self._btn_genCoor_2D.clicked.connect(self._generate_mapping_coordinate_2D)
        self._btn_genCoor_3D.clicked.connect(self._generate_mapping_coordinate_3D)
        
    def initialise(self):
        """
        Initialises the treeview and loads the mapping coordinates from the hub.
        """
        pass
        
    def terminate(self):
        """
        Terminates the treeview and removes the observer from the hub.
        """
        pass
        
    @Slot(str)
    def show_chosen_coorGen(self, method_name:str):
        """
        Shows the options for the selected mapping method
        
        Args:
            method_name (str): The name of the mapping method to show.
        """
        widgets = get_all_widgets_from_layout(self._widget.lyt_coorGen_holder)
        
        for widget in widgets:
            widget.deleteLater()
        qw.QApplication.processEvents()
        
        self._current_map_method:Map1 = self._dict_mappingmethods[method_name](**self._dict_mappingmethods_kwargs)
        self._widget.lyt_coorGen_holder.addWidget(self._current_map_method)
                
    @Slot()
    def _generate_mapping_coordinate_2D(self):
        """
        Adds the mapping coordinate to the list
        """
        mapping_coordinates = self._current_map_method.get_mapping_coordinates_mm()
        # Convert to list of tuples of floats
        if mapping_coordinates is None: return
        
        mapping_hub = self._dataHub_map.get_MappingHub()
        list_mappingUnit_names = list(mapping_hub.get_dict_nameToID().keys())
        while True:
            mappingUnit_name = qw.QInputDialog.getText(self, 'Mapping ID','Enter the ID for the mapping measurement:')[0]
            if mappingUnit_name == '' or not isinstance(mappingUnit_name,str)\
                or mappingUnit_name in list_mappingUnit_names or self._coorHub.search_mappingCoor(mappingUnit_name) is not None:
                retry = qw.QMessageBox.question(self, 'Error',"Invalid 'mappingUnit name'. The name cannot be empty or already exist. Please try again.",
                    qw.QMessageBox.Retry | qw.QMessageBox.Cancel) # pyright: ignore[reportAttributeAccessIssue] ; Retry and Cancel attributes exists
                if retry == qw.QMessageBox.Cancel: return # pyright: ignore[reportAttributeAccessIssue] ; Retry and Cancel attributes exists
            else: break
        
        mappingCoor = MeaCoor_mm(mappingUnit_name,mapping_coordinates)
        self._coorHub.append(mappingCoor)
        
    @Slot()
    def _generate_mapping_coordinate_3D(self):
        """
        Adds the z-scan mapping coordinate to the list
        """
        def check_mappingUnit_name(name:str) -> bool:
            nonlocal self, list_mappingUnit_names, list_mapping_coordinates
            res = True
            if name == ''\
                or not isinstance(name,str)\
                or name in list_mappingUnit_names\
                or self._coorHub.search_mappingCoor(name) is not None:
                res = False
            return res
            
        mapping_coordinates = self._current_map_method.get_mapping_coordinates_mm()
        list_mapping_coordinates = self._zscan_method.get_coordinates_mm(mapping_coordinates)
        if list_mapping_coordinates is None: return
        
        list_zcoor = [f'z{list_coor[0][2]*1e3:.1f}um' for list_coor in list_mapping_coordinates]
        
        mapping_hub = self._dataHub_map.get_MappingHub()
        list_mappingUnit_names = list(mapping_hub.get_dict_nameToID().keys())
        while True:
            mappingUnit_name = qw.QInputDialog.getText(self, 'Mapping ID','Enter the ID for the mapping measurement:')[0]
            list_new_mappingUnit_names = [mappingUnit_name+f'_{zcoor}' for zcoor in list_zcoor]
            if any([not check_mappingUnit_name(name) for name in list_new_mappingUnit_names]) or mappingUnit_name == '':
                retry = qw.QMessageBox.question(self, 'Error',"Invalid 'mappingUnit name'. The name cannot be empty or already exist. Please try again.",
                    qw.QMessageBox.Retry | qw.QMessageBox.Cancel) # pyright: ignore[reportAttributeAccessIssue] ; Retry and Cancel attributes exists
                if retry == qw.QMessageBox.Cancel: return # pyright: ignore[reportAttributeAccessIssue] ; Retry and Cancel attributes exists
            else: break
        
        list_mappingCoor = [
            MeaCoor_mm(mappingUnit_name=name,mapping_coordinates=coor)
            for name, coor in zip(list_new_mappingUnit_names, list_mapping_coordinates)
        ]
        
        self._coorHub.extend(list_mappingCoor)
        
        
def test_wdgTreeview_MappingCoordinates():
    app = qw.QApplication([])
    window = qw.QMainWindow()
    window.setWindowTitle('Dummy Treeview Mapping Coordinates')
    mappingCoorHub = List_MeaCoor_Hub()
    treeview = Wdg_Treeview_MappingCoordinates(window, mappingCoorHub)
    window.setCentralWidget(treeview)
    window.show()
    mappingCoorHub.generate_dummy_data(num_units=5, num_coords=10)
    app.exec()
        
def generate_dummy_wdg_hilvlCoorGenerator(
    parent:qw.QWidget,
    motion_controller:Wdg_MotionController|None=None,
    datahub_map:Wdg_DataHub_Mapping|None=None,
    datahub_img:Wdg_DataHub_Image|None=None,
    datahub_imgcal:Wdg_DataHub_ImgCal|None=None
    ) -> Wdg_Hilvl_CoorGenerator:
    """
    Generates a dummy coordinate generator frame for testing purposes.
    
    Args:
        parent (tk.Tk | tk.Frame): The parent frame or window.
        motion_controller (Frm_MotionController | None): The motion controller to use. If None, a dummy motion controller will be generated.
        datahub_map (Frm_DataHub_Mapping | None): The mapping data hub to use. If None, a dummy mapping data hub will be generated.
        datahub_img (ImageMeasurement_Hub | None): The image measurement hub to use. If None, a dummy image measurement hub will be generated.
        datahub_imgcal (ImageMeasurement_Calibration_Hub | None): The image calibration hub to use. If None, a dummy image calibration hub will be generated.
        
    Returns:
        sframe_CoorGenerator: The dummy coordinate generator frame.
    """
    from iris.gui.motion_video import generate_dummy_motion_controller
    from iris.data.calibration_objective import generate_dummy_calibrationHub
    from iris.gui.dataHub_MeaImg import generate_dummy_frmImageHub, generate_dummy_frmImgCalHub
    from iris.gui.dataHub_MeaRMap import generate_dummy_frmMappingHub
    
    coorHub = List_MeaCoor_Hub()
    motion_controller = generate_dummy_motion_controller(parent) if motion_controller is None else motion_controller
    dataHub_map = generate_dummy_frmMappingHub(parent) if datahub_map is None else datahub_map
    dataHub_img = generate_dummy_frmImageHub(parent) if datahub_img is None else datahub_img
    dataHub_imgcal = generate_dummy_frmImgCalHub(parent) if datahub_imgcal is None else datahub_imgcal
    
    return Wdg_Hilvl_CoorGenerator(
        parent=parent,
        coorHub=coorHub,
        motion_controller=motion_controller,
        dataHub_map=dataHub_map,
        dataHub_img=dataHub_img,
        dataHub_imgcal=dataHub_imgcal,
    )
    
def test_wdg_Hilvl_CoorGenerator():
    app = qw.QApplication([])
    window = qw.QMainWindow()
    window.setWindowTitle('Dummy High-level Coordinate Generator')
    mwdg = qw.QWidget()
    window.setCentralWidget(mwdg)
    lyt = qw.QHBoxLayout(mwdg)
    
    dummy_sfrmCoorGen = generate_dummy_wdg_hilvlCoorGenerator(mwdg)
    lyt.addWidget(dummy_sfrmCoorGen)
    
    window.show()
    app.exec()
    
if __name__ == '__main__':
    # test_wdgTreeview_MappingCoordinates()
    test_wdg_Hilvl_CoorGenerator()

    # root = tk.Tk()
    # root.title('Dummy Coordinate Generator')
    
    # dummy_sfrmCoorGen = generate_dummy_sfrmCoorGenerator(root)
    # dummy_sfrmCoorGen.pack(fill=tk.BOTH, expand=True)
    
    # root.mainloop()