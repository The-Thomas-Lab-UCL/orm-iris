"""
A GUI module to modify a mapping coordinates list by translating 
the coordinates in the X, Y and Z direction.
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

from iris.gui.motion_video import Frm_MotionController
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.utils.general import *

class TranslateXYZ(tk.Frame):
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
        self._frm_modifier = tk.LabelFrame(self, text='XYZ-coordinates translation', padx=5, pady=5)
        frm_options = tk.LabelFrame(self, text='Options', padx=5, pady=5)
        
        row=0; col_curr=0
        frm_instruction.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        frm_mapUnit_selection.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        self._frm_modifier.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
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
        
    # >>> Z-coordinates modification widgets <<<
        self._sfrm_reference_loc = tk.LabelFrame(self._frm_modifier, text='Translation reference location', padx=5, pady=5)
        self._init_referenceLocation_widgets()
        
        lbl_old_coor = tk.Label(self._frm_modifier, text='Reference coordinate [μm]:')
        self._str_refCoor = tk.StringVar(value='N/A')
        lbl_old_z_value = tk.Label(self._frm_modifier, textvariable=self._str_refCoor)
        
        lbl_new_z_coor = tk.Label(self._frm_modifier, text='New coordinate [μm]:')
        ssfrm_entry = self._init_coorEntryFields()
        self._btn_currentCoor = tk.Button(self._frm_modifier, text='Insert current coordinate (X,Y,Z)',\
            command=self._insert_current_coordinate)
        
        self._btn_commit_modification = tk.Button(self._frm_modifier, text='Commit modification',
                                                  command=self._run_coor_modification)
        
        row=0; col_curr=0; col_max=0
        self._sfrm_reference_loc.grid(row=row, column=col_curr, sticky='nsew', padx=5, pady=5,columnspan=2); row+=1; col_curr=0
        lbl_old_coor.grid(row=row, column=col_curr, sticky='w', padx=5, pady=5); col_curr+=1
        lbl_old_z_value.grid(row=row, column=col_curr, sticky='w', padx=5, pady=5); row+=1; col_max=max(col_max, col_curr); col_curr=0
        
        lbl_new_z_coor.grid(row=row, column=col_curr, sticky='w', padx=5, pady=5); col_curr+=1
        ssfrm_entry.grid(row=row, column=col_curr, sticky='ew', padx=5, pady=5); row+=1; col_max=max(col_max, col_curr); col_curr=0
        
        self._btn_currentCoor.grid(row=row, column=col_curr, sticky='ew', padx=5, pady=5); col_curr+=1
        self._btn_commit_modification.grid(row=row, column=col_curr, sticky='ew', padx=5, pady=5); col_curr+=1
        
        col_max = max(col_max, col_curr)
        [self._frm_modifier.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [self._frm_modifier.grid_columnconfigure(i, weight=1) for i in range(col_max+1)]
        
    # >>> Options frame <<<
        self._bool_auto_selectLast = tk.BooleanVar(value=True)  # Default to selected
        self._bool_auto_moveLastShift = tk.BooleanVar(value=True)  # Default to
        chk_auto_selectLast = tk.Checkbutton(frm_options, text='Auto-select last modified mapping unit', state='normal',
                                             variable=self._bool_auto_selectLast)
        chk_auto_moveLastShift = tk.Checkbutton(frm_options, text='Auto-move the stage using the last coordinate shift', state='normal',
                                                variable=self._bool_auto_moveLastShift)
        
        chk_auto_selectLast.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        chk_auto_moveLastShift.grid(row=1, column=0, sticky='w', padx=5, pady=5)
        
    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        self._modify_response:Literal['commit', 'cancel'] = None    # Response from the modification process
        
    # >>> Others <<<
        self._coorHub.add_observer(self._update_list_units)
        self._update_list_units()

    def _init_coorEntryFields(self):
        """
        Initialises the entry fields for the new coordinates
        """
        ssfrm_entry = tk.Frame(self._frm_modifier)
        self._entry_newCoor_x = tk.Entry(ssfrm_entry)
        self._entry_newCoor_y = tk.Entry(ssfrm_entry)
        self._entry_newCoor_z = tk.Entry(ssfrm_entry)
        self._entry_newCoor_x.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        self._entry_newCoor_y.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self._entry_newCoor_z.grid(row=0, column=2, sticky='ew', padx=5, pady=5)
        
        # Bind the entry fields to running the modification when the Enter key is pressed
        self._entry_newCoor_x.bind('<Return>', lambda event: self._run_coor_modification())
        self._entry_newCoor_y.bind('<Return>', lambda event: self._run_coor_modification())
        self._entry_newCoor_z.bind('<Return>', lambda event: self._run_coor_modification())
        
        return ssfrm_entry
        
    def _init_referenceLocation_widgets(self):
        """Initialises the widgets for the reference location"""
        self._ssfrm_reference_loc_xy = tk.LabelFrame(self._sfrm_reference_loc, text='XY reference location', padx=5, pady=5)
        self._ssfrm_reference_loc_z = tk.LabelFrame(self._sfrm_reference_loc, text='Z reference location', padx=5, pady=5)
        self._ssfrm_reference_loc_xy.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        self._ssfrm_reference_loc_z.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
        
        # Set the variables for the radio buttons
        self._radio_xy = tk.StringVar(value='cc')  # Default to center center
        self._radio_z = tk.StringVar(value='btm')  # Default to bottom
        
        # XY reference location radio buttons
        radio_topleft = tk.Radiobutton(self._ssfrm_reference_loc_xy, text='Top Left', variable=self._radio_xy, value='tl',command=self._update_reference_coordinates_label)
        radio_topcenter = tk.Radiobutton(self._ssfrm_reference_loc_xy, text='Top Center', variable=self._radio_xy, value='tc',command=self._update_reference_coordinates_label)
        radio_topright = tk.Radiobutton(self._ssfrm_reference_loc_xy, text='Top Right', variable=self._radio_xy, value='tr',command=self._update_reference_coordinates_label)
        radio_centerleft = tk.Radiobutton(self._ssfrm_reference_loc_xy, text='Center Left', variable=self._radio_xy, value='cl',command=self._update_reference_coordinates_label)
        radio_centercenter = tk.Radiobutton(self._ssfrm_reference_loc_xy, text='Center Center', variable=self._radio_xy, value='cc',command=self._update_reference_coordinates_label)
        radio_centerright = tk.Radiobutton(self._ssfrm_reference_loc_xy, text='Center Right', variable=self._radio_xy, value='cr',command=self._update_reference_coordinates_label)
        radio_bottomleft = tk.Radiobutton(self._ssfrm_reference_loc_xy, text='Bottom Left', variable=self._radio_xy, value='bl',command=self._update_reference_coordinates_label)
        radio_bottomcenter = tk.Radiobutton(self._ssfrm_reference_loc_xy, text='Bottom Center', variable=self._radio_xy, value='bc',command=self._update_reference_coordinates_label)
        radio_bottomright = tk.Radiobutton(self._ssfrm_reference_loc_xy, text='Bottom Right', variable=self._radio_xy, value='br',command=self._update_reference_coordinates_label)
        
        # Z reference location radio buttons
        radio_z_top = tk.Radiobutton(self._ssfrm_reference_loc_z, text='Top', variable=self._radio_z, value='top',command=self._update_reference_coordinates_label)
        radio_z_center = tk.Radiobutton(self._ssfrm_reference_loc_z, text='Center', variable=self._radio_z, value='ctr',command=self._update_reference_coordinates_label)
        radio_z_bottom = tk.Radiobutton(self._ssfrm_reference_loc_z, text='Bottom', variable=self._radio_z, value='btm',command=self._update_reference_coordinates_label)
        
        # Place the radio buttons in the XY reference location frame
        radio_topleft.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        radio_topcenter.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        radio_topright.grid(row=0, column=2, sticky='w', padx=5, pady=5)
        radio_centerleft.grid(row=1, column=0, sticky='w', padx=5, pady=5)
        radio_centercenter.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        radio_centerright.grid(row=1, column=2, sticky='w', padx=5, pady=5)
        radio_bottomleft.grid(row=2, column=0, sticky='w', padx=5, pady=5)
        radio_bottomcenter.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        radio_bottomright.grid(row=2, column=2, sticky='w', padx=5, pady=5)
        
        # Place the radio buttons in the Z reference location frame
        radio_z_top.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        radio_z_center.grid(row=1, column=0, sticky='w', padx=5, pady=5)
        radio_z_bottom.grid(row=2, column=0, sticky='w', padx=5, pady=5)
        
    def _empty_coorInputFields(self):
        """Empties the coordinate input fields"""
        self._entry_newCoor_x.delete(0, tk.END)
        self._entry_newCoor_y.delete(0, tk.END)
        self._entry_newCoor_z.delete(0, tk.END)
    
    def _update_reference_coordinates_label(self):
        """
        Updates the label showing the current reference coordinates
        """
        """Updates the label showing the current reference coordinates"""
        unit_name = self._combo_mapUnit.get()
        if unit_name not in self._dict_mapUnit: self._str_refCoor.set('N/A'); return
        
        mappingCoor = self._dict_mapUnit.get(unit_name)
        if not isinstance(mappingCoor, MeaCoor_mm): self._str_refCoor.set('N/A'); return
        
        coorRef_xy = self._get_reference_coordinates_XY(mappingCoor)
        coorRef_z = self._get_reference_coordinates_Z(mappingCoor)
        
        self._str_refCoor.set(f'({coorRef_xy[0]*1e3:.0f}, {coorRef_xy[1]*1e3:.0f}, {coorRef_z*1e3:.0f}) [μm]')
        
    def _get_reference_coordinates_XY(self, mappingCoor:MeaCoor_mm) -> tuple[float, float]:
        """Gets the reference coordinates for the mapping coordinates
        
        Args:
            mappingCoor (MappingCoordinates_mm): The mapping coordinates to get the reference coordinates from
            
        Returns:
            tuple[float, float]: The reference coordinates in mm (x, y)
        """
        assert isinstance(mappingCoor, MeaCoor_mm), "Invalid mapping coordinates type"
        
        x_min = min(coor[0] for coor in mappingCoor.mapping_coordinates)
        x_max = max(coor[0] for coor in mappingCoor.mapping_coordinates)
        y_min = min(coor[1] for coor in mappingCoor.mapping_coordinates)
        y_max = max(coor[1] for coor in mappingCoor.mapping_coordinates)
        x_ctr = (x_min + x_max) / 2
        y_ctr = (y_min + y_max) / 2
        
        if self._radio_xy.get() == 'tl':    return (x_min, y_max)
        elif self._radio_xy.get() == 'tc':  return (x_ctr, y_max)
        elif self._radio_xy.get() == 'tr':  return (x_max, y_max)
        elif self._radio_xy.get() == 'cl':  return (x_min, y_ctr)
        elif self._radio_xy.get() == 'cc':  return (x_ctr, y_ctr)
        elif self._radio_xy.get() == 'cr':  return (x_max, y_ctr)
        elif self._radio_xy.get() == 'bl':  return (x_min, y_min)
        elif self._radio_xy.get() == 'bc':  return (x_ctr, y_min)
        elif self._radio_xy.get() == 'br':  return (x_max, y_min)
        else: raise ValueError("No reference location selected")
            
    def _get_reference_coordinates_Z(self, mappingCoor:MeaCoor_mm) -> float:
        """Gets the reference Z-coordinate for the mapping coordinates
        
        Args:
            mappingCoor (MappingCoordinates_mm): The mapping coordinates to get the reference Z-coordinate from
            
        Returns:
            float: The reference Z-coordinate in mm
        """
        assert isinstance(mappingCoor, MeaCoor_mm), "Invalid mapping coordinates type"
        
        z_min = min(coor[2] for coor in mappingCoor.mapping_coordinates)
        z_max = max(coor[2] for coor in mappingCoor.mapping_coordinates)
        z_ctr = (z_min + z_max) / 2
        
        if self._radio_z.get() == 'top':    return z_max
        elif self._radio_z.get() == 'ctr':  return z_ctr
        elif self._radio_z.get() == 'btm':  return z_min
        else: raise ValueError("No reference Z-coordinate selected")
        
    def _insert_current_coordinate(self):
        """Inserts the current z-coordinate from the motion controller into the
        coordinate entry fields"""
        coor = self._motion_controller.get_coordinates_closest_mm()
        coorx_um = coor[0] * 1e3
        coory_um = coor[1] * 1e3
        coorz_um = coor[2] * 1e3
        
        self._entry_newCoor_x.delete(0, tk.END)
        self._entry_newCoor_y.delete(0, tk.END)
        self._entry_newCoor_z.delete(0, tk.END)
        self._entry_newCoor_x.insert(0, f'{coorx_um:.0f}')
        self._entry_newCoor_y.insert(0, f'{coory_um:.0f}')
        self._entry_newCoor_z.insert(0, f'{coorz_um:.0f}')
        
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
        
    @thread_assign
    def _run_coor_modification(self):
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
        
    # > Modify the coordinates <
        try:
            coorRef_xy = self._get_reference_coordinates_XY(mapping_coordinates)
            coorRef_z = self._get_reference_coordinates_Z(mapping_coordinates)
            
            new_coor_x = float(self._entry_newCoor_x.get()) * 1e-3
            new_coor_y = float(self._entry_newCoor_y.get()) * 1e-3
            new_coor_z = float(self._entry_newCoor_z.get()) * 1e-3
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
            return
        
        # Translate the coordinates
        shiftx = new_coor_x - coorRef_xy[0]
        shifty = new_coor_y - coorRef_xy[1]
        shiftz = new_coor_z - coorRef_z
        
        list_new_coor = []
        for x, y, z in mapping_coordinates.mapping_coordinates:
            new_x = x + shiftx
            new_y = y + shifty
            new_z = z + shiftz
            list_new_coor.append((new_x, new_y, new_z))
        
        while True:
            # Request for a new name
            new_name = messagebox_request_input(
                "New Mapping Unit Name",
                "Please enter a new name for the modified mapping coordinates:",
                default=f"{selected_unit_name}"
            )
            
            # Add the new mapping coordinates to the hub
            new_mapping_coor = MeaCoor_mm(new_name,list_new_coor)
            try: self._coorHub.append(new_mapping_coor); break
            except KeyError as e:
                retry = messagebox.askyesno("Error", f"Mapping unit '{new_name}' already exists. Please choose a different name.\n\nError: {e}\n\nDo you want to try again?")
                if not retry: return
            except Exception as e: messagebox.showerror("Error", f"Failed to add new mapping coordinates: {e}"); break
        
        self._empty_coorInputFields()
        messagebox.showinfo("Success", "Z-coordinates modified successfully.")
        
        if self._bool_auto_selectLast.get():
            self._combo_mapUnit.set(new_mapping_coor.mappingUnit_name)
            self._update_reference_coordinates_label()
        
        flg_autoMove = False
        if self._bool_auto_selectLast.get() and self._bool_auto_moveLastShift.get():
            flg_autoMove = messagebox.askyesno("Move Stage",
                "Auto-move is selected\nDo you want to move the stage to the new reference coordinate with the applied shift?")
        if flg_autoMove:
            # Move the stage to the new reference coordinate + shift
            new_xy = self._get_reference_coordinates_XY(new_mapping_coor)
            new_z = self._get_reference_coordinates_Z(new_mapping_coor)
            x, y, z = new_xy[0] + shiftx, new_xy[1] + shifty, new_z + shiftz
            self._motion_controller.go_to_coordinates(x,y,z)
    
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
    
    frm_coor_mod = TranslateXYZ(
        root,
        mappingCoorHub=coorHub,
        motion_controller=frm_motion,
    )
    
    frm_coor_mod.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
    
    root.mainloop()
    
if __name__ == '__main__':
    test()