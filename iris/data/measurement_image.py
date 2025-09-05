"""
Note:
- When developing this class, keep in mind of the following:
        - The image frame of reference is different from the stage frame of reference.
        - The display is that of the image frame of reference, whereas the coordinates are in the stage frame of reference
            i.e., flipping the conversion factor (mm/pixel) will flip the image, but the coordinates will remain the same.
        
    - The flip parameter inverses the image frame of reference (flips the positive and negative directions):
        - This means that when frame 1 has a stage coor of (x1,y1) and frame 2 has a stage coor of (x2,y2),
            the difference between the two frames is (x2-x1,y2-y1) in the stage frame of reference and this will
            stay constant regardless of the flip parameter value. The flip parameter, however, will change how the
            image is displayed on the screen because the difference in the image frame of reference will be
            (-(xp2-xp1),-(yp2-yp1)) if the flip parameter is True.
            (where xp is the pixel coordinate = x/scale*flip parameter). This is important for the image stitching
            and for the overlay of the ROIs (heatmap measurement results) on the image.
        - Because the flip parameters heavily depends on the way the image is displayed (i.e., if it is flipped
            from the get-go), the flip parameters are left as a user-defined parameter to be used by other methods/
            classes that requires it, e.g., the Frm_HeatmapOverlay class.
"""

import sys
import os

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

from tkinter import filedialog

import numpy as np
from PIL import Image

import sqlite3 as sql
import json
import glob
import uuid

from iris.utils.general import *


from iris.data.calibration_objective import ImgMea_Cal, ImgMea_Cal_Hub

from iris.data import SaveParamsEnum, ImageProcessingParamsEnum

