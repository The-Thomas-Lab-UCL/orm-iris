"""
An instance that manages a basic mapping method in tkinter
"""
import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot

from math import ceil

import numpy as np

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.gui.motion_video import Wdg_MotionController

from iris.resources.coordinate_generators.rect_startend_ui import Ui_meaCoor_Rect_StartEnd

class Rect_EndToEnd(Ui_meaCoor_Rect_StartEnd,qw.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.gridLayout)
        

class Wdg_Rect_StartEnd(qw.QWidget):
    
    sig_res_pt_changed = Signal()   # Signal emitted when the resolution points are changed
    sig_res_um_changed = Signal()   # Signal emitted when the resolution in um is changed
    
    def __init__(self,parent,motion_controller:Wdg_MotionController,*args, **kwargs) -> None:
        """Initializes the mapping method
        
        Args:
            parent (qw.QWidget): The frame to place the mapping method
            motion_controller (Wdg_MotionController): The motion controller to control the stage
        """
        # Place itself in the given master frame (container)
        super().__init__(parent)
        
        # Initialise the main widget
        self._widget = Rect_EndToEnd(self)
        wdg = self._widget
        
        self._main_layout = qw.QHBoxLayout(self)
        self._main_layout.addWidget(self._widget)
        
        # Sets up the other controllers
        self._motion_controller = motion_controller
        
        # Mapping parameters
        self._coor_xy1_mm = [None,None]     # Stores the start coordinates for the mapping. Required for movement boundary setting. Type: float
        self._coor_xy2_mm = [None,None]     # Stores the end coordinates for the mapping. Required for movement boundary setting. Type: float
        self._coor_z_mm = None              # Stores the start z-coordinate for the mapping. Required for movement boundary setting. Type: float
        self._m1_pointsx = None             # Stores the mapping resolution in the x-direction
        self._m1_pointsy = None             # Stores the mapping resolution in the y-direction
        self._m1_resx_um = None             # Stores the mapping resolution in the x-direction
        self._m1_resy_um = None             # Stores the mapping resolution in the y-direction
        self._mapping_coordinates = None # Stores the mapping coordinates in a (x,y,z) list
        
        # Make the widgets to store the coordinates
        self._ent_startx_um = wdg.ent_startx_um
        self._ent_starty_um = wdg.ent_starty_um
        self._btn_storexy_start = wdg.btn_curr_start_xy

        self._ent_endx_um = wdg.ent_endx_um
        self._ent_endy_um = wdg.ent_endy_um
        self._btn_storexy_end = wdg.btn_curr_end_xy

        self._ent_z_um = wdg.ent_z_um
        self._btn_storez = wdg.btn_curr_z
        
        # Make the widgets to manage the rest of the mapping parameters
        self._ent_xres = wdg.ent_res_pt_x
        self._ent_yres = wdg.ent_res_pt_y
        
        # Bind return to the set_coor buttons
        self._ent_startx_um.editingFinished.connect(self._update_resolution_field_um)
        self._ent_starty_um.editingFinished.connect(self._update_resolution_field_um)
        
        self._ent_endx_um.editingFinished.connect(self._update_resolution_field_um)
        self._ent_endy_um.editingFinished.connect(self._update_resolution_field_um)
        
        self._ent_xres.editingFinished.connect(self._update_resolution_field_um)
        self._ent_yres.editingFinished.connect(self._update_resolution_field_um)
        
        self._widget.ent_res_um_x.editingFinished.connect(self._update_resolution_field_points)
        self._widget.ent_res_um_y.editingFinished.connect(self._update_resolution_field_points)
        
        self._btn_storexy_start.clicked.connect(self._grab_startxy)
        self._btn_storexy_end.clicked.connect(self._grab_endxy)
        self._btn_storez.clicked.connect(self._grab_z)

    def get_mapping_coordinates_mm(self) -> list[tuple[float,float,float]]:
        """ 
        Returns the mapping coordinates
        
        Returns:
            list: List of tuple (x,y,z) coordinates
        """
        # Make sure to keep the generated coordinates up to date
        self._generate_mapping_coordinates()
        assert isinstance(self._mapping_coordinates,list)
        assert all([isinstance(coor,tuple) and len(coor)==3 for coor in self._mapping_coordinates])
        assert all([all([isinstance(val,float) for val in coor]) for coor in self._mapping_coordinates])
        return self._mapping_coordinates
    
    @Slot()
    def _generate_mapping_coordinates(self):
        """
        Generates the mapping coordinates. Also stores them in its own variable and the main
        operation variable
        """
        try: x1,y1,x2,y2,z = self._get_startendz_coor_mm()
        except ValueError as e:
            self._mapping_coordinates = None
            qw.QMessageBox.warning(None,'Warning',str(e))
            return
        
        try: res_pt_x, res_pt_y = self._get_resolution_points()
        except ValueError as e:
            self._mapping_coordinates = None
            qw.QMessageBox.warning(None,'Warning',str(e))
            return
        
        # Generate linearly spaced points along each axis
        x_points = np.linspace(x1, x2, res_pt_x) # type: ignore
        y_points = np.linspace(y1, y2, res_pt_y) # type: ignore

        # Create the grid
        X, Y = np.meshgrid(x_points, y_points)
        self._mapping_coordinates = [(float(x), float(y), float(z)) for x, y in zip(X.flatten(), Y.flatten())]
    
    def _reset_mapping_coordinates(self):
        self._m1_pointsx = None             # Stores the mapping resolution in the x-direction
        self._m1_pointsy = None             # Stores the mapping resolution in the y-direction
        self._m1_resx_um = None             # Stores the mapping resolution in the x-direction
        self._m1_resy_um = None             # Stores the mapping resolution in the y-direction
        self._mapping_coordinates = None    # Stores the mapping coordinates in a (x,y,z) list

    def _get_startendz_coor_mm(self) -> tuple[float,float,float,float,float]:
        """
        Returns the start and end coordinates in mm
        
        Returns:
            tuple: (x1_mm,y1_mm,x2_mm,y2_mm,z_mm)
        """
        try:
            coor_x1_mm = float(self._ent_startx_um.text())/1e3
            coor_y1_mm = float(self._ent_starty_um.text())/1e3
            coor_x2_mm = float(self._ent_endx_um.text())/1e3
            coor_y2_mm = float(self._ent_endy_um.text())/1e3
            coor_z_mm = float(self._ent_z_um.text())/1e3
        except ValueError as e:
            raise ValueError('Please enter numbers for the coordinates')
        return coor_x1_mm,coor_y1_mm,coor_x2_mm,coor_y2_mm,coor_z_mm

    def _get_resolution_points(self) -> tuple[int,int]:
        """
        Returns the resolution points in x and y direction
        """
        try:
            res_x_pts = int(self._ent_xres.text())
            res_y_pts = int(self._ent_yres.text())
        except ValueError as e:
            raise ValueError('Please enter integer numbers for the resolution points')
        
        return res_x_pts,res_y_pts
    
    def _get_resolution_um(self) -> tuple[float,float]:
        """
        Returns the resolution points in x and y direction
        """
        try:
            res_x_um = float(self._widget.ent_res_um_x.text())
            res_y_um = float(self._widget.ent_res_um_y.text())
        except ValueError as e:
            raise ValueError('Please enter integer numbers for the resolution points')
        
        return res_x_um,res_y_um
    
    def _block_signals_resolution(self,block:bool):
        """
        Blocks or unblocks the resolution entry field signals
        
        Args:
            block (bool): True to block, False to unblock
        """
        self._widget.ent_res_um_x.blockSignals(block)
        self._widget.ent_res_um_y.blockSignals(block)
        self._widget.ent_res_pt_x.blockSignals(block)
        self._widget.ent_res_pt_y.blockSignals(block)
    
    @Slot()
    def _update_resolution_field_points(self):
        """
        Sets the resolution of the mapping in the x and y direction
        using the stored distances
        """
        try: x_um, y_um = self._get_resolution_um()
        except ValueError as e: return
            
        
        try: x1,y1,x2,y2,_ = self._get_startendz_coor_mm()
        except ValueError as e:
            self._ent_xres.setPlaceholderText('Set coordinates first')
            self._ent_yres.setPlaceholderText('Set coordinates first')
            return
        
        self.blockSignals(True)
        
        distx = x2 - x1
        disty = y2 - y1
        
        resx_pt = ceil((distx*1000)/x_um)+1
        resy_pt = ceil((disty*1000)/y_um)+1
        
        self._ent_xres.setText('{}'.format(resx_pt))
        self._ent_yres.setText('{}'.format(resy_pt))
        
        self.blockSignals(False)
    
    @Slot()
    def _update_resolution_field_um(self):
        """
        Sets the resolution of the mapping in the x and y direction
        using the stored distances
        """
        try: x_pts, y_pts = self._get_resolution_points()
        except ValueError as e: return
            
        
        try: x1,y1,x2,y2,_ = self._get_startendz_coor_mm()
        except ValueError as e:
            self._ent_xres.setPlaceholderText('Set coordinates first')
            self._ent_yres.setPlaceholderText('Set coordinates first')
            return
        
        self.blockSignals(True)
        
        distx = x2 - x1
        disty = y2 - y1
        
        resx_um = (distx/(x_pts-1))*1000
        resy_um = (disty/(y_pts-1))*1000
        
        self._widget.ent_res_um_x.setText('{:.2f}'.format(resx_um))
        self._widget.ent_res_um_y.setText('{:.2f}'.format(resy_um))
        
        self.blockSignals(False)
    
    def _grab_z(self):
        """
        Gets the current stage coordinate and store it as the initial position
        """
        _,_,z = self._motion_controller.get_coordinates_closest_mm()
        if z is None: qw.QMessageBox.warning(None,'Warning','Unable to get current Z coordinate from the stage'); return
        
        self._ent_z_um.setText('{:.2f}'.format(z*1e3))
    
    def _grab_endxy(self):
        """
        Gets the current stage coordinate and store it as the initial position
        """
        x,y,_ = self._motion_controller.get_coordinates_closest_mm()
        if x is None or y is None: qw.QMessageBox.warning(None,'Warning','Unable to get current XY coordinates from the stage'); return
        
        self._ent_endx_um.setText('{:.2f}'.format(x*1e3))
        self._ent_endy_um.setText('{:.2f}'.format(y*1e3))
    
    def _grab_startxy(self):
        """
        Gets the current stage coordinate and store it as the initial position
        """
        x,y,_ = self._motion_controller.get_coordinates_closest_mm()
        if x is None or y is None: qw.QMessageBox.warning(None,'Warning','Unable to get current XY coordinates from the stage'); return
        
        self._ent_startx_um.setText('{:.2f}'.format(x*1e3))
        self._ent_starty_um.setText('{:.2f}'.format(y*1e3))
    
def test_rect1():
    import sys
    app = qw.QApplication([])
    main_window = qw.QMainWindow()
    main_window.show()
    wdg = qw.QWidget()
    lyt = qw.QHBoxLayout()
    main_window.setCentralWidget(wdg)
    wdg.setLayout(lyt)
    
    from iris.gui.motion_video import generate_dummy_motion_controller
    motion_controller = generate_dummy_motion_controller(wdg)
    mapping_method = Wdg_Rect_StartEnd(wdg,motion_controller)
    lyt.addWidget(motion_controller)
    lyt.addWidget(mapping_method)
    
    btn_print = qw.QPushButton('Print Coors')
    def on_print():
        coords = mapping_method.get_mapping_coordinates_mm()
        print(coords)
    btn_print.clicked.connect(on_print)
    mapping_method._main_layout.addWidget(btn_print)
    
    sys.exit(app.exec())
    
if __name__ == '__main__':
    test_rect1()