"""
A GUI module to modify a mapping coordinates list by translating 
the coordinates in the X, Y and Z direction.
"""

from PySide6.QtGui import QCloseEvent
import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QTimer, QModelIndex, QObject, QThread

from enum import Enum
import threading

import numpy as np
from PIL import ImageQt

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.gui.motion_video import Wdg_MotionController, ResizableQLabel
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.utils.gridify import generate_warped_grid

from iris.resources.coordinate_modifiers.gridify_setup_ui import Ui_gridify_setup
from iris.resources.coordinate_modifiers.gridify_setup_naming_ui import Ui_gridify_setup_naming
from iris.resources.coordinate_modifiers.gridify_setup_finetuning_ui import Ui_gridify_setup_finetuning

class Enums_RefXY(Enum):
    """Enumeration for the reference location of the mapping coordinates"""
    top_left = 'Top left'
    top_center = 'Top center'
    top_right = 'Top right'
    center_left = 'Center left'
    center_center = 'Center center'
    center_right = 'Center right'
    bottom_left = 'Bottom left'
    bottom_center = 'Bottom center'
    bottom_right = 'Bottom right'

class Enums_RefZ(Enum):
    """Enumeration for the reference Z-coordinate of the mapping coordinates"""
    top = 'Top Z'
    center = 'Center Z'
    bottom = 'Bottom Z'

class Enums_RefFourCorners(Enum):
    """Enumeration for the reference four corners of the mapping coordinates"""
    top_left = 'Top left'
    top_right = 'Top right'
    bottom_left = 'Bottom left'
    bottom_right = 'Bottom right'

class Enums_RefCornerDict(Enum):
    """Enum for the dict keys of the reference four corners"""
    x = 'x'
    y = 'y'
    z = 'z'
    loc_xy = 'location_xy'
    loc_z = 'location_z'
    
class Enums_NamingScheme(Enum):
    """Enumeration for the naming scheme of the gridified coordinates"""
    row_col = "Row, Column"
    col_row = "Column, Row"
    
def calculate_coordinatesCenter(ref_coor:np.ndarray, mappingCoor:MeaCoor_mm,
                                    loc_xy: Enums_RefXY, loc_z: Enums_RefZ) -> list:
    """
    Calculates the center coordinates based on the corner coordinates and specified locations
    
    Args:
        ref_coor (np.ndarray): The reference coordinates in the form of a numpy array
        mappingCoor (MappingCoordinates_mm): The mapping coordinates object
        loc_xy (Enums_RefXY): The location in the XY plane
        loc_z (Enums_RefZ): The location in the Z direction
        
    Returns:
        list: A list containing the calculated center coordinates in the form [x, y, z]
    """
    list_coors = mappingCoor.mapping_coordinates
    
    list_x = [coor[0] for coor in list_coors]
    list_y = [coor[1] for coor in list_coors]
    list_z = [coor[2] for coor in list_coors]
    
    wid_x = abs(max(list_x) - min(list_x))
    wid_y = abs(max(list_y) - min(list_y))
    wid_z = abs(max(list_z) - min(list_z))

    x_ref = ref_coor[0]
    y_ref = ref_coor[1]
    z_ref = ref_coor[2]
    
    if loc_xy == Enums_RefXY.top_left:
        x_final = x_ref + wid_x / 2
        y_final = y_ref - wid_y / 2
    elif loc_xy == Enums_RefXY.top_center:
        x_final = x_ref
        y_final = y_ref - wid_y / 2
    elif loc_xy == Enums_RefXY.top_right:
        x_final = x_ref - wid_x / 2
        y_final = y_ref - wid_y / 2
    elif loc_xy == Enums_RefXY.center_left:
        x_final = x_ref + wid_x / 2
        y_final = y_ref
    elif loc_xy == Enums_RefXY.center_center:
        x_final = x_ref
        y_final = y_ref
    elif loc_xy == Enums_RefXY.center_right:
        x_final = x_ref - wid_x / 2
        y_final = y_ref
    elif loc_xy == Enums_RefXY.bottom_left:
        x_final = x_ref + wid_x / 2
        y_final = y_ref + wid_y / 2
    elif loc_xy == Enums_RefXY.bottom_center:
        x_final = x_ref
        y_final = y_ref + wid_y / 2
    elif loc_xy == Enums_RefXY.bottom_right:
        x_final = x_ref - wid_x / 2
        y_final = y_ref + wid_y / 2
        
    if loc_z == Enums_RefZ.top:
        z_final = z_ref - wid_z / 2
    elif loc_z == Enums_RefZ.center:
        z_final = z_ref
    elif loc_z == Enums_RefZ.bottom:
        z_final = z_ref + wid_z / 2
        
    return [x_final, y_final, z_final]
    
