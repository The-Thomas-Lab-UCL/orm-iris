"""
A GUI to visualize the topology of a mapping coordinates
"""
import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer, QCoreApplication

from typing import Literal

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.colorbar import Colorbar
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub
from iris.utils.general import *

from iris.gui import AppPlotEnum

from iris.resources.coordinate_modifiers.topology_visuliser_ui import Ui_topology_visualiser

class MeaCoorTopologyPlotter_Worker(QObject):
    sig_draw = Signal() # Signal to trigger canvas redraw
    
    def __init__(self, fig:Figure, ax:Axes, cbar:Colorbar|None):
        super().__init__()
        self._fig = fig
        self._ax = ax
        self._cbar = cbar
        
    @Slot(MeaCoor_mm, bool)
    def plot(self, mapping_coordinates:MeaCoor_mm, show_edges:bool):
        fig = self._fig
        ax = self._ax
        cbar = self._cbar
        
        try:
            if isinstance(cbar, Colorbar): cbar.remove()
        except: pass
        try: ax.clear()
        except: pass
        
        # Plot the coordinates
        x, y, z = zip(*mapping_coordinates.mapping_coordinates)
        ax.tripcolor(
            x, y, z,
            cmap=AppPlotEnum.PLT_COLOUR_MAP.value,
            shading=AppPlotEnum.PLT_SHADING.value,
            edgecolors='k' if show_edges else 'none',
            vmin=min(z),
            vmax=max(z),
        )
        
        ax.set_aspect('equal', adjustable='box')
        ax.set_title(f"Topology of {mapping_coordinates.mappingUnit_name} [mm]")
        ax.set_xlabel('X Coordinate (mm)')
        ax.set_ylabel('Y Coordinate (mm)')
        cbar = fig.colorbar(ax.collections[0], ax=ax)
        cbar.set_label('Z Coordinate (mm)', rotation=270, labelpad=15)
        
        self._cbar = cbar
        
        fig.tight_layout()
        
        # Redraw the canvas
        self.sig_draw.emit()

class TopologyVisualiser(Ui_topology_visualiser, qw.QWidget):
    msg_instructions = (
        "This module allows you to visualise the topology of mapping coordinates stored in the MeaCoor Hub.\n"
        "To use this module:\n"
        "1. Select the mapping coordinates unit from the dropdown menu.\n"
        "2. Adjust the plot parameters as desired (e.g., show/hide edges).\n"
        "3. The topology will be displayed in the plot area.\n\n"
        "Note: The colour of the plot represents the Z-coordinate values of the mapping coordinates."
    )
    
    sig_updateListUnits = Signal()
    sig_req_plotTopo = Signal(MeaCoor_mm, bool) # Signal to request topology plotting
    
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
        
    # >>> Information widget <<<
        self.btn_instructions.clicked.connect(lambda: qw.QMessageBox.information(
            self,
            "Instructions",
            self.msg_instructions
        ))
        
    # >>> Plotting parameters and widget <<<
        self._figsize_pxl = AppPlotEnum.PLT_MAP_SIZE_PIXEL.value
        self._dpi = plt.rcParams['figure.dpi']
        self._figsize_in = (self._figsize_pxl[1]/self._dpi,self._figsize_pxl[0]/self._dpi)
        self._fig, self._ax = plt.subplots(figsize=self._figsize_in)
        
        self._plt_canvas = FigureCanvas(self._fig)
        self.lyt_plot.addWidget(self._plt_canvas)
        self._plt_canvas.draw()
        
        # Typehinting
        self._fig: Figure
        self._ax: Axes
        self._cbar: Colorbar|None = None
        
    # >>> Selection widget <<<
        self.combo_meaCoor.activated.connect(self._show_topology)
        self.chk_edges.clicked.connect(self._show_topology)
        
    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        
    # >>> Others <<<
        self.sig_updateListUnits.connect(self._update_list_units)
        self._coorHub.add_observer(self.sig_updateListUnits.emit)
        self.sig_updateListUnits.emit()
        
        self._init_worker()
        
    def _init_worker(self):
        """
        Initialises the worker thread for plotting the topology
        """
        self._thread_plotter = QThread()
        
        self._worker_plotter = MeaCoorTopologyPlotter_Worker(
            fig=self._fig,
            ax=self._ax,
            cbar=self._cbar,
        )
        self._worker_plotter.moveToThread(self._thread_plotter)
        
        self.sig_updateListUnits.connect(self._update_list_units)
        self.sig_updateListUnits.emit()
        
        self.sig_req_plotTopo.connect(self._worker_plotter.plot)
        self._worker_plotter.sig_draw.connect(self._plt_canvas.draw)
        
        self.destroyed.connect(self._worker_plotter.deleteLater)
        self.destroyed.connect(self._thread_plotter.quit)
        
        self._thread_plotter.start()
        
    @Slot()
    def _update_list_units(self):
        """Updates the list of mapping units in the combobox"""
        self._dict_mapUnit.clear()  # Clear the existing dictionary
        self._dict_mapUnit = {unit.mappingUnit_name: unit for unit in self._coorHub}
        
        self.combo_meaCoor.clear()
        self.combo_meaCoor.addItems(list(self._dict_mapUnit.keys()))
        
    @Slot()
    def _show_topology(self):
        """Shows the topology of the selected mapping coordinates"""
        selected_unit_name = self.combo_meaCoor.currentText()
        
        if not selected_unit_name or selected_unit_name not in self._dict_mapUnit:
            qw.QMessageBox.warning(self, "Warning", "No mapping unit selected or unit not found.")
            return
        
        selected_unit = self._dict_mapUnit.get(selected_unit_name)
        if not selected_unit:
            qw.QMessageBox.warning(self, "Warning", f"Mapping unit '{selected_unit_name}' not found.")
            return
        
        if len(selected_unit.mapping_coordinates) < 2:
            qw.QMessageBox.warning(self, "Warning", "Not enough coordinates to plot topology. Please select a unit with at least 2 coordinates.")
            return
        
        show_edges = self.chk_edges.isChecked()
        self.sig_req_plotTopo.emit(selected_unit, show_edges)
        
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
        mapping_coordinates=[
            (0, 0, 0),
            (1, 0, 1),
            (2, 0, 2),
            (0, 1, 1),
            (1, 1, 2),
            (2, 1, 3),
            (0, 2, 2),
            (1, 2, 3),
            (2, 2, 4),
        ]
    )
    
    coorHub = List_MeaCoor_Hub()
    coorHub.append(coorUnit)
    
    frm_coor_mod = TopologyVisualiser(
        mwdg,
        mappingCoorHub=coorHub,
        motion_controller=frm_motion,
    )
    lyt.addWidget(frm_coor_mod)
    
    mw.show()
    sys.exit(app.exec())
    
if __name__ == '__main__':
    test()