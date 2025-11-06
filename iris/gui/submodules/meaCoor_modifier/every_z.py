"""
A GUI module to modify the z-coordinates of a mapping coordinates list.
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from typing import Literal
import threading

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.gui.motion_video import Wdg_MotionController
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.utils.general import *

class EveryZ(tk.Frame):
    def __init__(
        self,
        parent,
        mappingCoorHub: List_MeaCoor_Hub,
        motion_controller:Wdg_MotionController,
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
        self._frm_zModification = tk.LabelFrame(self, text='Z-coordinates modifier', padx=5, pady=5)
        
        row=0; col_curr=0
        frm_instruction.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        frm_mapUnit_selection.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        self._frm_zModification.grid(row=row, column=0, sticky='nsew', padx=5, pady=5)
        
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
        self._btn_modifyZ = tk.Button(frm_mapUnit_selection, text='Modify Z-coordinates', command=self._run_modify_z_coordinates)
        
        row=0; col_curr=0
        self._combo_mapUnit.grid(row=row, column=0, sticky='ew', padx=5, pady=5); row+=1
        self._btn_modifyZ.grid(row=row, column=0, sticky='ew', padx=5, pady=5)
        
        [frm_mapUnit_selection.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [frm_mapUnit_selection.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]
        
    # >>> Z-coordinates modification widgets <<<
        lbl_coorinfo = tk.Label(self._frm_zModification, text='Coordinates left to modify:')
        self._str_coorinfo_val = tk.StringVar(value='N/A')
        lbl_coorinfo_value = tk.Label(self._frm_zModification, textvariable=self._str_coorinfo_val)
        
        lbl_old_z_coor = tk.Label(self._frm_zModification, text='Old Z-coordinate [μm]:')
        self._str_oldZCoor = tk.StringVar(value='N/A')
        lbl_old_z_value = tk.Label(self._frm_zModification, textvariable=self._str_oldZCoor)
        
        lbl_new_z_coor = tk.Label(self._frm_zModification, text='New Z-coordinate [μm]:')
        self._entry_newZCoor = tk.Entry(self._frm_zModification)
        self._btn_currentZCoor = tk.Button(self._frm_zModification, text='Insert current Z-coordinate',\
            command=self._insert_current_z_coordinate)
        
        self._btn_currentZCoor_commit = tk.Button(self._frm_zModification, text='Insert current Z-coordinate and commit')
        self._btn_commit_modification = tk.Button(self._frm_zModification, text='Commit modification')
        self._btn_cancel_modification = tk.Button(self._frm_zModification, text='Cancel modification')
        
        row=0; col_curr=0; col_max=0
        lbl_coorinfo.grid(row=row, column=0, sticky='w', padx=5, pady=5); col_curr+=1
        lbl_coorinfo_value.grid(row=row, column=1, sticky='w', padx=5, pady=5); row+=1; col_max=max(col_max, col_curr); col_curr=0
        
        lbl_old_z_coor.grid(row=row, column=0, sticky='w', padx=5, pady=5); col_curr+=1
        lbl_old_z_value.grid(row=row, column=1, sticky='w', padx=5, pady=5); row+=1; col_max=max(col_max, col_curr); col_curr=0
        
        lbl_new_z_coor.grid(row=row, column=0, sticky='w', padx=5, pady=5); col_curr+=1
        self._entry_newZCoor.grid(row=row, column=1, sticky='ew', padx=5, pady=5); row+=1; col_max=max(col_max, col_curr); col_curr=0
        
        self._btn_currentZCoor.grid(row=row, column=0, sticky='ew', padx=5, pady=5); col_curr+=1
        self._btn_currentZCoor_commit.grid(row=row, column=1, sticky='ew', padx=5, pady=5); row+=1; col_max=max(col_max, col_curr); col_curr=0
        
        self._btn_commit_modification.grid(row=row, column=0, sticky='ew', padx=5, pady=5); col_curr+=1
        self._btn_cancel_modification.grid(row=row, column=1, sticky='ew', padx=5, pady=5)
        
        col_max = max(col_max, col_curr)
        [self._frm_zModification.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [self._frm_zModification.grid_columnconfigure(i, weight=1) for i in range(col_max+1)]
        
        # Disable the buttons and entry fields initially
        self._reset_zMod_widgets('disabled')
        
    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        self._modify_response:Literal['commit', 'cancel'] = None    # Response from the modification process
        
    # >>> Others <<<
        self._coorHub.add_observer(self._update_list_units)
        self._update_list_units()
        
    def _insert_current_z_coordinate(self):
        """Inserts the current z-coordinate from the motion controller into the new
        Z-coordinate entry field"""
        current_z_um = self._motion_controller.get_coordinates_closest_mm()[2]*1e3
        self._entry_newZCoor.delete(0, tk.END)
        self._entry_newZCoor.insert(0, f'{current_z_um:.0f}')
        
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
        
        self._combo_mapUnit.configure(
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
        
    @thread_assign
    def _run_modify_z_coordinates(self):
        """
        Runs the modification of the z-coordinates of the selected mapping coordinates
        """
    # > Retrieve the selected mapping unit from the combobox and check it <
        selected_unit_name = self._combo_mapUnit.get()
        if not selected_unit_name:
            messagebox.showwarning("Warning", "Please select a mapping unit to modify.")
            return
        
        if selected_unit_name not in self._dict_mapUnit:
            messagebox.showerror("Error", f"Mapping unit '{selected_unit_name}' not found.")
            return
        
        # Get the current mapping coordinates
        mapping_coordinates = self._dict_mapUnit[selected_unit_name]
        
        if not isinstance(mapping_coordinates, MeaCoor_mm):
            messagebox.showerror("Error", "Invalid mapping coordinates type.")
            return
        
    # > Prep the parameters for the modification process <
        flg_input = threading.Event()
        
        def commit(): flg_input.set(); self._modify_response = 'commit'
        def cancel(): flg_input.set(); self._modify_response = 'cancel'
        def insert_and_commit(): self._insert_current_z_coordinate(); flg_input.set(); self._modify_response = 'commit'
        def reset_flg_input(): flg_input.clear()
        
        # Assign the functions to the buttons
        self._btn_commit_modification.configure(command=commit)
        self._btn_cancel_modification.configure(command=cancel)
        self._btn_currentZCoor_commit.configure(command=insert_and_commit)
        self._entry_newZCoor.bind('<Return>', lambda event: commit())  # Pressing Enter commits the modification
        
    # > Modify the z-coordinates <
        list_new_coordinates = mapping_coordinates.mapping_coordinates.copy()
        # Enable the widgets
        self._reset_zMod_widgets('normal')
        
        
        # Modify the z-coordinates
        for i in range(len(list_new_coordinates)):
            reset_flg_input()
            # Get the current z-coordinate
            old_z_value_um = list_new_coordinates[i][2]*1e3
            self._str_oldZCoor.set(f'{old_z_value_um:.0f}')
            self._entry_newZCoor.delete(0, tk.END)  # Clear the entry field
            self._entry_newZCoor.insert(0, f'{old_z_value_um:.0f}')  # Insert the current z-coordinate
            
            self._motion_controller.go_to_coordinates(
                coor_x_mm= list_new_coordinates[i][0],
                coor_y_mm= list_new_coordinates[i][1],
                coor_z_mm= list_new_coordinates[i][2],
            )
            
            self._str_coorinfo_val.set(f'{len(list_new_coordinates)-i}/{len(list_new_coordinates)}')
            
            flg_input.wait()  # Wait for the user to input the new z-coordinate
            if self._modify_response == 'cancel':
                messagebox.showinfo("Cancelled", "Z-coordinates modification cancelled.")
                self._reset_zMod_widgets('disabled')
                return
            try:
                new_z_value_um = float(self._entry_newZCoor.get())
                new_coor_mm = (list_new_coordinates[i][0], list_new_coordinates[i][1], new_z_value_um*1e-3)
                valid = self._motion_controller.check_coordinates(new_coor_mm)
                if not valid: raise ValueError("Out of the stage's travel range")
            except Exception as e:
                i-=1 # Repeat the current iteration if the input is invalid
                messagebox.showerror("Error", f"Invalid input for new Z-coordinate: {e}")
                continue
            # Update the z-coordinate
            list_new_coordinates[i] = new_coor_mm
        
        self._str_coorinfo_val.set('N/A')
        
        while True:
            # Request for a new name
            new_name = messagebox_request_input(
                "New Mapping Unit Name",
                "Please enter a new name for the modified mapping coordinates:",
                default=f"{selected_unit_name}_z modified"
            )
            
            # Add the new mapping coordinates to the hub
            new_mapping_coor = MeaCoor_mm(new_name,list_new_coordinates)
            try: self._coorHub.append(new_mapping_coor); break
            except Exception as e: messagebox.showerror("Error", f"Failed to add new mapping coordinates: {e}"); continue
        
        messagebox.showinfo("Success", "Z-coordinates modified successfully.")
        self._reset_zMod_widgets('disabled')
        
    
def test():
    from iris.gui.motion_video import generate_dummy_motion_controller
    
    root = tk.Tk()
    root.title('Test')
    
    frm_motion = generate_dummy_motion_controller(root)
    frm_motion._init_workers()
    frm_motion.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
    
    coorUnit = MeaCoor_mm(
        mappingUnit_name='Test Mapping Unit',
        mapping_coordinates=[(0, 0, 0), (1, 1, 1), (2, 2, 2), (3, 3, 3)]
    )
    
    coorHub = List_MeaCoor_Hub()
    coorHub.append(coorUnit)
    
    frm_coor_mod = EveryZ(
        root,
        mappingCoorHub=coorHub,
        motion_controller=frm_motion,
    )
    
    frm_coor_mod.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
    
    root.mainloop()
    
if __name__ == '__main__':
    test()