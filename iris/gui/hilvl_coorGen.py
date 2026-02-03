import sys
import os

import PySide6.QtWidgets as qw
from PySide6.QtCore import Slot

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
from iris.gui.submodules.meaCoor_modifier.ellipsify import Ellipsify as MapMod6
from iris.gui.submodules.meaCoor_modifier.multitranslateXYZ import MultiTranslatorXYZ as MapMod7

from iris.utils.general import get_all_widgets_from_layout

from iris.gui.motion_video import Wdg_MotionController
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image, Wdg_DataHub_ImgCal
from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping
from iris.gui.submodules.mappingCoordinatesTreeview import Wdg_Treeview_MappingCoordinates

from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.resources.hilvl_coorGen_ui import Ui_hilvl_coorGen
from iris.resources.hilvl_coorGen_coorMod_ui import Ui_coorMod

class Hilvl_CoorGen_UiDesign(qw.QWidget, Ui_hilvl_coorGen):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

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
            '5. Gridify': MapMod5,
            '6. Ellipsify': MapMod6,
            '7. Multi-translate XYZ': MapMod7,
        }   # Mapping methods, to be programmed manually

        self.combo_methods.addItems(list(self._dict_mapModMethods.keys()))
        self.combo_methods.currentTextChanged.connect(
            lambda text: self.show_chosen_mapModMethod(text))
        
        # > Initial map modifier method setup - create all widgets upfront <
        self._dict_mapModMethod_widgets = {}
        for method_name, method_class in self._dict_mapModMethods.items():
            widget = method_class(**self._dict_mapModMethods_kwargs)
            self._dict_mapModMethod_widgets[method_name] = widget
            self.lyt_holder_modifiers.addWidget(widget)
            widget.hide()
        
        # Show the first one
        first_method_name = list(self._dict_mapModMethods.keys())[0]
        self._current_mapModMethod = self._dict_mapModMethod_widgets[first_method_name]
        self._current_mapModMethod.show()
        
    @Slot(str)
    def show_chosen_mapModMethod(self, method_name:str):
        """
        Shows the options for the selected mapping method
        
        Args:
            method_name (str): The name of the mapping method to show.
        """
        # Hide the current widget
        if self._current_mapModMethod is not None:
            self._current_mapModMethod.hide()
        
        # Show the selected widget
        self._current_mapModMethod = self._dict_mapModMethod_widgets[method_name]
        self._current_mapModMethod.show()
    
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
        
        # Create all mapping method widgets upfront and store them
        self._dict_mappingmethod_widgets = {}
        for method_name, method_class in self._dict_mappingmethods.items():
            widget = method_class(**self._dict_mappingmethods_kwargs)
            self._dict_mappingmethod_widgets[method_name] = widget
            wdg.lyt_coorGen_holder.addWidget(widget)
            widget.hide()
        
        self._current_map_method = self._dict_mappingmethod_widgets['1. Start/End']
        self._current_map_method.show()
        
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
        # Hide the current widget
        if self._current_map_method is not None:
            self._current_map_method.hide()
        
        # Show the selected widget
        self._current_map_method = self._dict_mappingmethod_widgets[method_name]
        self._current_map_method.show()
                
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