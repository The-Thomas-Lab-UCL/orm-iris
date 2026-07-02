"""
A GUI module to modify the z-coordinates of a mapping coordinates list.
"""

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread, QModelIndex

from enum import Enum
import threading

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.gui.motion_video import Wdg_MotionController
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.utils.general import messagebox_request_input, get_all_widgets_from_layout

from iris.resources.coordinate_modifiers.every_z_ui import Ui_every_z

class Option_NextZ(Enum):
    ORIGINAL = 'original'
    LAST = 'last'

class EveryZModifier_Worker(QObject):
    sig_error = Signal(str)
    sig_finish = Signal(str)
    sig_saveModification = Signal(MeaCoor_mm)
    sig_current_coordinate_index = Signal(str)
    sig_current_coordinate_z_mm = Signal(float)
    sig_original_coordinate_z_mm = Signal(str)
    
    msg_error_finish = "Error in modifying z-coordinates:"
    msg_error_inprogress = "Error in modifying z-coordinates (in progress):"
    msg_success_finish = "Successfully modified z-coordinates."
    msg_cancelled_finish = "Z-coordinates modification cancelled by user."
    
    _sig_gotocoor = Signal(tuple,threading.Event)
    
    def __init__(self, motion_controller:Wdg_MotionController):
        super().__init__()
        self._motion_controller = motion_controller
        self._mappingCoor:MeaCoor_mm|None = None
        self._index:int = 0
        self._last_z_mm:float|None = None
        
        self._gotoworker = self._motion_controller.get_goto_worker()
        self._sig_gotocoor.connect(self._gotoworker.work)
        
    def _emit_current_coordinate(self):
        """Emits the current coordinate index as a string"""
        if self._mappingCoor is None:
            self.sig_current_coordinate_index.emit('N/A')
            return
        
        total = len(self._mappingCoor.mapping_coordinates)
        current = self._index + 1  # 1-based index for user display
        self.sig_current_coordinate_index.emit(f'{current} of {total}')
        self.sig_original_coordinate_z_mm.emit(
            f"{self._mappingCoor.mapping_coordinates[self._index][2]*1e3:.2f} µm"
        )
        
    @Slot(MeaCoor_mm)
    def _set_mapping_coordinates(self, mapping_coordinates:MeaCoor_mm):
        """
        Runs the modification of the z-coordinates of the selected mapping coordinates
        """
        self._mappingCoor = mapping_coordinates.copy()
        self.sig_current_coordinate_z_mm.emit(self._mappingCoor.mapping_coordinates[self._index][2])
        self._emit_current_coordinate()
        
    @Slot(float)
    def _set_newZCoor_mm(self, new_z_mm:float):
        """Sets the last known z-coordinate
        """
        if self._mappingCoor is None:
            self.sig_error.emit(f"{self.msg_error_inprogress} No mapping coordinates set.")
            return
        
        new_coor_mm = self._mappingCoor.mapping_coordinates[self._index]
        new_coor_mm = (
            new_coor_mm[0],
            new_coor_mm[1],
            new_z_mm,
        )
        self._mappingCoor.mapping_coordinates[self._index] = new_coor_mm
        self._last_z_mm = new_z_mm
        
    @Slot(Option_NextZ)
    def _go_to_next_coordinate(self, option_nextZ:Option_NextZ):
        """Moves the motion controller to the next coordinate
        
        Args:
            target_coor_mm (tuple): The target coordinate to move to
        """
        self._index += 1
        
        if self._mappingCoor is None:
            self.sig_error.emit(f"{self.msg_error_inprogress} No mapping coordinates set.")
            return
        
        if self._index >= len(self._mappingCoor.mapping_coordinates):
            self._index = len(self._mappingCoor.mapping_coordinates) - 1
            self.sig_error.emit(f"{self.msg_error_inprogress} Already at the last coordinate.")
            return
        
        target_coor_mm = self._mappingCoor.mapping_coordinates[self._index]
        nextZ = target_coor_mm[2]
        if option_nextZ == Option_NextZ.LAST and isinstance(self._last_z_mm, (int,float)):
            target_coor_mm = (
                target_coor_mm[0],
                target_coor_mm[1],
                self._last_z_mm,
            )
            nextZ = self._last_z_mm
        
        try:
            reached = threading.Event()
            self._sig_gotocoor.emit(target_coor_mm, reached)
            reached.wait(10)
            if not reached.is_set(): raise TimeoutError("Motion controller did not reach target coordinate in time.")
        except Exception as e:
            self.sig_error.emit(f"{self.msg_error_inprogress} Failed to move to next coordinate: {e}")
            return
        
        self._emit_current_coordinate()
        self.sig_current_coordinate_z_mm.emit(nextZ)
        
    @Slot()
    def _go_to_prev_coordinate(self):
        if self._mappingCoor is None:
            self.sig_error.emit(f"{self.msg_error_inprogress} No mapping coordinates set.")
            return
        
        self._index -= 1
        if self._index < 0:
            self._index = 0
            self.sig_error.emit(f"{self.msg_error_inprogress} Already at the first coordinate.")
            return
        
        target_coor_mm = self._mappingCoor.mapping_coordinates[self._index]
        try:
            reached = threading.Event()
            self._sig_gotocoor.emit(target_coor_mm, reached)
            reached.wait(10)
            if not reached.is_set(): raise TimeoutError("Motion controller did not reach target coordinate in time.")
        except Exception as e:
            self.sig_error.emit(f"{self.msg_error_inprogress} Failed to move to previous coordinate: {e}")
            return
        
        self.sig_current_coordinate_z_mm.emit(self._mappingCoor.mapping_coordinates[self._index][2])
        
    @Slot(int, float)
    def _set_z_at_index(self, index: int, new_z_mm: float):
        if self._mappingCoor is None: return
        coor = self._mappingCoor.mapping_coordinates[index]
        self._mappingCoor.mapping_coordinates[index] = (coor[0], coor[1], new_z_mm)
        self._last_z_mm = new_z_mm

    @Slot()
    def _cancel_modification(self):
        """Cancels the modification process
        """
        self._mappingCoor = None
        self._index = 0
        self._last_z_mm = None
        self.sig_finish.emit(self.msg_cancelled_finish)
        
    @Slot()
    def _finish_modification(self):
        """Finishes the modification process and emits the modified mapping coordinates
        """
        if self._mappingCoor is None:
            self.sig_error.emit(f"{self.msg_error_finish} No mapping coordinates set.")
            return
        
        modified_mappingCoor = self._mappingCoor
        self._mappingCoor = None
        self._index = 0
        self._last_z_mm = None
        
        self.sig_saveModification.emit(modified_mappingCoor)
        self.sig_finish.emit(self.msg_success_finish)

