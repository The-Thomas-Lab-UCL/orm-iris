import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot

import numpy as np


if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.gui.motion_video import Wdg_MotionController

from iris.resources.coordinate_generators.rect_aroundcentre_ui import Ui_meaCoor_Rect_StartEnd

class Rect_AroundCentre(Ui_meaCoor_Rect_StartEnd, qw.QWidget):
    """A basic class that manage a mapping method

    Args:
        tk (tkinter): tkinter library
    """
    sig_updateResPt = Signal()
    sig_updateResUm = Signal()
    sig_error = Signal(str)
    
    msg_error = 'Error: '
    
    def __init__(self,parent:qw.QWidget,motion_controller:Wdg_MotionController,
                 *args, **kwargs) -> None:
        # Place itself in the given master frame (container)
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
        # Sets up the other controllers
        self._motion_controller = motion_controller
        
        # Make the widgets to store the coordinates
        self.btn_storecentre.clicked.connect(self._store_current_coor_center)
        self.btn_storez.clicked.connect(self._store_current_coorz)
        
        self._init_signals()

    def _init_signals(self):
        self.spin_centrex.valueChanged.connect(self._update_resolution_pt)
        self.spin_centrey.valueChanged.connect(self._update_resolution_pt)
        self.spin_widx.valueChanged.connect(self._update_resolution_pt)
        self.spin_heiy.valueChanged.connect(self._update_resolution_pt)
        
        self.spin_resxpt.valueChanged.connect(self._update_resolution_um)
        self.spin_resypt.valueChanged.connect(self._update_resolution_um)
        self.spin_resxum.valueChanged.connect(self._update_resolution_pt)
        self.spin_resyum.valueChanged.connect(self._update_resolution_pt)

    def get_mapping_coordinates_mm(self) -> list[tuple[float,float,float]]|None:
        """ 
        Returns the mapping coordinates
        
        Returns:
            list: List of tuple (x,y,z) coordinates
        """
        # Define the grid boundaries
        centre_x = self.spin_centrex.value()/1e3
        centre_y = self.spin_centrey.value()/1e3
        dist_x = self.spin_widx.value()/1e3/2
        dist_y = self.spin_heiy.value()/1e3/2
        
        x_min = centre_x - dist_x
        y_min = centre_y - dist_y
        x_max = centre_x + dist_x
        y_max = centre_y + dist_y
        z_const = self.spin_z.value()/1e3  # Convert from um to mm

        # Number of points in each direction
        num_pointsx = self.spin_resxpt.value()
        num_pointsy = self.spin_resypt.value()

        # Generate linearly spaced points along each axis
        x_points = np.linspace(x_min, x_max, num_pointsx)
        y_points = np.linspace(y_min, y_max, num_pointsy)

        # Create the grid
        X, Y = np.meshgrid(x_points, y_points)
        return [(x, y, z_const) for x, y in zip(X.flatten(), Y.flatten())]
    
    @Slot()
    def _store_current_coorz(self):
        """
        Gets the current stage coordinate and store it as the initial position
        """
        try:
            coor_z_mm = self._motion_controller.get_coordinates_closest_mm()[2]
            if not isinstance(coor_z_mm,float): raise ValueError('Z coordinate is not a float')
        except Exception as e:
            print(e)
            self.sig_error.emit(self.msg_error + str(e))
            return
        
        self.spin_z.setValue(coor_z_mm*1e3)
    
    @Slot()
    def _store_current_coor_center(self):
        """
        Gets the current stage coordinate and store it as the initial position
        """
        try:
            # Get the current coordinates from the device
            coor_x_mm,coor_y_mm = self._motion_controller.get_coordinates_closest_mm()[:2]
            if not isinstance(coor_x_mm,float) or not isinstance(coor_y_mm,float):
                raise ValueError('X or Y coordinate is not a float')
        except Exception as e:
            print(e)
            self.sig_error.emit(self.msg_error + str(e))
            return
        
        self.spin_centrex.setValue(coor_x_mm*1e3)
        self.spin_centrey.setValue(coor_y_mm*1e3)
        
    def _block_signals_resolution(self,block:bool):
        """
        Blocks or unblocks the resolution spinbox signals
        
        Args:
            block (bool): True to block, False to unblock
        """
        self.spin_resxpt.blockSignals(block)
        self.spin_resypt.blockSignals(block)
        self.spin_resxum.blockSignals(block)
        self.spin_resyum.blockSignals(block)
        
    @Slot()
    def _update_resolution_um(self):
        """
        Updates the um resolution entry based on the other entries
        """
        self._block_signals_resolution(True)
        
        dist_x = self.spin_widx.value()
        dist_y = self.spin_heiy.value()
        
        points_x = self.spin_resxpt.value()
        points_y = self.spin_resypt.value()
        
        resUm_x = dist_x/(points_x-1) if points_x>1 else 0
        resUm_y = dist_y/(points_y-1) if points_y>1 else 0
        
        self.spin_resxum.setValue(resUm_x)
        self.spin_resyum.setValue(resUm_y)
        
        self._block_signals_resolution(False)
        
    @Slot()
    def _update_resolution_pt(self):
        """
        Updates the point resolution entry based on the other entries
        """
        self._block_signals_resolution(True)
        
        dist_x = self.spin_widx.value()
        dist_y = self.spin_heiy.value()
        
        resUm_x = self.spin_resxum.value()
        resUm_y = self.spin_resyum.value()
        
        points_x = int(dist_x/resUm_x)+1 if resUm_x>0 else 1
        points_y = int(dist_y/resUm_y)+1 if resUm_y>0 else 1
        
        # print(f'Res pt update requested: distx={dist_x}, resUmx={resUm_x} => pointsx={points_x}, disty={dist_y}, resUmy={resUm_y} => pointsy={points_y}')
        
        self.spin_resxpt.setValue(points_x)
        self.spin_resypt.setValue(points_y)
        
        self._block_signals_resolution(False)
        
def test_rect2():
    import sys
    from iris.gui.motion_video import generate_dummy_motion_controller
    
    app = qw.QApplication([])
    main_window = qw.QMainWindow()
    wdg_main = qw.QWidget()
    main_window.setCentralWidget(wdg_main)
    layout_main = qw.QHBoxLayout()
    wdg_main.setLayout(layout_main)
    
    motion_controller = generate_dummy_motion_controller(wdg_main)
    wdg_rect = Rect_AroundCentre(wdg_main,motion_controller)
    layout_main.addWidget(motion_controller)
    layout_main.addWidget(wdg_rect)
    main_window.show()
    
    sys.exit(app.exec())
    
if __name__ == '__main__':
    test_rect2()