class Gridify(Ui_gridify_setup, qw.QWidget):
    def __init__(
        self,
        parent,
        mappingCoorHub: List_MeaCoor_Hub,
        motion_controller:Wdg_MotionController,
        *args, **kwargs) -> None:
        """Initializes the mapping method
        
        Args:
            parent (tk.Frame): The parent frame to place this widget in
            MappingCoorHub (MappingCoordinatesHub): The hub to store the resulting mapping coordinates in
            getter_MappingCoor (Callable[[], MappingCoordinates_mm]): A function to get the mapping coordinates to modify
            motion_controller (Frm_MotionController): The motion controller to use for the mapping
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
        self._coorHub = mappingCoorHub
        self._motion_controller = motion_controller
        
    # >>> Information widget <<<
        self.btn_instructions.clicked.connect(self._show_instructions)
        
    # >>> Reference coordinates widget <<<
        # Parameters setup
        self._dict_refFourCorners = {
            Enums_RefFourCorners.top_left: dict(),
            Enums_RefFourCorners.top_right: dict(),
            Enums_RefFourCorners.bottom_left: dict(),
            Enums_RefFourCorners.bottom_right: dict(),
        }
        self._init_refFourCorners_widgets()
        
    # >>> Options frame <<<
        self.btn_finalise.clicked.connect(self._run_gridSetup)
        
    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        self._mw_naming = None  # Reference to the naming setup window
        self._mw_finetune = None  # Reference to the finetune window
        self._is_deleted = False  # Flag to track if widget is being deleted
        
    # >>> Others <<<
        self._coorHub.add_observer(self._update_list_units)
        self._update_list_units()
        
    def _init_refFourCorners_widgets(self):
        """Initializes the reference four corners for the mapping coordinates"""
        # >> Setup the widgets <<
        list_combo_xy = [self.combo_tl_xy, self.combo_tr_xy, self.combo_bl_xy, self.combo_br_xy]
        list_combo_z = [self.combo_tl_z, self.combo_tr_z, self.combo_bl_z, self.combo_br_z]
        
        [combo_xy.addItems([e.value for e in Enums_RefXY]) for combo_xy in list_combo_xy]
        [combo_z.addItems([e.value for e in Enums_RefZ]) for combo_z in list_combo_z]
        
        [combo_xy.setCurrentText(Enums_RefXY.center_center.value) for combo_xy in list_combo_xy]
        [combo_z.setCurrentText(Enums_RefZ.bottom.value) for combo_z in list_combo_z]
        
        self.btn_currcoor_tl.clicked.connect(lambda: self._insert_current_coordinate(self.spin_tl_x, self.spin_tl_y, self.spin_tl_z))
        self.btn_currcoor_tr.clicked.connect(lambda: self._insert_current_coordinate(self.spin_tr_x, self.spin_tr_y, self.spin_tr_z))
        self.btn_currcoor_bl.clicked.connect(lambda: self._insert_current_coordinate(self.spin_bl_x, self.spin_bl_y, self.spin_bl_z))
        self.btn_currcoor_br.clicked.connect(lambda: self._insert_current_coordinate(self.spin_br_x, self.spin_br_y, self.spin_br_z))
        
        # >> Setup the dictionary <<
        self._dict_refFourCorners[Enums_RefFourCorners.top_left] = {
            Enums_RefCornerDict.x: self.spin_tl_x,
            Enums_RefCornerDict.y: self.spin_tl_y,
            Enums_RefCornerDict.z: self.spin_tl_z,
            Enums_RefCornerDict.loc_xy: self.combo_tl_xy,
            Enums_RefCornerDict.loc_z: self.combo_tl_z,
        }
        self._dict_refFourCorners[Enums_RefFourCorners.top_right] = {
            Enums_RefCornerDict.x: self.spin_tr_x,
            Enums_RefCornerDict.y: self.spin_tr_y,
            Enums_RefCornerDict.z: self.spin_tr_z,
            Enums_RefCornerDict.loc_xy: self.combo_tr_xy,
            Enums_RefCornerDict.loc_z: self.combo_tr_z,
        }
        self._dict_refFourCorners[Enums_RefFourCorners.bottom_left] = {
            Enums_RefCornerDict.x: self.spin_bl_x,
            Enums_RefCornerDict.y: self.spin_bl_y,
            Enums_RefCornerDict.z: self.spin_bl_z,
            Enums_RefCornerDict.loc_xy: self.combo_bl_xy,
            Enums_RefCornerDict.loc_z: self.combo_bl_z,
        }
        self._dict_refFourCorners[Enums_RefFourCorners.bottom_right] = {
            Enums_RefCornerDict.x: self.spin_br_x,
            Enums_RefCornerDict.y: self.spin_br_y,
            Enums_RefCornerDict.z: self.spin_br_z,
            Enums_RefCornerDict.loc_xy: self.combo_br_xy,
            Enums_RefCornerDict.loc_z: self.combo_br_z,
        }
        
    def _insert_current_coordinate(self, ent_x:qw.QDoubleSpinBox, ent_y:qw.QDoubleSpinBox, ent_z:qw.QDoubleSpinBox):
        """
        Inserts the current coordinates from the motion controller into the reference coordinates
        
        Args:
            ent_x (QDoubleSpinBox): The spinbox for the X coordinate
            ent_y (QDoubleSpinBox): The spinbox for the Y coordinate
            ent_z (QDoubleSpinBox): The spinbox for the Z coordinate
        """
        coor = self._motion_controller.get_coordinates_closest_mm()
        if any(c is None for c in coor):
            qw.QMessageBox.warning(self, "Warning", "Failed to get current coordinates from the motion controller.")
            return
        
        coorx_um = coor[0] * 1e3    # pyright: ignore[reportOptionalOperand] ; coor is checked for None above
        coory_um = coor[1] * 1e3    # pyright: ignore[reportOptionalOperand] ; coor is checked for None above
        coorz_um = coor[2] * 1e3    # pyright: ignore[reportOptionalOperand] ; coor is checked for None above
        
        ent_x.setValue(coorx_um)
        ent_y.setValue(coory_um)
        ent_z.setValue(coorz_um)
        
    @Slot()
    def _show_instructions(self):
        instructions = (
            "This module takes an existing mapping coordinates list and creates a grid layout based on the specified parameters.\n"
            "NOTE: Make sure that the XY stage coordinate increases when the XY stage physically moves to the left and bottom.\n"
            "And the Z coordinate increases when the objective's stage moves closer to the sample."
        )
        qw.QMessageBox.information(self, "Instructions", instructions)
    
    def _update_list_units(self):
        """Updates the list of mapping units in the combobox"""
        # Don't update if widget is being deleted
        if self._is_deleted:
            return
        
        try:
            self._dict_mapUnit.clear()  # Clear the existing dictionary
            self._dict_mapUnit = {unit.mappingUnit_name: unit for unit in self._coorHub}
            
            selection = self.combo_roi.currentText()
            self.combo_roi.clear()
            list_roi_names = list(self._dict_mapUnit.keys())
            self.combo_roi.addItems(list_roi_names)
            
            if selection in list_roi_names: self.combo_roi.setCurrentText(selection)
        except Exception:
            pass
        
    @Slot()
    def reset_and_handle_cancellation(self):
        """
        Resets the finalise button to enabled state
        """
        self.btn_finalise.setEnabled(True)
        
    @Slot()
    def _run_gridSetup(self):
        """
        Runs the modification of the z-coordinates of the selected mapping coordinates
        """
        self.btn_finalise.setEnabled(False)
        
    # > Retrieve the selected mapping unit from the combobox and check it <
        selected_unit_name = self.combo_roi.currentText()
        if not selected_unit_name:
            qw.QMessageBox.warning(self, "Warning", "Please select a mapping unit to modify.")
            self.reset_and_handle_cancellation()
            return
        
        if selected_unit_name not in self._dict_mapUnit:
            qw.QMessageBox.warning(self, "Error", f"Mapping unit '{selected_unit_name}' not found.")
            self.reset_and_handle_cancellation()
            return
        
        # Get the current mapping coordinates
        mapping_coordinates = self._dict_mapUnit[selected_unit_name]
        
        if not isinstance(mapping_coordinates, MeaCoor_mm):
            qw.QMessageBox.warning(self, "Error", "Invalid mapping coordinates type.")
            self.reset_and_handle_cancellation()
            return
        
    # > Calculate the center of the four corners coordinates <
        corner_coords = []
        for corner in self._dict_refFourCorners:
            x_mm = float(self._dict_refFourCorners[corner][Enums_RefCornerDict.x].value())/1e3
            y_mm = float(self._dict_refFourCorners[corner][Enums_RefCornerDict.y].value())/1e3
            z_mm = float(self._dict_refFourCorners[corner][Enums_RefCornerDict.z].value())/1e3
            ctr_x, ctr_y, ctr_z = calculate_coordinatesCenter(
                ref_coor=np.array([x_mm, y_mm, z_mm]),
                mappingCoor=mapping_coordinates,
                loc_xy=Enums_RefXY(self._dict_refFourCorners[corner][Enums_RefCornerDict.loc_xy].currentText()),
                loc_z=Enums_RefZ(self._dict_refFourCorners[corner][Enums_RefCornerDict.loc_z].currentText())
            )
            corner_coords.append(np.array([ctr_x, ctr_y, ctr_z]))
            
    # > Get the number of rows and columns from the entry fields <
        try:
            num_rows = self.spin_row.value()
            num_cols = self.spin_col.value()
            if num_rows < 2 or num_cols < 2:
                raise ValueError("Number of rows and columns must be at least 2.")
        except ValueError as e:
            qw.QMessageBox.critical(self, "Error", f"Invalid input: {e}")
            self.reset_and_handle_cancellation()
            return
        
        mapping_coor = mapping_coordinates.copy()
        
    # > Open the grid setup dialog <
        self._mw_naming = Gridify_NamingSetup(
            gridify_main=self,
            corner_coords=corner_coords,
            num_rows=num_rows,
            num_cols=num_cols,
            mapping_coor=mapping_coor,
            ctrl_motion_video=self._motion_controller,
        )
        self._mw_naming.show()
        
    def initialise_Gridify_Finetune(self, list_mapping_coor:list[MeaCoor_mm],
        list_loc:list[tuple[int,int]]) -> None:
        """
        Initialises the fine-tune gridify window.

        Args:
            list_mapping_coor (list[MeaCoor_mm]): List of mapping coordinates to fine-tune
            list_loc (list[tuple[int,int]]): List of (row, column) locations for each mapping coordinate
        """
        self._mw_finetune = Gridify_Finetune(
            gridify_main=self,
            list_mapping_coor=list_mapping_coor,
            list_loc=list_loc,
            ctrl_motion_video=self._motion_controller,
        )
        self._mw_finetune.show()
        
    @Slot(list)
    def handle_gridify_completion(self, res:list[MeaCoor_mm]):
        list_newMapCoor = []
        for mapcoor in res:
            mapcoor:MeaCoor_mm
            list_coor = [(float(coor[0]), float(coor[1]), float(coor[2])) for coor in mapcoor.mapping_coordinates.copy()]
            new_mapcoor = MeaCoor_mm(
                mappingUnit_name=mapcoor.mappingUnit_name,
                mapping_coordinates=list_coor
            )
            list_newMapCoor.append(new_mapcoor)
            
        if len(list_newMapCoor) > 0:
            self._coorHub.extend(list_newMapCoor)
        self.reset_and_handle_cancellation()
        
    def deleteLater(self) -> None:
        # Set flag to prevent callbacks after deletion
        self._is_deleted = True
        
        # Clean up any observers or resources here if needed
        try:
            self._coorHub.remove_observer(self._update_list_units)
        except Exception:
            pass
        
        # Clean up child windows if they exist
        if hasattr(self, '_mw_naming') and self._mw_naming is not None:
            try:
                self._mw_naming.close()
                self._mw_naming.deleteLater()
            except Exception:
                pass
        
        if hasattr(self, '_mw_finetune') and self._mw_finetune is not None:
            try:
                self._mw_finetune.close()
                self._mw_finetune.deleteLater()
            except Exception:
                pass
        
        return super().deleteLater()
    
class Gridify_NamingSetup(Ui_gridify_setup_naming, qw.QMainWindow):
    sig_cancelled = Signal()
    
    def __init__(self, gridify_main:Gridify, corner_coords: list[np.ndarray],
                 num_rows: int, num_cols: int, mapping_coor: MeaCoor_mm,
                 ctrl_motion_video: Wdg_MotionController, *args, **kwargs):
        super().__init__(gridify_main, *args, **kwargs)
        self.setupUi(self)
        
    # >>> Store the parameters <<<
        self._gridify_main = gridify_main
        self._corner_coords = corner_coords
        self._num_rows = num_rows
        self._num_cols = num_cols
        self._mapping_coor = mapping_coor
        self._ctrl_motion_video = ctrl_motion_video
        
    # >>> Create the gridify interface <<<
        # Parameters setup
        self._list_rowNames:list[qw.QLineEdit] = []
        self._list_colNames:list[qw.QLineEdit] = []
        self._init_rowColSetup_widgets()
        self._init_namingScheme_widgets()
        
    # >>> Finalise button <<<
        self.btn_finalise.clicked.connect(self._run_gridFinetune)
        self.btn_cancel.clicked.connect(self.close)
        
    # >> Signals <<<
        self._programmatic_close = False
        self.sig_cancelled.connect(self._gridify_main.reset_and_handle_cancellation)
        
    def closeEvent(self, event: QCloseEvent) -> None:
        if self._programmatic_close:
            event.accept()
            return
        
        cancel = qw.QMessageBox.question(
            self,
            "Confirm Close",
            "Are you sure you want to close the gridify naming setup? This will cancel the operation.",
            qw.QMessageBox.Yes | qw.QMessageBox.No, # pyright: ignore[reportAttributeAccessIssue]
            qw.QMessageBox.No # pyright: ignore[reportAttributeAccessIssue]
        )
        if cancel == qw.QMessageBox.Yes: # pyright: ignore[reportAttributeAccessIssue]
            self.sig_cancelled.emit()
            event.accept()
        else:
            event.ignore()
    
    def _init_rowColSetup_widgets(self):
        """Initializes the row and column setup widgets"""
        for i in range(self._num_rows):
            lbl_row = qw.QLabel(f'Row {i+1}:')
            entry_row = qw.QLineEdit(f'Row {i+1}')
            self.lyt_row.addRow(lbl_row, entry_row)
            self._list_rowNames.append(entry_row)
            
        for j in range(self._num_cols):
            lbl_col = qw.QLabel(f'Col {j+1}:')
            entry_col = qw.QLineEdit(f'Col {j+1}')
            self.lyt_col.addRow(lbl_col, entry_col)
            self._list_colNames.append(entry_col)
        
    def _init_namingScheme_widgets(self):
        """Initializes the naming scheme setup widgets"""
        # Create radio buttons for naming scheme selection
        self.btn_example.clicked.connect(self._show_example_names)
        
    def _show_example_names(self):
        qw.QMessageBox.information(self, "Example", f"Example naming: {self._generate_names()[0][:5] if self._generate_names() else 'No names could be generated'}")
        
    def _generate_names(self) -> tuple[list[str], list[tuple[int, int]]]:
        """
        Generates the names for the gridified coordinates based on the row and column names.
        
        Returns:
            tuple: A tuple containing two lists:
            list: of names generated based on the naming scheme and row/column names in 
                the order of rows first then columns (u then v, e.g., (row1,col1),(row2,col1),...,(row1,col2),...)
                the order of columns first then rows (u then v, e.g., (col1,row1),(col1,row2),...,(col2,row1),...)
            list: of tuples containing the (row, column) indices for each name.
                """
        separator = self.ent_separator.text()
        
        list_name = []
        list_loc = []
        # Generate the rows in the reverse order
        for j in range(self._num_cols):
            for i in reversed(range(self._num_rows)):
                if self.rad_rowcol.isChecked():
                    name = f"{self._list_rowNames[i].text()}{separator}{self._list_colNames[j].text()}"
                else:
                    name = f"{self._list_colNames[j].text()}{separator}{self._list_rowNames[i].text()}"
                    
                list_name.append(name)
                list_loc.append((i, j))
        return list_name, list_loc

    def _generate_coordinates(self):
        """Generates the coordinates for the gridified mapping coordinates"""
        corner_coords = np.array(self._corner_coords)
        num_rows = self._num_rows
        num_cols = self._num_cols
        
        # Generate the gridified coordinates
        result = generate_warped_grid(
            p00=corner_coords[2],
            p01=corner_coords[3],
            p10=corner_coords[0],
            p11=corner_coords[1],
            num_u_lines=num_rows,
            num_v_lines=num_cols,
        )
        
        # flatten the result and convert to lists
        list_x = result[0].flatten().tolist()
        list_y = result[1].flatten().tolist()
        list_z = result[2].flatten().tolist()

        list_coor = [(x,y,z) for x,y,z in zip(list_x, list_y, list_z)]
        return list_coor
        
    def _translate_mappingCoor(self, mappingCoor:MeaCoor_mm, new_center_coor:np.ndarray) -> MeaCoor_mm:
        """Translates the mapping coordinates to the new center coordinates
        
        Args:
            mappingCoor (MappingCoordinates_mm): The mapping coordinates to translate
            new_center_coor (np.ndarray): The new center coordinates in the form of a numpy array
            
        Returns:
            MappingCoordinates_mm: The translated mapping coordinates
        """
        assert isinstance(mappingCoor, MeaCoor_mm), "mappingCoor must be an instance of MappingCoordinates_mm"
        assert isinstance(new_center_coor, np.ndarray), "new_center_coor must be a numpy array"
        assert new_center_coor.shape == (3,), "new_center_coor must be a 3-element numpy array"
        assert mappingCoor.mapping_coordinates, "mappingCoor must contain coordinates to translate"
        
        current_center = np.mean(mappingCoor.mapping_coordinates, axis=0)
        translation_vector = new_center_coor - current_center
        translated_coordinates = mappingCoor.mapping_coordinates + translation_vector
        
        mappingCoor.mapping_coordinates = translated_coordinates
        
        return mappingCoor
        
    @Slot()
    def _run_gridFinetune(self):
        """
        Performs the gridify operation by generating the mapping coordinates based on the specified parameters.
        """
        self.btn_finalise.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        
        list_names, list_loc = self._generate_names()
        coordinates = self._generate_coordinates()
        
        list_mapping_coor = []
        for i, name in enumerate(list_names):
            mapping_coor = self._mapping_coor.copy()
            mapping_coor.mappingUnit_name = name
            mapping_coor = self._translate_mappingCoor(
                mappingCoor=mapping_coor,
                new_center_coor=np.array(coordinates[i]))
            
            list_mapping_coor.append(mapping_coor)
            
        # Make sure that all the names are unique
        unique_names = set(list_names)
        if len(unique_names) < len(list_names):
            qw.QMessageBox.warning(self, "Warning", "Duplicate names found in the generated mapping coordinates. Please ensure unique names.")
            self.btn_finalise.setEnabled(True)
            self.btn_cancel.setEnabled(True)
            return
        
        self._gridify_main.initialise_Gridify_Finetune(
            list_mapping_coor=list_mapping_coor,
            list_loc=list_loc,
        )
        
        self._programmatic_close = True
        self.close()
        
class StageComm_Worker(QObject):
    """
    A worker to communicate with the stage to move and set the speed.
    """
    sig_gotocoor = Signal(tuple, threading.Event)
    sig_setspeed = Signal(float, float, threading.Event)
        
    def __init__(self, ctrl_motion_video: Wdg_MotionController):
        super().__init__()
        self._controller = ctrl_motion_video
        self.sig_gotocoor.connect(ctrl_motion_video.get_goto_worker().work)
        self.sig_setspeed.connect(ctrl_motion_video.set_vel_relative)
        
    @Slot(tuple, bool)
    def goto_coordinate(self, coor_mm: tuple, maxspeed:bool):
        try:
            current_speed = self._controller.get_VelocityParameters()
            if maxspeed:
                event_finish_speed = threading.Event()
                self.sig_setspeed.emit(100.0, 100.0, event_finish_speed) # Set to max speed (example values, adjust as needed)
                event_finish_speed.wait()
            
            event_finish = threading.Event()
            self.sig_gotocoor.emit(coor_mm, event_finish)
            event_finish.wait()
            
            if maxspeed:
                self._controller.set_vel_relative(*current_speed)
                
        except Exception as e: print(f"Error in goto_coordinate: {e}")
        
        
class Gridify_Finetune(Ui_gridify_setup_finetuning, qw.QMainWindow):
    
    sig_list_modified_ROI = Signal(list)
    sig_cancelled = Signal()
    
    _sig_gotocoor = Signal(tuple, bool)
    
    def __init__(self, gridify_main:Gridify, list_mapping_coor:list[MeaCoor_mm],
                 list_loc:list[tuple[int, int]], ctrl_motion_video:Wdg_MotionController,
                 *args, **kwargs):
        """
        Initializes the fine-tune gridify window.
        
        Args:
            parent (tk.Tk): The parent window.
            list_mapping_coor (list[MappingCoordinates_mm]): The list of mapping coordinates.
            list_loc (list[tuple[int, int]]): The list of (row, column) locations.
            ctrl_motion_video (Frm_MotionController): The motion controller for the video feed.
        """
        super().__init__(gridify_main, *args, **kwargs)
        self.setupUi(self)
        
    # >>> Store the parameters <<<
        self._gridify_main = gridify_main
        self._list_mapping_coor = list_mapping_coor
        self._list_loc = list_loc
        self._ctrl_motion_video = ctrl_motion_video
        
    # >> Connect signals <<<
        self.sig_list_modified_ROI.connect(self._gridify_main.handle_gridify_completion)
        self.sig_cancelled.connect(self._gridify_main.reset_and_handle_cancellation)
        
    # >>> Initialise the parameters <<<
        self._list_mod = [False] * len(self._list_mapping_coor)  # List to track modified coordinates
        
    # >>> Layout setup <<<
        self._init_finetune_widgets()
        
    # >>> Initialize the video feed parameters <<<
        self._flg_video_feed = threading.Event()
        
        self._lbl_vid = ResizableQLabel(min_height=1)
        self.lyt_video.addWidget(self._lbl_vid)
        
    # >>> Start a qtimer to update the video feed <<<
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._auto_video_updater)
        self._timer.start(20)  # Update every 20 ms
        self._flg_video_feed.set()  # Set the flag to start the video feed
        self._last_imgqt = None
        QTimer.singleShot(0, self._auto_video_updater)  # Initial call to start the video feed immediately
        
    # >>> Goto worker setup <<<
        self._init_goto_worker()
        
    # >>> Autofocus setup <<<
        self._init_autofocus_workers()
        self.btn_autofocus.clicked.connect(self._start_autofocus)
        
    # >>> Others <<<
        self._programmatic_close = False
        
    def _init_goto_worker(self):
        self._thread_goto = QThread()
        self._goto_worker = StageComm_Worker(self._ctrl_motion_video)
        self._sig_gotocoor.connect(self._goto_worker.goto_coordinate)
        self._goto_worker.moveToThread(self._thread_goto)
        self._thread_goto.start()
        
    def _init_autofocus_workers(self):
        self._autofocus_worker = self._ctrl_motion_video.get_autofocus_worker()
        self._autofocus_worker.sig_finished.connect(self._handle_autofocus_finished)
        
    def _start_autofocus(self):
        confirm = qw.QMessageBox.question(
            self,
            "Confirm Autofocus",
            "This will move the stage automatically and perform autofocus.\n"
            "CAUTION: This may move the stage to an unsafe position, such as CRASHING the objective.\n"
            "Do you want to proceed?",
            qw.QMessageBox.Yes | qw.QMessageBox.No, # pyright: ignore[reportAttributeAccessIssue] ; pyqt5 vs PySide6 difference
            qw.QMessageBox.No # pyright: ignore[reportAttributeAccessIssue] ; pyqt5 vs PySide6 difference
        )
        if confirm != qw.QMessageBox.Yes: # pyright: ignore[reportAttributeAccessIssue] ; pyqt5 vs PySide6 difference
            return
        
        self._perform_autofocus()
        
    @Slot(float)
    def _handle_autofocus_finished(self, coor_z_mm: float):
        self._update_coordinate_withGivenZCoor(coor_z_mm)
        self._go_to_nextMappingCoor()
        self._perform_autofocus()
        
    @Slot()
    def _perform_autofocus(self):
        result = self._get_selected_mappingCoor()
        if not result: return
        
        idx, mapping_coor = result
        if idx == len(self._list_mapping_coor) - 1: return
        
        target_coor_mm = self._calculate_target_coordinate(mapping_coor)
        target_coor_mm = target_coor_mm.astype(float)
        target_coor_mm = (target_coor_mm[0], target_coor_mm[1], target_coor_mm[2])
        
        range_mm = self.spin_range_um.value() / 1e3
        start_mm = target_coor_mm[2] - range_mm/2
        end_mm = target_coor_mm[2] + range_mm/2
        
        self._ctrl_motion_video.perform_autofocus(start_mm=start_mm, end_mm=end_mm, bypass_confirmation=True)
        
    @Slot()
    def _auto_video_updater(self):
        """Automatically updates the video feed"""
        if not self._flg_video_feed.is_set():
            self._timer.stop()
            return
        try:
            new_img = self._ctrl_motion_video.get_current_image()
            if new_img is None: return
            new_imgqt = ImageQt.toqpixmap(new_img)
            if new_imgqt != self._last_imgqt:
                self._lbl_vid.setPixmap(new_imgqt)
                self._last_imgqt = new_imgqt
        except Exception as e:
            print(f"Error updating video feed: {e}")
            
    def _init_finetune_widgets(self):
        """Initializes the fine-tune widgets for the gridified coordinates"""
        # >>> Create a treeview widget to display the gridified coordinates <<<
        self.tree_roi.setColumnCount(5)
        self.tree_roi.setHeaderLabels(['Row', 'Col', 'Name', 'Center coor [μm]', 'Modified'])
        
        # Bind double-click event to the treeview
        self.tree_roi.doubleClicked.connect(self._on_treeview_double_click)
        
        self._update_treeview()
        item = self.tree_roi.topLevelItem(0)
        if item is not None: self.tree_roi.setCurrentItem(item)
        
    # >>> Setup the parameters widget <<<
        self.combo_xy.addItems([e.value for e in Enums_RefXY])
        self.combo_z.addItems([e.value for e in Enums_RefZ])
        
        self.combo_xy.setCurrentText(Enums_RefXY.center_center.value)
        self.combo_z.setCurrentText(Enums_RefZ.bottom.value)
        
        self.btn_set_currcoor.clicked.connect(self._update_coordinate_withCurrentCoor)
        self.btn_set_nextROI.clicked.connect(self._update_coordinate_withCurrentCoor_and_go_next)
        self.btn_nextROI.clicked.connect(self._go_to_nextMappingCoor)
        self.btn_finish.clicked.connect(self._finalise_editing)
        self.btn_cancel.clicked.connect(self.close)

    @Slot()
    def _update_treeview(self) -> None:
        """Updates the treeview with the gridified coordinates"""
        # Store the current selection
        sel = self._get_selected_mappingCoor(suppress_warning=True)
        idx = sel[0] if sel else None
        
        self.tree_roi.clear()
        for i, mapping_coor in enumerate(self._list_mapping_coor):
            center_coor = np.mean(mapping_coor.mapping_coordinates, axis=0)
            center_coor_str = f"({center_coor[0]*1e3:.1f}, {center_coor[1]*1e3:.1f}, {center_coor[2]*1e3:.1f})"
            row, col = self._list_loc[i]
            name = mapping_coor.mappingUnit_name
            modified = 'Yes' if self._list_mod[i] else 'No'
            item = qw.QTreeWidgetItem([str(row+1), str(col+1), name, center_coor_str, modified])
            self.tree_roi.addTopLevelItem(item)
            
        # Restore the selection
        if idx is not None and idx < len(self._list_mapping_coor):
            iid = self.tree_roi.topLevelItem(idx)
            if iid is None: return
            self.tree_roi.setCurrentItem(iid)
            self.tree_roi.scrollToItem(iid)
        
    def _calculate_target_coordinate(self, mapping_coor:MeaCoor_mm) -> np.ndarray:
        """
        Calculates the target coordinate based on the selected reference coordinates and the mapping coordinates.
        
        Args:
            mapping_coor (MappingCoordinates_mm): The mapping coordinates from which to select the coordinate
        
        Returns:
            np.ndarray: The selected coordinate in the form of a numpy array [x, y, z]
        """
        loc_xy = Enums_RefXY(self.combo_xy.currentText())
        loc_z = Enums_RefZ(self.combo_z.currentText())
        
        if loc_xy == Enums_RefXY.top_left:
            x = np.min([coor[0] for coor in mapping_coor.mapping_coordinates])
            y = np.max([coor[1] for coor in mapping_coor.mapping_coordinates])
        elif loc_xy == Enums_RefXY.top_center:
            x = np.mean([coor[0] for coor in mapping_coor.mapping_coordinates])
            y = np.max([coor[1] for coor in mapping_coor.mapping_coordinates])
        elif loc_xy == Enums_RefXY.top_right:
            x = np.max([coor[0] for coor in mapping_coor.mapping_coordinates])
            y = np.max([coor[1] for coor in mapping_coor.mapping_coordinates])
        elif loc_xy == Enums_RefXY.center_left:
            x = np.min([coor[0] for coor in mapping_coor.mapping_coordinates])
            y = np.mean([coor[1] for coor in mapping_coor.mapping_coordinates])
        elif loc_xy == Enums_RefXY.center_center:
            x = np.mean([coor[0] for coor in mapping_coor.mapping_coordinates])
            y = np.mean([coor[1] for coor in mapping_coor.mapping_coordinates])
        elif loc_xy == Enums_RefXY.center_right:
            x = np.max([coor[0] for coor in mapping_coor.mapping_coordinates])
            y = np.mean([coor[1] for coor in mapping_coor.mapping_coordinates])
        elif loc_xy == Enums_RefXY.bottom_left:
            x = np.min([coor[0] for coor in mapping_coor.mapping_coordinates])
            y = np.min([coor[1] for coor in mapping_coor.mapping_coordinates])
        elif loc_xy == Enums_RefXY.bottom_center:
            x = np.mean([coor[0] for coor in mapping_coor.mapping_coordinates])
            y = np.min([coor[1] for coor in mapping_coor.mapping_coordinates])
        elif loc_xy == Enums_RefXY.bottom_right:
            x = np.max([coor[0] for coor in mapping_coor.mapping_coordinates])
            y = np.min([coor[1] for coor in mapping_coor.mapping_coordinates])
        else: raise ValueError(f"Invalid loc_xy value: {loc_xy}")
            
        if loc_z == Enums_RefZ.top:
            z = np.max([coor[2] for coor in mapping_coor.mapping_coordinates])
        elif loc_z == Enums_RefZ.center:
            z = np.mean([coor[2] for coor in mapping_coor.mapping_coordinates])
        elif loc_z == Enums_RefZ.bottom:
            z = np.min([coor[2] for coor in mapping_coor.mapping_coordinates])
        else: raise ValueError(f"Invalid loc_z value: {loc_z}")
            
        return np.array([x, y, z])
    
    def _update_coordinate_withGivenZCoor(self, z_coor_mm:float) -> None:
        """Updates the selected coordinate with the current position of the motion controller"""
        result = self._get_selected_mappingCoor()
        if not result: return
        
        idx, mapping_coor = result
        
        current_coor = self._ctrl_motion_video.get_coordinates_closest_mm()
        current_coor = np.array([current_coor[0], current_coor[1], z_coor_mm])
        
        new_center_coor = calculate_coordinatesCenter(
            ref_coor=current_coor,
            mappingCoor=mapping_coor,
            loc_xy=Enums_RefXY(self.combo_xy.currentText()),
            loc_z=Enums_RefZ(self.combo_z.currentText())
        )
        
        # Update the mapping coordinates by translating them to the new center coordinates
        translated_coor = np.array(mapping_coor.mapping_coordinates) + (new_center_coor - np.mean(mapping_coor.mapping_coordinates, axis=0))
        translated_coor_tup = [tuple(coor) for coor in translated_coor]
        new_mapping_coor = MeaCoor_mm(
            mappingUnit_name=mapping_coor.mappingUnit_name,
            mapping_coordinates=translated_coor_tup
        )
        
        # Update the mapping coordinates in the list
        self._list_mapping_coor[idx] = new_mapping_coor
        self._list_mod[idx] = True  # Mark the coordinate as modified
        self._update_treeview()

        return
    
    @Slot()
    def _update_coordinate_withCurrentCoor_and_go_next(self) -> None:
        """Updates the selected coordinate with the current position of the motion controller
        and moves the motion controller to the next coordinate"""
        self._update_coordinate_withCurrentCoor()
        self._go_to_nextMappingCoor()
    
    def _update_coordinate_withCurrentCoor(self) -> None:
        """Updates the selected coordinate with the current position of the motion controller"""
        result = self._get_selected_mappingCoor()
        if not result: return
        
        idx, mapping_coor = result
        
        current_coor = np.array(self._ctrl_motion_video.get_coordinates_closest_mm())
        
        new_center_coor = calculate_coordinatesCenter(
            ref_coor=current_coor,
            mappingCoor=mapping_coor,
            loc_xy=Enums_RefXY(self.combo_xy.currentText()),
            loc_z=Enums_RefZ(self.combo_z.currentText())
        )
        
        # Update the mapping coordinates by translating them to the new center coordinates
        translated_coor = np.array(mapping_coor.mapping_coordinates) + (new_center_coor - np.mean(mapping_coor.mapping_coordinates, axis=0))
        translated_coor_tup = [tuple(coor) for coor in translated_coor]
        new_mapping_coor = MeaCoor_mm(
            mappingUnit_name=mapping_coor.mappingUnit_name,
            mapping_coordinates=translated_coor_tup
        )
        
        # Update the mapping coordinates in the list
        self._list_mapping_coor[idx] = new_mapping_coor
        self._list_mod[idx] = True  # Mark the coordinate as modified
        self._update_treeview()

        return
    
    def _go_to_nextMappingCoor(self) -> None:
        """Updates the next coordinate with the current position of the motion controller
        and moves the motion controller to the next coordinate"""
        # Select the next coordinate in the treeview
        result = self._get_selected_mappingCoor()
        if not result: return None
        idx, _ = result
        if idx == len(self._list_mapping_coor) - 1:
            qw.QMessageBox.information(self, "Info", "You have reached the last coordinate.")
            return
        
        item = self.tree_roi.topLevelItem(idx + 1)
        if item is not None: self.tree_roi.setCurrentItem(item)
        
        # Move to the next coordinate
        self._go_to_selectedMappingCoor()

    def _get_selected_mappingCoor(self, suppress_warning: bool = False) -> tuple[int,MeaCoor_mm]|None:
        """Returns the currently selected mapping coordinates from the treeview
        
        Args:
            suppress_warning (bool): If True, suppresses the warning message if no item is selected.
            
        Returns:
            tuple: A tuple containing the index of the selected mapping coordinates and the mapping coordinates object
        """
        selected_item = self.tree_roi.currentItem()
        if not selected_item and not suppress_warning:
            qw.QMessageBox.warning(self, "Warning", "Please select a mapping coordinate to modify.")
            return None
        
        idx = self.tree_roi.indexOfTopLevelItem(selected_item)
        return idx, self._list_mapping_coor[idx]
        
    @Slot()
    def _go_to_selectedMappingCoor(self) -> None:
        """
        Moves the motion controller to the selected mapping coordinates
        """
        result = self._get_selected_mappingCoor()
        if not result: return
        
        _, mapping_coor = result
        target_coor = self._calculate_target_coordinate(mapping_coor)
        target_coor = target_coor.astype(float)
        target_coor = (target_coor[0], target_coor[1], target_coor[2])
        
        try:
            self._sig_gotocoor.emit(target_coor, self.chk_maxspeed.isChecked())
        except Exception as e:
            qw.QMessageBox.critical(self, "Error", f"Failed to move to coordinates: {e}")
            return
    
    @Slot()
    def _on_treeview_double_click(self, index: QModelIndex) -> None:
        self._go_to_selectedMappingCoor()
        
    @Slot()
    def _finalise_editing(self):
        """Finalises the editing of the gridified coordinates and returns the modified coordinates"""
        self.btn_cancel.setEnabled(False)
        self.btn_finish.setEnabled(False)
        
        confirmation = qw.QMessageBox.question(self, "Confirm", "Are you sure you want to finish editing?\n"
            "This will save all changes made to the mapping coordinates.",
            qw.QMessageBox.Yes | qw.QMessageBox.No, # pyright: ignore[reportAttributeAccessIssue]
            qw.QMessageBox.No # pyright: ignore[reportAttributeAccessIssue]
        )
        if confirmation != qw.QMessageBox.Yes: # pyright: ignore[reportAttributeAccessIssue]
            self.btn_cancel.setEnabled(True)
            self.btn_finish.setEnabled(True)
            return
        
        # Return the modified mapping coordinates
        self.sig_list_modified_ROI.emit(self._list_mapping_coor)
        self._flg_video_feed.clear()
        
        self._programmatic_close = True
        self.close()
        
    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Terminates the video feed and closes the window
        """
        if self._programmatic_close:
            event.accept()
            return super().closeEvent(event)
        
        self.btn_cancel.setEnabled(False)
        self.btn_finish.setEnabled(False)
        
        confirmation = qw.QMessageBox.question(self, "Confirm", "Are you sure you want to cancel all modifications?\n"
            "This will discard all changes made to the mapping coordinates.\n"
            "There is no way to undo this action.",
            qw.QMessageBox.Yes | qw.QMessageBox.No, # pyright: ignore[reportAttributeAccessIssue]
            qw.QMessageBox.No # pyright: ignore[reportAttributeAccessIssue]
        )
        if confirmation != qw.QMessageBox.Yes: # pyright: ignore[reportAttributeAccessIssue]
            self.btn_cancel.setEnabled(True)
            self.btn_finish.setEnabled(True)
            return

        self._flg_video_feed.clear()
        self.sig_cancelled.emit()
        
        return super().closeEvent(event)
        
def test():
    from iris.gui.motion_video import generate_dummy_motion_controller
    
    app = qw.QApplication([])
    mw = qw.QMainWindow()
    mwd = qw.QWidget()
    mw.setCentralWidget(mwd)
    lyt = qw.QHBoxLayout()
    mwd.setLayout(lyt)
    
    frm_motion = generate_dummy_motion_controller(mwd)
    lyt.addWidget(frm_motion)
    
    coorUnit = MeaCoor_mm(
        mappingUnit_name='Test Mapping Unit',
        mapping_coordinates=[(0, 0, 0), (1, 0, 1), (0, 1, 2), (1, 1, 3)]
    )
    
    coorHub = List_MeaCoor_Hub()
    coorHub.append(coorUnit)
    
    frm_coor_mod = Gridify(
        mwd,
        mappingCoorHub=coorHub,
        motion_controller=frm_motion,
    )
    lyt.addWidget(frm_coor_mod)
    
    mw.show()
    app.exec()
    
if __name__ == '__main__':
    test()