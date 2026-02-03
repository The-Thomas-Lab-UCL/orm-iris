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

from iris.resources.coordinate_modifiers.multiTranslatorXYZ_ui import Ui_MultiTranslatorXYZ

class MultiTranslator_Worker(QObject):
    sig_result = Signal(list)
    sig_finished = Signal(str)
    
    msg_success = "Multi-translate modification completed successfully."
    msg_error = "An error occurred during the Multi-translate modification: "
    
    def __init__(self):
        super().__init__()
        
    @Slot(list, tuple)
    def multitranslate_coordinates(self, list_coors:list[MeaCoor_mm], translation_mm:tuple[float,float,float]) -> None:
        """
        Translates ROI coordinates by specified amounts along the x, y, and z axes.
        
        Args:
            list_coors (list[MeaCoor_mm]): List of MeaCoor_mm objects to modify
            translation_mm (tuple[float,float,float]): Translation values for x, y, z axes in millimeters
        """
        modified_coors = []
        
        # Go through all coordinates and exclude those that are not in the translation
        for coor in list_coors:
            try: modified_coors.append(self._translate(coor, translation_mm))
            except Exception as e:
                self.sig_finished.emit(self.msg_error + str(e)); return
                
        self.sig_result.emit(modified_coors)
        self.sig_finished.emit(self.msg_success)
                

    def _translate(self, coor:MeaCoor_mm, translation_mm:tuple[float,float,float]) -> MeaCoor_mm:
        translated_coors = []
        for (x, y, z) in coor.mapping_coordinates:
            x_new = x + translation_mm[0]
            y_new = y + translation_mm[1]
            z_new = z + translation_mm[2]
            translated_coors.append((x_new, y_new, z_new))
            
        modified_coor = MeaCoor_mm(
                mappingUnit_name=coor.mappingUnit_name,
                mapping_coordinates=translated_coors
            )
        
        print(f"Translated {coor.mappingUnit_name} by {translation_mm} mm.")
        print(f"Original first coordinate: {coor.mapping_coordinates[0]}, Translated first coordinate: {modified_coor.mapping_coordinates[0]}")
        print(f'New coordinates: {modified_coor.mapping_coordinates[:5]}')
        
        return modified_coor

class MultiTranslatorXYZ(Ui_MultiTranslatorXYZ, qw.QWidget):
    
    _sig_req_translate = Signal(list, tuple)
    
    msg_instructions = (
        "The Multi-translate modifier allows you to translate ROI coordinates by specified amounts along the x, y, and z axes.\n\n"
        "To use this modifier:\n"
        "1. Select the target ROI coordinates to modify.\n"
        "2. Enter the translation values for x, y, and z axes.\n"
        "3. Click the 'Translate selected ROI coordinates' button to perform the translation.\n"
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
            "Instructions - Multi-translate Modifier",
            self.msg_instructions
        ))
        
        self._treeview = Wdg_Treeview_MappingCoordinates(parent=self,mappingCoorHub=self._coorHub)
        self.lyt_coorhub.addWidget(self._treeview)
        self._treeview._sig_update_tree.emit()
        
        self.btn_commit.clicked.connect(self._run_multitranslate)
        
    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        
    # >>> Others <<<
        self._init_worker_and_signals()
        
    def _init_worker_and_signals(self):
        self._thread = QThread()
        self._worker = MultiTranslator_Worker()
        self._worker.moveToThread(self._thread)
        self._thread.start()
        
        self._sig_req_translate.connect(self._worker.multitranslate_coordinates)
        self._worker.sig_finished.connect(self._handle_worker_finished)
        self._worker.sig_result.connect(self._handle_worker_result)
        
    @Slot(list)
    def _handle_worker_result(self, list_coors:list[MeaCoor_mm]):
        if self.chk_deleteori.isChecked():
            for coor in list_coors:
                try: self._coorHub.remove_mappingCoor(coor.mappingUnit_name)
                except KeyError: pass  # If not found, skip
        else:
            for coor in list_coors: coor.mappingUnit_name += "_translated"
        
        try: self._coorHub.extend(list_coors)
        except Exception as e:
            qw.QMessageBox.warning(
                self,
                "Multi-translate Modifier - Error",
                "Failed to add modified coordinates to hub: " + str(e)
            )
        
    @Slot(str)
    def _handle_worker_finished(self, msg:str):
        if msg.startswith(MultiTranslator_Worker.msg_error):
            qw.QMessageBox.critical(
                self,
                "Multi-translate Modifier - Error",
                msg
            )
        elif msg == MultiTranslator_Worker.msg_success:
            qw.QMessageBox.information(
                self,
                "Multi-translate Modifier - Success",
                msg
            )
            self._treeview._sig_update_tree.emit()
        else: raise ValueError("Unknown message from worker: " + msg)
        
    @Slot()
    def _run_multitranslate(self):
        """
        Takes the selected meaCoor and send it to the worker to process
        """
        trans_x_mm = self.spin_x_um.value()/1e3
        trans_y_mm = self.spin_y_um.value()/1e3
        trans_z_mm = self.spin_z_um.value()/1e3
        
        list_coors = self._treeview.get_selected_mappingCoor()
        list_coors = [coor.copy() for coor in list_coors]
        
        self._sig_req_translate.emit(list_coors, (trans_x_mm, trans_y_mm, trans_z_mm))
    
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
    
    frm_coor_mod = MultiTranslatorXYZ(
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