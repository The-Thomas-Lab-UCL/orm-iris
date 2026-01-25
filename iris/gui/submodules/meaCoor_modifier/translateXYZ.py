"""
A GUI module to modify a mapping coordinates list by translating 
the coordinates in the X, Y and Z direction.
"""

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QThread, QObject

import threading
from enum import Enum

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.gui.motion_video import Wdg_MotionController
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.utils.general import messagebox_request_input, thread_assign

from iris.resources.coordinate_modifiers.translator_xyz_ui import Ui_translator_xyz

class RadioOptionXY(Enum):
    TOP_LEFT = 'tl'
    TOP_CENTER = 'tc'
    TOP_RIGHT = 'tr'
    CENTER_LEFT = 'cl'
    CENTER_CENTER = 'cc'
    CENTER_RIGHT = 'cr'
    BOTTOM_LEFT = 'bl'
    BOTTOM_CENTER = 'bc'
    BOTTOM_RIGHT = 'br'
    
class RadioOptionZ(Enum):
    TOP = 'top'
    CENTER = 'ctr'
    BOTTOM = 'btm'

class TranslatorXYZ_Worker(QObject):
    
    sig_updatePrevCoor_mm = Signal(str)
    sig_currentCoor_mm = Signal(tuple)
    
    sig_finished = Signal(str)
    sig_error = Signal(str)
    sig_saveModifiedCoor = Signal(MeaCoor_mm, MeaCoor_mm)
    
    msg_error = "Error during translation: "
    msg_success = "Translation completed successfully."
    
    _sig_gotocoor = Signal(tuple,threading.Event)
    
    def __init__(self, motion_controller:Wdg_MotionController):
        super().__init__()
        self._motion_controller = motion_controller
        
        self._sig_gotocoor.connect(self._motion_controller.get_goto_worker().work)
        
    def go_to_reference_coordinate(self, mappingCoor:MeaCoor_mm, xyLoc:RadioOptionXY, zLoc:RadioOptionZ):
        """
        Moves the motion controller to the reference location of the selected mapping coordinates
        """
        ref_coor = self._get_reference_coordinate(mappingCoor, xyLoc, zLoc)
        
        evt_moveDone = threading.Event()
        self._sig_gotocoor.emit(ref_coor, evt_moveDone)
        evt_moveDone.wait()
        
    def _get_reference_coordinate(self, mappingCoor:MeaCoor_mm, xyLoc:RadioOptionXY, zLoc:RadioOptionZ)\
        -> tuple[float, float, float]:
        """
        Updates the label showing the current reference coordinates
        """
        assert isinstance(mappingCoor, MeaCoor_mm), "Invalid mapping coordinates type"
        
        x_min = min(coor[0] for coor in mappingCoor.mapping_coordinates)
        x_max = max(coor[0] for coor in mappingCoor.mapping_coordinates)
        y_min = min(coor[1] for coor in mappingCoor.mapping_coordinates)
        y_max = max(coor[1] for coor in mappingCoor.mapping_coordinates)
        x_ctr = (x_min + x_max) / 2
        y_ctr = (y_min + y_max) / 2
        
        if xyLoc == RadioOptionXY.TOP_LEFT:         coor_xy = (x_min, y_max)
        elif xyLoc == RadioOptionXY.TOP_CENTER:     coor_xy = (x_ctr, y_max)
        elif xyLoc == RadioOptionXY.TOP_RIGHT:      coor_xy = (x_max, y_max)
        elif xyLoc == RadioOptionXY.CENTER_LEFT:    coor_xy = (x_min, y_ctr)
        elif xyLoc == RadioOptionXY.CENTER_CENTER:  coor_xy = (x_ctr, y_ctr)
        elif xyLoc == RadioOptionXY.CENTER_RIGHT:   coor_xy = (x_max, y_ctr)
        elif xyLoc == RadioOptionXY.BOTTOM_LEFT:    coor_xy = (x_min, y_min)
        elif xyLoc == RadioOptionXY.BOTTOM_CENTER:  coor_xy = (x_ctr, y_min)
        elif xyLoc == RadioOptionXY.BOTTOM_RIGHT:   coor_xy = (x_max, y_min)
        else: raise ValueError("No reference location selected")
        
        z_min = min(coor[2] for coor in mappingCoor.mapping_coordinates)
        z_max = max(coor[2] for coor in mappingCoor.mapping_coordinates)
        z_ctr = (z_min + z_max) / 2
        
        if zLoc == RadioOptionZ.TOP:    coor_z = z_max
        elif zLoc == RadioOptionZ.CENTER:  coor_z = z_ctr
        elif zLoc == RadioOptionZ.BOTTOM:  coor_z = z_min
        else: raise ValueError("No reference Z-coordinate selected")
        
        return (coor_xy[0], coor_xy[1], coor_z)
        
    @Slot(MeaCoor_mm, RadioOptionXY, RadioOptionZ)
    def get_reference_coordinate(self, mappingCoor:MeaCoor_mm, xyLoc:RadioOptionXY, zLoc:RadioOptionZ):
        """
        Emits the reference coordinate signal
        """
        coor = self._get_reference_coordinate(mappingCoor, xyLoc, zLoc)
        self.sig_updatePrevCoor_mm.emit(f'{coor[0]*1e3:.0f}, {coor[1]*1e3:.0f}, {coor[2]*1e3:.0f} (μm)')
        
    @Slot()
    def get_current_coordinate(self):
        """
        Emits the current coordinate from the motion controller
        """
        coor = self._motion_controller.get_coordinates_closest_mm()
        if not all(isinstance(c, (int,float)) for c in coor):
            self.sig_error.emit('Could not retrieve current coordinates from motion controller.')
            return
        
        self.sig_currentCoor_mm.emit(coor)
    
    
    @Slot(MeaCoor_mm, RadioOptionXY, RadioOptionZ, tuple)
    def _perform_translation(self,mappingCoor:MeaCoor_mm, loc_xy:RadioOptionXY, loc_z:RadioOptionZ,
                             new_coor:tuple[float,float,float]):
        """
        Runs the modification of the z-coordinates of the selected mapping coordinates
        
        Args:
            mappingCoor (MeaCoor_mm): The mapping coordinates to modify
            loc_xy (RadioOptionXY): The reference location in XY
            loc_z (RadioOptionZ): The reference location in Z
            new_coor (tuple[float,float,float]): The new coordinate to move the reference location to
        """
    # > Modify the coordinates <
        try:
            ref_coor = self._get_reference_coordinate(mappingCoor, loc_xy, loc_z)
        except ValueError as e:
            self.sig_finished.emit(f"{self.msg_error} Invalid input: {e}")
            return
        
        # Translate the coordinates
        shiftx = new_coor[0] - ref_coor[0]
        shifty = new_coor[1] - ref_coor[1]
        shiftz = new_coor[2] - ref_coor[2]
        
        list_new_coor = []
        for x, y, z in mappingCoor.mapping_coordinates:
            new_x = x + shiftx
            new_y = y + shifty
            new_z = z + shiftz
            list_new_coor.append((new_x, new_y, new_z))
        
        self.sig_saveModifiedCoor.emit(mappingCoor, MeaCoor_mm(
            mappingUnit_name=mappingCoor.mappingUnit_name+'_translated',
            mapping_coordinates=list_new_coor
        ))
        
    @Slot(MeaCoor_mm, MeaCoor_mm, RadioOptionXY, RadioOptionZ, bool)
    def _move_to_next_meaCoor_ref(self, prev_meaCoor:MeaCoor_mm, current_meaCoor:MeaCoor_mm,
                                  loc_xy:RadioOptionXY, loc_z:RadioOptionZ, xy_only:bool):
        """
        Moves the stage to the new reference coordinate of the modified mapping coordinates
        """
        prev_coor = self._get_reference_coordinate(prev_meaCoor, loc_xy, loc_z)
        curr_coor = self._get_reference_coordinate(current_meaCoor, loc_xy, loc_z)
        
        new_x = curr_coor[0] + (curr_coor[0] - prev_coor[0])
        new_y = curr_coor[1] + (curr_coor[1] - prev_coor[1])
        
        if xy_only: new_z = curr_coor[2]
        else: new_z = curr_coor[2] + (curr_coor[2] - prev_coor[2])
        
        evt_moveDone = threading.Event()
        self._sig_gotocoor.emit((new_x, new_y, new_z), evt_moveDone)
        evt_moveDone.wait()
    

