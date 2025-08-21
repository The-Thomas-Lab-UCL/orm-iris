"""
A GUI module to modify the z-coordinates of a mapping coordinates list.
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from typing import Literal
import threading

import numpy as np
from scipy.interpolate import griddata

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))

from iris.gui.motion_video import Frm_MotionController
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.utils.general import *

class ZInterpolate(tk.Frame):
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
        self._coorHub = mappingCoorHub
        
    # >>> Top level frame <<<
        frm_instruction = tk.Frame(self)
        frm_mapUnit_selection = tk.Frame(self)
        self._frm_zModification = tk.LabelFrame(self, text='Z-coordinates modifier', padx=5, pady=5)
        frm_modParams = tk.Frame(self)
        
        row=0; col_curr=0
        frm_instruction.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        frm_mapUnit_selection.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        self._frm_zModification.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        frm_modParams.grid(row=row, column=0, sticky='nsew', padx=5, pady=5)
        
        [self.grid_rowconfigure(i, weight=1) for i in range(row+1)]
        [self.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]
        
    # >>> Information widget <<<
        btn_instructions = tk.Button(frm_instruction, text='Show instructions', command=self._show_instructions)
        
        row=0; col_curr=0
        btn_instructions.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        [frm_instruction.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [frm_instruction.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]
        
    # >>> Selection widget <<<
        lbl_mapUnit_source = tk.Label(frm_mapUnit_selection, text='Select the mapping coordinates to modify:')
        self._combo_mapUnit_source = ttk.Combobox(frm_mapUnit_selection, state='readonly')
        lbl_mapUnit_ref = tk.Label(frm_mapUnit_selection, text='Select the mapping coordinates reference:')
        self._combo_mapUnit_ref = ttk.Combobox(frm_mapUnit_selection, state='readonly')
        self._btn_commit = tk.Button(frm_mapUnit_selection, text='Modify Z-coordinates', command=self._run_modify_z_coordinates)
        
        row=0; col_curr=0
        lbl_mapUnit_source.grid(row=row, column=0, sticky='w', padx=5, pady=5); row+=1
        self._combo_mapUnit_source.grid(row=row, column=0, sticky='ew', padx=5, pady=5); row+=1
        lbl_mapUnit_ref.grid(row=row, column=0, sticky='w', padx=5, pady=5); row+=1
        self._combo_mapUnit_ref.grid(row=row, column=0, sticky='ew', padx=5, pady=5); row+=1
        self._btn_commit.grid(row=row, column=0, sticky='ew', padx=5, pady=5)
        
        [frm_mapUnit_selection.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [frm_mapUnit_selection.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]
        
    # >>> Parameter widgets <<<
        lbl_approx_method = tk.Label(frm_modParams, text='Interpolation method:')
        self._combo_approx_method = ttk.Combobox(
            frm_modParams,
            values=['linear', 'nearest', 'cubic'],
            state='readonly',
            width=10
        )
        self._combo_approx_method.set('linear')  # Default method
        
        row=0; col_curr=0
        lbl_approx_method.grid(row=0, column=0, sticky='w', padx=5, pady=5); row+=1
        self._combo_approx_method.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        
        [frm_modParams.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [frm_modParams.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]
        
    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        
    # >>> Others <<<
        self._coorHub.add_observer(self._update_list_units)
        self._update_list_units()
        
    def _show_instructions(self):
        instructions = (
            "This module allows you to modify the z-coordinates of a mapping coordinates list.\n"
            "TODO: Add instructions on how to use this module.\n"
        )
        messagebox.showinfo("Instructions", instructions)
    
    def _update_list_units(self):
        """Updates the list of mapping units in the combobox"""
        self._dict_mapUnit.clear()  # Clear the existing dictionary
        self._dict_mapUnit = {unit.mappingUnit_name: unit for unit in self._coorHub}
        
        self._combo_mapUnit_source.configure(
            values=list(self._dict_mapUnit.keys()),
            state='readonly'
        )
        self._combo_mapUnit_ref.configure(
            values=list(self._dict_mapUnit.keys()),
            state='readonly'
        )
        
    def _reset_zMod_widgets(self,state:Literal['normal', 'disabled']):
        """Resets the widgets in the z-coordinates modification frame to the given state
        Args:
            state (Literal['normal', 'disabled']): The state to set the widgets to
        """
        assert state in ['normal', 'disabled'], f"Invalid state: {state}"
        [widget.configure(state=state) for widget in get_all_widgets(self._frm_zModification) if isinstance(widget, (tk.Button, tk.Entry))]
        
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
        
    @thread_assign
    def _run_modify_z_coordinates(self):
        """
        Runs the modification of the z-coordinates of the selected mapping coordinates
        """
    # > Retrieve the selected mapping unit from the combobox and check it <
        sel_unitName_source = self._combo_mapUnit_source.get()
        sel_unitName_ref = self._combo_mapUnit_ref.get()
        
        if not sel_unitName_source or not sel_unitName_ref:
            messagebox.showwarning("Warning", "Please select a mapping unit to modify.")
            return
        
        if sel_unitName_source not in self._dict_mapUnit or sel_unitName_ref not in self._dict_mapUnit:
            messagebox.showerror("Error", f"Mapping unit '{sel_unitName_source}' not found.")
            return
        
        # Get the current mapping coordinates
        mapCoor_source = self._dict_mapUnit[sel_unitName_source]
        mapCoor_ref = self._dict_mapUnit[sel_unitName_ref]
        
        if not isinstance(mapCoor_source, MeaCoor_mm):
            messagebox.showerror("Error", "Invalid mapping coordinates type.")
            return
        
    # > Modify the z-coordinates <
        list_coor_source = mapCoor_source.mapping_coordinates.copy()
        list_coor_ref = mapCoor_ref.mapping_coordinates.copy()
        # Enable the widgets
        self._reset_zMod_widgets('normal')
        
        # try:
        approx_method = self._combo_approx_method.get()
        list_coor_interp = self._interpolate_z_values(
            list_coor=list_coor_source,
            list_ref=list_coor_ref,
            method=approx_method,
            skip_nan=True
        )
        if len(list_coor_interp) == 0:
            raise ValueError("No valid coordinates were interpolated. Please check the reference coordinates.")
        if len(list_coor_interp) != len(list_coor_source):
            messagebox.showwarning(
                "Warning",
                "Some coordinates could not be calculated due to them being outside the reference range.\n"
                "Only the valid coordinates have been modified.")
        # except Exception as e:
        #     messagebox.showerror("Error", f"Failed to modify z-coordinates: {e}")
        #     return
        
        while True:
            # Request for a new name
            new_name = messagebox_request_input(
                "New Mapping Unit Name",
                "Please enter a new name for the modified mapping coordinates:",
                default=f"{sel_unitName_source}_z modified"
            )
            
            # Add the new mapping coordinates to the hub
            new_mapping_coor = MeaCoor_mm(new_name,list_coor_interp)
            try: self._coorHub.append(new_mapping_coor); break
            except Exception as e: messagebox.showerror("Error", f"Failed to add new mapping coordinates: {e}"); continue
        
        messagebox.showinfo("Success", "Z-coordinates modified successfully.")
        self._reset_zMod_widgets('disabled')
    
def test():
    from iris.gui.motion_video import generate_dummy_motion_controller
    
    root = tk.Tk()
    root.title('Test')
    
    frm_motion = generate_dummy_motion_controller(root)
    frm_motion.initialise_auto_updater()
    frm_motion.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
    
    coorUnit = MeaCoor_mm(
        mappingUnit_name='Test Mapping Unit',
        mapping_coordinates=[(0, 0, 0), (1, 1, 1), (2, 2, 2), (3, 3, 3)]
    )
    
    coorHub = List_MeaCoor_Hub()
    coorHub.append(coorUnit)
    
    frm_coor_mod = ZInterpolate(
        root,
        mappingCoorHub=coorHub,
        motion_controller=frm_motion,
    )
    
    frm_coor_mod.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
    
    root.mainloop()
    
if __name__ == '__main__':
    test()