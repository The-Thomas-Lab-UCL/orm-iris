"""
A GUI module to modify the z-coordinates of a mapping coordinates list.
"""

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread

from typing import Literal
from enum import Enum

import numpy as np
from scipy.interpolate import griddata

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub
from iris.gui.submodules.mappingCoordinatesTreeview import Wdg_Treeview_MappingCoordinates

from iris.utils.general import messagebox_request_input

from iris.resources.coordinate_modifiers.ellipsify_ui import Ui_Ellipsify

class Ellipsify_Worker(QObject):
    sig_result = Signal(list)
    sig_finished = Signal(str)
    
    msg_success = "Ellipsify modification completed successfully."
    msg_error = "An error occurred during the Ellipsify modification: "
    
    def __init__(self):
        super().__init__()
        
    @Slot(list)
    def ellipsify_coordinates(self, list_coors:list[MeaCoor_mm]) -> None:
        """
        Converts rectangular ROIs into ellipses by adjusting the coordinates accordingly.
        
        Args:
            list_coors (list[MeaCoor_mm]): List of MeaCoor_mm objects to modify
        """
        modified_coors = []
        
        # Go through all coordinates and exclude those that are not in the ellipse
        for coor in list_coors:
            try: modified_coors.append(self._ellipsify(coor))
            except Exception as e:
                self.sig_finished.emit(self.msg_error + str(e)); return
                
        self.sig_result.emit(modified_coors)
        self.sig_finished.emit(self.msg_success)
                

    def _ellipsify(self, coor:MeaCoor_mm) -> MeaCoor_mm:
        coords = np.array(coor.mapping_coordinates)[:, :2]  # Extract x, y coordinates
        x_min, y_min = coords.min(axis=0)
        x_max, y_max = coords.max(axis=0)
        x_center = (x_min + x_max) / 2
        y_center = (y_min + y_max) / 2
        a = (x_max - x_min) / 2  # Semi-major axis
        b = (y_max - y_min) / 2  # Semi-minor axis
            
        ellipsified_coords = []
        for (x, y, z) in coor.mapping_coordinates:
                # Check if the point is inside the ellipse
            if ((x - x_center) ** 2) / (a ** 2) + ((y - y_center) ** 2) / (b ** 2) <= 1:
                ellipsified_coords.append((x, y, z))
            
        modified_coor = MeaCoor_mm(
                mappingUnit_name=coor.mappingUnit_name,
                mapping_coordinates=ellipsified_coords
            )
        
        return modified_coor

class Ellipsify(Ui_Ellipsify, qw.QWidget):
    
    _sig_req_ellipsify = Signal(list)
    
    msg_instructions = (
        "The Ellipsify modifier allows you to convert rectangular ROIs into ellipses by adjusting the coordinates accordingly.\n\n"
        "To use this modifier:\n"
        "1. Select the target ROI coordinates to modify.\n"
        "2. Click the 'Convert selected ROI into ellipses' button to perform the conversion.\n"
    )
    
    def __init__(
        self,
        parent,
        mappingCoorHub: List_MeaCoor_Hub,
        *args, **kwargs) -> None:
        """Initializes the mapping method
        
        Args:
            parent (tk.Frame): The parent frame to place this widget in
            mappingCoorHub (List_MeaCoor_Hub): The hub to store the resulting mapping coordinates in
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
        self._coorHub = mappingCoorHub
        
        self.btn_instruction.clicked.connect(lambda: qw.QMessageBox.information(
            self,
            "Instructions - Ellipsify Modifier",
            self.msg_instructions
        ))
        
        self._treeview = Wdg_Treeview_MappingCoordinates(parent=self,mappingCoorHub=self._coorHub)
        self.lyt_coorhub.addWidget(self._treeview)
        self._treeview._sig_update_tree.emit()
        
        self.btn_commit.clicked.connect(self._run_ellipsify)
        
    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        
    # >>> Others <<<
        self._init_worker_and_signals()
        
    def _init_worker_and_signals(self):
        self._thread = QThread()
        self._worker = Ellipsify_Worker()
        self._worker.moveToThread(self._thread)
        self._thread.start()
        
        self._sig_req_ellipsify.connect(self._worker.ellipsify_coordinates)
        self._worker.sig_finished.connect(self._handle_worker_finished)
        self._worker.sig_result.connect(self._handle_worker_result)
        
    @Slot(list)
    def _handle_worker_result(self, list_coors:list[MeaCoor_mm]):
        if self.chk_deleteori.isChecked():
            for coor in list_coors:
                try: self._coorHub.remove_mappingCoor(coor.mappingUnit_name)
                except KeyError: pass  # If not found, skip
        else:
            for coor in list_coors: coor.mappingUnit_name += "_ellipsified"
        
        try: self._coorHub.extend(list_coors)
        except Exception as e:
            qw.QMessageBox.warning(
                self,
                "Ellipsify Modifier - Error",
                "Failed to add modified coordinates to hub: " + str(e)
            )
        
    @Slot(str)
    def _handle_worker_finished(self, msg:str):
        if msg.startswith(Ellipsify_Worker.msg_error):
            qw.QMessageBox.critical(
                self,
                "Ellipsify Modifier - Error",
                msg
            )
        elif msg == Ellipsify_Worker.msg_success:
            qw.QMessageBox.information(
                self,
                "Ellipsify Modifier - Success",
                msg
            )
            self._treeview._sig_update_tree.emit()
        else: raise ValueError("Unknown message from worker: " + msg)
        
    @Slot()
    def _run_ellipsify(self):
        """
        Takes the selected meaCoor and send it to the worker to process
        """
        list_coors = self._treeview.get_selected_mappingCoor()
        list_coors = [coor.copy() for coor in list_coors]
        
        self._sig_req_ellipsify.emit(list_coors)
    
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
    
    frm_coor_mod = Ellipsify(
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