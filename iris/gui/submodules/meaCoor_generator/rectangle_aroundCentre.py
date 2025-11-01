import tkinter as tk

import numpy as np

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.gui.motion_video import Wdg_MotionController
from iris.utils.general import *

class Rect_AroundCentre(tk.Frame):
    """A basic class that manage a mapping method

    Args:
        tk (tkinter): tkinter library
    """
    def __init__(self,container_frame,motion_controller:Wdg_MotionController,status_bar:tk.Label=None,
                 *args, **kwargs) -> None:
        # Place itself in the given master frame (container)
        super().__init__(container_frame)
        
        # Sets up the other controllers
        self._motion_controller = motion_controller
        self._statbar = status_bar
        self._bg_colour = self._statbar.cget('background')
        
        # Mapping parameters
        self._coor_xy_1_mm = [None,None]     # Stores the start coordinates for the mapping. Required for movement boundary setting. Type: float
        self._coor_xy_2_mm = [None,None]     # Stores the end coordinates for the mapping. Required for movement boundary setting. Type: float
        self._coor_xy_center_mm = [None,None]     # Stores the center coordinates for the mapping. Required for movement boundary setting. Type: float
        self._coor_xy_dist_mm = [None,None]     # Stores the distance from the center [mm] for the mapping. Required for movement boundary setting. Type: float
        self._coor_z_mm = None              # Stores the start z-coordinate for the mapping. Required for movement boundary setting. Type: float
        self._m1_pointsx = None             # Stores the mapping resolution in the x-direction
        self._m1_pointsy = None             # Stores the mapping resolution in the y-direction
        self._m1_resx_um = None             # Stores the mapping resolution in the x-direction
        self._m1_resy_um = None             # Stores the mapping resolution in the y-direction
        self._mapping_coordinates = None # Stores the mapping coordinates in a (x,y,z) list
        
        # Make the widgets to store the coordinates
        self._lbl_CoorCtr = tk.Label(self,text='Center coordinates (X,Y) [μm]:')
        self._entry_CoorCtrX = tk.Entry(self)
        self._entry_CoorCtrY = tk.Entry(self)
        self._btn_storecurrent_CoorCtr = tk.Button(self,text='Store current coor.',
                                            command=lambda: self.store_current_coor_center())
        self._btn_goto_CoorCtr = tk.Button(self,text='Set',command=lambda: self.set_coor_center())
        
        self._lbl_CoorDist = tk.Label(self,text='Scan distance from center (X,Y) [μm]:')
        self._entry_CoorDistX = tk.Entry(self)
        self._entry_CoorDistY = tk.Entry(self)
        self._btn_set_CoorDist = tk.Button(self,text='Set',command=lambda: self.set_coor_dist_calc_endpoints())
        
        self._lbl_CoorZ = tk.Label(self,text='Z-coordinate (Z) [μm]:')
        self._entry_CoorZ = tk.Entry(self)
        self._btn_storecurrent_CoorZ = tk.Button(self,text='Store current coor.',
                                            command=lambda: self.store_current_coorz())
        self._btn_goto_CoorZ = tk.Button(self,text='Set',
                                    command=lambda: self.set_coorz())
        
        # Make the widgets to manage the rest of the mapping parameters
        self._lbl_res = tk.Label(self,text='Mapping resolution (X,Y): [_μm, _μm]')
        self._spin_xres = tk.Spinbox(self,from_=1,to=1000,increment=1)
        self._spin_yres = tk.Spinbox(self,from_=1,to=1000,increment=1)
        # Button to store the mapping parameters
        self._btn_res = tk.Button(self,text='Set',command=lambda: self.store_resolution())
        # Button to generate and store the mapping coordinates
        self._btn_gen = tk.Button(self,text='Generate coordinates',
                                    command=lambda: self.generate_mapping_coordinates())
        
        # Bind return to the set_coor buttons
        self._entry_CoorCtrX.bind('<Return>',lambda event: self.set_coor_center())
        self._entry_CoorCtrY.bind('<Return>',lambda event: self.set_coor_center())
        self._entry_CoorDistX.bind('<Return>',lambda event: self.set_coor_dist_calc_endpoints())
        self._entry_CoorDistY.bind('<Return>',lambda event: self.set_coor_dist_calc_endpoints())
        self._entry_CoorZ.bind('<Return>',lambda event: self.set_coorz())
        self._spin_xres.bind('<Return>',lambda event: self.store_resolution())
        self._spin_yres.bind('<Return>',lambda event: self.store_resolution())
        
        # Pack the widgets
        row=0
        self._lbl_CoorCtr.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._entry_CoorCtrX.grid(row=row,column=0)
        self._entry_CoorCtrY.grid(row=row,column=1)
        row+=1
        self._btn_goto_CoorCtr.grid(row=row,column=0)
        self._btn_storecurrent_CoorCtr.grid(row=row,column=1)
        
        row+=1
        self._lbl_CoorDist.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._entry_CoorDistX.grid(row=row,column=0)
        self._entry_CoorDistY.grid(row=row,column=1)
        row+=1
        self._btn_set_CoorDist.grid(row=row,column=0)
        
        row+=1
        self._lbl_CoorZ.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._entry_CoorZ.grid(row=row,column=0)
        row+=1
        self._btn_goto_CoorZ.grid(row=row,column=0)
        self._btn_storecurrent_CoorZ.grid(row=row,column=1)
        
        row+=1
        self._lbl_res.grid(row=row,column=0,columnspan=2,sticky='w')
        row+=1
        self._spin_xres.grid(row=row,column=0)
        self._spin_yres.grid(row=row,column=1)
        row+=1
        self._btn_res.grid(row=row,column=0)
        self._btn_gen.grid(row=row,column=1)

    def get_mapping_coordinates_mm(self) -> list[tuple[float,float,float]]|None:
        """ 
        Returns the mapping coordinates
        
        Returns:
            list: List of tuple (x,y,z) coordinates
        """
        # Make sure to keep the generated coordinates up to date
        self.generate_mapping_coordinates()
        return self._mapping_coordinates
    
    def disable_widgets(self,root):
        """
        Disables all widgets in a Tkinter frame and sub-frames

        Args:
            root (frame): Tkinter frame
        """
        def get_all_widgets(parent_frame:tk.Frame):
            widget_list = []
            for child_widget in parent_frame.winfo_children():
                widget_list.append(child_widget)
                widget_list.extend(get_all_widgets(child_widget))  # Recursion
            return widget_list
        
        for widget in get_all_widgets(root):
            widget:tk.Widget
            widget.configure(state='disabled')
    
    def generate_mapping_coordinates(self):
        """
        Generates the mapping coordinates. Also stores them in its own variable and the main
        operation variable
        """
        if self._coor_xy_1_mm[0] == None or self._coor_xy_2_mm[0] == None or self._coor_z_mm == None:
            self.status_update(message='Please set the coordinates first', bg_colour='yellow')
            return
        
        if self._m1_pointsx == None or self._m1_pointsy == None:
            self.status_update(message='Please set the resolution first', bg_colour='yellow')
            return
        
        # Define the grid boundaries
        x_min, y_min = self._coor_xy_1_mm
        x_max, y_max = self._coor_xy_2_mm
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
        
        self.status_update(message='Mapping coordinates generated')
        
        self.print_parameters()
    
    def reset_self(self):
        self._coor_xy_1_mm = [None,None]     # Stores the start coordinates for the mapping. Required for movement boundary setting. Type: float
        self._coor_xy_2_mm = [None,None]     # Stores the end coordinates for the mapping. Required for movement boundary setting. Type: float
        self._coor_xy_center_mm = [None,None]     # Stores the center coordinates for the mapping. Required for movement boundary setting. Type: float
        self._coor_xy_dist_mm = [None,None]     # Stores the distance from the center [mm] for the mapping. Required for movement boundary setting. Type: float
        self._coor_z_mm = None              # Stores the start z-coordinate for the mapping. Required for movement boundary setting. Type: float
        self._m1_pointsx = None             # Stores the mapping resolution in the x-direction
        self._m1_pointsy = None             # Stores the mapping resolution in the y-direction
        self._m1_resx_um = None             # Stores the mapping resolution in the x-direction
        self._m1_resy_um = None             # Stores the mapping resolution in the y-direction
        self._mapping_coordinates = None # Stores the mapping coordinates in a (x,y,z) list
        
        # Reset the label widgets
        self.after(10,lambda: self._lbl_CoorCtr.configure(text='Center coordinate (X,Y):'))
        self.after(10,lambda: self._lbl_CoorDist.configure(text='Scan distance from center (X,Y):'))
        self.after(10,lambda: self._lbl_CoorZ.configure(text='Z coordinates (Z): '))
        self.after(10,self._lbl_res.configure(text='Mapping resolution (X,Y): [_um, _um]'))
    
    def reset_mapping_coordinates(self):
        self._m1_pointsx = None             # Stores the mapping resolution in the x-direction
        self._m1_pointsy = None             # Stores the mapping resolution in the y-direction
        self._m1_resx_um = None             # Stores the mapping resolution in the x-direction
        self._m1_resy_um = None             # Stores the mapping resolution in the y-direction
        self._mapping_coordinates = None # Stores the mapping coordinates in a (x,y,z) list
        
        self.after(10,self._lbl_res.configure(text='Mapping resolution (X,Y): [_um, _um]'))
    
    def _set_resolution(self):
        """
        Sets the resolution of the mapping in the x and y direction
        using the stored distances
        """
        distx = self._coor_xy_dist_mm[0]*2
        disty = self._coor_xy_dist_mm[1]*2
        
        self._m1_resx_um = (distx/self._m1_pointsx)*1000
        self._m1_resy_um = (disty/self._m1_pointsy)*1000
    
    def store_resolution(self):
        """
        Stores the resolution set in the spinbox for the x and y mapping resolutions.
        Also updates the label.
        """
        try:
            # Try retreiving the value and convert it into integer
            m1_pointsx = int(self._spin_xres.get())
            m1_pointsy = int(self._spin_yres.get())
        except Exception as e:
            print(e)
            self.status_update(message='Unable to store the requested resolution',bg_colour='yellow')
            return
        
        # Save it
        self._m1_pointsx = m1_pointsx
        self._m1_pointsy = m1_pointsy
        
        try:
            self._set_resolution()
            # Update the label
            self.after(10,self._lbl_res.configure(text='Mapping resolution: {}X {}Y [{:.0f} um, {:.0f} um]'
                .format(self._m1_pointsx,self._m1_pointsy,self._m1_resx_um,self._m1_resy_um)))
        except:
            self.after(10,self._lbl_res.configure(text='Mapping resolution: {}X {}Y [_um, _um]'
                .format(self._m1_pointsx,self._m1_pointsy)))
            
    def store_current_coorz(self):
        """
        Gets the current stage coordinate and store it as the initial position
        """
        try:
            # Get the current coordinates from the device
            coor_z_mm = self._motion_controller.get_coordinates_closest_mm()[2]
        except Exception as e:
            print(e)
            return
        
        # Store the coordinate if all checks out
        self._coor_z_mm = coor_z_mm
        self.reset_mapping_coordinates()
        
        # Update the label
        self.after(10,lambda: self._lbl_CoorZ.configure(text='Z coordinates [μm]: {:.1f}Z'
                                    .format(self._coor_z_mm*1e3)))
        
        # Update the status bar
        self.status_update(message='Mapping start coordinate stored')
    
    @thread_assign
    def set_coorz(self):
        """
        Attempts to go to the specified coordinate. If successful, allows the user to store this 
        as a coordinate
        """
        try:
            coor_z_mm = float(self._entry_CoorZ.get())/1e3
        except ValueError as e:
            self.status_update(message='Please enter numbers for the coordinates', bg_colour='yellow')
            return
        
        self._coor_z_mm = coor_z_mm
        self.reset_mapping_coordinates()
        
        # Update the label
        self.after(10,lambda: self._lbl_CoorZ.configure(text='Z coordinates [μm]: {:.1f}Z'
                                    .format(self._coor_z_mm*1e3)))
        
        # Update the status bar
        self.status_update(message='Mapping Z coordinate stored')
    
    @thread_assign
    def set_coor_dist_calc_endpoints(self,coor_x_mm:float=None,coor_y_mm:float=None):
        """
        Sets the distance from the center and calculates the start and end points for the mapping.
        
        Args:
            coor_x (float): The x-coordinate
            coor_y (float): The y-coordinate
        
        Note:
            - If the coordinates are not provided, it will try to get the coordinates from the entry
        """
        if not isinstance(self._coor_xy_center_mm[0],float) or not isinstance(self._coor_xy_center_mm[1],float):
            self.status_update(message='Please set the center coordinates first', bg_colour='yellow')
            return
        
        flg_manual_entry = False
        if coor_x_mm is None or coor_y_mm is None:
            flg_manual_entry = True
            try:
                # Try retrieving the coordinates from the entry and see if the device can get there
                coor_x_mm = float(self._entry_CoorDistX.get())/1e3
                coor_y_mm = float(self._entry_CoorDistY.get())/1e3
            except ValueError as e:
                # If something fails, tells the user to restart
                if not flg_manual_entry:
                    return
                self.status_update(message='Please enter numbers for the coordinates', bg_colour='yellow')
                return
            except Exception as e:
                print(e)
        
        if coor_x_mm < 0 or coor_y_mm < 0:
            if not flg_manual_entry:
                return
            self.status_update(message='Please enter a positive value for the distance', bg_colour='yellow')
            return
        
        self._coor_xy_dist_mm = [coor_x_mm,coor_y_mm]
        
        # Store the start and end points
        coor_x1_mm = self._coor_xy_center_mm[0] - self._coor_xy_dist_mm[0]
        coor_y1_mm = self._coor_xy_center_mm[1] - self._coor_xy_dist_mm[1]
        
        coor_x2_mm = self._coor_xy_center_mm[0] + self._coor_xy_dist_mm[0]
        coor_y2_mm = self._coor_xy_center_mm[1] + self._coor_xy_dist_mm[1]
        
        # Store the coordinates once they're validated
        self._coor_xy_1_mm = [coor_x1_mm,coor_y1_mm]
        self._coor_xy_2_mm = [coor_x2_mm,coor_y2_mm]
        
        # Resets the mapping coordinates to prevent previous coordinates from being used
        self.reset_mapping_coordinates()
        
        # Update the label
        self.after(10,lambda: self._lbl_CoorDist.configure(text='Scan distance from center [μm]: {:.1f}X {:.1f}Y'
                                    .format(float(str(self._coor_xy_dist_mm[0]))*1e3,float(str(self._coor_xy_dist_mm[1]))*1e3)))
        
        # Update the status bar
        self.status_update(message='Mapping XY start coordinate stored')
    
    @thread_assign
    def store_current_coor_center(self):
        """
        Gets the current stage coordinate and store it as the initial position
        """
        try:
            # Get the current coordinates from the device
            coor_x_mm,coor_y_mm = self._motion_controller.get_coordinates_closest_mm()[:2]
        except Exception as e:
            print(e)
            return
        
        self._coor_xy_center_mm = [coor_x_mm,coor_y_mm]
        
        # Resets the mapping coordinates to prevent previous coordinates from being used
        self.reset_mapping_coordinates()
        
        # Reset the endpoints calculation and label
        self.set_coor_dist_calc_endpoints(coor_x_mm=self._coor_xy_dist_mm[0],coor_y_mm=self._coor_xy_dist_mm[1])
        
        # Update the label
        self.after(10,lambda: self._lbl_CoorCtr.configure(text='Center coordinate [μm]: {:.1f}X {:.1f}Y'
                                    .format(self._coor_xy_center_mm[0]*1e3,self._coor_xy_center_mm[1]*1e3)))
        
        # Update the status bar
        self.status_update(message='Mapping XY start coordinate stored')
    
    @thread_assign
    def set_coor_center(self):
        """
        Attempts to go to the specified coordinate. If successful, allows the user to store this 
        as a coordinate
        """
        try:
            coor_x_mm = float(self._entry_CoorCtrX.get())/1e3
            coor_y_mm = float(self._entry_CoorCtrY.get())/1e3
        except ValueError as e:
            self.status_update(message='Please enter numbers for the coordinates', bg_colour='yellow')
            return
        
        self._coor_xy_center_mm = [coor_x_mm,coor_y_mm]
        
        # Resets the mapping coordinates to prevent previous coordinates from being used
        self.reset_mapping_coordinates()
        
        # Reset the endpoints calculation and label
        self.set_coor_dist_calc_endpoints(coor_x_mm=self._coor_xy_dist_mm[0],coor_y_mm=self._coor_xy_dist_mm[1])
        
        # Update the label
        self.after(10,lambda: self._lbl_CoorCtr.configure(text='Center coordinate [μm]: {:.1f}X {:.1f}Y'
                                    .format(self._coor_xy_center_mm[0]*1e3,self._coor_xy_center_mm[1]*1e3)))
        
        # Update the status bar
        self.status_update(message='Mapping XY start coordinate stored')
    
    def status_update(self,message=None,bg_colour=None):
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
        
    def print_parameters(self):
        """Prints the parameters to the console"""
        print('Center coordinates [mm]: {:.3f}X {:.3f}Y'.format(self._coor_xy_center_mm[0],self._coor_xy_center_mm[1]))
        print('Distance from center [mm]: {:.3f}X {:.3f}Y'.format(self._coor_xy_dist_mm[0],self._coor_xy_dist_mm[1]))
        print('Start coordinates [mm]: {:.3f}X {:.3f}Y'.format(self._coor_xy_1_mm[0],self._coor_xy_1_mm[1]))
        print('End coordinates [mm]: {:.3f}X {:.3f}Y'.format(self._coor_xy_2_mm[0],self._coor_xy_2_mm[1]))
        print('Z-coordinate [mm]: {:.3f}Z'.format(self._coor_z_mm))
        print('Resolution: {}X {}Y'.format(self._m1_pointsx,self._m1_pointsy))
        print('Resolution: {:.0f}X {:.0f}Y'.format(self._m1_resx_um,self._m1_resy_um))
        
def test_rect2():
    root = tk.Tk()
    root.title('Test')
    
    status_bar = tk.Label(root,text='Ready',bd=1,relief=tk.SUNKEN,anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM,fill=tk.X)
    motion_controller = Wdg_MotionController(root,True)
    
    mapping_method = Rect_AroundCentre(root,motion_controller,status_bar)
    mapping_method.pack()
    
    root.mainloop()
    
if __name__ == '__main__':
    test_rect2()