class _AutofocusGotoWorker(QObject):
    _sig_gotocoor = Signal(tuple, threading.Event)
    sig_finished = Signal()

    def __init__(self, motion_controller: Wdg_MotionController):
        super().__init__()
        self._sig_gotocoor.connect(motion_controller.get_goto_worker().work)

    @Slot(tuple)
    def goto(self, coor_mm: tuple):
        event = threading.Event()
        self._sig_gotocoor.emit(coor_mm, event)
        event.wait(15)
        self.sig_finished.emit()


class EveryZ(Ui_every_z, qw.QWidget):
    msg_instructions = (
        "This module allows you to modify the z-coordinates of a mapping coordinates list.\n"
        "1. Select a mapping unit from the dropdown menu.\n"
        "2. Click 'Start modification' to start the modification process.\n"
        "3. For each coordinate, the current z-coordinate will be displayed.\n"
        "4. You can either enter a new z-coordinate manually or click 'Insert current Z-coor'.\n"
        "5. Move to the next coordinate by either enabling the 'Automove' checkbos or clicking 'Next coordinate'.\n"
        "6. You can cancel the modification process at any time by clicking 'Cancel modification'.\n"
        "7. After all coordinates have been modified or after pressing 'Finish and save modification',"
        "you will be prompted to enter a name for the new mapping unit.\n")
    
    sig_updateCombo_mappingUnits = Signal()
    sig_perform_zModification = Signal(MeaCoor_mm)
    
    sig_gotonext_coordinate = Signal(Option_NextZ)
    sig_store_coorZ_mm = Signal(float)
    sig_set_z_at_index = Signal(int, float)
    _sig_goto_autofocus = Signal(tuple)
    
    def __init__(
        self,
        parent,
        mappingCoorHub: List_MeaCoor_Hub,
        motion_controller:Wdg_MotionController,
        *args, **kwargs) -> None:
        """Initializes the mapping method
        
        Args:
            parent (qw.QWidget): The parent widget to place this widget in
            MappingCoorHub (MappingCoordinatesHub): The hub to store the resulting mapping coordinates in
            getter_MappingCoor (Callable[[], MappingCoordinates_mm]): A function to get the mapping coordinates to modify
            motion_controller (Frm_MotionController): The motion controller to use for the mapping
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
        self._coorHub = mappingCoorHub
        self._motion_controller = motion_controller
        self._active_mappingCoor: MeaCoor_mm | None = None
        
        # Button setup
        self.btn_showInstructions.clicked.connect(lambda: qw.QMessageBox.information(self, "Instructions", self.msg_instructions))
        self.btn_start.clicked.connect(self._start_modify_z_coordinates)
        self._set_enabled_modifier(enabled=False)
        
        # Params
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        
        # Initialize the worker thread for motion controller communication
        self._init_worker()
        self._init_signals()
        self.sig_updateCombo_mappingUnits.emit()
        
    def _init_worker(self):
        # Initialize the worker thread for z-coordinate modification
        self._thread_modifier = QThread()
        self._worker_modifier = EveryZModifier_Worker(self._motion_controller)
        self._worker_modifier.moveToThread(self._thread_modifier)
        
        self._worker_modifier.sig_finish.connect(self._handle_finish)
        self._worker_modifier.sig_saveModification.connect(self._handle_save_modification)
        self._worker_modifier.sig_error.connect(self._handle_error)
        
        self._worker_modifier.sig_current_coordinate_index.connect(lambda idx_str: self.lbl_coorLeft.setText(idx_str))
        self._worker_modifier.sig_current_coordinate_z_mm.connect(lambda z_mm: self.spin_newZUm.setValue(z_mm*1e3))
        self._worker_modifier.sig_original_coordinate_z_mm.connect(lambda z_str: self.lbl_prevZ.setText(z_str))
        
        self.sig_perform_zModification.connect(self._worker_modifier._set_mapping_coordinates)
        self.sig_gotonext_coordinate.connect(self._worker_modifier._go_to_next_coordinate)
        self.sig_store_coorZ_mm.connect(self._worker_modifier._set_newZCoor_mm)
        self.sig_set_z_at_index.connect(self._worker_modifier._set_z_at_index)

        self.btn_goToNext.clicked.connect(self._go_to_next_coordinate)
        self.btn_goToPrev.clicked.connect(self._worker_modifier._go_to_prev_coordinate)
        self.btn_storeZ.clicked.connect(self._store_current_z_coordinate)
        
        self.btn_cancel.clicked.connect(self._worker_modifier._cancel_modification)
        self.btn_finishAndSave.clicked.connect(self._worker_modifier._finish_modification)
        
        self._thread_modifier.start()
        self._init_autofocus()

    def _init_autofocus(self):
        self._autofocus_running = False
        self._autofocus_queue: list[int] = []
        self._autofocus_queue_pos = 0
        self._autofocus_mode = ''
        self._autofocus_results: list[str] = []

        self._autofocus_worker = self._motion_controller.get_autofocus_worker()
        self._autofocus_worker.sig_finished.connect(self._handle_autofocus_finished)
        self._autofocus_worker.sig_peak_not_in_range.connect(self._handle_autofocus_peak_not_in_range)

        self._thread_goto_af = QThread()
        self._goto_worker_af = _AutofocusGotoWorker(self._motion_controller)
        self._goto_worker_af.moveToThread(self._thread_goto_af)
        self._sig_goto_autofocus.connect(self._goto_worker_af.goto)
        self._goto_worker_af.sig_finished.connect(self._on_goto_autofocus_finished)
        self._thread_goto_af.start()

        self.tree_report.setColumnCount(4)
        self.tree_report.setHeaderLabels(['#', 'X, Y (µm)', 'Z (µm)', 'Status'])
        self.tree_report.setSelectionMode(qw.QAbstractItemView.SelectionMode.ExtendedSelection)

        self.btn_autofocusAll.clicked.connect(self._toggle_autofocus)
        self.btn_autofocusSel.clicked.connect(self._toggle_autofocus_selected)
        self.btn_AF_insertCoor.clicked.connect(self._af_insert_current_coordinate)
        self.btn_AF_next.clicked.connect(self._af_go_to_next)
        self.btn_AF_finish.clicked.connect(self._af_finish_and_save)
        self.tree_report.doubleClicked.connect(self._on_tree_report_double_click)
        self._set_enabled_autofocus_tab(False)

    def _init_signals(self):
        self.sig_updateCombo_mappingUnits.connect(self._update_list_units)
        self._coorHub.add_observer(self.sig_updateCombo_mappingUnits.emit)
        
    @Slot()
    def _update_list_units(self):
        """Updates the list of mapping units in the combobox"""
        self._dict_mapUnit.clear()  # Clear the existing dictionary
        self._dict_mapUnit = {unit.mappingUnit_name: unit for unit in self._coorHub}
        
        self.combo_mappingCoor.clear()
        self.combo_mappingCoor.addItems(list(self._dict_mapUnit.keys()))
        
    @Slot(str)
    def _handle_error(self, msg:str):
        """Handles errors from the modifier worker"""
        qw.QMessageBox.critical(self, "Error", msg)
        
    @Slot(str)
    def _handle_finish(self, msg:str):
        """Handles the finishing of the modification process"""
        if self._autofocus_running:
            self._stop_autofocus()
        self._active_mappingCoor = None
        self._set_enabled_modifier(False)
        self._set_enabled_selector(True)
        self._set_enabled_autofocus_tab(False)

        if msg.startswith(self._worker_modifier.msg_error_finish):
            qw.QMessageBox.critical(self, "Error", msg)
        elif msg.startswith(self._worker_modifier.msg_success_finish):
            qw.QMessageBox.information(self, "Success", msg)
        elif msg.startswith(self._worker_modifier.msg_cancelled_finish):
            qw.QMessageBox.information(self, "Cancelled", msg)
            
    @Slot(MeaCoor_mm)
    def _handle_save_modification(self, mapping_coor:MeaCoor_mm):
        """Handles saving the modified mapping coordinates
        
        Args:
            mapping_coor (MeaCoor_mm): The modified mapping coordinates
        """
        new_name = messagebox_request_input(
            self,
            title="New Mapping Unit Name",
            message="Enter a name for the new mapping unit:",
            default=mapping_coor.mappingUnit_name + "_modified",
            validator=self._coorHub.validator_new_name,
            invalid_msg="The name is already in use. Please enter a different name.",
            loop_until_valid=True
        )
        
        if new_name is None:
            qw.QMessageBox.warning(self, "Warning", "Modification cancelled: No name provided for new mapping unit.")
            return
        
        # Add the new mapping coordinates to the hub
        new_mapping_coor = MeaCoor_mm(new_name, mapping_coor.mapping_coordinates)
        try: self._coorHub.append(new_mapping_coor)
        except Exception as e:
            qw.QMessageBox.critical(self, "Error", f"Failed to add new mapping coordinates: {e}")
            return
        
    def _set_enabled_selector(self, enabled:bool):
        """Resets the widgets in the mapping coordinates selection frame to the given state
        Args:
            enabled (bool): The state to set the widgets to enabled or disabled. True for enabled, False for disabled.
        """
        list_widgets = get_all_widgets_from_layout(self.lyt_selector)
        
        for widget in list_widgets:
            if isinstance(widget, (qw.QPushButton, qw.QComboBox)):
                widget.setEnabled(enabled)
        
    def _set_enabled_modifier(self, enabled:bool):
        """Resets the widgets in the z-coordinates modification frame to the given state
        Args:
            enabled (bool): The state to set the widgets to enabled or disabled. True for enabled, False for disabled.
        """
        list_widgets = get_all_widgets_from_layout(self.lyt_modifications)
        
        for widget in list_widgets:
            if isinstance(widget, (qw.QPushButton, qw.QLineEdit, qw.QCheckBox, qw.QRadioButton)):
                widget.setEnabled(enabled)
        
    def _get_mapping_coordinates(self) -> MeaCoor_mm|None:
        """Retrieves the selected mapping coordinates from the combobox
        
        Returns:
            MeaCoor_mm|None: The selected mapping coordinates, or None if not found
        """
        selected_unit_name = self.combo_mappingCoor.currentText()
        if not selected_unit_name:
            qw.QMessageBox.warning(self, "Warning", "Please select a mapping unit to modify.")
            return None
        
        if selected_unit_name not in self._dict_mapUnit:
            qw.QMessageBox.critical(self, "Error", f"Mapping unit '{selected_unit_name}' not found.")
            return None
        
        mapping_coordinates = self._dict_mapUnit[selected_unit_name]
        
        if not isinstance(mapping_coordinates, MeaCoor_mm):
            qw.QMessageBox.critical(self, "Error", "Invalid mapping coordinates type.")
            return None
        
        return mapping_coordinates
        
    @Slot()
    def _start_modify_z_coordinates(self):
        """
        Runs the modification of the z-coordinates of the selected mapping coordinates
        """
        mapping_coordinate = self._get_mapping_coordinates()
        if mapping_coordinate is None: return

        self._active_mappingCoor = mapping_coordinate.copy()
        self._autofocus_results = [''] * len(self._active_mappingCoor.mapping_coordinates)
        self._update_tree_report()

        self.sig_perform_zModification.emit(mapping_coordinate)
        self._set_enabled_modifier(True)
        self._set_enabled_selector(False)
        self._set_enabled_autofocus_tab(True)
        
    @Slot()
    def _go_to_next_coordinate(self):
        """
        Moves to the next coordinate using the modifier worker
        """
        self.sig_gotonext_coordinate.emit(self._get_nextZ_option())
        
    def _get_nextZ_option(self) -> Option_NextZ:
        """Retrieves the next Z-coordinate option from the radio buttons
        
        Returns:
            Option_NextZ: The selected next Z-coordinate option
        """
        return Option_NextZ.ORIGINAL if self.rad_originalZ.isChecked() else Option_NextZ.LAST
        
    def _set_autofocus_button_state(self, running: bool):
        if running:
            if self._autofocus_mode == 'all':
                self.btn_autofocusAll.setText("Stop Autofocus")
                self.btn_autofocusSel.setEnabled(False)
            else:
                self.btn_autofocusSel.setText("Stop Autofocus")
                self.btn_autofocusAll.setEnabled(False)
        else:
            self.btn_autofocusAll.setText("Perform autofocus on all")
            self.btn_autofocusSel.setText("Perform autofocus on selected")
            self.btn_autofocusAll.setEnabled(True)
            self.btn_autofocusSel.setEnabled(True)

    def _set_enabled_autofocus_tab(self, enabled: bool):
        self.btn_autofocusAll.setEnabled(enabled)
        self.btn_autofocusSel.setEnabled(enabled)
        self.btn_AF_insertCoor.setEnabled(enabled)
        self.btn_AF_next.setEnabled(enabled)
        self.btn_AF_finish.setEnabled(enabled)
        self.spin_autofocusRange.setEnabled(enabled)

    @Slot()
    def _af_finish_and_save(self):
        if self._autofocus_running:
            self._stop_autofocus()
        self._worker_modifier._finish_modification()

    def _update_tree_report(self):
        if self._active_mappingCoor is None:
            return
        selected_rows = {self.tree_report.indexOfTopLevelItem(item)
                         for item in self.tree_report.selectedItems()}
        self.tree_report.clear()
        for i, coor in enumerate(self._active_mappingCoor.mapping_coordinates):
            x_um, y_um, z_um = coor[0] * 1e3, coor[1] * 1e3, coor[2] * 1e3
            status = self._autofocus_results[i] if i < len(self._autofocus_results) else ''
            item = qw.QTreeWidgetItem([
                str(i + 1),
                f"({x_um:.1f}, {y_um:.1f})",
                f"{z_um:.2f}",
                status,
            ])
            self.tree_report.addTopLevelItem(item)
            if i in selected_rows:
                item.setSelected(True)

    @Slot(QModelIndex)
    def _on_tree_report_double_click(self, index: QModelIndex):
        if self._active_mappingCoor is None:
            return
        row = index.row()
        if row < 0 or row >= len(self._active_mappingCoor.mapping_coordinates):
            return
        coor = self._active_mappingCoor.mapping_coordinates[row]
        self._sig_goto_autofocus.emit(tuple(coor))

    @Slot()
    def _toggle_autofocus(self):
        if self._autofocus_running:
            self._stop_autofocus()
            return

        if self._active_mappingCoor is None:
            qw.QMessageBox.warning(self, "Warning", "Please start the modification first.")
            return

        confirm = qw.QMessageBox.question(
            self, "Confirm Autofocus",
            "This will move the stage automatically and perform autofocus on all coordinates.\n"
            "CAUTION: This may move the stage to an unsafe position, such as CRASHING the objective.\n"
            "Do you want to proceed?",
            qw.QMessageBox.Yes | qw.QMessageBox.No,  # pyright: ignore[reportAttributeAccessIssue]
            qw.QMessageBox.No,  # pyright: ignore[reportAttributeAccessIssue]
        )
        if confirm != qw.QMessageBox.Yes:  # pyright: ignore[reportAttributeAccessIssue]
            return

        queue = list(range(len(self._active_mappingCoor.mapping_coordinates)))
        self._start_autofocus(queue, mode='all')

    @Slot()
    def _toggle_autofocus_selected(self):
        if self._autofocus_running:
            self._stop_autofocus()
            return

        if self._active_mappingCoor is None:
            qw.QMessageBox.warning(self, "Warning", "Please start the modification first.")
            return

        selected_items = self.tree_report.selectedItems()
        if not selected_items:
            qw.QMessageBox.warning(self, "Warning", "Please select at least one coordinate to autofocus.")
            return

        confirm = qw.QMessageBox.question(
            self, "Confirm Autofocus",
            "This will move the stage automatically and perform autofocus on the selected coordinates.\n"
            "CAUTION: This may move the stage to an unsafe position, such as CRASHING the objective.\n"
            "Do you want to proceed?",
            qw.QMessageBox.Yes | qw.QMessageBox.No,  # pyright: ignore[reportAttributeAccessIssue]
            qw.QMessageBox.No,  # pyright: ignore[reportAttributeAccessIssue]
        )
        if confirm != qw.QMessageBox.Yes:  # pyright: ignore[reportAttributeAccessIssue]
            return

        queue = sorted(self.tree_report.indexOfTopLevelItem(item) for item in selected_items)
        self._start_autofocus(queue, mode='sel')

    def _start_autofocus(self, queue: list[int], mode: str):
        self._autofocus_mode = mode
        self._autofocus_running = True
        self._autofocus_queue = queue
        self._autofocus_queue_pos = 0
        for idx in queue:
            self._autofocus_results[idx] = ''
        self._update_tree_report()
        self._set_autofocus_button_state(True)
        self._motion_controller.suppress_peak_not_found_error(True)
        self._goto_for_autofocus()

    def _goto_for_autofocus(self):
        if self._active_mappingCoor is None or \
                self._autofocus_queue_pos >= len(self._autofocus_queue):
            self._stop_autofocus()
            return
        idx = self._autofocus_queue[self._autofocus_queue_pos]
        coor = self._active_mappingCoor.mapping_coordinates[idx]
        self._sig_goto_autofocus.emit(tuple(coor))

    @Slot()
    def _on_goto_autofocus_finished(self):
        if self._autofocus_running:
            self._perform_autofocus()

    @Slot()
    def _perform_autofocus(self):
        if self._active_mappingCoor is None:
            self._stop_autofocus()
            return
        idx = self._autofocus_queue[self._autofocus_queue_pos]
        coor = self._active_mappingCoor.mapping_coordinates[idx]
        z_mm = coor[2]
        range_mm = self.spin_autofocusRange.value() / 1e3
        self._motion_controller.perform_autofocus(
            start_mm=z_mm - range_mm / 2,
            end_mm=z_mm + range_mm / 2,
            bypass_confirmation=True,
        )

    @Slot(float)
    def _handle_autofocus_finished(self, coor_z_mm: float):
        if not self._autofocus_running:
            return
        idx = self._autofocus_queue[self._autofocus_queue_pos]
        self.sig_set_z_at_index.emit(idx, coor_z_mm)
        if self._active_mappingCoor is not None:
            coor = self._active_mappingCoor.mapping_coordinates[idx]
            self._active_mappingCoor.mapping_coordinates[idx] = (coor[0], coor[1], coor_z_mm)
        self._autofocus_results[idx] = 'Found'
        self._update_tree_report()
        self._advance_autofocus()

    @Slot(str)
    def _handle_autofocus_peak_not_in_range(self, _msg: str = ''):
        if not self._autofocus_running:
            return
        idx = self._autofocus_queue[self._autofocus_queue_pos]
        self._autofocus_results[idx] = 'Not Found'
        self._update_tree_report()
        self._advance_autofocus()

    def _advance_autofocus(self):
        self._autofocus_queue_pos += 1
        if self._autofocus_queue_pos >= len(self._autofocus_queue):
            self._show_autofocus_completion_message()
            self._stop_autofocus()
            return
        self._goto_for_autofocus()

    def _show_autofocus_completion_message(self):
        queue = self._autofocus_queue
        found = sum(1 for i in queue if self._autofocus_results[i] == 'Found')
        not_found = sum(1 for i in queue if self._autofocus_results[i] == 'Not Found')
        total = len(queue)
        if self._autofocus_mode == 'all':
            scope = "all coordinates"
        elif total == 1:
            scope = "the selected coordinate"
        else:
            scope = f"the {total} selected coordinates"
        qw.QMessageBox.information(
            self, "Autofocus Complete",
            f"Autofocus completed on {scope}.\n\nFound: {found}\nNot found: {not_found}",
        )

    @Slot()
    def _af_insert_current_coordinate(self):
        if self._active_mappingCoor is None:
            return
        selected_items = self.tree_report.selectedItems()
        if not selected_items:
            qw.QMessageBox.warning(self, "Warning", "Please select a coordinate in the list.")
            return
        new_z_mm = self._motion_controller.get_coordinates_closest_mm()[2]
        if not isinstance(new_z_mm, (int, float)):
            qw.QMessageBox.warning(self, "Error", "Could not retrieve current Z coordinate from motion controller.")
            return
        for item in selected_items:
            idx = self.tree_report.indexOfTopLevelItem(item)
            self.sig_set_z_at_index.emit(idx, new_z_mm)
            coor = self._active_mappingCoor.mapping_coordinates[idx]
            self._active_mappingCoor.mapping_coordinates[idx] = (coor[0], coor[1], new_z_mm)
            self._autofocus_results[idx] = 'Manual'
        self._update_tree_report()

    @Slot()
    def _af_go_to_next(self):
        if self._active_mappingCoor is None:
            return
        n = len(self._active_mappingCoor.mapping_coordinates)
        selected_items = self.tree_report.selectedItems()
        if not selected_items:
            next_idx = 0
        else:
            last_row = max(self.tree_report.indexOfTopLevelItem(item) for item in selected_items)
            next_idx = last_row + 1
        if next_idx >= n:
            qw.QMessageBox.information(self, "Info", "Already at the last coordinate.")
            return
        self.tree_report.clearSelection()
        next_item = self.tree_report.topLevelItem(next_idx)
        if next_item is not None:
            next_item.setSelected(True)
            self.tree_report.setCurrentItem(next_item)
            self.tree_report.scrollToItem(next_item)
        coor = self._active_mappingCoor.mapping_coordinates[next_idx]
        self._sig_goto_autofocus.emit(tuple(coor))

    def _stop_autofocus(self):
        self._autofocus_running = False
        self._set_autofocus_button_state(False)
        self._motion_controller.suppress_peak_not_found_error(False)
        self._motion_controller.stop_autofocus()

    @Slot()
    def _store_current_z_coordinate(self):
        """
        Stores the current z-coordinate from the motion controller into the modifier worker
        """
        new_z_mm = self._motion_controller.get_coordinates_closest_mm()[2]
        if not isinstance(new_z_mm, (int,float)):
            qw.QMessageBox.warning(self, "Error", "Could not retrieve current Z coordinate from motion controller.")
            return
        
        self.spin_newZUm.setValue(new_z_mm*1e3)
        self.sig_store_coorZ_mm.emit(new_z_mm)
        
        if self.chk_autoNextCoor.isChecked():
            self.sig_gotonext_coordinate.emit(self._get_nextZ_option())
        
    
def test():
    from iris.gui.motion_video import generate_dummy_motion_controller
    import sys
    
    app = qw.QApplication([])
    mw = qw.QMainWindow()
    mwdg = qw.QWidget()
    mw.setCentralWidget(mwdg)
    lyt = qw.QHBoxLayout(mwdg)
    
    frm_motion = generate_dummy_motion_controller(mwdg)
    
    coorUnit = MeaCoor_mm(
        mappingUnit_name='Test Mapping Unit',
        mapping_coordinates=[(0, 0, 0), (1, 1, 1), (2, 2, 2), (3, 3, 3)]
    )
    
    coorHub = List_MeaCoor_Hub()
    coorHub.append(coorUnit)
    
    frm_coor_mod = EveryZ(
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