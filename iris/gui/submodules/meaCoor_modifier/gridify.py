"""
A GUI module to modify a mapping coordinates list by translating 
the coordinates in the X, Y and Z direction.
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from typing import Self
from enum import Enum
import threading
from queue import Queue, Empty

import numpy as np
from PIL import Image, ImageTk

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))

from iris.gui.motion_video import Frm_MotionController
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.utils.general import *
from iris.utils.gridify import generate_warped_grid

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
    
class Gridify(tk.Frame):
    def __init__(
        self,
        parent,
        mappingCoorHub: List_MeaCoor_Hub,
        motion_controller:Frm_MotionController,
        *args, **kwargs) -> None:
        """Initializes the mapping method
        
        Args:
            parent (tk.Frame): The parent frame to place this widget in
            MappingCoorHub (MappingCoordinatesHub): The hub to store the resulting mapping coordinates in
            getter_MappingCoor (Callable[[], MappingCoordinates_mm]): A function to get the mapping coordinates to modify
            motion_controller (Frm_MotionController): The motion controller to use for the mapping
        """
        super().__init__(parent)
        self._coorHub = mappingCoorHub
        self._motion_controller = motion_controller
        
    # >>> Top level frame <<<
        frm_instruction = tk.Frame(self)
        frm_mapUnit_selection = tk.Frame(self)
        self._frm_modifier = tk.LabelFrame(self, text='Multi-coordinates generation (Gridify')
        self._frm_refCoor = tk.LabelFrame(self, text='Reference coordinates')
        self._frm_rowCol = tk.LabelFrame(self, text='Row/Column setup')
        frm_options = tk.Frame(self)
        
        row=0; col_curr=0
        frm_instruction.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        frm_mapUnit_selection.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        self._frm_modifier.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        self._frm_refCoor.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        self._frm_rowCol.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        frm_options.grid(row=row, column=0, sticky='nsew', padx=5, pady=5)
        
        [self.grid_rowconfigure(i, weight=1) for i in range(row+1)]
        [self.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]
        
    # >>> Information widget <<<
        btn_instructions = tk.Button(frm_instruction, text='Show instructions', command=self._show_instructions)
        
        row=0; col_curr=0
        btn_instructions.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        [frm_instruction.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [frm_instruction.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]
        
    # >>> Selection widget <<<
        self._combo_mapUnit = ttk.Combobox(frm_mapUnit_selection, state='readonly')
        
        row=0; col_curr=0
        self._combo_mapUnit.grid(row=row, column=0, sticky='ew', padx=5, pady=5)
        
        [frm_mapUnit_selection.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [frm_mapUnit_selection.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]
        
    # >>> Reference coordinates widget <<<
        # Parameters setup
        self._dict_refFourCorners = {
            Enums_RefFourCorners.top_left: None,
            Enums_RefFourCorners.top_right: None,
            Enums_RefFourCorners.bottom_left: None,
            Enums_RefFourCorners.bottom_right: None,
        }
        self._init_refFourCorners_widgets()
        
    # >>> Row/Column setup widget <<<
        # Parameters setup
        self._str_noOfRows = tk.StringVar(value='2')
        self._str_noOfCols = tk.StringVar(value='2')
        self._init_rowCol_widgets()
        
    # >>> Options frame <<<
        self._btn_setupGrid = tk.Button(frm_options, text='Fine-tune grid', command=self._run_gridSetup)
        self._btn_setupGrid.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        
    # >>> Others <<<
        self._coorHub.add_observer(self._update_list_units)
        self._update_list_units()
        
    def _init_refFourCorners_widgets(self):
        """Initializes the reference four corners for the mapping coordinates"""
        
        sfrm_topleft = tk.LabelFrame(self._frm_refCoor, text=Enums_RefFourCorners.top_left.value)
        sfrm_topright = tk.LabelFrame(self._frm_refCoor, text=Enums_RefFourCorners.top_right.value)
        sfrm_bottomleft = tk.LabelFrame(self._frm_refCoor, text=Enums_RefFourCorners.bottom_left.value)
        sfrm_bottomright = tk.LabelFrame(self._frm_refCoor, text=Enums_RefFourCorners.bottom_right.value)
        
        sfrm_topleft.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        sfrm_topright.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
        sfrm_bottomleft.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        sfrm_bottomright.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)
        
        dict_sfrm = {
            Enums_RefFourCorners.top_left: sfrm_topleft,
            Enums_RefFourCorners.top_right: sfrm_topright,
            Enums_RefFourCorners.bottom_left: sfrm_bottomleft,
            Enums_RefFourCorners.bottom_right: sfrm_bottomright,
        }
        
        for corner in self._dict_refFourCorners:
            frm = dict_sfrm[corner]
            self._dict_refFourCorners[corner] = {
                Enums_RefCornerDict.x: tk.StringVar(value='0.0'),
                Enums_RefCornerDict.y: tk.StringVar(value='0.0'),
                Enums_RefCornerDict.z: tk.StringVar(value='0.0'),
                Enums_RefCornerDict.loc_xy: tk.StringVar(value=Enums_RefXY.center_center.value),
                Enums_RefCornerDict.loc_z: tk.StringVar(value=Enums_RefZ.bottom.value),
            }
            
            lbl_xyz = tk.Label(frm, text=f'Ref. coor (X,Y,Z) [μm]:')
            entry_x = tk.Entry(frm, textvariable=self._dict_refFourCorners[corner][Enums_RefCornerDict.x], width=10)
            entry_y = tk.Entry(frm, textvariable=self._dict_refFourCorners[corner][Enums_RefCornerDict.y], width=10)
            entry_z = tk.Entry(frm, textvariable=self._dict_refFourCorners[corner][Enums_RefCornerDict.z], width=10)
            btn_insert = tk.Button(frm, text='Insert current coor (X,Y,Z)', command=lambda
                x=self._dict_refFourCorners[corner][Enums_RefCornerDict.x],
                y=self._dict_refFourCorners[corner][Enums_RefCornerDict.y],
                z=self._dict_refFourCorners[corner][Enums_RefCornerDict.z]: self._insert_current_coordinate(x, y, z))
            
            sfrm = tk.Frame(frm)
            lbl_loc = tk.Label(sfrm, text='Location (XY,Z):')
            combo_xy = ttk.Combobox(sfrm, textvariable=self._dict_refFourCorners[corner][Enums_RefCornerDict.loc_xy],
                                    values=[e.value for e in Enums_RefXY], state='readonly', width=15)
            combo_z = ttk.Combobox(sfrm, textvariable=self._dict_refFourCorners[corner][Enums_RefCornerDict.loc_z],
                                   values=[e.value for e in Enums_RefZ], state='readonly', width=10)
            combo_xy.set(Enums_RefXY.center_center.value)  # Default to center-center
            combo_z.set(Enums_RefZ.bottom.value)  # Default to center
            
            # Layout
            lbl_xyz.grid(row=0, column=0, sticky='w', padx=5, pady=5)
            entry_x.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
            entry_y.grid(row=0, column=2, sticky='ew', padx=5, pady=5)
            entry_z.grid(row=0, column=3, sticky='ew', padx=5, pady=5)
            btn_insert.grid(row=1, column=0, columnspan=4, sticky='ew', padx=5, pady=5)
            sfrm.grid(row=2, column=0, columnspan=4, sticky='ew', padx=5, pady=5)
            
            lbl_loc.grid(row=0, column=0, sticky='w', padx=5, pady=5)
            combo_xy.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
            combo_z.grid(row=0, column=2, sticky='ew', padx=5, pady=5)
            
    def _init_rowCol_widgets(self):
        """Initializes the row/column setup widgets"""
        frm = tk.Frame(self._frm_rowCol)
        frm.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        lbl_noOfRows = tk.Label(frm, text='Number of rows:')
        lbl_noOfCols = tk.Label(frm, text='Number of columns:')
        
        entry_noOfRows = tk.Entry(frm, textvariable=self._str_noOfRows, width=5)
        entry_noOfCols = tk.Entry(frm, textvariable=self._str_noOfCols, width=5)
        
        lbl_noOfRows.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        entry_noOfRows.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        
        lbl_noOfCols.grid(row=1, column=0, sticky='w', padx=5, pady=5)
        entry_noOfCols.grid(row=1, column=1, sticky='ew', padx=5, pady=5)

    def _insert_current_coordinate(self,strvar_x:tk.StringVar,strvar_y:tk.StringVar,strvar_z:tk.StringVar):
        """Inserts the current coordinates from the motion controller into the reference coordinates"""
        coor = self._motion_controller.get_coordinates_closest_mm()
        coorx_um = coor[0] * 1e3
        coory_um = coor[1] * 1e3
        coorz_um = coor[2] * 1e3
        
        strvar_x.set(f'{coorx_um:.2f}')
        strvar_y.set(f'{coory_um:.2f}')
        strvar_z.set(f'{coorz_um:.2f}')

    def _show_instructions(self):
        instructions = (
            "This module takes an existing mapping coordinates list and creates a grid layout based on the specified parameters.\n"
            "NOTE: Make sure that the XY stage coordinate increases when the XY stage physically moves to the left and bottom.\n"
            "And the Z coordinate increases when the objective's stage moves closer to the sample."
        )
        messagebox.showinfo("Instructions", instructions)
    
    def _update_list_units(self):
        """Updates the list of mapping units in the combobox"""
        self._dict_mapUnit.clear()  # Clear the existing dictionary
        self._dict_mapUnit = {unit.mappingUnit_name: unit for unit in self._coorHub}
        
        self._combo_mapUnit.configure(
            values=list(self._dict_mapUnit.keys()),
            state='readonly'
        )

    @thread_assign
    def _run_gridSetup(self):
        """
        Runs the modification of the z-coordinates of the selected mapping coordinates
        """
        def reset(): self._btn_setupGrid.config(state='normal')
        self._btn_setupGrid.config(state='disabled')
        
    # > Retrieve the selected mapping unit from the combobox and check it <
        selected_unit_name = self._combo_mapUnit.get()
        if not selected_unit_name:
            messagebox.showwarning("Warning", "Please select a mapping unit to modify.")
            reset()
            return
        
        if selected_unit_name not in self._dict_mapUnit:
            messagebox.showerror("Error", f"Mapping unit '{selected_unit_name}' not found.")
            reset()
            return
        
        # Get the current mapping coordinates
        mapping_coordinates = self._dict_mapUnit[selected_unit_name]
        
        if not isinstance(mapping_coordinates, MeaCoor_mm):
            messagebox.showerror("Error", "Invalid mapping coordinates type.")
            return
        
    # > Calculate the center of the four corners coordinates <
        corner_coords = []
        for corner in self._dict_refFourCorners:
            x_mm = float(self._dict_refFourCorners[corner][Enums_RefCornerDict.x].get())/1e3
            y_mm = float(self._dict_refFourCorners[corner][Enums_RefCornerDict.y].get())/1e3
            z_mm = float(self._dict_refFourCorners[corner][Enums_RefCornerDict.z].get())/1e3
            ctr_x, ctr_y, ctr_z = calculate_coordinatesCenter(
                ref_coor=np.array([x_mm, y_mm, z_mm]),
                mappingCoor=mapping_coordinates,
                loc_xy=Enums_RefXY(self._dict_refFourCorners[corner][Enums_RefCornerDict.loc_xy].get()),
                loc_z=Enums_RefZ(self._dict_refFourCorners[corner][Enums_RefCornerDict.loc_z].get())
            )
            corner_coords.append(np.array([ctr_x, ctr_y, ctr_z]))
            
    # > Get the number of rows and columns from the entry fields <
        try:
            num_rows = int(self._str_noOfRows.get())
            num_cols = int(self._str_noOfCols.get())
            if num_rows < 2 or num_cols < 2:
                raise ValueError("Number of rows and columns must be at least 2.")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
            reset()
            return
        
        mapping_coor = mapping_coordinates.copy()
        
    # > Open the grid setup dialog <
        queue_result = Queue()
        TopLevel_GridSetup(
            parent=self,
            corner_coords=corner_coords,
            num_rows=num_rows,
            num_cols=num_cols,
            mapping_coor=mapping_coor,
            ctrl_motion_video=self._motion_controller,
            queue_result=queue_result
        )
        
        while True:
            try: res = queue_result.get_nowait()
            except Empty: time.sleep(0.1); continue
            
            if res is None:
                reset()
                break
            try:
                list_newMapCoor = []
                for mapcoor in res:
                    mapcoor:MeaCoor_mm
                    list_coor = [(float(coor[0]), float(coor[1]), float(coor[2])) for coor in mapcoor.mapping_coordinates.copy()]
                    new_mapcoor = MeaCoor_mm(
                        mappingUnit_name=mapcoor.mappingUnit_name,
                        mapping_coordinates=list_coor
                    )
                    list_newMapCoor.append(new_mapcoor)
                self._coorHub.extend(list_newMapCoor)
                reset()
                break
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update mapping coordinates: {e}")
                reset()
                return
    
class TopLevel_GridSetup(tk.Toplevel):
    def __init__(self, parent, corner_coords: list[np.ndarray],
                 num_rows: int, num_cols: int, mapping_coor: MeaCoor_mm,
                 ctrl_motion_video: Frm_MotionController, queue_result: Queue, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title("Gridify Setup")
        
    # >>> Store the parameters <<<
        self._parent = parent
        self._corner_coords = corner_coords
        self._num_rows = num_rows
        self._num_cols = num_cols
        self._mapping_coor = mapping_coor
        self._ctrl_motion_video = ctrl_motion_video
        self._queue_result = queue_result
        
    # >>> Layout setup <<<
        self._frm_rowSetup = tk.LabelFrame(self, text='Row name setup\n(top to bottom)')
        self._frm_colSetup = tk.LabelFrame(self, text='Column name setup\n(left to right)')
        self._frm_namingScheme = tk.LabelFrame(self, text='Naming scheme setup')
        frm_finalise = tk.Frame(self)
        
        self._frm_rowSetup.grid(row=0, column=0, rowspan=2, sticky='nsew', padx=5, pady=5)
        self._frm_colSetup.grid(row=0, column=1, rowspan=2, sticky='nsew', padx=5, pady=5)
        self._frm_namingScheme.grid(row=0, column=2, sticky='nsew', padx=5, pady=5)
        frm_finalise.grid(row=1, column=2, sticky='nsew', padx=5, pady=5)
        
    # >>> Create the gridify interface <<<
        # Parameters setup
        self._list_rowNames = []
        self._list_colNames = []
        self._naming_scheme = tk.StringVar(value=Enums_NamingScheme.row_col.value)
        self._separator = tk.StringVar(value='_')
        self._init_rowColSetup_widgets()
        self._init_namingScheme_widgets()
        
    # >>> Finalise button <<<
        self._btn_finetune = tk.Button(frm_finalise, text='Fine-tune grid', command=self._run_gridFinetune)
        self._btn_cancel = tk.Button(frm_finalise, text='Cancel', command=self._terminate)
        
        self._btn_finetune.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        self._btn_cancel.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        
        # Override the window close button to prevent accidental closure
        self.protocol("WM_DELETE_WINDOW", self._terminate)
    
    def _init_rowColSetup_widgets(self):
        """Initializes the row and column setup widgets"""
        for i in range(self._num_rows):
            row_name = tk.StringVar(value=f'Row {i+1}')
            entry_row = tk.Entry(self._frm_rowSetup, textvariable=row_name)
            entry_row.grid(row=i, column=0, sticky='ew', padx=5, pady=5)
            self._list_rowNames.append(row_name)

        for j in range(self._num_cols):
            col_name = tk.StringVar(value=f'Col {j+1}')
            entry_col = tk.Entry(self._frm_colSetup, textvariable=col_name)
            entry_col.grid(row=j, column=0, sticky='ew', padx=5, pady=5)
            self._list_colNames.append(col_name)
        
    def _init_namingScheme_widgets(self):
        """Initializes the naming scheme setup widgets"""
        # Create radio buttons for naming scheme selection
        for i, scheme in enumerate(Enums_NamingScheme):
            rb = tk.Radiobutton(self._frm_namingScheme, text=scheme.value, variable=self._naming_scheme, value=scheme.value)
            rb.grid(row=i, column=0, sticky='w', padx=5, pady=5)

        lbl_separator = tk.Label(self._frm_namingScheme, text='Separator:')
        entry_separator = tk.Entry(self._frm_namingScheme, textvariable=self._separator, width=5)
        btn_example = tk.Button(self._frm_namingScheme, text='Show example', command=self._show_example_names)
        
        lbl_separator.grid(row=len(Enums_NamingScheme), column=0, sticky='w', padx=5, pady=5)
        entry_separator.grid(row=len(Enums_NamingScheme), column=1, sticky='ew', padx=5, pady=5)
        btn_example.grid(row=len(Enums_NamingScheme), column=2, sticky='ew', padx=5, pady=5)
        
    def _show_example_names(self):
        messagebox.showinfo("Example", f"Example naming: {self._generate_names()[0] if self._generate_names() else 'No names could be generated'}")
        self.lift()
        
    def _generate_names(self) -> tuple[list[str], list[tuple[int, int]]]:
        """
        Generates the names for the gridified coordinates based on the row and column names.
        
        Returns:
            tuple: A tuple containing two lists:
            list: A list of names generated based on the naming scheme and row/column names in 
                the order of rows first then columns (u then v, e.g., (row1,col1),(row2,col1),...,(row1,col2),...)
                the order of columns first then rows (u then v, e.g., (col1,row1),(col1,row2),...,(col2,row1),...)
            list: A list of tuples containing the (row, column) indices for each name.
                """
        naming_scheme = Enums_NamingScheme(self._naming_scheme.get())
        separator = self._separator.get()
        
        names = []
        loc = []
        # Generate the rows in the reverse order
        for j in range(self._num_cols):
            for i in reversed(range(self._num_rows)):
                if naming_scheme == Enums_NamingScheme.row_col:
                    name = f"{self._list_rowNames[i].get()}{separator}{self._list_colNames[j].get()}"
                elif naming_scheme == Enums_NamingScheme.col_row:
                    name = f"{self._list_colNames[j].get()}{separator}{self._list_rowNames[i].get()}"
                names.append(name)
                loc.append((i, j))
        return names, loc

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
        
    def _run_gridFinetune(self):
        """
        Performs the gridify operation by generating the mapping coordinates based on the specified parameters.
        """
        self._btn_finetune.config(state='disabled')
        self._btn_cancel.config(state='disabled')
        
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
            messagebox.showerror("Error", "Duplicate names found in the generated mapping coordinates. Please ensure unique names.")
            return

        TopLevel_FineTuneGridify(
            parent=self._parent,
            list_mapping_coor=list_mapping_coor,
            list_loc=list_loc,
            ctrl_motion_video=self._ctrl_motion_video,
            queue_result=self._queue_result
        )
        self.destroy()
        
    def _terminate(self):
        self._queue_result.put(None)  # Signal termination
        self.destroy()  # Close the window
        pass
    
class TopLevel_FineTuneGridify(tk.Toplevel):
    def __init__(self, parent, list_mapping_coor:list[MeaCoor_mm],
                 list_loc:list[tuple[int, int]], ctrl_motion_video:Frm_MotionController,
                 queue_result:Queue,*args, **kwargs):
        """
        Initializes the fine-tune gridify window.

        Args:
            parent (tk.Tk): The parent window.
            list_mapping_coor (list[MappingCoordinates_mm]): The list of mapping coordinates.
            list_loc (list[tuple[int, int]]): The list of (row, column) locations.
            ctrl_motion_video (Frm_MotionController): The motion controller for the video feed.
        """
        super().__init__(parent, *args, **kwargs)
        self.title("Fine-tune Gridify")
        
    # >>> Store the parameters <<<
        self._list_mapping_coor = list_mapping_coor
        self._list_loc = list_loc
        self._ctrl_motion_video = ctrl_motion_video
        self._queue_result = queue_result
        
    # >>> Initialise the parameters <<<
        self._list_mod = [False] * len(self._list_mapping_coor)  # List to track modified coordinates
        
    # >>> Layout setup <<<
        self._frm_video = tk.LabelFrame(self, text='Video feed')
        self._frm_finetune = tk.LabelFrame(self, text='Fine-tune coordinates')
        
        self._frm_video.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        self._frm_finetune.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self._init_finetune_widgets()
        
    # >>> Initialize the video feed parameters <<<
        self._flg_video_feed = threading.Event()
        self._vid_size = (640, 480)  # Default video size
        self._lbl_vid = tk.Label(self._frm_video, image=ImageTk.PhotoImage(Image.new('RGB', self._vid_size, color='black')))
        self._lbl_vid.pack(fill=tk.BOTH, expand=True)
        self._thread_video = self._auto_video_updater()
        
        # Override the window close button to prevent accidental closure
        self.protocol("WM_DELETE_WINDOW", self._terminate)
        
    @thread_assign
    def _auto_video_updater(self):
        """Automatically updates the video feed"""
        current_image = None
        self._flg_video_feed.set()  # Set the flag to start the video feed
        while self._flg_video_feed.is_set():
            try:
                new_img = self._ctrl_motion_video.get_current_image()
                new_img_tk = ImageTk.PhotoImage(new_img.resize(self._vid_size, Image.LANCZOS))
                if new_img_tk != current_image and new_img is not None:
                    self.after(0, lambda: self._lbl_vid.config(image=new_img_tk))
                    current_image = new_img_tk
            except Exception as e:
                print(f"Error updating video feed: {e}")
            finally: time.sleep(20/1000)
            
    def _init_finetune_widgets(self):
        """Initializes the fine-tune widgets for the gridified coordinates"""
    # >>> Create a treeview widget to display the gridified coordinates <<<
        sfrm_treeview = tk.Frame(self._frm_finetune)
        sfrm_params = tk.LabelFrame(self._frm_finetune, text='Parameters')
        sfrm_treeview.pack(side=tk.LEFT,fill=tk.BOTH, expand=True, padx=5, pady=5)
        sfrm_params.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        self._treeview_mapcoor = ttk.Treeview(sfrm_treeview, columns=('row','col','name','coor','mod'), show='headings',
                                              selectmode='browse')
        self._treeview_mapcoor.heading('row', text='Row')
        self._treeview_mapcoor.heading('col', text='Col')
        self._treeview_mapcoor.heading('name', text='Name')
        self._treeview_mapcoor.heading('coor', text='Center coor [μm]')
        self._treeview_mapcoor.heading('mod', text='Modified')
        self._treeview_mapcoor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._treeview_mapcoor.bind('<Double-1>', self._on_treeview_double_click)
        
        self._update_treeview()
        try: self._treeview_mapcoor.selection_set(self._treeview_mapcoor.get_children()[0])
        except Exception as e: print(f"Error selecting first item in treeview: {e}")
        
        # Create a scrollbar for the treeview
        scrollbar_y = ttk.Scrollbar(sfrm_treeview, orient='vertical', command=self._treeview_mapcoor.yview)
        scrollbar_x = ttk.Scrollbar(sfrm_treeview, orient='horizontal', command=self._treeview_mapcoor.xview)
        self._treeview_mapcoor.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create a label for the instructions
        lbl_instruction = tk.Label(sfrm_treeview, text="Double-click on a coordinate to modify it.")
        lbl_instruction.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        
    # >>> Setup the parameters widget <<<
        self._str_loc_xy = tk.StringVar(value=Enums_RefXY.center_center.value)
        self._str_loc_z = tk.StringVar(value=Enums_RefZ.bottom.value)
        self._combo_loc_xy = ttk.Combobox(sfrm_params, textvariable=self._str_loc_xy,
                                          values=[e.value for e in Enums_RefXY], state='readonly', width=15)
        self._combo_loc_z = ttk.Combobox(sfrm_params, textvariable=self._str_loc_z,
                                          values=[e.value for e in Enums_RefZ], state='readonly', width=15)
        btn_commit = tk.Button(sfrm_params, text='Set current coor as reference',
                               command=self._update_coordinate_withCurrentCoor)
        btn_goToNext = tk.Button(sfrm_params, text='Go to next coordinate',
                               command=self._go_to_nextMappingCoor)
        self._btn_finish = tk.Button(sfrm_params, text='Finish editing', command=self._finalise_editing)
        self._btn_cancel_all = tk.Button(sfrm_params, text='Cancel all modifications', command=self._terminate)
        
        self._combo_loc_xy.pack(fill=tk.X, padx=5, pady=5)
        self._combo_loc_z.pack(fill=tk.X, padx=5, pady=5)
        btn_commit.pack(fill=tk.X, padx=5, pady=5)
        btn_goToNext.pack(fill=tk.X, padx=5, pady=5)
        self._btn_finish.pack(fill=tk.X, padx=5, pady=5)
        self._btn_cancel_all.pack(fill=tk.X, padx=5, pady=5)

    @thread_assign
    def _update_treeview(self) -> threading.Thread:
        """Updates the treeview with the gridified coordinates"""
        # Store the current selection
        sel = self._get_selected_mappingCoor(suppress_warning=True)
        idx = sel[0] if sel else None
        
        self._treeview_mapcoor.delete(*self._treeview_mapcoor.get_children())
        for i, mapping_coor in enumerate(self._list_mapping_coor):
            center_coor = np.mean(mapping_coor.mapping_coordinates, axis=0)
            center_coor_str = f"({center_coor[0]*1e3:.1f}, {center_coor[1]*1e3:.1f}, {center_coor[2]*1e3:.1f})"
            row, col = self._list_loc[i]
            name = mapping_coor.mappingUnit_name
            modified = 'Yes' if self._list_mod[i] else 'No'
            self._treeview_mapcoor.insert('', 'end', values=(row, col, name, center_coor_str, modified))
            
        # Restore the selection
        if idx is not None and idx < len(self._list_mapping_coor):
            iid = self._treeview_mapcoor.get_children()[idx]
            self._treeview_mapcoor.selection_set(iid)
            self._treeview_mapcoor.see(iid)
        
    def _calculate_target_coordinate(self, mapping_coor:MeaCoor_mm) -> np.ndarray:
        """
        Calculates the target coordinate based on the selected reference coordinates and the mapping coordinates.
        
        Args:
            mapping_coor (MappingCoordinates_mm): The mapping coordinates from which to select the coordinate
        
        Returns:
            np.ndarray: The selected coordinate in the form of a numpy array [x, y, z]
        """
        loc_xy = Enums_RefXY(self._str_loc_xy.get())
        loc_z = Enums_RefZ(self._str_loc_z.get())
        
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
            
        if loc_z == Enums_RefZ.top:
            z = np.max([coor[2] for coor in mapping_coor.mapping_coordinates])
        elif loc_z == Enums_RefZ.center:
            z = np.mean([coor[2] for coor in mapping_coor.mapping_coordinates])
        elif loc_z == Enums_RefZ.bottom:
            z = np.min([coor[2] for coor in mapping_coor.mapping_coordinates])
            
        return np.array([x, y, z])
    
    @thread_assign
    def _update_coordinate_withCurrentCoor(self) -> bool:
        """Updates the selected coordinate with the current position of the motion controller"""
        result = self._get_selected_mappingCoor()
        if not result: return False

        idx, mapping_coor = result
        
        current_coor = np.array(self._ctrl_motion_video.get_coordinates_closest_mm())
        
        new_center_coor = calculate_coordinatesCenter(
            ref_coor=current_coor,
            mappingCoor=mapping_coor,
            loc_xy=Enums_RefXY(self._str_loc_xy.get()),
            loc_z=Enums_RefZ(self._str_loc_z.get())
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
        self._update_treeview().join()  # Refresh the treeview to show the updated coordinates

        return True
    
    @thread_assign
    def _go_to_nextMappingCoor(self) -> threading.Thread:
        """Updates the next coordinate with the current position of the motion controller
        and moves the motion controller to the next coordinate"""
        # Select the next coordinate in the treeview
        result = self._get_selected_mappingCoor()
        if not result: return None
        idx, _ = result
        if idx == len(self._list_mapping_coor) - 1:
            messagebox.showinfo("Info", "You have reached the last coordinate.")
            self.lift()
            return
        self._treeview_mapcoor.selection_set(self._treeview_mapcoor.get_children()[idx + 1])
        
        # Move to the next coordinate
        self._go_to_selectedMappingCoor().join()

    def _get_selected_mappingCoor(self, suppress_warning: bool = False) -> tuple[int,MeaCoor_mm]|None:
        """Returns the currently selected mapping coordinates from the treeview
        
        Args:
            suppress_warning (bool): If True, suppresses the warning message if no item is selected.
            
        Returns:
            tuple: A tuple containing the index of the selected mapping coordinates and the mapping coordinates object
        """
        selected_item = self._treeview_mapcoor.selection()
        if not selected_item and not suppress_warning:
            messagebox.showwarning("Warning", "Please select a mapping coordinate to modify.")
            return None
        
        idx = self._treeview_mapcoor.index(selected_item)
        return idx, self._list_mapping_coor[idx]
        
    @thread_assign
    def _go_to_selectedMappingCoor(self) -> threading.Thread:
        """Moves the motion controller to the selected mapping coordinates"""
        result = self._get_selected_mappingCoor()
        if not result:
            return
        
        _, mapping_coor = result
        target_coor = self._calculate_target_coordinate(mapping_coor)
        
        try: self._ctrl_motion_video.go_to_coordinates(*target_coor)
        except Exception as e: messagebox.showerror("Error", f"Failed to move to coordinates: {e}"); return
        
    @thread_assign
    def _on_treeview_double_click(self, event):
        print("Treeview double-clicked")
        self._go_to_selectedMappingCoor()
        
    @thread_assign
    def _finalise_editing(self):
        """Finalises the editing of the gridified coordinates and returns the modified coordinates"""
        self._btn_cancel_all.config(state='disabled')
        self._btn_finish.config(state='disabled')
        
        confirmation = messagebox.askyesno("Confirm", "Are you sure you want to finish editing?\n"
            "This will save all changes made to the mapping coordinates.")
        if not confirmation:
            self._btn_cancel_all.config(state='normal')
            self._btn_finish.config(state='normal')
            return
        
        # Return the modified mapping coordinates
        self._queue_result.put(self._list_mapping_coor)
        self._flg_video_feed.clear()
        self.destroy()
        
    @thread_assign
    def _terminate(self):
        """Terminates the video feed and closes the window"""
        self._btn_cancel_all.config(state='disabled')
        self._btn_finish.config(state='disabled')
        confirmation = messagebox.askyesno("Confirm", "Are you sure you want to cancel all modifications?\n"
            "This will discard all changes made to the mapping coordinates.\n"
            "There is no way to undo this action.")
        if not confirmation:
            self._btn_cancel_all.config(state='normal')
            self._btn_finish.config(state='normal')
            return

        self._flg_video_feed.clear()
        self._queue_result.put(None)
        self.destroy()
        
def test():
    from iris.gui.motion_video import generate_dummy_motion_controller
    
    root = tk.Tk()
    root.title('Test')
    
    frm_motion = generate_dummy_motion_controller(root)
    frm_motion.initialise_auto_updater()
    frm_motion.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
    
    coorUnit = MeaCoor_mm(
        mappingUnit_name='Test Mapping Unit',
        mapping_coordinates=[(0, 0, 0), (1, 0, 1), (0, 1, 2), (1, 1, 3)]
    )
    
    coorHub = List_MeaCoor_Hub()
    coorHub.append(coorUnit)
    
    frm_coor_mod = Gridify(
        root,
        mappingCoorHub=coorHub,
        motion_controller=frm_motion,
    )
    
    frm_coor_mod.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
    
    root.mainloop()
    
if __name__ == '__main__':
    test()