class TranslateXYZ(Ui_translator_xyz, qw.QWidget):
    msg_instructions = (
        "The Translate XYZ module allows you to translate the coordinates of a selected mapping unit, "
        "essentially moving it to another location while maintaining its points distribution.\n\n"
        "To use the module:\n"
        "1. Select the mapping unit you wish to modify from the dropdown menu.\n"
        "2. Choose the reference location for the translation using the radio buttons. "
        "e.g., top left (XY) means that the coordinates' top-left most coordinate will be moved to the newly specified coordinate.\n"
        "3. The current reference coordinate will be displayed next to 'Reference coordinate [μm]'.\n"
        "4. Enter the new desired coordinate for the reference location in the 'New coordinate [μm]' fields.\n"
        "5. You can click 'Insert current coordinate (X,Y,Z)' to automatically fill in the current position of the motion controller.\n"
        "6. Click 'Commit modification' to apply the translation to the selected mapping unit.\n\n"
        "Options:\n"
        "- 'Auto-select last modified mapping unit': Automatically selects the newly created mapping unit after modification.\n"
        "- 'Auto-move the stage using the last coordinate shift': Moves the motion controller to the new reference coordinate after modification.\n"
    )
    
    sig_updateListUnits = Signal()
    sig_update_prevCoor = Signal(MeaCoor_mm, RadioOptionXY, RadioOptionZ)
    sig_performTranslation = Signal(MeaCoor_mm, RadioOptionXY, RadioOptionZ, tuple, bool)
    sig_goto_nextMeaCoor_ref = Signal(MeaCoor_mm, MeaCoor_mm, RadioOptionXY, RadioOptionZ, bool)
    sig_goto_refCoor = Signal(MeaCoor_mm, RadioOptionXY, RadioOptionZ)
    
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
        self.btn_instructions.clicked.connect(lambda: qw.QMessageBox.information(
            self,
            "Instructions",
            self.msg_instructions
        ))
        
    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        
        self._init_worker_and_signals()
    
    def _init_worker_and_signals(self):
        """
        Initialises the worker thread for communication with the motion controller
        """
        # Create the worker thread
        self._thread_worker = QThread()
        
        self._worker_translator = TranslatorXYZ_Worker(
            motion_controller=self._motion_controller)
        self._worker_translator.moveToThread(self._thread_worker)
        
        # Signal: Store current stage coordinate
        self.btn_storeCoor.clicked.connect(self._worker_translator.get_current_coordinate)
        self._worker_translator.sig_currentCoor_mm.connect(self._update_current_coordinate)
        
        # Signal: Update reference coordinate
        self.sig_update_prevCoor.connect(self._worker_translator.get_reference_coordinate)
        self._worker_translator.sig_updatePrevCoor_mm.connect(lambda text: self.lbl_prevCoor.setText(text))
        
        # Signal: Perform translation
        self.sig_performTranslation.connect(self._worker_translator._perform_translation)
        
        # Signal: Handle saving modified coordinates
        self._worker_translator.sig_saveModifiedCoor.connect(self._handle_save_modified_coor)
        
        # Signal: Move to next mapping coordinate reference
        self.sig_goto_nextMeaCoor_ref.connect(self._worker_translator._move_to_next_meaCoor_ref)
        
        self.destroyed.connect(self._worker_translator.deleteLater)
        self.destroyed.connect(self._thread_worker.quit)
        
        self._thread_worker.start()
        
        # >>> Others <<<
        self.sig_updateListUnits.connect(self._update_list_units)
        self._coorHub.add_observer(self.sig_updateListUnits.emit)
        self.sig_updateListUnits.emit()
        
        # Move to current coordinate button
        self.btn_goto_refLoc.clicked.connect(self._go_to_reference_coordinate)
        self.sig_goto_refCoor.connect(self._worker_translator.go_to_reference_coordinate)
        
        # Commit button
        self.btn_commit.clicked.connect(self._perform_translation)
    
    @Slot(tuple)
    def _update_current_coordinate(self, coor:tuple):
        """
        Updates the current coordinate displayed in the entry fields
        """
        coorx_um = coor[0] * 1e3
        coory_um = coor[1] * 1e3
        coorz_um = coor[2] * 1e3
        
        self.spin_coorXUm.setValue(coorx_um)
        self.spin_coorYUm.setValue(coory_um)
        self.spin_coorZUm.setValue(coorz_um)
        
    def _go_to_reference_coordinate(self):
        """
        Moves the motion controller to the reference location of the selected mapping coordinates
        """
        selected_unit_name = self.combo_meaCoor.currentText()
        if not selected_unit_name:
            qw.QMessageBox.warning(self, "Warning", "Please select a mapping unit.")
            return
        
        if selected_unit_name not in self._dict_mapUnit:
            qw.QMessageBox.warning(self, "Warning", f"Mapping unit '{selected_unit_name}' not found.")
            return
        
        mapping_coordinates = self._dict_mapUnit[selected_unit_name]
        
        if not isinstance(mapping_coordinates, MeaCoor_mm):
            qw.QMessageBox.warning(self, "Warning", "Invalid mapping coordinates type.")
            return
        
        loc_xy, loc_z = self._get_reference_location()
        
        self.sig_goto_refCoor.emit(mapping_coordinates, loc_xy, loc_z)
        
        
    def _get_reference_location(self) -> tuple[RadioOptionXY, RadioOptionZ]:
        """Gets the selected reference location from the radio buttons
        
        Returns:
            tuple[RadioOptionXY, RadioOptionZ]: The selected reference locations for XY and Z
        """
        # Get XY location
        if self.btn_xy_topleft.isChecked():         xyLoc = RadioOptionXY.TOP_LEFT
        elif self.btn_xy_topcentre.isChecked():     xyLoc = RadioOptionXY.TOP_CENTER
        elif self.btn_xy_topright.isChecked():      xyLoc = RadioOptionXY.TOP_RIGHT
        elif self.btn_xy_centreleft.isChecked():    xyLoc = RadioOptionXY.CENTER_LEFT
        elif self.btn_xy_centrecentre.isChecked():  xyLoc = RadioOptionXY.CENTER_CENTER
        elif self.btn_xy_centreright.isChecked():   xyLoc = RadioOptionXY.CENTER_RIGHT
        elif self.btn_xy_bottomleft.isChecked():    xyLoc = RadioOptionXY.BOTTOM_LEFT
        elif self.btn_xy_bottomcentre.isChecked():  xyLoc = RadioOptionXY.BOTTOM_CENTER
        elif self.btn_xy_bottomright.isChecked():   xyLoc = RadioOptionXY.BOTTOM_RIGHT
        else: raise ValueError("No reference location selected")
        
        # Get Z location
        if self.btn_z_top.isChecked():      zLoc = RadioOptionZ.TOP
        elif self.btn_z_centre.isChecked():    zLoc = RadioOptionZ.CENTER
        elif self.btn_z_bottom.isChecked():    zLoc = RadioOptionZ.BOTTOM
        else: raise ValueError("No reference Z-coordinate selected")
        
        return (xyLoc, zLoc)
    
    @Slot()
    def _update_list_units(self):
        """Updates the list of mapping units in the combobox"""
        self._dict_mapUnit.clear()  # Clear the existing dictionary
        self._dict_mapUnit = {unit.mappingUnit_name: unit for unit in self._coorHub}
        
        self.combo_meaCoor.clear()
        self.combo_meaCoor.addItems(list(self._dict_mapUnit.keys()))
        
    @thread_assign
    def _perform_translation(self):
        """
        Runs the modification of the z-coordinates of the selected mapping coordinates
        """
    # > Retrieve the selected mapping unit from the combobox and check it <
        selected_unit_name = self.combo_meaCoor.currentText()
        if not selected_unit_name:
            qw.QMessageBox.warning(self, "Warning", "Please select a mapping unit to modify.")
            return
        
        if selected_unit_name not in self._dict_mapUnit:
            qw.QMessageBox.warning(self, "Warning", f"Mapping unit '{selected_unit_name}' not found.")
            return
        
        # Get the current mapping coordinates
        mapping_coordinates = self._dict_mapUnit[selected_unit_name]
        
        if not isinstance(mapping_coordinates, MeaCoor_mm):
            qw.QMessageBox.warning(self, "Warning", "Invalid mapping coordinates type.")
            return
        
        new_coor_mm = (self.spin_coorXUm.value()/1e3,
                    self.spin_coorYUm.value()/1e3,
                    self.spin_coorZUm.value()/1e3)
        
        print('Check if the "*" delivery works')
        self.sig_performTranslation.emit(
            mapping_coordinates,
            *self._get_reference_location(),
            new_coor_mm,
            self.chk_automove_xyonly.isChecked()
        )
        
    @Slot(MeaCoor_mm, MeaCoor_mm)
    def _handle_save_modified_coor(self, prev_meaCoor:MeaCoor_mm, modified_meaCoor:MeaCoor_mm):
        new_name = messagebox_request_input(
            parent=self,
            title="New Mapping Unit Name",
            message="Please enter a new name for the modified mapping coordinates:",
            default=f"{modified_meaCoor.mappingUnit_name}",
            validator=self._coorHub.validator_new_name,
            invalid_msg="Mapping unit name already exists. Please choose a different name.",
            loop_until_valid=True,
        )
        
        if new_name is None:
            qw.QMessageBox.warning(self, "Warning", "Modification cancelled. No new mapping unit name provided.")
            return
        
        new_mappingCoor = MeaCoor_mm(
            mappingUnit_name=new_name,
            mapping_coordinates=modified_meaCoor.mapping_coordinates
        )
        
        try: self._coorHub.append(new_mappingCoor)
        except Exception as e:
            qw.QMessageBox.warning(self, "Warning", f"Could not save modified mapping coordinates: {e}")
            return
        
        self._update_list_units()
        
        if self.rad_autoSel_lastModified.isChecked(): # Auto-select last modified mapping unit
            self.combo_meaCoor.setCurrentText(new_name)
            self.sig_update_prevCoor.emit(new_mappingCoor, *self._get_reference_location())
        elif self.rad_autoSel_next.isChecked(): # Auto-select the next mapping unit
            idx = self.combo_meaCoor.currentIndex()
            if idx + 1 < self.combo_meaCoor.count():
                self.combo_meaCoor.setCurrentIndex(idx + 1)
                next_meaCoor = self._dict_mapUnit[self.combo_meaCoor.currentText()]
                self.sig_update_prevCoor.emit(next_meaCoor, *self._get_reference_location())
            else:
                qw.QMessageBox.information(self, "Info", "Last ROI. There no next ROI to select.")
            
        # Auto-move the stage
        if self.rad_autoSel_lastModified.isChecked() and self.chk_autoMove.isChecked():
            self.sig_goto_nextMeaCoor_ref.emit(
                prev_meaCoor,
                new_mappingCoor,
                *self._get_reference_location(),
                self.chk_automove_xyonly.isChecked(),
            )
        elif self.rad_autoSel_next.isChecked() and self.chk_autoMove.isChecked():
            idx = self.combo_meaCoor.currentIndex()
            if idx + 1 < self.combo_meaCoor.count():
                next_meaCoor = self._dict_mapUnit[self.combo_meaCoor.currentText()]
                self.sig_goto_nextMeaCoor_ref.emit(
                    prev_meaCoor,
                    next_meaCoor,
                    *self._get_reference_location(),
                    self.chk_automove_xyonly.isChecked(),
                )
        
        print(f'Newly saved coordinates: {new_mappingCoor.mapping_coordinates}')
    
