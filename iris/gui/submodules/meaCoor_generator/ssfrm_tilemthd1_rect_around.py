import tkinter as tk
from tkinter import messagebox
from typing import Callable
from PIL import Image
import numpy as np
from math import ceil
from scipy.interpolate import griddata

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))

from iris.gui.motion_video import Frm_MotionController
from iris.gui.hilvl_coorGen import Frm_Treeview_MappingCoordinates

from iris.data.calibration_objective import ImgMea_Cal
from iris.data.measurement_coordinates import List_MeaCoor_Hub, MeaCoor_mm

from iris.utils.general import *

OVERLAP = 0.00   # Overlap between each tile (ratio to the image size)

class tiling_method_rectxy_scan_constz_around_a_point(tk.Frame):
    """A basic class that manage a mapping method

    Args:
        tk (tkinter): tkinter library
    """
    def __init__(
        self,
        master:tk.Tk|tk.Frame,
        motion_controller:Frm_MotionController,
        coorHub:List_MeaCoor_Hub,
        getter_cal:Callable[[],ImgMea_Cal],
        *args, **kwargs) -> None:
        # Place itself in the given master frame (container)
        super().__init__(master)
        
        # Sets up the other controllers
        self._motion_controller = motion_controller
        self._getter_img = self._motion_controller.get_current_image    # Function to get the current image
        self._getter_imgCal = getter_cal    # Function to get the image calibration
        self._coorHub = coorHub
        
    # >>> Top level frames <<<
        self._frm_tv_mapCoor = Frm_Treeview_MappingCoordinates(master=self,mappingCoorHub=coorHub)
        frm_control = tk.Frame(self)
        
        row=0; col=0
        self._frm_tv_mapCoor.grid(row=row,column=0,sticky='nsew');row+=1
        frm_control.grid(row=row,column=0,sticky='nsew')
        
        [self.grid_rowconfigure(i,weight=1) for i in range(row+1)]  # Make the rows expandable
        [self.grid_columnconfigure(i,weight=1) for i in range(col+1)]  # Make the columns expandable
        
    # >>> Widgets <<<
        # Make the widgets to store the coordinates
        self._lbl_crop = tk.Label(frm_control,text='Cropping factors (X,Y) [a.u.]:')
        self._entry_cropx = tk.Entry(frm_control)
        self._entry_cropy = tk.Entry(frm_control)
        self._entry_cropx.insert(0,'0.0')  # Default cropping factor x
        self._entry_cropy.insert(0,'0.0')  # Default cropping factor y
        
        # Pack the widgets
        row=0; col=0
        self._lbl_crop.grid(row=row,column=0,columnspan=2,sticky='w');row+=1
        self._entry_cropx.grid(row=row,column=0);col+=1
        self._entry_cropy.grid(row=row,column=1)
        
        [self.grid_rowconfigure(i,weight=1) for i in range(row+1)]  # Make the rows expandable
        [self.grid_columnconfigure(i,weight=1) for i in range(col+1)]  # Make the columns expandable

    def get_tiling_coordinates_mm_and_cropFactors_rel(self) -> tuple[list[MeaCoor_mm],float,float]|None:
        """
        Returns the mapping coordinates and the cropping factors
        
        Returns:
            tuple[list[MeaCoor_mm], float, float]|None: The mapping coordinates (list of MeaCoor_mm objects), crop factor x, and crop factor y
        """
        # Make sure to keep the generated coordinates up to date
        list_meaCoor_mm = self._generate_tiling_coordinates()
        
        if list_meaCoor_mm is None:
            messagebox.showerror('Error','No mapping coordinates generated. Please generate the coordinates first.')
            return None
        else:
            cropx_reduction, cropy_reduction = self._get_crop_factors()
            return (list_meaCoor_mm,cropx_reduction,cropy_reduction)
    
    def _get_xy_scales_mmPerPixel(self) -> tuple[float,float]:
        """
        Gets the pixel to um conversion factor for the x and y direction 
        
        Returns:
            tuple: The pixel to um conversion factor for the x and y direction [mm/pixel]
        """
        img_cal:ImgMea_Cal = self._getter_imgCal()
        scl_x = 1/img_cal.scale_x_pixelPerMm
        scl_y = 1/img_cal.scale_y_pixelPerMm
        return (abs(scl_x),abs(scl_y))
    
    def _get_crop_factors(self) -> tuple[float,float]:
        """
        Gets the cropping factors for the x and y direction.
        
        Returns:
            tuple: The cropping factors for the x and y direction
        """
        try:
            cropx_reduction = float(self._entry_cropx.get())
            cropy_reduction = float(self._entry_cropy.get())
            assert 0 <= cropx_reduction < 1 and 0 <= cropy_reduction < 1, 'Cropping factors must be between 0 and 1'
            return (cropx_reduction,cropy_reduction)
        except Exception as e:
            messagebox.showerror('Error',f'{e}\nUsing the default cropping factors (0.0, 0.0) instead')
            return (0.0,0.0)
    
    def _generate_tiling_coordinates(self) -> list[MeaCoor_mm]|None:
        """
        Generates the mapping coordinates. Also stores them in its own variable and the main
        operation variable.
        
        Returns:
            list[MeaCoor_mm]|None: The mapping coordinates (list of (x,y,z) tuples) or None if an error occurs
        """
        list_meaCoor_mm = self._frm_tv_mapCoor.get_selected_mappingCoor()
        if len(list_meaCoor_mm) < 1: messagebox.showerror('Error','Please select at least one mapping coordinate'); return
        
        cropx_reduction, cropy_reduction = self._get_crop_factors()
        
        image = self._getter_img()
        if not isinstance(image,Image.Image):
            messagebox.showerror('Error','No image set. Please set the image first.')
            return
        
        cal = self._getter_imgCal()
        if not isinstance(cal,ImgMea_Cal):
            messagebox.showerror('Error','No objective calibration selected. Please set the objective calibration first.')
            return
        
        # Define the grid boundaries
        list_ret_MeaCoor_mm = [self._calculate_tiling_coordinates(meaCoor_mm, cropx_reduction, cropy_reduction, image, cal) for meaCoor_mm in list_meaCoor_mm]
        list_ret_MeaCoor_mm = [meaCoor_mm for meaCoor_mm in list_ret_MeaCoor_mm if len(meaCoor_mm.mapping_coordinates) > 0]
        if len(list_ret_MeaCoor_mm) == 0:
            messagebox.showerror('Error','No valid mapping coordinates generated. Please check the input parameters.')
            return None
        
        return list_ret_MeaCoor_mm

    def _calculate_tiling_coordinates(self, meaCoor_mm: MeaCoor_mm, cropx_reduction: float,
        cropy_reduction: float, image: Image.Image, cal: ImgMea_Cal) -> MeaCoor_mm:
        """
        Calculates the tiling coordinates based on the input parameters.

        Args:
            meaCoor_mm (MeaCoor_mm): The mapping coordinates to tile.
            cropx_reduction (float): The cropping factor for the x direction.
            cropy_reduction (float): The cropping factor for the y direction.
            image (Image.Image): An example image to be used for the size calculation. (Typically this would be\
                an image from the video camera)
            cal (ImgMea_Cal): The objective calibration object.

        Returns:
            MeaCoor_mm: The calculated mapping coordinates with the original MeaCoor_mm mapping unit name.
        """
        list_coor_mm = meaCoor_mm.mapping_coordinates
        x_min = min([coor[0] for coor in list_coor_mm])
        x_max = max([coor[0] for coor in list_coor_mm])
        y_min = min([coor[1] for coor in list_coor_mm])
        y_max = max([coor[1] for coor in list_coor_mm])
        list_coor_xy_mm = [(coor[0], coor[1]) for coor in list_coor_mm]
        list_coor_z_mm = [coor[2] for coor in list_coor_mm]
                        
        # Calculate the resolution required
        x_scale, y_scale = self._get_xy_scales_mmPerPixel()
        img_size_x, img_size_y = image.size
        x_size_mm = img_size_x * x_scale
        y_size_mm = img_size_y * y_scale
        
        # Take into account the crop and the overlap
        x_size_mm *= (1 - cropx_reduction)    # Taking into account the: Crop
        y_size_mm *= (1 - cropy_reduction)
        x_size_mm_temp, y_size_mm_temp = x_size_mm, y_size_mm
        x_size_mm -= y_size_mm_temp * abs(np.sin(cal.rotation_rad)) # Taking into account the: Rotation
        y_size_mm -= x_size_mm_temp * abs(np.sin(cal.rotation_rad))
        x_size_mm *= (1 - OVERLAP)  # Taking into account the: Overlap
        y_size_mm *= (1 - OVERLAP)
        
        # Calculate the number of points required
        num_x = ceil((x_max - x_min) / x_size_mm) + 1 # +1 to include the last point
        num_y = ceil((y_max - y_min) / y_size_mm) + 1 # +1 to include the last point
        
        m1_pointsx = num_x
        m1_pointsy = num_y
        
        # Generate linearly spaced points along each axis
        x_points_mm = np.linspace(x_min, x_max, m1_pointsx)
        y_points_mm = np.linspace(y_min, y_max, m1_pointsy)
        
        list_xy_mm = [(x, y) for x in x_points_mm for y in y_points_mm]
        
        # Interpolate the z-coordinates using griddata
        list_z_mm = griddata(
            points=list_coor_xy_mm,
            values=list_coor_z_mm,
            xi=list_xy_mm,
            method='linear',
            fill_value=np.nan
        )
        
        list_xyz_mm = [(x, y, z) for (x, y), z in zip(list_xy_mm, list_z_mm) if not np.isnan(z)]
        ret_mapCoor_mm = MeaCoor_mm(
            mappingUnit_name=meaCoor_mm.mappingUnit_name,
            mapping_coordinates=list_xyz_mm,
        )
        return ret_mapCoor_mm
            
def test_rect2():
    root = tk.Tk()
    root.title('Test')
    
    status_bar = tk.Label(root,text='Ready',bd=1,relief=tk.SUNKEN,anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM,fill=tk.X)
    motion_controller = Frm_MotionController(root,True)
    
    mapping_method = tiling_method_rectxy_scan_constz_around_a_point(root,motion_controller,status_bar)
    mapping_method.pack()
    
    root.mainloop()
    
if __name__ == '__main__':
    test_rect2()