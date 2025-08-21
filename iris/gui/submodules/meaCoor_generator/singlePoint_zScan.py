"""
An instance that manages a basic mapping method in tkinter
"""
import tkinter as tk
from tkinter import messagebox

import numpy as np
from math import floor

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))

from iris.gui.motion_video import Frm_MotionController
from iris.utils.general import *

class singlePoint_zScan(tk.Frame):
    def __init__(self,container_frame,motion_controller:Frm_MotionController,status_bar:tk.Label=None,
                 *args, **kwargs) -> None:
        """Initializes the mapping method
        
        Args:
            container_frame (tk.Frame): The frame to place the mapping method
            motion_controller (Frm_MotionController): The motion controller to control the stage
            status_bar (tk.Label, optional): The status bar to show the status of the mapping method. Defaults to None.
        """
        # Place itself in the given master frame (container)
        super().__init__(container_frame)
        
        # Sets up the other controllers
        self._motion_controller = motion_controller
        self._statbar = status_bar
        self._bg_colour = self._statbar.cget('background')
        
        # Make the widgets to store the coordinates
        self._lbl_coor_xy = tk.Label(self,text='Scan coordinates (X,Y) [μm]:')
        self._entry_coor1x = tk.Entry(self)
        self._entry_coor1y = tk.Entry(self)
        self._btn_storecurrent_coor1 = tk.Button(self,text='Store current coor.',
                                            command=lambda: self._store_current_coor_xy())
        
        self._lbl_coor_z1 = tk.Label(self,text='Start z-coordinate (Z) [μm]:')
        self._entry_coor_z1 = tk.Entry(self)
        self._btn_storecurrent_coor_z1 = tk.Button(self,text='Store current coor.',
                                            command=lambda: self._store_current_coor_z1())
        
        self._lbl_coor_z2 = tk.Label(self,text='Start z-coordinate (Z) [μm]:')
        self._entry_coor_z2 = tk.Entry(self)
        self._btn_storecurrent_coor_z2 = tk.Button(self,text='Store current coor.',
                                            command=lambda: self._store_current_coor_z2())
        
        # Make the widgets to manage the rest of the mapping parameters
        self._lbl_res = tk.Label(self,text='Mapping resolution (Z) [μm]:')
        self._entry_res_z = tk.Entry(self)
        
        # Bind return to the set_coor buttons
        self._entry_coor1x.bind('<Return>',lambda event: self._check_coordinates())
        self._entry_coor1y.bind('<Return>',lambda event: self._check_coordinates())
        self._entry_coor_z1.bind('<Return>',lambda event: self._check_coordinates())
        self._entry_coor_z2.bind('<Return>',lambda event: self._check_coordinates())
        self._entry_res_z.bind('<Return>',lambda event: self._check_coordinates())
        
        # Pack the widgets
        row=0
        self._lbl_coor_xy.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._entry_coor1x.grid(row=row,column=0)
        self._entry_coor1y.grid(row=row,column=1)
        row+=1
        self._btn_storecurrent_coor1.grid(row=row,column=1)
        
        row+=1
        self._lbl_coor_z1.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._entry_coor_z1.grid(row=row,column=0)
        row+=1
        self._btn_storecurrent_coor_z1.grid(row=row,column=1)
        
        row+=1
        self._lbl_coor_z2.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._entry_coor_z2.grid(row=row,column=0)
        row+=1
        self._btn_storecurrent_coor_z2.grid(row=row,column=1)
        
        row+=1
        self._lbl_res.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._entry_res_z.grid(row=row,column=0)

    def get_mapping_coordinates_mm(self):
        """ 
        Returns the mapping coordinates
        
        Returns:
            list: List of tuple (x,y,z) coordinates
        """
        # Make sure to keep the generated coordinates up to date
        return self._generate_mapping_coordinates()
    
    def _store_current_coor_xy(self) -> None:
        """Stores the current coordinates in the entry boxes"""
        # Get the current coordinates
        coor = self._motion_controller.get_coordinates_closest_mm()
        
        # Store the coordinates in the entry boxes
        self._entry_coor1x.delete(0,tk.END)
        self._entry_coor1x.insert(0,coor[0]*1e3)
        self._entry_coor1y.delete(0,tk.END)
        self._entry_coor1y.insert(0,coor[1]*1e3)
    
    def _store_current_coor_z1(self) -> None:
        """Stores the current coordinates in the entry boxes"""
        # Get the current coordinates
        coor = self._motion_controller.get_coordinates_closest_mm()
        
        # Store the coordinates in the entry boxes
        self._entry_coor_z1.delete(0,tk.END)
        self._entry_coor_z1.insert(0,coor[2]*1e3)
        
    def _store_current_coor_z2(self) -> None:
        """Stores the current coordinates in the entry boxes"""
        # Get the current coordinates
        coor = self._motion_controller.get_coordinates_closest_mm()
        
        # Store the coordinates in the entry boxes
        self._entry_coor_z2.delete(0,tk.END)
        self._entry_coor_z2.insert(0,coor[2]*1e3)
    
    def _check_coordinates(self) -> tuple[float,float,float,float] | None:
        """Checks if the coordinates are valid"""
        # Retrieve the coordinates
        try:
            coor_xy_um = (float(self._entry_coor1x.get()),float(self._entry_coor1y.get()))
            
            coor_z1_um = float(self._entry_coor_z1.get())
            coor_z2_um = float(self._entry_coor_z2.get())
            
            res_z_um = float(self._entry_res_z.get())
            
            # Calculate the number of points in the z direction
            num_points_z = floor(abs(coor_z2_um-coor_z1_um)/res_z_um)+1
            messagebox.showinfo('Info',f'Entries validated:\nNumber of points in z direction: {num_points_z}')
            
            return coor_xy_um, coor_z1_um, coor_z2_um, res_z_um
        except ValueError:
            messagebox.showerror('Error','Invalid entries. Please ensure that all entries contain valid coordinates/resolution values.')
            return None
        
    def _generate_mapping_coordinates(self) -> list[tuple[float,float,float]]:
        """
        Generates the mapping coordinates based on the given parameters
        
        Raises:
            ValueError: If the coordinates are not valid
        
        Returns:
            list: List of tuple (x,y,z) coordinates
        """
        res = self._check_coordinates()
        if res is None: raise ValueError('Invalid coordinates')
        
        coor_xy_um, coor_z1_um, coor_z2_um, res_z_um = res
        
        # Generate the mapping coordinates
        list_z_um = np.linspace(coor_z1_um,coor_z2_um,num=int(abs(coor_z2_um-coor_z1_um)/res_z_um)+1)
        list_mapping_coor_mm = [(coor_xy_um[0]/1e3,coor_xy_um[1]/1e3,z/1e3) for z in list_z_um]
        
        return list_mapping_coor_mm
        
    
def test_rect1():
    root = tk.Tk()
    root.title('Test')
    
    status_bar = tk.Label(root,text='Ready',bd=1,relief=tk.SUNKEN,anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM,fill=tk.X)
    motion_controller = Frm_MotionController(root,True)
    
    mapping_method = singlePoint_zScan(root,motion_controller,status_bar)
    mapping_method.pack()
    
    root.mainloop()
    
if __name__ == '__main__':
    test_rect1()