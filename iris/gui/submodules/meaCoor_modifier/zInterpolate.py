"""
A GUI module to modify the z-coordinates of a mapping coordinates list.
"""

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer, QCoreApplication

from typing import Literal
from enum import Enum
import threading

import numpy as np
from scipy.interpolate import griddata

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.gui.motion_video import Wdg_MotionController
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.utils.general import *

from iris.resources.coordinate_modifiers.zInterpolate_ui import Ui_zInterpolate

class Option_InterpolationMethod(Enum):
    LINEAR = 'linear'
    NEAREST = 'nearest'
    CUBIC = 'cubic'

class Interpolator_Worker(QObject):
    sig_finished = Signal(str)
    sig_saveModification = Signal(MeaCoor_mm)
    
    msg_error = 'Error during interpolation: \n'
    msg_success = 'Z-coordinate interpolation and modification completed successfully.'
    msg_partial_success = 'Z-coordinate interpolation completed with some warnings: \n'
    
    def __init__(self):
        super().__init__()
        
    def _interpolate_z_values(self,list_coor:list,list_ref:list,method:Option_InterpolationMethod,
                              skip_nan:bool=True) -> list[tuple[float, float, float]]:
        """
        Interpolates the z-values of the given coordinates based on the reference coordinates.
        
        Args:
            list_coor (list): List of coordinates to interpolate, each coordinate is a list of [X, Y].
            list_ref (list): List of reference coordinates, each coordinate is a list of [X, Y, Z].
            method (Option_InterpolationMethod): Interpolation method to use.
            skip_nan (bool): If True, skips NaN values in the interpolation result.
        
        Returns:
            list: List of interpolated coordinates with z-values, each coordinate is a list of [X, Y, Z].
        """
        points = np.array(list_ref)[:, :2]  # X, Y coordinates from list_ref
        values = np.array(list_ref)[:, 2]   # Z values from list_ref
        xi = np.array(list_coor)[:, :2]     # X, Y coordinates for which to interpolate
        
        interpolated_z = griddata(points, values, xi, method=method.value)
        
        list_coor_interpolated = []
        for i in range(len(list_coor)):
            if np.isnan(interpolated_z[i]) and skip_nan:
                print(f"Warning: Interpolated z-value for {list_coor[i]} is NaN, skipping.")
                continue
            list_coor_interpolated.append((list_coor[i][0], list_coor[i][1], interpolated_z[i]))
            
        return list_coor_interpolated
    
    @Slot(MeaCoor_mm, MeaCoor_mm, Option_InterpolationMethod)
    def _run_modify_z_coordinates(self, meaCoorTarget:MeaCoor_mm, meaCoorRef:MeaCoor_mm,
                                  method:Option_InterpolationMethod):
        """
        Runs the modification of the z-coordinates of the selected mapping coordinates
        
        Args:
            meaCoorTarget (MeaCoor_mm): The mapping coordinates to modify
            meaCoorRef (MeaCoor_mm): The reference mapping coordinates
            method (Option_InterpolationMethod): The interpolation method to use
        """
    # > Modify the z-coordinates <
        list_coor_tgt = meaCoorTarget.mapping_coordinates.copy()
        list_coor_ref = meaCoorRef.mapping_coordinates.copy()
        
        # try:
        list_coor_interp = self._interpolate_z_values(
            list_coor=list_coor_tgt,
            list_ref=list_coor_ref,
            method=method,
            skip_nan=True
        )
        
        modified_coor = MeaCoor_mm(meaCoorTarget.mappingUnit_name + "_zInterpolated", list_coor_interp)
        
        if len(list_coor_interp) == 0:
            self.sig_finished.emit(self.msg_error + "No valid coordinates were interpolated. Please check the reference coordinates.")
        if len(list_coor_interp) != len(list_coor_tgt):
            self.sig_finished.emit(self.msg_partial_success + 
                                   "Some coordinates could not be calculated due to them being outside the reference range.\n"
                                   "Only the valid coordinates have been modified.")
            self.sig_saveModification.emit(modified_coor)
        else:
            self.sig_finished.emit(self.msg_success)
            self.sig_saveModification.emit(modified_coor)