class MeaImg_Unit():
    """
    Handles the storage of image measurements for the ROI definition:
        1. Timestamp
        2. Stage coordinates (when the image was taken)
        3. Image
        4. Calibration parameters (mm/pixel, laser coordinate offset)
        
    """
    def __init__(self,unit_name:str|None=None,calibration:ImgMea_Cal|None=None,
                 reconstruct:bool=False):
        """
        Initialises the image measurement class
        
        Args:
            unit_name (str|None): Name of the image measurement unit. Default is None
            calibration (ImageMeasurement_Calibration): Calibration parameters
            reconstruct (bool): Flag to skip all the checks, used for reconstruction from
                the local disk. Default is False
            
        Note:
            If the unit_name or unit_id is None, the timestamp will be used as the unit name and unit ID
        """
        if not reconstruct:
            assert isinstance(calibration, ImgMea_Cal), 'Calibration must be an ImageMeasurement_Calibration object'
            assert calibration.check_calibration_set(), 'Calibration parameters are not set'
        
        self._unitName:str = unit_name if unit_name != None else get_timestamp_us_str()
        self._unitID:str = uuid.uuid4().hex
        self._calibration:ImgMea_Cal = calibration
        
        self._list_metadata_keys = ['id','name','calibration_id','calibration_dict']
        
        # Stitched image parameters
        self._flg_mat_calculated:bool = False    # Flag to check if the rotation correction matrix is calculated
        self._mat_stitch2ori:np.ndarray = np.eye(2)    # Rotation matrix to convert pixel coordinates from the stitched image to the original image
        self._mat_ori2stitch:np.ndarray = np.eye(2)    # Rotation matrix to convert pixel coordinates from the original image to the stitched image
        self._lres_scale:float = ImageProcessingParamsEnum.LOW_RESOLUTION_SCALE.value    # Low resolution scale for the images
        
        # Dictionary to store the measurements
        self._dict_measurements = {
            'timestamp':[],
            'coor_x':[],
            'coor_y':[],
            'coor_z':[],
            'image':[],
        }
        
        self._dict_measurements_types = {
            'timestamp':str,
            'coor_x':float,
            'coor_y':float,
            'coor_z':float,
            'image':Image.Image,
        }
        
        self._list_lowResImg = []   # List to store the low resolution images
        
        assert set(self._dict_measurements.keys()) == set(self._dict_measurements_types.keys()), 'Measurement keys must match the measurement types'
        
        self._metadata_types = {
            'id':str,
            'name':str,
            'calibration_id':str,
            'calibration_dict':dict,
        }
        
        self._idname_keys = ['id','name']   # Keys for the ID and name to access the metadata
        
        if reconstruct: self._metadata = {}
        else:
            self._metadata = {
                'id':self._unitID,
                'name':self._unitName,
                'calibration_id':self._calibration.id,
                'calibration_dict':self._calibration.get_calibration_asdict()
            }
            assert set(self._metadata.keys()) == set(self._metadata_types.keys()), 'Metadata keys must match the metadata types'
        
    def set_name(self,unit_name:str) -> None:
        """
        Sets the name of the ImageMeasurement_Unit
        
        Args:
            unit_name (str): Name of the ImageMeasurement_Unit
        """
        assert isinstance(unit_name,str), 'Name must be a string'
        self._unitName = unit_name
        self._metadata['name'] = unit_name
        
    def get_dict_measurement_types(self) -> dict:
        """
        Returns the measurements dictionary types
        
        Returns:
            dict: Measurements dictionary types
        """
        return self._dict_measurements_types
        
    def get_dict_measurement(self) -> dict:
        """
        Returns the measurements dictionary for saving to local disk

        Returns:
            dict: Measurements dictionary
        """
        return self._dict_measurements
        
    def get_IdName(self) -> tuple[str,str]:
        """
        Returns the unit ID and name
        
        Returns:
            tuple[str,str]: Unit ID, Unit name
        """
        return self._unitID, self._unitName
        
    def get_numMeasurements(self) -> int:
        """
        Returns the number of measurements taken
        
        Returns:
            int: Number of measurements taken
        """
        return len(self._dict_measurements['timestamp'])
        
    def set_metadata_fromfile(self,dict_meta:dict) -> None:
        """
        Sets the unit attributes based on the given metadata dictionary

        Args:
            dict_meta (dict): Metadata dictionary
        """
        assert all([key in dict_meta.keys() for key in set(self._metadata.keys())]), 'Metadata keys must match the metadata types'
        
        self._unitID = dict_meta['id']
        self._unitName = dict_meta['name']
        
        cal = ImgMea_Cal()
        cal.set_calibration_fromdict(dict_meta['calibration_id'],dict_meta['calibration_dict'])
        
        self._calibration = cal
        self._flg_mat_calculated = False
        
        self.refresh_metadata()
        
    def refresh_metadata(self):
        """
        Resets the metadata using the internally stored values
        """
        self._metadata = {
            'id':self._unitID,
            'name':self._unitName,
            'calibration_id':self._calibration.id,
            'calibration_dict':self._calibration.get_calibration_asdict()
        }
        
    def get_metadata_types(self) -> dict:
        """
        Returns the metadata types
        
        Returns:
            dict: Metadata types
        """
        return self._metadata_types
        
    def get_metadata(self, incl_nameid:bool=True) -> dict:
        """
        Returns the metadata of the ImageMeasurement_Unit
        
        Args:
            incl_nameid (bool): Include the name and ID in the metadata. Default is True
            
        Returns:
            dict: Metadata of the ImageMeasurement_Unit (id, name, calibration_id, calibration_dict)
        """
        if incl_nameid: return self._metadata
        else: return {key:self._metadata[key] for key in self._metadata.keys() if key not in self._idname_keys}
        
    def get_ImageMeasurement_Calibration(self) -> ImgMea_Cal:
        """
        Returns the ImageMeasurement_Calibration object for the calibration parameters
        """
        return self._calibration
        
    def _calculate_RotationCorrectionMatrix(self) -> None:
        """
        Calculates the rotation correction matrix for the image stitching
        """
        assert self.check_calibration_exist(), 'Calibration parameters are not set'
        
        rot_rad = self._calibration.rotation_rad
        
        # Rotate the points counter to the detected rotation angle to align the
        # image frame of reference with the stage frame of reference
        self._mat_ori2stitch = np.array([[np.cos(-rot_rad),-np.sin(-rot_rad)],
                                         [np.sin(-rot_rad),np.cos(-rot_rad)]])
        
        
        # Rotate the points clockwise to the detected rotation angle to align the
        # stage frame of reference with the image frame of reference (inverse the
        # rotation transformation above)
        self._mat_stitch2ori = np.array([[np.cos(rot_rad),-np.sin(rot_rad)],
                                         [np.sin(rot_rad),np.cos(rot_rad)]])
        
        self._flg_mat_calculated = True
        
        
    def _correctRotationFlip(self,coor_pixel:tuple[int,int],stitch2ori:bool) -> tuple[int,int]:
        """
        Corrects the rotation of the pixel coordinates due to the image stitching
        
        Args:
            coor_pixel (tuple[int,int]): Pixel coordinates (x,y)
            stitch2ori (bool): Flag to correct the rotation from the stitched image to the original image
        
        Returns:
            tuple[int,int]: Corrected pixel coordinates
        """
        if not self._flg_mat_calculated: self._calculate_RotationCorrectionMatrix()
        
        if stitch2ori:
            coor_pixel_arr = self._mat_stitch2ori @ np.array(coor_pixel).reshape(2,1)
            return coor_pixel_arr.flatten().astype(int).tolist()
        else:
            coor_pixel_arr = self._mat_ori2stitch @ np.array(coor_pixel).reshape(2,1)
            return coor_pixel_arr.flatten().astype(int).tolist()
        
    def get_image_all_stitched(self, low_res:bool=False) -> tuple[Image.Image,tuple[float,float],tuple[float,float]]:
        """
        Stitches all the images taken
        
        Args:
            low_res (bool): Flag to use the low resolution images. Default is False
        
        Returns:
            tuple[Image.Image,tuple[float,float],tuple[float,float]]:
                Stitched image, image min limits in mm (xmin,ymin) [mm],
                image max limits in mm (xmax,ymax) [mm]
        
        NOTE:
            - Note that the shown image is rotated according to the calibration parameters.
                i.e., the image shown is now aligned with the stage frame of reference's axes
                such that another coordinate rotation correction needs to be done when converting
                the coordinats between the image and the stage frame of reference. For this reason,
                the rotation angle is stored internally.
        """
        assert len(self._dict_measurements['timestamp']) > 0, 'No images taken'
        assert self.check_calibration_exist(), 'Calibration parameters are not set'
        
        cal = self._calibration
        
    # > Get the measurements
        if low_res: list_images = self._list_lowResImg
        else: list_images = self._dict_measurements['image']
        
        list_coorx_mm = self._dict_measurements['coor_x']
        list_coory_mm = self._dict_measurements['coor_y']
        
        # Calculate the rotation angle
        # print(f'Stored rotation angle [rad]: {cal.rotation_rad}')
        rot_deg = -cal.rotation_rad*180/np.pi
        # print(f'Operation rotation angle [deg]: {rot_deg}')
        
    # > Calculate the crop and the coordinate shift because of the cropping
        sizex,sizey = list_images[0].size
        cropx_pixel = abs(int(sizey*np.sin(cal.rotation_rad)))
        cropy_pixel = abs(int(sizex*np.sin(cal.rotation_rad)))
        # print(f'Crop size [pixel]: {cropx_pixel,cropy_pixel}')
        
        # Ensure that the angle is within -180 to 180 degrees
        while True:
            if rot_deg > 180: rot_deg -= 360
            elif rot_deg < -180: rot_deg += 360
            else: break
        
        if rot_deg > 0:
            crop_coor = (0,cropy_pixel,sizex-cropx_pixel,sizey)
            coor_shift_pixel = (cropx_pixel,0)
        elif rot_deg < 0:
            crop_coor = (cropx_pixel,0,sizex,sizey-cropy_pixel)
            coor_shift_pixel = (0,cropy_pixel)
        else:
            crop_coor = (0,0,sizex,sizey)
            coor_shift_pixel = (0,0)
        
        coor_shift_stage = self.convert_imgpt2stg(frame_coor_mm=(0,0),\
            coor_pixel=coor_shift_pixel,correct_rot=True,low_res=low_res)
        
        list_coorx_mm = [coor+coor_shift_stage[0] for coor in list_coorx_mm]
        list_coory_mm = [coor+coor_shift_stage[1] for coor in list_coory_mm]
        
    # > Rotate and crop the images
        list_images_converted = []
        for img in list_images:
            img_rot_crop:Image.Image = img.copy()
            img_rot_crop = img_rot_crop.rotate(-rot_deg,expand=False,center=(0,0)) if rot_deg != 0 else img_rot_crop
            img_rot_crop = img_rot_crop.crop(crop_coor)
            list_images_converted.append(img_rot_crop)
            
        list_images = list_images_converted
        
    # > Stitch the image
        # Calculate each image location in the stitched image (in pixel coordinates)
        list_coor_mm = [(coorx_mm,coory_mm) for coorx_mm,coory_mm in zip(list_coorx_mm,list_coory_mm)]
        list_coor_min_mm = list_coor_mm
        
        # Flip the coordinates based on the calibration parameters
        # rot_rad = cal.rotation_rad
        # flip_rot_x = np.sign(np.cos(rot_rad))
        # flip_rot_x = 1 if flip_rot_x == 0 else flip_rot_x
        # flip_rot_y = np.sign(np.sin(rot_rad))
        # flip_rot_y = 1 if flip_rot_y == 0 else flip_rot_y
        
        # x_flip = np.sign(cal.scale_x_pixelPerMm*flip_rot_x*-1).astype(int)
        # y_flip = np.sign(cal.scale_y_pixelPerMm*cal.flip_y*flip_rot_y*-1).astype(int)
        x_flip = -1
        y_flip = -1
        assert x_flip !=0 and y_flip != 0, 'CHECK ERROR: Flip parameters cannot be 0, there must be something unaccounted for'
        
        list_coor_min_pixel = [self.convert_stg2imgpt(coor_stage_mm=coor,coor_point_mm=(0,0),correct_rot=True,low_res=low_res)\
            for coor in list_coor_mm]
        list_coor_min_pixel = [(coor[0]*x_flip,coor[1]*y_flip) for coor in list_coor_min_pixel]
        
        img_limit_coor_min_pixel = (min([coor[0] for coor in list_coor_min_pixel]),\
            min([coor[1] for coor in list_coor_min_pixel]))
        
        # Calculate the relative pixel coordinates
        list_coor_pixel_rel = [(
            coor[0]-img_limit_coor_min_pixel[0],\
            coor[1]-img_limit_coor_min_pixel[1]
            ) for coor in list_coor_min_pixel]
        
        # Generate an empty image 
        img_wid = max([abs(coor[0]) for coor in list_coor_pixel_rel]) + img_rot_crop.size[0]
        img_hei = max([abs(coor[1]) for coor in list_coor_pixel_rel]) + img_rot_crop.size[1]
        img_stitched = Image.new('RGB',(img_wid,img_hei))
        
        # Paste the images onto the empty image
        for i in range(len(list_images)):
            img = list_images[i]
            coor_pixel = list_coor_pixel_rel[i]
            img_stitched.paste(img,coor_pixel)
        
    # > Calculate the image limits in mm
        # Note to myself:
        # The limit is not the minimum coordinates of the image but the coordinate of the 0,0 pixel
        # of the stitched image in the stage frame of reference
        # This can be calculated by converting the pixel coordinates of the one of the image 
        # in the list_coor_pixel_rel
        
        # This minimum coordinate is also the reference coordinate to be returned (i.e., the stage coordinate
        # of the stitched image, corresponding to the 0,0 pixel of the stitched image)
        
        # Similarly, the maximum coordinates of the image is the maximum coordinates of the img_rot_crop
        # i.e., the image shape
        
        mea_coor = list_coor_min_mm[0]
        mea_coor_pixel = list_coor_pixel_rel[0]
        neg = (-mea_coor_pixel[0],-mea_coor_pixel[1])
        img_limit_coor_min_mm = self.convert_imgpt2stg(frame_coor_mm=mea_coor,coor_pixel=neg,correct_rot=True,
                                                       low_res=low_res)
        img_limit_coor_max_mm = self.convert_imgpt2stg(frame_coor_mm=img_limit_coor_min_mm,coor_pixel=(img_wid,img_hei),
                                                       correct_rot=True,low_res=low_res)
        
        return img_stitched, img_limit_coor_min_mm, img_limit_coor_max_mm
        
    def reset_measurement(self):
        """
        Deletes all stored measurement in the _dict_measurements
        """
        for key in self._dict_measurements.keys():
            self._dict_measurements[key].clear()
        
    def reprocess_lowres_images(self):
        """
        Reprocesses the low resolution images to be used for the stitching using the original images
        """
        self._list_lowResImg.clear()
        
        for img in self._dict_measurements['image']:
            img_lres = img.copy()
            img_lres.thumbnail((int(img.size[0]*self._lres_scale),int(img.size[1]*self._lres_scale)))
            self._list_lowResImg.append(img_lres)
        
    def set_dict_measurement_fromfile(self,dict_measurements:dict) -> None:
        """
        Sets the measurements from a dictionary
        
        Args:
            dict_measurements (dict): Measurements dictionary
        """
        assert set(dict_measurements.keys()) == set(self._dict_measurements.keys()), 'Measurement keys must match the measurement types'
        assert all([isinstance(dict_measurements[key], list) for key in dict_measurements.keys()]), 'Measurement values must be lists'
        assert all([all([isinstance(val, self._dict_measurements_types[key]) for val in dict_measurements[key]]) for key in dict_measurements.keys()]), 'Measurement values must match the measurement types'
        
        self._dict_measurements.clear()
        for key in dict_measurements.keys():
            self._dict_measurements[key] = dict_measurements[key]
            
        self.reprocess_lowres_images()
        
    def add_measurement(self, timestamp:str, x_coor:float, y_coor:float,
                        z_coor:float, image:Image.Image):
        """
        Adds a measurement to the dictionary
        
        Args:
            timestamp (str): Timestamp of the measurement
            x_coor (float): X-coordinate of the measurement
            y_coor (float): Y-coordinate of the measurement
            z_coor (float): Z-coordinate of the measurement
            image (Image.Image): Image of the measurement
        """
        assert isinstance(timestamp, str), 'Timestamp must be a string'
        assert isinstance(x_coor, float), 'X-coordinate must be a float'
        assert isinstance(y_coor, float), 'Y-coordinate must be a float'
        assert isinstance(z_coor, float), 'Z-coordinate must be a float'
        assert isinstance(image, Image.Image), 'Image must be an Image.Image object'
        
        # Add the parameters to the dictionary
        self._dict_measurements['timestamp'].append(timestamp)
        self._dict_measurements['coor_x'].append(x_coor)
        self._dict_measurements['coor_y'].append(y_coor)
        self._dict_measurements['coor_z'].append(z_coor)
        self._dict_measurements['image'].append(image)
        
        # Generate the low resolution image and store it
        image_lres = image.copy()
        image_lres.thumbnail((int(image.size[0]*self._lres_scale),int(image.size[1]*self._lres_scale)))
        self._list_lowResImg.append(image_lres)
        
    def check_readyForProcessing(self):
        """
        Checks if the image measurement is ready for processing. Checks for:
            1. If the measurements exist
            2. If the calibration parameters exist
            3. If the low resolution images have been generated for all the images taken
        
        Returns:
            bool: True if the image measurement is ready for processing, False otherwise
        """
        flg = True
        if not self.check_measurement_exist(): flg = False
        if not self.check_calibration_exist(): flg = False
        if not len(self._dict_measurements['image']) == len(self._list_lowResImg): flg = False
        return flg
        
    def check_measurement_exist(self) -> bool:
        """
        Checks if the measurements are stored
        
        Returns:
            bool: True if the measurements are stored, False otherwise
        """
        return len(self._dict_measurements['timestamp']) > 0
        
    def check_calibration_exist(self) -> bool:
        """
        Checks if the calibration parameters are set
        
        Returns:
            bool: True if the calibration parameters are set, False otherwise
        """
        return self._calibration.check_calibration_set()
        
    def convert_imgpt2stg(self, frame_coor_mm:tuple[float,float], coor_pixel:tuple[int,int],
                          correct_rot:bool, low_res:bool)\
        -> tuple[float,float]:
        """
        Converts the coordinates from pixels to mm based on the stored calibration parameters
        
        Args:
            frame_coor_mm (tuple[float,float]): X, Y, Z coordinates or X, Y coordinates in mm of the image frame
            coor_pixel (tuple[int,int]): X, Y coordinates in pixels
            correct_rot (bool): Correct for the rotation angle if the shown stitched image is rotated corrected
            low_res (bool): Set to True if the image being processed is a low resolution (i.e., downsampled) image of the original image.
            
        Returns:
            tuple[float,float]: X and Y coordinates in mm
        """
        if low_res: coor_pixel = (int(coor_pixel[0]/self._lres_scale),int(coor_pixel[1]/self._lres_scale))
        
        if correct_rot:
            coor_pixel = self._correctRotationFlip(coor_pixel,stitch2ori=True)
        
        coor_stg_mm = self._calibration.convert_imgpt2stg(
            coor_img_pixel=np.array(coor_pixel[:2]),
            coor_stage_mm=np.array(frame_coor_mm[:2])
        )
        
        x_mm,y_mm = coor_stg_mm.tolist()
        return x_mm, y_mm
        
    def convert_stg2imgpt(self, coor_stage_mm:tuple[float,float,float]|tuple[float,float],
            coor_point_mm:tuple[float,float,float]|tuple[float,float],correct_rot:bool,low_res:bool) -> tuple[int,int]:
        """
        Converts the coordinates from mm to pixels based on the stored calibration parameters
        
        Args:
            stage_coor_mm (tuple[float,float,float]): X, Y, Z coordinates or X, Y coordinates in mm of the image frame
            coor_mm (tuple[float,float,float]): X, Y, Z coordinates or X, Y coordinates in mm
            rot_rad (float): Rotation angle in radians to correct for. Default is 0.0
            correct_rot (bool): Correct for the rotation angle if the shown stitched image is rotated corrected
            low_res (bool): Set to True if the image being processed is a low resolution (i.e., downsampled) image of the original image.
        
        Returns:
            tuple[int,int]: X and Y coordinates in pixels
        
        NOTE:
            - The rotation angle is to correct for the rotation applied of the shown image
                from the 'get stitched image' method
            - The rotation angle is in radians and is counter clockwise
        """
        coor_pixel = self._calibration.convert_stg2imgpt(
            coor_point_mm=np.array(coor_point_mm[:2]),
            coor_stg_mm=np.array(coor_stage_mm[:2])
        )
        
        if correct_rot: coor_pixel = self._correctRotationFlip(coor_pixel,stitch2ori=False)
        
        x_pixel,y_pixel = [int(coor) for coor in coor_pixel]
        
        if low_res:
            x_pixel = int(x_pixel*self._lres_scale)
            y_pixel = int(y_pixel*self._lres_scale)
        
        return x_pixel, y_pixel
        
    def convert_stg2mea(self, coor_stage_mm:tuple[float,float,float])\
        -> tuple[float,float,float]:
        """
        Calculates the measurement coordinates from the stage coordinates based on the laser coordinates
        stored in the calibration parameters
        
        Args:
            stage_coor (tuple[float,float,float]): Stage coordinates (X,Y,Z) in mm
        
        Returns:
            tuple[float,float,float]: Measurement coordinates (X,Y,Z) in mm
        """
        coor_stage_mm_arr = np.array(coor_stage_mm[:2])
        coor_mea_mm = self._calibration.convert_stg2mea(coor_stage_mm_arr)
        
        x_mm,y_mm = coor_mea_mm.tolist()
        
        if len(coor_stage_mm) == 2: return x_mm, y_mm
        if len(coor_stage_mm) >= 2: return x_mm, y_mm, coor_stage_mm[2]
    
    def convert_mea2stg(self, coor_mea_mm:tuple[float,float,float]|tuple[float,float])\
        -> tuple[float,float,float]|tuple[float,float]:
        """
        Calculates the stage coordinates from the measurement coordinates based on the laser coordinates
        stored in the calibration parameters
        
        Args:
            coor_mea_mm (tuple[float,float,float]|tuple[float,float]): Measurement coordinates (X,Y,Z) in mm or (X,Y) in mm
        
        Returns:
            tuple[float,float,float]|tuple[float,float]: Stage coordinates (X,Y,Z) in mm or (X,Y) in mm
        """
        coor_mea_mm_arr = np.array(coor_mea_mm[:2])
        coor_stage_mm = self._calibration.convert_mea2stg(coor_mea_mm_arr)
        
        x_mm,y_mm = coor_stage_mm.tolist()
        
        if len(coor_mea_mm) == 2:return x_mm, y_mm
        if len(coor_mea_mm) >= 2: return x_mm, y_mm, coor_mea_mm[2]
        
    def set_calibration_rel(self, scl_x_mmPerPixel:float, scl_y_mmPerPixel:float,
            laser_coor_x_mm:float, laser_coor_y_mm:float,flipx:bool,flipy:bool):
        # REMFLAG: This method now overlaps with another method or with the ImageMeasurement_Calibration object's method. This will be removed.
        raise NotImplementedError('This method will be removed entirely soon')
        
    def set_calibration(self, scl_x_mmPerPixel:float, scl_y_mmPerPixel:float,
                        laser_coor_x_mm:tuple[float,float], laser_coor_y_mm:tuple[float,float],
                        inverse:bool=False,flipx:bool=False,flipy:bool=False):
        # REMFLAG: This method now overlaps with another method or with the ImageMeasurement_Calibration object's method. This will be removed.
        raise NotImplementedError('This method will be removed entirely soon')
        
    def get_calibration(self, flipx:bool, flipy:bool) -> tuple[float,float,float,float]:
        # REMFLAG: This method now overlaps with another method or with the ImageMeasurement_Calibration object's method. This will be removed.
        raise NotImplementedError('This method will be removed entirely soon')
    
    def get_calibration_asdict(self) -> tuple[str,dict]:
        """
        Returns the calibration parameters as a dictionary
        
        Returns:
            tuple[str,dict]: Calibration ID, calibration parameters
        """
        return self._calibration.id, self._calibration.get_calibration_asdict()
    
    def set_calibration_ImageMeasurement_Calibration(self,calibration:ImgMea_Cal) -> None:
        """
        Sets the calibration parameters from an ImageMeasurement_Calibration object

        Args:
            calibration (ImageMeasurement_Calibration): Calibration parameters object
            
        Raises:
            AssertionError: Calibration parameters are not set
            AssertionError: Calibration parameters are not an ImageMeasurement_Calibration object
        """
        assert isinstance(calibration, ImgMea_Cal), 'Calibration must be an ImageMeasurement_Calibration object'
        assert calibration.check_calibration_set(), 'Calibration parameters are not set'
        
        self._calibration = calibration
        self._flg_mat_calculated = False
        self.refresh_metadata()
        return
    
    def test_generate_dummy(self):
        """
        Generates dummy measurements for testing purposes
        """
        for i in range(5):
            timestamp = get_timestamp_us_str()
            x_coor = float(np.random.uniform(0,1))
            y_coor = float(np.random.uniform(0,1))
            z_coor = float(0)
            image = Image.new('RGB',(100,100),color=(255,255,0))
            
            self.add_measurement(timestamp, x_coor, y_coor, z_coor, image)
        return
        
