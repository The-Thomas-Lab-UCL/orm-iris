"""
An instance that manages a basic mapping method in tkinter
"""

import tkinter as tk

import numpy as np

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))

from iris.gui.motion_video import Frm_MotionController
from iris.utils.general import *

class Rect_EndToEnd(tk.Frame):
    """A basic class that manage a mapping method

    Args:
        tk (tkinter): tkinter library
    """
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
        self._lbl_coor1 = tk.Label(self,text='Start coordinates (X,Y) [μm]:')
        self._entry_coor1x = tk.Entry(self)
        self._entry_coor1y = tk.Entry(self)
        self._btn_storecurrent_coor1 = tk.Button(self,text='Store current coor.',
                                            command=lambda: self._store_current_coor1())
        self._btn_goto_coor1 = tk.Button(self,text='Set',command=lambda: self._set_coor1())
        
        self._lbl_coor2 = tk.Label(self,text='End coordinates (X,Y) [μm]:')
        self._entry_coor2x = tk.Entry(self)
        self._entry_coor2y = tk.Entry(self)
        self._btn_storecurrent_coor2 = tk.Button(self,text='Store current coor.',
                                            command=lambda: self._store_current_coor2())
        self._btn_goto_coor2 = tk.Button(self,text='Set',
                                    command=lambda: self._set_coor2())
        
        self._lbl_coorz = tk.Label(self,text='Z-coordinate (Z) [μm]:')
        self._entry_coorz = tk.Entry(self)
        self._btn_storecurrent_coorz = tk.Button(self,text='Store current coor.',
                                            command=lambda: self._store_current_coorz())
        self._btn_goto_coorz = tk.Button(self,text='Set',
                                    command=lambda: self._set_coorz())
        
        # Make the widgets to manage the rest of the mapping parameters
        self._lbl_res = tk.Label(self,text='Mapping resolution (X,Y) [_μm, _μm]:')
        self._spin_xres = tk.Spinbox(self,from_=1,to=1000,increment=1)
        self._spin_yres = tk.Spinbox(self,from_=1,to=1000,increment=1)
        # Button to store the mapping parameters
        self._btn_res = tk.Button(self,text='Set',command=lambda: self._store_resolution())
        # Button to generate and store the mapping coordinates
        self._btn_gen = tk.Button(self,text='Generate coordinates',
                                    command=lambda: self._generate_mapping_coordinates())
        
        # Bind return to the set_coor buttons
        self._entry_coor1x.bind('<Return>',lambda event: self._set_coor1())
        self._entry_coor1y.bind('<Return>',lambda event: self._set_coor1())
        self._entry_coor2x.bind('<Return>',lambda event: self._set_coor2())
        self._entry_coor2y.bind('<Return>',lambda event: self._set_coor2())
        self._entry_coorz.bind('<Return>',lambda event: self._set_coorz())
        self._spin_xres.bind('<Return>',lambda event: self._store_resolution())
        self._spin_yres.bind('<Return>',lambda event: self._store_resolution())
        
        # Pack the widgets
        row=0
        self._lbl_coor1.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._entry_coor1x.grid(row=row,column=0)
        self._entry_coor1y.grid(row=row,column=1)
        row+=1
        self._btn_goto_coor1.grid(row=row,column=0)
        self._btn_storecurrent_coor1.grid(row=row,column=1)
        
        row+=1
        self._lbl_coor2.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._entry_coor2x.grid(row=row,column=0)
        self._entry_coor2y.grid(row=row,column=1)
        row+=1
        self._btn_goto_coor2.grid(row=row,column=0)
        self._btn_storecurrent_coor2.grid(row=row,column=1)
        
        row+=1
        self._lbl_coorz.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._entry_coorz.grid(row=row,column=0)
        row+=1
        self._btn_goto_coorz.grid(row=row,column=0)
        self._btn_storecurrent_coorz.grid(row=row,column=1)
        
        row+=1
        self._lbl_res.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._spin_xres.grid(row=row,column=0)
        self._spin_yres.grid(row=row,column=1)
        row+=1
        self._btn_res.grid(row=row,column=0)
        self._btn_gen.grid(row=row,column=1)

    def get_mapping_coordinates_mm(self):
        """ 
        Returns the mapping coordinates
        
        Returns:
            list: List of tuple (x,y,z) coordinates
        """
        # Make sure to keep the generated coordinates up to date
        self._generate_mapping_coordinates()
        return self._mapping_coordinates
    
    def _generate_mapping_coordinates(self):
        """
        Generates the mapping coordinates. Also stores them in its own variable and the main
        operation variable
        """
        if self._coor_xy1_mm[0] == None or self._coor_xy2_mm[0] == None or self._coor_z_mm == None:
            self._status_update(message='Please set the coordinates first', bg_colour='yellow')
            return
        
        if self._m1_pointsx == None or self._m1_pointsy == None:
            self._status_update(message='Please set the resolution first', bg_colour='yellow')
            return
        
        # Define the grid boundaries
        x_min, y_min = self._coor_xy1_mm
        x_max, y_max = self._coor_xy2_mm
        z_const = self._coor_z_mm

        # Number of points in each direction
        num_pointsx = self._m1_pointsx
        num_pointsy = self._m1_pointsy

        # Generate linearly spaced points along each axis
        x_points = np.linspace(x_min, x_max, num_pointsx)
        y_points = np.linspace(y_min, y_max, num_pointsy)

        # Create the grid
        X, Y = np.meshgrid(x_points, y_points)
        self._mapping_coordinates = [(x, y, z_const) for x, y in zip(X.flatten(), Y.flatten())]
        
        self._status_update(message='Mapping coordinates generated')
    
    def _reset_self(self):
        self._coor_xy1_mm = [None,None]     # Stores the start coordinates for the mapping. Required for movement boundary setting. Type: float
        self._coor_xy2_mm = [None,None]     # Stores the end coordinates for the mapping. Required for movement boundary setting. Type: float
        self._coor_z_mm = None              # Stores the start z-coordinate for the mapping. Required for movement boundary setting. Type: float
        self._m1_pointsx = None             # Stores the mapping resolution in the x-direction
        self._m1_pointsy = None             # Stores the mapping resolution in the y-direction
        self._m1_resx_um = None             # Stores the mapping resolution in the x-direction
        self._m1_resy_um = None             # Stores the mapping resolution in the y-direction
        self._mapping_coordinates = None # Stores the mapping coordinates in a (x,y,z) list
        
        # Reset the label widgets
        self.after(10,lambda: self._lbl_coor1.configure(text='Start coordinates (X,Y):'))
        self.after(10,lambda: self._lbl_coor2.configure(text='End coordinates (X,Y):'))
        self.after(10,lambda: self._lbl_coorz.configure(text='Z coordinates (Z): '))
        self.after(10,self._lbl_res.configure(text='Mapping resolution (X,Y) [_μm, _μm]:'))
    
    def _reset_mapping_coordinates(self):
        self._m1_pointsx = None             # Stores the mapping resolution in the x-direction
        self._m1_pointsy = None             # Stores the mapping resolution in the y-direction
        self._m1_resx_um = None             # Stores the mapping resolution in the x-direction
        self._m1_resy_um = None             # Stores the mapping resolution in the y-direction
        self._mapping_coordinates = None # Stores the mapping coordinates in a (x,y,z) list
        
        self.after(10,self._lbl_res.configure(text='Mapping resolution (X,Y) [_μm, _μm]:'))
    
    def _set_resolution(self):
        """
        Sets the resolution of the mapping in the x and y direction
        using the stored distances
        """
        distx = self._coor_xy2_mm[0] - self._coor_xy1_mm[0]
        disty = self._coor_xy2_mm[1] - self._coor_xy1_mm[1]
        
        self._m1_resx_um = (distx/self._m1_pointsx)*1000
        self._m1_resy_um = (disty/self._m1_pointsy)*1000
    
    def _store_resolution(self):
        """
        Stores the resolution set in the spinbox for the x and y mapping resolutions.
        Also updates the label.
        """
        try:
            # Try retreiving the value and convert it into integer
            m1_pointsx = int(self._spin_xres.get())
            m1_pointsy = int(self._spin_yres.get())
        except Exception as e:
            print('_store_resolution',e)
            self._status_update(message='Unable to store the requested resolution',bg_colour='yellow')
            return
        
        # Save it
        self._m1_pointsx = m1_pointsx
        self._m1_pointsy = m1_pointsy
        
        try:
            self._set_resolution()
            # Update the label
            self.after(10,self._lbl_res.configure(text='Mapping resolution: {}X {}Y [{:.0f} μm, {:.0f} μm]'
                .format(self._m1_pointsx,self._m1_pointsy,self._m1_resx_um,self._m1_resy_um)))
        except:
            self.after(10,self._lbl_res.configure(text='Mapping resolution: {}X {}Y [_μm, _μm]'
                .format(self._m1_pointsx,self._m1_pointsy)))
    
    def _store_current_coorz(self):
        """
        Gets the current stage coordinate and store it as the initial position
        """
        try:
            # Get the current coordinates from the device
            coor_z = self._motion_controller.get_coordinates_closest_mm()[2]
        except Exception as e:
            print('_store_current_coorz',e)
            return
        
        # Store the coordinate if all checks out
        self._coor_z_mm = coor_z
        
        # Reset the mapping coordinates to prevent previous coordinates from being used
        self._reset_mapping_coordinates()
        
        # Update the label
        self.after(10,lambda: self._lbl_coorz.configure(text='Z coordinates [μm]: {:.1f}Z'
                                    .format(self._coor_z_mm*1e3)))
        
        # Update the status bar
        self._status_update(message='Mapping start coordinate stored')
    
    @thread_assign
    def _set_coorz(self):
        """
        Attempts to go to the specified coordinate. If successful, allows the user to store this 
        as a coordinate
        """
        try:
            coor_z_mm = float(self._entry_coorz.get())/1e3
        except ValueError as e:
            self._status_update(message='Please enter numbers for the coordinates', bg_colour='yellow')
            return
        
        self._coor_z_mm = coor_z_mm
        
        # Reset the mapping coordinates to prevent previous coordinates from being used
        self._reset_mapping_coordinates()
        
        # Update the label
        self.after(10,lambda: self._lbl_coorz.configure(text='Z coordinates [μm]: {:.1f}Z'
                                    .format(self._coor_z_mm*1e3)))
        
        # Update the status bar
        self._status_update(message='Mapping Z coordinate stored')
    
    def _store_current_coor2(self):
        """
        Gets the current stage coordinate and store it as the initial position
        """
        try:
            # Get the current coordinates from the device
            coor_x_mm,coor_y_mm = self._motion_controller.get_coordinates_closest_mm()[:2]
        except Exception as e:
            print('_store_current_coor2',e)
            return
        
        self._coor_xy2_mm = [coor_x_mm,coor_y_mm]
        
        # Reset the mapping coordinates to prevent previous coordinates from being used
        self._reset_mapping_coordinates()
        
        # Update the label
        self.after(10,lambda: self._lbl_coor2.configure(text='End coordinates [μm]: {:.1f}X {:.1f}Y'
                                    .format(self._coor_xy2_mm[0]*1e3,self._coor_xy2_mm[1]*1e3)))
        
        # Update the status bar
        self._status_update(message='Mapping XY start coordinate stored')
    
    @thread_assign
    def _set_coor2(self):
        """
        Attempts to go to the specified coordinate. If successful, allows the user to store this 
        as a coordinate
        """
        try:
            coor_x_mm = float(self._entry_coor2x.get())/1e3
            coor_y_mm = float(self._entry_coor2y.get())/1e3
        except ValueError as e:
            self._status_update(message='Please enter numbers for the coordinates', bg_colour='yellow')
            return
        
        self._coor_xy2_mm = [coor_x_mm,coor_y_mm]
        
        # Reset the mapping coordinates to prevent previous coordinates from being used
        self._reset_mapping_coordinates()
        
        # Update the label
        self.after(10,lambda: self._lbl_coor2.configure(text='End coordinates [μm]: {:.1f}X {:.1f}Y'
                                    .format(float(str(self._coor_xy2_mm[0]))*1e3,float(str(self._coor_xy2_mm[1]))*1e3)))
        
        # Update the status bar
        self._status_update(message='Mapping XY start coordinate stored')
    
    def _store_current_coor1(self):
        """
        Gets the current stage coordinate and store it as the initial position
        """
        try:
            # Get the current coordinates from the device
            coor_x_mm,coor_y_mm = self._motion_controller.get_coordinates_closest_mm()[:2]
        except Exception as e:
            print('_store_current_coor1',e)
            return
        
        self._coor_xy1_mm = [coor_x_mm,coor_y_mm]
        
        # Reset the mapping coordinates to prevent previous coordinates from being used
        self._reset_mapping_coordinates()
        
        # Update the label
        self.after(10,lambda: self._lbl_coor1.configure(text='Start coordinates [μm]: {:.1f}X {:.1f}Y'
                                    .format(self._coor_xy1_mm[0]*1e3,self._coor_xy1_mm[1]*1e3)))
        
        # Update the status bar
        self._status_update(message='Mapping XY start coordinate stored')
    
    @thread_assign
    def _set_coor1(self):
        """
        Attempts to go to the specified coordinate. If successful, allows the user to store this 
        as a coordinate
        """
        try:
            coor_x_mm = float(self._entry_coor1x.get())/1e3
            coor_y_mm = float(self._entry_coor1y.get())/1e3
        except ValueError as e:
            self._status_update(message='Please enter numbers for the coordinates', bg_colour='yellow')
            return
        
        self._coor_xy1_mm = [coor_x_mm,coor_y_mm]
        
        # Reset the mapping coordinates to prevent previous coordinates from being used
        self._reset_mapping_coordinates()
        
        # Update the label
        self.after(10,lambda: self._lbl_coor1.configure(text='Start coordinates [μm]: {:.1f}X {:.1f}Y'
                                    .format(self._coor_xy1_mm[0]*1e3,self._coor_xy1_mm[1]*1e3)))
        
        # Update the status bar
        self._status_update(message='Mapping XY start coordinate stored')
    
    def _status_update(self,message=None,bg_colour=None):
        """
        To update the status bar at the bottom

        Args:
            message (str): The update message
            bg_colour (str, optional): Background colour. Defaults to 'default'.
        """
        if bg_colour == None:
            bg_colour = self._bg_colour
        
        if message == None:
            message = 'Controller ready'
        self._statbar.configure(text=message,background=bg_colour)
    
def test_rect1():
    root = tk.Tk()
    root.title('Test')
    
    status_bar = tk.Label(root,text='Ready',bd=1,relief=tk.SUNKEN,anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM,fill=tk.X)
    motion_controller = Frm_MotionController(root,True)
    
    mapping_method = Rect_EndToEnd(root,motion_controller,status_bar)
    mapping_method.pack()
    
    root.mainloop()
    
if __name__ == '__main__':
    test_rect1()