def test():
    from iris.gui.motion_video import generate_dummy_motion_controller
    import sys
    
    app = qw.QApplication([])
    mw = qw.QMainWindow()
    mwdg = qw.QWidget()
    mw.setCentralWidget(mwdg)
    lyt = qw.QHBoxLayout(mwdg)
    
    frm_motion = generate_dummy_motion_controller(mwdg)
    
    coorUnit1 = MeaCoor_mm(
        mappingUnit_name='Test Mapping Unit 1',
        mapping_coordinates=[
            (-0.5, -0.5, 0),
            (0.5, -0.5, 0),
            (0.5, 0.5, 0),
            (-0.5, 0.5, 0),
        ]
    )
    
    coorUnit2 = MeaCoor_mm(
        mappingUnit_name='Test Mapping Unit 2',
        mapping_coordinates=[
            (-0.5, -0.5, 1.0),
            (0.5, -0.5, 1.0),
            (0.5, 0.5, 1.0),
            (-0.5, 0.5, 1.0),
        ]
    )
    
    coorHub = List_MeaCoor_Hub()
    coorHub.append(coorUnit1)
    coorHub.append(coorUnit2)
    
    frm_coor_mod = TranslateXYZ(
        mwdg,
        mappingCoorHub=coorHub,
        motion_controller=frm_motion,
    )
    
    lyt.addWidget(frm_motion)
    lyt.addWidget(frm_coor_mod)
    
    mw.show()
    sys.exit(app.exec())
    
if __name__ == '__main__':
    test()