class ZInterpolate(Ui_zInterpolate, qw.QWidget):
    
    msg_instructions = (
        "The Z-Coordinate Interpolation Modifier allows you to modify the z-coordinates of a selected mapping coordinates unit "
        "based on the z-coordinates of a reference mapping coordinates unit using interpolation methods.\n\n"
        "Instructions:\n"
        "1. Select the mapping coordinates unit you want to modify from the 'Select the mapping coordinates to modify' dropdown.\n"
        "2. Select the reference mapping coordinates unit from the 'Select the mapping coordinates reference' dropdown.\n"
        "3. Choose the interpolation method (linear, nearest, or cubic) from the 'Interpolation method' dropdown.\n"
        "4. Click the 'Modify Z-coordinates' button to perform the interpolation and modify the z-coordinates.\n"
        "5. You will be prompted to enter a new name for the modified mapping coordinates unit. Enter a unique name and click OK.\n"
        "6. The modified mapping coordinates unit will be added to the hub with the new name.\n\n"
        "Note: Ensure that the reference mapping coordinates unit has valid z-coordinates for accurate interpolation."
    )
    
    sig_updateListUnits = Signal()
    sig_performInterpolation = Signal(MeaCoor_mm, MeaCoor_mm, Option_InterpolationMethod)
    
    def __init__(
        self,
        parent,
        mappingCoorHub: List_MeaCoor_Hub,
        *args, **kwargs) -> None:
        """Initializes the mapping method
        
        Args:
            parent (tk.Frame): The parent frame to place this widget in
            MappingCoorHub (MappingCoordinatesHub): The hub to store the resulting mapping coordinates in
            getter_MappingCoor (Callable[[], MappingCoordinates_mm]): A function to get the mapping coordinates to modify
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
        self._coorHub = mappingCoorHub
        
        self.btn_instruction.clicked.connect(lambda: qw.QMessageBox.information(
            self,
            "Z-Coordinate Interpolation Modifier Instructions",
            self.msg_instructions
        ))
        
        self.btn_performInterp.clicked.connect(self._run_modify_z_coordinates)
        
    # >>> Parameter widgets <<<
        self.combo_interpMethod.addItems([method.value for method in Option_InterpolationMethod])
        
    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        
    # >>> Others <<<
        self._init_worker_and_signals()
        
    def _init_worker_and_signals(self):
        self.sig_updateListUnits.connect(self._update_list_units)
        self._coorHub.add_observer(self.sig_updateListUnits.emit)
        self.sig_updateListUnits.emit()
        
        # Signal to perform the interpolation
        self._thread_interp = QThread()
        self._worker_interp = Interpolator_Worker()
        self._worker_interp.moveToThread(self._thread_interp)
        
        self._worker_interp.sig_finished.connect(self._handle_finished_interpolation)
        self._worker_interp.sig_saveModification.connect(self._handle_store_modification)
        
        self.sig_performInterpolation.connect(self._worker_interp._run_modify_z_coordinates)
        
        self.destroyed.connect(self._thread_interp.quit)
        self.destroyed.connect(self._worker_interp.deleteLater)
        self.destroyed.connect(self._thread_interp.deleteLater)
        self._thread_interp.start()
        
    @Slot()
    def _update_list_units(self):
        """Updates the list of mapping units in the combobox"""
        self._dict_mapUnit.clear()  # Clear the existing dictionary
        self._dict_mapUnit = {unit.mappingUnit_name: unit for unit in self._coorHub}
        
        self.combo_target.clear()
        self.combo_reference.clear()
        
        self.combo_target.addItems(list(self._dict_mapUnit.keys()))
        self.combo_reference.addItems(list(self._dict_mapUnit.keys()))
        
    @Slot(MeaCoor_mm)
    def _handle_store_modification(self, mapping_coor:MeaCoor_mm):
        """Handles the saving of the modified mapping coordinates
        
        Args:
            mapping_coor (MeaCoor_mm): The modified mapping coordinates
        """
        # Prompt for new name
        new_name = messagebox_request_input(
            self,
            title="New Mapping Unit Name",
            message="Enter a name for the new mapping unit:",
            default=mapping_coor.mappingUnit_name,
            validator=self._coorHub.validator_new_name,
            invalid_msg="The name is already in use. Please enter a different name.",
            loop_until_valid=True
        )
        
        if not new_name:
            qw.QMessageBox.warning(self, "Warning", "Modification cancelled: No name provided for new mapping unit.")
            return
        
        # Add the new mapping coordinates to the hub
        new_mapping_coor = MeaCoor_mm(new_name, mapping_coor.mapping_coordinates)
        try: self._coorHub.append(new_mapping_coor)
        except ValueError as e:
            qw.QMessageBox.critical(self, "Error", str(e))
            
        # print(f'Modified mapping coordinates saved as "{new_name}".')
        # print(f'Number of coordinates: {len(new_mapping_coor.mapping_coordinates)}')
        # print(f'First 5 coordinates: {new_mapping_coor.mapping_coordinates[:5]}')
        
    @Slot(str)
    def _handle_finished_interpolation(self,msg:str):
        """Handles the finished signal from the interpolation worker
        
        Args:
            msg (str): The message to display
        """
        if msg.startswith(self._worker_interp.msg_error):
            qw.QMessageBox.warning(self, "Interpolation Error", msg)
        elif msg.startswith(self._worker_interp.msg_partial_success):
            qw.QMessageBox.warning(self, "Interpolation Partial Success", msg)
        else:
            qw.QMessageBox.information(self, "Interpolation Success", msg)
            
        self.btn_performInterp.setEnabled(True)
        
    def _interpolate_z_values(self,list_coor:list,list_ref:list,method:Literal['linear','nearest','cubic'],
                              skip_nan:bool=True) -> list[tuple[float, float, float]]:
        """
        Interpolates the z-values of the given coordinates based on the reference coordinates.
        
        Args:
            list_coor (list): List of coordinates to interpolate, each coordinate is a list of [X, Y].
            list_ref (list): List of reference coordinates, each coordinate is a list of [X, Y, Z].
            method (Literal['linear','nearest','cubic']): Interpolation method to use.
            skip_nan (bool): If True, skips NaN values in the interpolation result.
        
        Returns:
            list: List of interpolated coordinates with z-values, each coordinate is a list of [X, Y, Z].
        """
        points = np.array(list_ref)[:, :2]  # X, Y coordinates from list_ref
        values = np.array(list_ref)[:, 2]   # Z values from list_ref
        xi = np.array(list_coor)[:, :2]     # X, Y coordinates for which to interpolate
        
        interpolated_z = griddata(points, values, xi, method=method)
        
        list_coor_interpolated = []
        for i in range(len(list_coor)):
            if np.isnan(interpolated_z[i]) and skip_nan:
                print(f"Warning: Interpolated z-value for {list_coor[i]} is NaN, skipping.")
                continue
            list_coor_interpolated.append((list_coor[i][0], list_coor[i][1], interpolated_z[i]))
            
        return list_coor_interpolated
        
    @Slot()
    def _run_modify_z_coordinates(self):
        """
        Runs the modification of the z-coordinates of the selected mapping coordinates
        """
    # > Retrieve the selected mapping unit from the combobox and check it <
        sel_unitName_tgt = self.combo_target.currentText()
        sel_unitName_ref = self.combo_reference.currentText()
        
        if not sel_unitName_tgt or not sel_unitName_ref:
            qw.QMessageBox.warning(self, "Warning", "Please select both target and reference mapping units.")
            return
        
        if sel_unitName_ref == sel_unitName_tgt:
            qw.QMessageBox.warning(self, "Warning", "Target and reference mapping units must be different.")
            return
        
        if sel_unitName_tgt not in self._dict_mapUnit or sel_unitName_ref not in self._dict_mapUnit:
            qw.QMessageBox.warning(self, "Error", f"Mapping unit '{sel_unitName_tgt}' not found.")
            return
        
        # Get the current mapping coordinates
        mapCoor_source = self._dict_mapUnit[sel_unitName_tgt]
        mapCoor_ref = self._dict_mapUnit[sel_unitName_ref]
        
        if not isinstance(mapCoor_source, MeaCoor_mm) or not isinstance(mapCoor_ref, MeaCoor_mm):
            qw.QMessageBox.critical(self, "Error", "Invalid mapping coordinates type.")
            return
        
        approx_method = Option_InterpolationMethod(self.combo_interpMethod.currentText())
        
        self.btn_performInterp.setEnabled(False)
        self.sig_performInterpolation.emit(mapCoor_source, mapCoor_ref, approx_method)
    
def test():
    from iris.gui.motion_video import generate_dummy_motion_controller
    import sys
    
    app = qw.QApplication([])
    mw = qw.QMainWindow()
    mwdg = qw.QWidget()
    mw.setCentralWidget(mwdg)
    lyt = qw.QHBoxLayout(mwdg)
    
    frm_motion = generate_dummy_motion_controller(mwdg)
    
    coorUnit_ref = MeaCoor_mm(
        mappingUnit_name='Reference MeaCoor',
        mapping_coordinates=[(0, 0, 0), (0, 2, 1), (2, 0, 2), (2, 2, 3)]
    )
    coorUnit_tgt = MeaCoor_mm(
        mappingUnit_name='Target MeaCoor',
        mapping_coordinates=[(-0.5, -0.5, 0), (0.5, -0.5, 0), (1.5, -0.5, 0),
                             (-0.5, 0.5, 0), (0.5, 0.5, 0), (1.5, 0.5, 0),
                             (-0.5, 1.5, 0), (0.5, 1.5, 0), (1.5, 1.5, 0)]
    )
    
    coorHub = List_MeaCoor_Hub()
    coorHub.append(coorUnit_tgt)
    coorHub.append(coorUnit_ref)
    
    frm_coor_mod = ZInterpolate(
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