class MeaImg_Hub():
    """
    A hub to store multiple ImageMeasurement_Units generated in a measurement session
    """
    def __init__(self):
        self._version = 'v2.5.0-2024.11.04' # Version of the ImageMeasurement_Hub
        self._dict_ImageUnits = {           # Dictionary to store the ImageMeasurement_Units
            'version': self._version,
            'unit_id': [],
            'image_unit': []
            }
        
        self._dict_unit_NameID = {}         # Dictionary to store the unit name and ID relation (name:ID)
        self._dict_unit_IDName = {}         # Dictionary to store the unit ID and name relation (ID:name)
        
    def check_measurement_exist(self) -> bool:
        """
        Checks if the measurements are stored
        
        Returns:
            bool: True if the measurements are stored, False otherwise
        """
        return len(self._dict_ImageUnits['unit_id']) > 0
    
    def get_dict_IDtoName(self) -> dict:
        """
        Returns the dictionary of the unit ID to name
        
        Returns:
            dict: Dictionary of the unit ID to name
        """
        return self._dict_unit_IDName
    
    def get_dict_nameToID(self) -> dict:
        """
        Returns the dictionary of the unit name to ID
        
        Returns:
            dict: Dictionary of the unit name to ID
        """
        return self._dict_unit_NameID
        
    def get_list_ImageUnit_ids(self) -> list[str]:
        """
        Returns the list of the ImageMeasurement_Unit IDs
        
        Returns:
            list[str]: List of the ImageMeasurement_Unit IDs
        """
        return self._dict_ImageUnits['unit_id']
    
    def get_list_ImageUnit_names(self) -> list[str]:
        """
        Returns the list of the ImageMeasurement_Unit names

        Returns:
            list[str]: List of the ImageMeasurement_Unit names
        """
        return list(self._dict_unit_IDName.values())

    def get_summary_units(self) -> tuple[list,list]:
        """
        Returns the summary of the ImageMeasurement_Units
        
        Returns:
            tuple: list of unit IDs, list of unit names,
                list of number of measurements in the unit,
                list of metadata dictionaries
        """
        list_units:list[MeaImg_Unit] = self._dict_ImageUnits['image_unit']
        
        list_ids = self._dict_ImageUnits['unit_id']
        list_names = [self._dict_unit_IDName[id] for id in list_ids]
        list_numMeasurements = [unit.get_numMeasurements() for unit in list_units]
        list_metadata = [unit.get_metadata(incl_nameid=False) for unit in list_units]
        
        return list_ids, list_names, list_numMeasurements, list_metadata
    
    def append_ImageMeasurementUnit(self,unit:MeaImg_Unit) -> None:
        """
        Appends an ImageMeasurement_Unit to the hub

        Args:
            unit (ImageMeasurement_Unit): ImageMeasurement_Unit object to be appended
        """
        assert isinstance(unit, MeaImg_Unit), 'Unit must be an ImageMeasurement_Unit object'
        assert unit.get_IdName()[0] not in self._dict_unit_IDName, 'Unit ID already exists'
        assert unit.get_IdName()[1] not in self._dict_unit_NameID, 'Unit name already exists'
        
        self._dict_ImageUnits['unit_id'].append(unit.get_IdName()[0])
        self._dict_ImageUnits['image_unit'].append(unit)
        
        unitId,unitName = unit.get_IdName()
        self._dict_unit_NameID[unitName] = unitId
        self._dict_unit_IDName[unitId] = unitName
        
    def reset_ImageMeasurementUnits(self) -> None:
        """
        Resets the ImageMeasurement_Units in the hub
        """
        self._dict_ImageUnits['unit_id'].clear()
        self._dict_ImageUnits['image_unit'].clear()
        self._dict_unit_NameID.clear()
        self._dict_unit_IDName.clear()
        
    def remove_ImageMeasurementUnit(self,unit_id:str) -> None:
        """
        Removes an ImageMeasurement_Unit from the hub

        Args:
            unit_id (str): ID of the ImageMeasurement_Unit to be removed
        """
        assert unit_id in self._dict_ImageUnits['unit_id'], 'Unit ID does not exist'
        
        idx = self._dict_ImageUnits['unit_id'].index(unit_id)
        self._dict_ImageUnits['unit_id'].pop(idx)
        self._dict_ImageUnits['image_unit'].pop(idx)
        
        unit_name = self._dict_unit_IDName[unit_id]
        self._dict_unit_NameID.pop(unit_name)
        self._dict_unit_IDName.pop(unit_id)
        
    def get_ImageMeasurementUnit(self,unit_id:str) -> MeaImg_Unit:
        """
        Returns an ImageMeasurement_Unit from the hub

        Args:
            unit_id (str): ID of the ImageMeasurement_Unit
        
        Returns:
            ImageMeasurement_Unit: ImageMeasurement_Unit object
        """
        assert unit_id in self._dict_ImageUnits['unit_id'], 'Unit ID does not exist'
        
        idx = self._dict_ImageUnits['unit_id'].index(unit_id)
        return self._dict_ImageUnits['image_unit'][idx]
    
    def test_generate_dummy(self):
        """
        Generates dummy ImageMeasurement_Units for testing purposes
        """
        cal = ImgMea_Cal()
        cal.generate_dummy_params()
        for i in range(5):
            unit = MeaImg_Unit(reconstruct=True)
            unit.test_generate_dummy()
            unit.set_name(f'unit_{i}')
            unit.set_calibration_ImageMeasurement_Calibration(cal)
            self.append_ImageMeasurementUnit(unit)
        return
            
