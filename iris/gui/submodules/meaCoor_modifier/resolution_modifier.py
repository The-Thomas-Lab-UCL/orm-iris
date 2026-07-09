"""
A GUI module to modify a mapping coordinates list by regenerating the coordinates
within the boundary of the selected ROI(s) at a given x/y resolution.
"""
import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread

import numpy as np
from scipy.spatial import ConvexHull, QhullError
from matplotlib.path import Path as MplPath

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub
from iris.gui.submodules.mappingCoordinatesTreeview import Wdg_Treeview_MappingCoordinates

from iris.resources.coordinate_modifiers.resolution_modifier_ui import Ui_ResolutionModifier

class ResolutionModifier_Worker(QObject):
    sig_result = Signal(list)
    sig_finished = Signal(str)

    msg_success = "Resolution modification completed successfully."
    msg_error = "An error occurred during the Resolution modification: "

    def __init__(self):
        super().__init__()

    @Slot(list, float, float)
    def resolutionmodify_coordinates(self, list_coors:list[MeaCoor_mm], res_x_mm:float, res_y_mm:float) -> None:
        """
        Regenerates ROI coordinates on a rectilinear grid at the given x/y resolution,
        confined to the boundary of each ROI's original coordinates.

        Args:
            list_coors (list[MeaCoor_mm]): List of MeaCoor_mm objects to modify
            res_x_mm (float): Grid spacing along the x-axis in millimeters
            res_y_mm (float): Grid spacing along the y-axis in millimeters
        """
        modified_coors = []

        for coor in list_coors:
            try: modified_coors.append(self._regenerate(coor, res_x_mm, res_y_mm))
            except Exception as e:
                self.sig_finished.emit(self.msg_error + str(e)); return

        self.sig_result.emit(modified_coors)
        self.sig_finished.emit(self.msg_success)

    def _regenerate(self, coor:MeaCoor_mm, res_x_mm:float, res_y_mm:float) -> MeaCoor_mm:
        pts = np.array(coor.mapping_coordinates)
        xy = pts[:, :2]
        z_mm = float(np.mean(pts[:, 2]))

        if len(xy) < 3:
            raise ValueError(f"'{coor.mappingUnit_name}' needs at least 3 coordinates to determine a boundary")

        boundary = self._get_boundary(xy)
        polygon = MplPath(boundary)

        x_min, y_min = boundary.min(axis=0)
        x_max, y_max = boundary.max(axis=0)

        xs = np.arange(x_min, x_max + res_x_mm, res_x_mm)
        ys = np.arange(y_min, y_max + res_y_mm, res_y_mm)
        xx, yy = np.meshgrid(xs, ys)
        candidates = np.column_stack([xx.ravel(), yy.ravel()])
        inside = polygon.contains_points(candidates)
        grid_pts = candidates[inside]

        if len(grid_pts) == 0:
            raise ValueError(f"No coordinates could be generated for '{coor.mappingUnit_name}' with the given resolution")

        new_coordinates = [(float(x), float(y), z_mm) for x, y in grid_pts]

        modified_coor = MeaCoor_mm(
                mappingUnit_name=coor.mappingUnit_name,
                mapping_coordinates=new_coordinates
            )

        return modified_coor

    @staticmethod
    def _get_boundary(xy:np.ndarray) -> np.ndarray:
        """
        Returns the boundary polygon vertices enclosing the given points: the convex
        hull, or the bounding-box rectangle if the points are degenerate (e.g. collinear).

        Args:
            xy (np.ndarray): Array of shape (N, 2) of the x, y coordinates

        Returns:
            np.ndarray: Array of shape (M, 2) of the boundary polygon vertices, in order
        """
        try:
            hull = ConvexHull(xy)
            return xy[hull.vertices]
        except QhullError:
            x_min, y_min = xy.min(axis=0)
            x_max, y_max = xy.max(axis=0)
            return np.array([[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]])

class ResolutionModifier(Ui_ResolutionModifier, qw.QWidget):

    _sig_req_resmodify = Signal(list, float, float)

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

        self._coorHub = mappingCoorHub

        self._treeview = Wdg_Treeview_MappingCoordinates(parent=self,mappingCoorHub=self._coorHub)
        self.lyt_coorHub.addWidget(self._treeview)
        self._treeview._sig_update_tree.emit()

        self.btn_commit.clicked.connect(self._run_resolutionmodify)

    # >>> Others <<<
        self._init_worker_and_signals()

    def _init_worker_and_signals(self):
        self._thread = QThread()
        self._worker = ResolutionModifier_Worker()
        self._worker.moveToThread(self._thread)
        self._thread.start()

        self._sig_req_resmodify.connect(self._worker.resolutionmodify_coordinates)
        self._worker.sig_finished.connect(self._handle_worker_finished)
        self._worker.sig_result.connect(self._handle_worker_result)

    @Slot(list)
    def _handle_worker_result(self, list_coors:list[MeaCoor_mm]):
        if self.chk_deleteOri.isChecked():
            for coor in list_coors:
                try: self._coorHub.remove_mappingCoor(coor.mappingUnit_name)
                except KeyError: pass  # If not found, skip
        else:
            for coor in list_coors: coor.mappingUnit_name += "_resampled"

        try: self._coorHub.extend(list_coors)
        except Exception as e:
            qw.QMessageBox.warning(
                self,
                "Resolution Modifier - Error",
                "Failed to add modified coordinates to hub: " + str(e)
            )

    @Slot(str)
    def _handle_worker_finished(self, msg:str):
        if msg.startswith(ResolutionModifier_Worker.msg_error):
            qw.QMessageBox.critical(
                self,
                "Resolution Modifier - Error",
                msg
            )
        elif msg == ResolutionModifier_Worker.msg_success:
            qw.QMessageBox.information(
                self,
                "Resolution Modifier - Success",
                msg
            )
            self._treeview._sig_update_tree.emit()
        else: raise ValueError("Unknown message from worker: " + msg)

    @Slot()
    def _run_resolutionmodify(self):
        """
        Takes the selected meaCoor and sends it to the worker to regenerate at the
        requested resolution
        """
        res_x_mm = self.spin_xresUm.value()/1e3
        res_y_mm = self.spin_yresUm.value()/1e3

        if res_x_mm <= 0 or res_y_mm <= 0:
            qw.QMessageBox.warning(self, "Resolution Modifier - Error", "Please enter positive x- and y-resolutions.")
            return

        list_coors = self._treeview.get_selected_mappingCoor()
        if not list_coors:
            qw.QMessageBox.information(self, "No selection", "No mapping coordinates have been selected.")
            return
        list_coors = [coor.copy() for coor in list_coors]

        self._sig_req_resmodify.emit(list_coors, res_x_mm, res_y_mm)

def test():
    import sys

    app = qw.QApplication([])
    mw = qw.QMainWindow()
    mwdg = qw.QWidget()
    mw.setCentralWidget(mwdg)
    lyt = qw.QHBoxLayout(mwdg)

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

    frm_coor_mod = ResolutionModifier(
        mwdg,
        mappingCoorHub=coorHub,
    )
    lyt.addWidget(frm_coor_mod)

    mw.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    test()