class MeaImg_Handler():
    """
    Handles the saving of image measurements to a database
    """
    def __init__(self):
        # Save parameters
        self._save_parameters = {
            'table_label_measurement':'measurement',    # Label for the measurement table
            'table_label_calibration':'calibration',    # Label for the calibration table
            'folder_sublevel':'images'    # Sublevel folder to save the data
        }
        
        self._new_save_parameters = {
            'meta_table':'metadata',    # Label for the metadata table in the database
            'folder_sublevel':'images', # Sublevel folder to save the data
        }
        
        self._table_prefix = SaveParamsEnum.IMGUNIT_DB_PREFIX.value    # Prefix for the database tables
        # self._defaultDirPath = SaveParamsEnum.DEFAULT_SAVE_PATH.value
        # assert os.path.exists(self._defaultDirPath), 'Default directory path does not exist'
        # assert os.path.isdir(self._defaultDirPath), 'Default directory path is not a directory'
        
    # def load_calibration_json_to_ImgMea(self,measurement:ImageMeasurement_Unit)\
    #     -> tuple[ImageMeasurement_Unit,str,str]:
    #     """
    #     Loads the calibration parameters from a JSON file and sets them to the measurement object
        
    #     Args:
    #         measurement (image_measurement): Image measurement object which calibration parameters are to be set
        
    #     Returns:
    #         tuple[image_measurement,str,str]: Image measurement object, directory path, and name of the JSON
    #     """
        
    #     print('!!!!! TO BE MODIFIED !!!!!')
    #     # Modification idea: to load the calibration file into a handler or to return the
    #     # ImageMeasurement_Calibration obj instead of loading it into an ImageMeasurement_Unit
    #     # obj
        
    #     assert isinstance(measurement, ImageMeasurement_Unit), 'Measurement must be an image measurement object'
        
    #     savepath = filedialog.askopenfilename(title='Choose a JSON file to load the calibration parameters from',
    #         filetypes=[('JSON files','*.json')])
    #     assert savepath != '', 'Load path is empty'
        
    #     cal = ImageMeasurement_Calibration()
    #     cal.load_calibration_json(savepath)
        
    #     saveDirPath = os.path.dirname(savepath)
    #     savename = os.path.basename(savepath)
        
    #     # Set the calibration parameters to the measurement object
    #     measurement.set_calibration_ImageMeasurement_Calibration(cal)
    #     return measurement, saveDirPath, savename
    
    def save_calibration_json(self,calibration:ImgMea_Cal) -> tuple[str,str]|None:
        """
        Saves the calibration parameters to a JSON file

        Args:
            calibration (ImageMeasurement_Calibration): Calibration parameters object to be saved

        Returns:
            tuple[str,str]|None: Directory path and name of the saved JSON file or None if failed
        """
        try:
            assert isinstance(calibration, ImgMea_Cal), 'Calibration must be an ImageMeasurement_Calibration object'
            assert calibration.check_calibration_set(), 'Calibration parameters are not set'
            
            # Open a file dialog to choose the savepath
            savepath = filedialog.asksaveasfilename(title='Choose a JSON file to save the calibration parameters to',
                                                    filetypes=[('JSON files','*.json')],initialfile=calibration.id)
            assert savepath != '', 'Save path is empty'
            
            if savepath[-5:] != '.json': savepath += '.json'
            saveDirPath = os.path.dirname(savepath)
            savename = os.path.basename(savepath)
            
            ret = (saveDirPath,savename)
            
            calibration.save_calibration_json(savepath)
        except Exception as e:
            print(f'save_calibration_json ERROR: {e}')
            ret = None
            
        return ret
        
    
    def load_calibration_json(self) -> ImgMea_Cal|None:
        """
        Loads the calibration parameters from a JSON file

        Returns:
            ImageMeasurement_Calibration: ImageMeasurement_Calibration object
        """
        try:
            savepath = filedialog.askopenfilename(title='Choose a JSON file to load the calibration parameters from',
                filetypes=[('JSON files','*.json')])
            assert savepath != '', 'Load path is empty'
            
            cal = ImgMea_Cal()
            cal.load_calibration_json(savepath)
            
        except Exception as e:
            print(f'load_calibration_json ERROR: {e}')
            cal = None
        finally: return cal
    
    def save_calibration_json_from_ImgMea(self,measurement:MeaImg_Unit,savename:str=None):
        """
        Saves the calibration parameters to a JSON file
        
        Args:
            measurement (image_measurement): Image measurement object which calibration parameters are to be saved
            savename (str): Name of the JSON file. Default is the ID.
        
        Returns:
            tuple[str,str]: Directory path and name of the saved JSON file
        """
        
        print('!!!!! TO BE MODIFIED !!!!!')
        # Modification idea: to save the calibration file from an ImageMeasurement_Calibration
        # obj instead of an ImageMeasurement_Unit obj
        
        assert isinstance(measurement, MeaImg_Unit), 'Measurement must be an image measurement object'
        assert measurement.check_calibration_exist(), 'Calibration parameters are not set'
            
        # Open a file dialog to choose the savepath
        savepath = filedialog.asksaveasfilename(title='Choose a JSON file to save the calibration parameters to',
                                                filetypes=[('JSON files','*.json')])
        assert savepath != '', 'Save path is empty'
        
        if savepath[-5:] != '.json': savepath += '.json'
        saveDirPath = os.path.dirname(savepath)
        savename = os.path.basename(savepath)
        
        # Rename the calibration id to the savename
        measurement.get_ImageMeasurement_Calibration().id = savename[:-5]   # Remove the '.json' extension
        
        # Save the calibration parameters to a JSON file
        _,dict_calibration = measurement.get_calibration_asdict()
        with open(savepath,'w') as file:
            json.dump(dict_calibration,file)
        
        return saveDirPath, savename
        
    @thread_assign
    def save_ImageMeasurementHub_database(self,hub:MeaImg_Hub,initdir:str,savename:str) -> threading.Thread:
        """
        Saves the measurements to a database
        
        Args:
            hub (image_measurement_hub): Image measurement hub object to save
            initdir (str): Path to the directory
            savename (str): Name of the database
            
        Returns:
            threading.Thread: Thread of the saving process
            
        Raises:
            AssertionError: Initial directory path does not exist
            AssertionError: Initial directory path is not a directory
            AssertionError: Save name is empty
            
        Note:
            If the file already exist, it will still connect into the database and try to write into it
        """
        assert isinstance(hub, MeaImg_Hub), 'Hub must be an image measurement hub object'
        assert os.path.exists(initdir), 'Initial directory path does not exist'
        assert os.path.isdir(initdir), 'Initial directory path is not a directory'
        assert savename != '', 'Save name is empty'
        if savename[-3:] != '.db': savename += '.db'
        savepath = os.path.join(initdir,savename)
        
        # Connect to the database
        conn = sql.connect(savepath)
        
        # Save the measurements to a database
        list_unitIDs = hub.get_list_ImageUnit_ids()
        
        for unitID in list_unitIDs:
            unit = hub.get_ImageMeasurementUnit(unitID)
            self.save_ImageMeasurementUnit_database(unit,conn,savepath)
            
        conn.close()
        return
        
    def save_ImageMeasurementUnit_database(\
        self,unit:MeaImg_Unit,conn:sql.Connection,conn_path:str):
        """
        Saves the measurements to a database connected.

        Args:
            unit (ImageMeasurement_Unit): Unit to be saved
            conn (sql.Connection): Connection to the database
            conn_path (str): Path to the database
        """
        self._save_ImageMeasurementUnit_metadata_database(unit,conn)
        self._save_ImageMeasurementUnit_measurement_database(unit,conn,conn_path)
        
    def _save_image_to_png(self,saveDirPath:str,image:Image.Image,id) -> str:
        """
        Saves an image to a PNG file and returns the relative path
        
        Args:
            saveDirPath (str): Path to the directory to save the image
            image (Image.Image): Image to be saved
        """
        assert isinstance(saveDirPath, str), 'Save directory path must be a string'
        assert not os.path.exists(saveDirPath) or (os.path.exists(saveDirPath) and os.path.isdir(saveDirPath)),\
            'Save directory path is not a directory'
        assert isinstance(image, Image.Image), 'Image must be an Image.Image object'
        
        # Save the image to a PNG file
        subdirpath = os.path.join(saveDirPath,self._save_parameters['folder_sublevel'])
        if not os.path.exists(subdirpath): os.makedirs(subdirpath)
        imagepath = os.path.join(subdirpath,'{}.png'.format(id))
        image.save(imagepath,bitmap_format='png')
        
        relpath = os.path.relpath(imagepath,saveDirPath)
        relpath = r'.\{}'.format(relpath).replace('\\','/')
        
        return relpath
        
    def _save_ImageMeasurementUnit_measurement_database(
        self,unit:MeaImg_Unit,conn:sql.Connection,
        conn_path:str) -> None:
        """
        Saves the measurements to a database connected

        Args:
            unit (ImageMeasurement_Unit): Image measurement unit object to save
            conn (sql.Connection): Connection to the database
            conn_path (str): Path to the database
            
        Raises:
            AssertionError: Unit is not an ImageMeasurement_Unit object
            AssertionError: The unit does not contain any measurements and/or calibration parameters
            AssertionError: Connection is not a sqlite3 connection
        """
        assert isinstance(unit, MeaImg_Unit), 'Unit must be an image measurement unit object'
        assert unit.check_measurement_exist(), 'Unit does not contain any measurements'
        assert unit.check_calibration_exist(), 'Unit does not contain any calibration parameters'
        assert isinstance(conn, sql.Connection), 'Connection must be a sqlite3 connection'
        
        saveDirPath = os.path.dirname(conn_path)
        
        unitID,unitName = unit.get_IdName()
        table_name = self._table_prefix + unitID
        
    # >>> Image measurement save to database <<<
        dict_mea = unit.get_dict_measurement()
        dict_mea_types = unit.get_dict_measurement_types()
        
        query_keys = ''
        for key in dict_mea.keys():
            if dict_mea_types[key] in [int,float]:
                query_keys += ', {} REAL'.format(key)
            elif dict_mea_types[key] == str:
                query_keys += ', {} TEXT'.format(key)
            elif dict_mea_types[key] in [list,tuple,dict]:
                query_keys += ', {} TEXT'.format(key)
            elif dict_mea_types[key] == Image.Image:
                query_keys += ', {} TEXT'.format(key)
            else:
                raise TypeError('Measurement type not recognized')
            
        query_keys = query_keys[2:]
        
        conn.execute('CREATE TABLE IF NOT EXISTS {} ({})'\
            .format(table_name,query_keys))
        
        # Insert the measurements into the table
        keys = list(dict_mea.keys())
        for i in range(len(dict_mea[keys[0]])):
            # Generate a unique id
            unique_id = '{}_{}'.format(unitName,uuid.uuid4().hex)
            list_values = []
            for key in dict_mea.keys():
                if dict_mea_types[key] in [int,float]:
                    list_values.append(dict_mea[key][i])
                elif dict_mea_types[key] == str:
                    list_values.append(dict_mea[key][i])
                elif dict_mea_types[key] in [list,tuple,dict]:
                    list_values.append(json.dumps(dict_mea[key][i]))
                elif dict_mea_types[key] == Image.Image:
                    image = dict_mea[key][i]
                    imagepath = self._save_image_to_png(saveDirPath,image,unique_id)
                    list_values.append(imagepath)
                else:
                    raise TypeError('Measurement type not recognized')
            
            query_values = ', '.join(['?' for _ in range(len(list_values))])
            conn.execute('INSERT INTO {} VALUES ({})'.format(table_name,query_values),list_values)
        
        # Commit the changes and close the connection
        conn.commit()
        return
        
    def _save_ImageMeasurementUnit_metadata_database(self,unit:MeaImg_Unit,conn:sql.Connection) -> None:
        """
        Saves the metadata to a database connected

        Args:
            unit (ImageMeasurement_Unit): Image measurement unit object to save
            conn (sql.Connection): Connection to the database
            
        Raises:
            AssertionError: Unit is not an ImageMeasurement_Unit object
            AssertionError: The unit does not contain any metadata
            AssertionError: Connection is not a sqlite3 connection
            TypeError: Metadata type not recognized
        """
        assert isinstance(unit, MeaImg_Unit), 'Unit must be an image measurement unit object'
        assert unit.check_calibration_exist(), 'Unit does not contain any metadata'
        assert isinstance(conn, sql.Connection), 'Connection must be a sqlite3 connection'
        
        cursor = conn.cursor()
        
        # Retrieve the metadata
        meta_dict = unit.get_metadata()
        meta_types_dict = unit.get_metadata_types()
        table_metadata = self._table_prefix + self._new_save_parameters['meta_table']
        
        # Create the table for the metadata and calibration parameters
        query_keys = ''
        list_values_metadata = []
        for key in meta_dict.keys():
            if meta_types_dict[key] in [int,float]:
                query_keys += ', {} REAL'.format(key)
                list_values_metadata.append(meta_dict[key])
            elif meta_types_dict[key] == str:
                query_keys += ', {} TEXT'.format(key)
                list_values_metadata.append(meta_dict[key])
            elif meta_types_dict[key] in [list,tuple,dict]:
                query_keys += ', {} TEXT'.format(key)
                list_values_metadata.append(json.dumps(meta_dict[key]))
            else:
                raise TypeError('Metadata type not recognized')
            
        if query_keys == '': raise AssertionError('No metadata found')
            
        query_keys = query_keys[2:]
        cursor.execute('CREATE TABLE IF NOT EXISTS {} ({})'.format(table_metadata,query_keys))
        
        # Prepare the values for insertion
        query_keys = ', '.join(meta_dict.keys())
        query_metadata_values = ', '.join(['?' for _ in range(len(meta_dict.keys()))])
        query = 'INSERT INTO {} ({}) VALUES ({})'.format(table_metadata,query_keys,query_metadata_values)
        cursor.execute(query, list_values_metadata)
        
        conn.commit()
        return
        
    def load_ImageMeasurementHub_database(self,loadpath:str,hub:MeaImg_Hub|None=None)\
        -> MeaImg_Hub:
        """
        Loads the measurements from a database
        
        Args:
            loadpath (str): Path to the database
            hub (ImageMeasurement_Hub|None): Image measurement hub object, if None, a new hub is created.
                Defaults to None.
        
        Returns:
            ImageMeasurement_Hub: Image measurement hub object
        """
        assert os.path.exists(loadpath), 'Path does not exist'
        assert loadpath[-3:] == '.db', 'File is not a database'
        
        # Initialise the ImageMeasurement_Hub
        if not isinstance(hub, MeaImg_Hub): hub = MeaImg_Hub()
        
        # Connect to the database
        conn = sql.connect(loadpath)
        conn.row_factory = sql.Row
        
        # Create a cursor object
        cursor = conn.cursor()
        
        # Load the measurements from the database
        table_metadata = self._table_prefix + self._new_save_parameters['meta_table']
        
        # Select all the rows in the metadata table
        cursor.execute('SELECT * FROM {}'.format(table_metadata))
        rows = cursor.fetchall()
        
        unit = MeaImg_Unit(None,None,reconstruct=True)
        metadata_types = unit.get_metadata_types()
        key_dict = [key for key in metadata_types.keys() if metadata_types[key] == dict]
        
        for row in rows:
            row:sql.Row
            dict_row = dict(row)
            for key in key_dict:
                dict_row[key] = json.loads(dict_row[key])
            unit = MeaImg_Unit(None,None,reconstruct=True)
            unit.set_metadata_fromfile(dict_row)
            unit = self.load_ImageMeasurementUnit_database(unit,unit.get_IdName()[0],
                                                           conn=conn,conn_path=loadpath)
            hub.append_ImageMeasurementUnit(unit)
            
    def load_ImageMeasurementUnit_database(self,unit:MeaImg_Unit,
        unit_id:str,conn:sql.Connection,conn_path:str) -> MeaImg_Unit:
        """
        Loads the measurements from a database connected
        
        Args:
            unit (ImageMeasurement_Unit): Image measurement unit object to load
            unit_id (str): ID of the ImageMeasurement_Unit
            conn (sql.Connection): Connection to the database
            conn_path (str): Path to the database
        
        Returns:
            ImageMeasurement_Unit: Image measurement unit object
        """
        assert isinstance(unit, MeaImg_Unit), 'Unit must be an image measurement unit object'
        assert isinstance(unit_id, str), 'Unit ID must be a string'
        assert isinstance(conn, sql.Connection), 'Connection must be a sqlite3 connection'
        
        conn.row_factory = sql.Row
        cursor = conn.cursor()
        table_name = self._table_prefix + unit_id
        
        # Load the measurements from the database
        cursor.execute('SELECT * FROM {}'.format(table_name))
        rows = cursor.fetchall()
        
        dict_types = unit.get_dict_measurement_types()
        dict_mea = {}
        for key in dict_types.keys():
            dict_mea[key] = []
        
        for row in rows:
            row:sql.Row
            dict_row = dict(row)
            
            for key in dict_types.keys():
                if dict_types[key] == int:
                    dict_mea[key].append(int(float(dict_row[key])))
                elif dict_types[key] == float:
                    dict_mea[key].append(float(dict_row[key]))
                elif dict_types[key] == str:
                    dict_mea[key].append(str(dict_row[key]))
                elif dict_types[key] in [list,tuple,dict]:
                    dict_mea[key].append(json.loads(dict_row[key]))
                elif dict_types[key] == Image.Image:
                    imagepath = dict_row[key]
                    imagepath = os.path.join(os.path.dirname(conn_path),imagepath)
                    image = Image.open(imagepath)
                    dict_mea[key].append(image)
                else:
                    raise TypeError('Measurement type not recognized')
                
        unit.set_dict_measurement_fromfile(dict_mea)
        
        return unit

def test():
    cal = ImgMea_Cal('test cal')
    cal.generate_dummy_params()
    
    hub = MeaImg_Hub()
    for i in range(3):
        unit = MeaImg_Unit('test unit {}'.format(i),calibration=cal)
        unit.test_generate_dummy()
        hub.append_ImageMeasurementUnit(unit)
        
    handler = MeaImg_Handler()
    
    savepath = './sandbox/test - Copy2.db'
    dirpath = os.path.dirname(savepath)
    savename = os.path.basename(savepath)
    
    thread = handler.save_ImageMeasurementHub_database(hub,dirpath,savename)
    thread.join()
    
    hub2 = MeaImg_Hub()
    handler.load_ImageMeasurementHub_database(savepath,hub2)
    savename2 = 'test - Copy3.db'
    thread = handler.save_ImageMeasurementHub_database(hub2,dirpath,savename2)
    thread.join()
    
    print('Test completed')
    return

if __name__ == '__main__':
    test()