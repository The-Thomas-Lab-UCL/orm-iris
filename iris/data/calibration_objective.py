"""
NOTE:
- FLIPNOTE: Sometimes, there will be a *= -1 multiplier when calculating or converting the coordinate between the
    stage and the camera frame of reference (FoR). This is because the stage FoR and the camera FoR are
    opposite to each other. i.e., when we see that a feature moves in a certain direction in the camera,
    the stage is actually moving in the oppsite direction. Think about it, when we see that a feature
    moves to the right in the camera, the stage is actually moving to the left.
"""

import sys
import os

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

from tkinter import filedialog

import numpy as np
from numpy import ndarray as arr
from PIL import Image

import sqlite3 as sql
import json
import glob
import uuid

from dataclasses import dataclass,asdict

from iris.utils.general import *


@dataclass
class ImgMea_Cal:
    id: str = None                      # Calibration ID
    scale_x_pixelPerMm: float = None    # Scale in pixels per mm in the x direction
    scale_y_pixelPerMm: float = None    # Scale in pixels per mm in the y direction
    flip_y: int = -1                    # Flip the y-axis of the image (-1: flip, 1: no flip)
    rotation_rad: float = 0             # Rotation in radians (-pi < rot <= pi)
    laser_coor_x_mm: float = None       # Laser coordinate x in mm from the image's center frame of reference
    laser_coor_y_mm: float = None       # Laser coordinate y in mm from the image's center frame of reference
    
    mat_M_stg2img: arr = None           # Transformation matrix from the camera frame of reference to the stage frame of reference
    mat_M_inv_img2stg: arr = None       # Inverse transformation matrix from the stage frame of reference to the camera frame of reference
    
    def check_calibration_set(self,exclude_laser:bool=False) -> bool:
        """
        Checks if all the calibration parameters are set
        
        Args:
            exclude_laser (bool): Exclude the laser coordinate from the check
            
        Returns:
            bool: True if all the calibration parameters are set, False otherwise
        """
        if exclude_laser:
            laser_x = self.laser_coor_x_mm
            laser_y = self.laser_coor_y_mm
            self.laser_coor_x_mm = 0.0
            self.laser_coor_y_mm = 0.0
        
        dict_self = asdict(self)
        ret = not any([v is None for v in dict_self.values()])
        
        if exclude_laser:
            self.laser_coor_x_mm = laser_x
            self.laser_coor_y_mm = laser_y
            
        return ret
    
    def _check_reshape(self,coor:arr) -> arr:
        """
        Reshapes the coordinate if it is not of shape (2,1)
        
        Args:
            coor(np.ndarray): Coordinate
        
        Returns:
            np.ndarray: Reshaped coordinate (2,1)
        """
        if not coor.shape == (2,1):
            try: coor = coor.reshape((2,1))
            except: raise AssertionError('Coordinate must be of shape (2,1) and cannot be reshaped to this shape')
        return coor
    
    def convert_stg2mea(self,coor_stg:arr) -> arr:
        """
        Converts the stage coordinate to the measurement coordinate
        
        Args:
            coor_stg(np.ndarray): Stage coordinate
        
        Returns:
            np.ndarray: Measurement coordinate (flattened 1D array (x,y))
        """
        assert self.check_calibration_set(), 'Calibration parameters are not set'
        assert isinstance(coor_stg, arr), 'Stage coordinate must be a numpy array'
        coor_stg = self._check_reshape(coor_stg)
        
        laser_coor = np.array([[self.laser_coor_x_mm],[self.laser_coor_y_mm]])
        ret = coor_stg + laser_coor
        return ret.reshape([-1])
    
    def convert_mea2stg(self,coor_mea:arr) -> arr:
        """
        Converts the measurement coordinate to the stage coordinate
        
        Args:
            coor_mea(np.ndarray): Measurement coordinate
        
        Returns:
            np.ndarray: Stage coordinate (flattened 1D array (x,y))
        """
        assert self.check_calibration_set(), 'Calibration parameters are not set'
        assert isinstance(coor_mea, arr), 'Measurement coordinate must be a numpy array'
        coor_mea = self._check_reshape(coor_mea)
        
        laser_coor = np.array([[self.laser_coor_x_mm],[self.laser_coor_y_mm]])
        ret = coor_mea - laser_coor
        return ret.reshape([-1])
    
    def convert_stg2imgpt(self,coor_stg_mm:arr,coor_point_mm:arr) -> arr:
        """
        Converts the stage coordinate to the coordinate in the camera frame of reference
        
        Args:
            coor_stg(np.ndarray): Stage coordinate
            coor_point_mm(np.ndarray): Point coordinate in the stage frame of reference
        
        Returns:
            np.ndarray: Image coordinate (flattened 1D array (x,y))
        """
        assert self.check_calibration_set(exclude_laser=True), 'Calibration parameters are not set'
        assert isinstance(coor_stg_mm, arr), 'Stage coordinate must be a numpy array'
        coor_stg_mm = self._check_reshape(coor_stg_mm)
        assert isinstance(coor_point_mm, arr), 'Point coordinate must be a numpy array'
        coor_point_mm = self._check_reshape(coor_point_mm)
        
        ret = self.mat_M_stg2img @ (coor_point_mm - coor_stg_mm)
        
        return ret.reshape([-1])
    
    def convert_imgpt2stg(self,coor_img_pixel:arr,coor_stage_mm:arr) -> arr:
        """
        Converts coordinate of a point in the camera frame of refernece
        to the coordinate in the stage frame of reference
        
        Args:
            coor_img_pixel(np.ndarray): Image coordinate
            coor_stage_mm(np.ndarray): Stage coordinate
        
        Returns:
            np.ndarray: Stage coordinate (flattened 1D array (x,y))
        """
        assert self.check_calibration_set(exclude_laser=True), 'Calibration parameters are not set'
        assert isinstance(coor_img_pixel, arr), 'Image coordinate must be a numpy array'
        coor_img_pixel = self._check_reshape(coor_img_pixel)
        assert isinstance(coor_stage_mm, arr), 'Stage coordinate must be a numpy array'
        coor_stage_mm = self._check_reshape(coor_stage_mm)
        
        ret = self.mat_M_inv_img2stg @ coor_img_pixel + coor_stage_mm
        
        return ret.reshape([-1])
    
    def set_calibration_params(self,scale_x_pixelPerMm:float,scale_y_pixelPerMm:float,laser_coor_x_mm:float,laser_coor_y_mm:float,
                               rotation_rad:float,flip_y:int|None=None) -> None:
        """
        Sets the calibration parameters manually

        Args:
            scale_x_pixelPerMm (float): Scale in pixels per mm in the x direction
            scale_y_pixelPerMm (float): Scale in pixels per mm in the y direction
            laser_coor_x_mm (float): Laser coordinate x in mm from the image's origin frame of reference
            laser_coor_y_mm (float): Laser coordinate y in mm from the image's origin frame of reference
            rotation_rad (float): Rotation in radians (-pi < rot <= pi)
            flip_y (int): Flip the y-axis of the image (-1: flip, 1: no flip). If None, the flip is unchanged
        """
        assert all([isinstance(v,float) for v in [scale_x_pixelPerMm,scale_y_pixelPerMm,laser_coor_x_mm,laser_coor_y_mm,rotation_rad]]),\
            'Calibration parameters must be floats'
            
        self.scale_x_pixelPerMm = scale_x_pixelPerMm
        self.scale_y_pixelPerMm = scale_y_pixelPerMm
        self.laser_coor_x_mm = laser_coor_x_mm
        self.laser_coor_y_mm = laser_coor_y_mm
        self.rotation_rad = rotation_rad
        if flip_y is not None: self.flip_y = flip_y
        
        sx = self.scale_x_pixelPerMm
        sy = self.scale_y_pixelPerMm
        f = self.flip_y
        theta = self.rotation_rad
        
        # Calculate the transformation matrix
        mat_S = np.array(   # Scale matrix [pixel/mm]
            [[sx, 0],
             [0, sy]]
        )
        
        mat_F = np.array(   # Flip matrix [a.u.]
            [[1, 0],
             [0, f]]
        )
        
        mat_R = np.array(   # Rotation matrix [a.u.]
            [[np.cos(theta), -np.sin(theta)],
             [np.sin(theta), np.cos(theta)]]
        )
        
        self.mat_M_stg2img = mat_R @ mat_F @ mat_S # [pixel/mm]
        self.mat_M_inv_img2stg = np.linalg.inv(self.mat_M_stg2img)
        
    
    def set_calibration_vector(self,v1s:arr,v2s:arr,v3s:arr,v1c:arr,v2c:arr,v3c:arr,vlc:arr) -> None:
        """
        Sets the calibration parameters from the vectors of the tracked features in the image
        and their corresponding stage coordinates (vector 1, 2, 3) and laser coordinate
        
        Args:
            v1s(np.ndarray): Vector 1 (stage frame of reference (FoR)) [mm]
            v2s(np.ndarray): Vector 2 (stage FoR), must have the same x coordinate as v1s [mm]
            v3s(np.ndarray): Vector 3 (stage FoR), must have the same y coordinate as v1s [mm]
            v1c(np.ndarray): Vector 1 (camera FoR) corresponding to v1s [pixel]
            v2c(np.ndarray): Vector 2 (camera FoR) corresponding to v2s [pixel]
            v3c(np.ndarray): Vector 3 (camera FoR) corresponding to v3s [pixel]
            vlc(np.ndarray): Vector of the laser coordinate in the camera FoR [pixel]
        """
        assert all([isinstance(v, arr) for v in [v1s,v2s,v3s,v1c,v2c,v3c,vlc]]), 'Vectors must be numpy arrays'
        v1s,v2s,v3s,v1c,v2c,v3c,vlc = [self._check_reshape(v) for v in [v1s,v2s,v3s,v1c,v2c,v3c,vlc]]
        
        # assert np.allclose(v1s[1],v2s[1]), 'Vector 2 must have the same y coordinate as vector 1'
        # assert np.allclose(v2s[0],v3s[0]), 'Vector 3 must have the same x coordinate as vector 2'
        
        v1s*= -1
        v2s*= -1
        v3s*= -1
        
        # Calculate the vector distances
        dvs_12 = v2s - v1s  # Vector 1 to 2 in the stage frame of reference
        dvs_23 = v3s - v2s  # Vector 2 to 3 in the stage frame of reference
        
        dvc_12 = v2c - v1c  # Vector 1 to 2 in the camera frame of reference
        dvc_23 = v3c - v2c  # Vector 2 to 3 in the camera frame of reference
                
        theta_sign = np.sign(dvs_12[0][0])
        # Calculate the rotation angle in radians, float
        theta = np.arctan2(dvc_12[1][0]*theta_sign,dvc_12[0][0]*theta_sign)
        
        # Calculate the scale in pixels per mm in the x direction
        sx = dvc_12[0][0]/(dvs_12[0][0]*np.cos(theta)) # [pixel/mm]
        
        # Calculate the y-axis flip
        f = np.sign(dvc_23[1][0]/(dvs_23[1][0]*np.cos(theta)))
        
        # Calculate the scale in pixels per mm in the y direction
        sy = (dvc_23[1][0]/(dvs_23[1][0]*f*np.cos(theta))) # [pixel/mm]
        
        if abs(theta) > np.pi/2:
            theta -= np.sign(theta)*np.pi
            sx *= -1
            sy *= -1
        
        # Calculate the transformation matrix
        mat_S = np.array(   # Scale matrix [pixel/mm]
            [[sx, 0],
             [0, sy]]
        )
        
        mat_F = np.array(   # Flip matrix [a.u.]
            [[1, 0],
             [0, f]]
        )
        
        mat_R = np.array(   # Rotation matrix [a.u.]
            [[np.cos(theta), -np.sin(theta)],
             [np.sin(theta), np.cos(theta)]]
        )
        
        self.mat_M_stg2img = mat_R @ mat_F @ mat_S # [pixel/mm]
        self.mat_M_inv_img2stg = np.linalg.inv(self.mat_M_stg2img)
        
        self.scale_x_pixelPerMm = sx
        self.scale_y_pixelPerMm = sy
        self.flip_y = f
        self.rotation_rad = theta
        
        self.set_laser_coor(vlc)
        
    def set_laser_coor(self,coor_laser_pixel:arr) -> None:
        """
        Sets the laser coordinate in the camera frame of reference

        Args:
            coor_laser_pixel (arr): Laser coordinate in the camera frame of reference [pixel]
        """
        assert self.check_calibration_set(exclude_laser=True), 'Calibration parameters are not set'
        assert isinstance(coor_laser_pixel, arr), 'Laser coordinate must be a numpy array'
        coor_laser_pixel = self._check_reshape(coor_laser_pixel)
        
        coor_laser_stage = self.convert_imgpt2stg(coor_laser_pixel,np.array([0,0]))
                
        self.laser_coor_x_mm = coor_laser_stage[0]
        self.laser_coor_y_mm = coor_laser_stage[1]
        
    def save_calibration_json(self,path:str) -> None:
        """
        Saves the calibration parameters to a JSON file
        
        Args:
            path (str): Path to save the JSON file
        """
        assert self.check_calibration_set(), 'Calibration parameters are not set'
        if not path.endswith('.json'): path += '.json'
        if not os.path.exists(os.path.dirname(path)): os.makedirs(os.path.dirname(path))
        assert not os.path.exists(path), 'File already exists'
        
        self.mat_M_inv_img2stg = self.mat_M_inv_img2stg.tolist()
        self.mat_M_stg2img = self.mat_M_stg2img.tolist()
        
        with open(path,'w') as f:
            json.dump(asdict(self),f)
        
        self.mat_M_inv_img2stg = np.array(self.mat_M_inv_img2stg)
        self.mat_M_stg2img = np.array(self.mat_M_stg2img)
        
        return
        
    def load_calibration_json(self,path:str) -> None:
        """
        Loads the calibration parameters from a JSON file

        Args:
            path (str): Path to the JSON file
            
        Raises:
            AssertionError: Path does not exist
            AssertionError: File must be a JSON file
            ValueError: Error loading the JSON file
        """
        assert os.path.exists(path), 'Path does not exist'
        assert path.endswith('.json'), 'File must be a JSON file'
        
        try:
            if not os.path.isabs(path): path = os.path.abspath(path)
            dict = json.load(open(path,'r'))
            id = os.path.basename(path).split('.')[0]
            self.set_calibration_fromfile_legacy(id,dict)
        except KeyError: pass
        except Exception as e: raise ValueError(f'Error loading the JSON file (legacy): {e}')
        
        try:
            with open(path,'r') as f:
                dict_cal = json.load(f)
                
            [self.__setattr__(key,dict_cal[key]) for key in dict_cal.keys()]
            
            self.mat_M_inv_img2stg = np.array(self.mat_M_inv_img2stg)
            self.mat_M_stg2img = np.array(self.mat_M_stg2img)
        except Exception as e: raise ValueError(f'Error loading the JSON file: {e}')
        
    def set_calibration_fromfile_legacy(self,cal_id:str,dict_calibration:dict) -> None:
        """
        Sets the calibration parameters from a dictionary (legacy)
        
        Args:
            cal_id (str): Calibration ID
            dict_calibration (dict): Calibration parameters dictionary
        """
        keys = set([
            'scale_x_mmPerPixel',    # Float: Scale in mm per pixel in the x direction
            'scale_y_mmPerPixel',    # Float: Scale in mm per pixel in the y direction
            'laser_coor_x_mm',       # float: Laser coordinate x in mm from the image's center frame of reference
            'laser_coor_y_mm',       # float: Laser coordinate y in mm from the image's center frame of reference
        ])
        
        keys_type = {
            'scale_x_mmPerPixel': float,
            'scale_y_mmPerPixel': float,
            'laser_coor_x_mm': (tuple,list),
            'laser_coor_y_mm': (tuple,list)
        }
        
        assert isinstance(cal_id,str), 'Calibration ID must be a string'
        assert isinstance(dict_calibration, dict), 'Calibration parameters must be a dictionary'
        if not all([key in keys for key in dict_calibration.keys()]): raise KeyError('Dictionary keys must match the calibration keys')
        assert all([isinstance(dict_calibration[key], keys_type[key]) for key in list(dict_calibration.keys())]),\
            'Calibration parameters must be float or integers'
        
        self.id = cal_id
        # Assign the calibration parameters
        sx_pixelPerMm = 1/dict_calibration['scale_x_mmPerPixel']
        sy_pixelPerMm = 1/dict_calibration['scale_y_mmPerPixel']
        
        self.scale_x_pixelPerMm = sx_pixelPerMm
        self.scale_y_pixelPerMm = sy_pixelPerMm
        self.flip_y = -1
        self.rotation_rad = 0
        self.laser_coor_x_mm = dict_calibration['laser_coor_x_mm']
        self.laser_coor_y_mm = dict_calibration['laser_coor_y_mm']
        
        S_inv = np.array(
            [[sx_pixelPerMm, 0],
             [0, sy_pixelPerMm]]
        )
        
        F_inv = np.array(
            [[1, 0],
             [0, self.flip_y]]
        )
        
        R_inv = np.array(
            [[np.cos(self.rotation_rad), -np.sin(self.rotation_rad)],
             [np.sin(self.rotation_rad), np.cos(self.rotation_rad)]]
        )
        
        self.mat_M_inv_img2stg = S_inv @ F_inv @ R_inv
        self.mat_M_stg2img = np.linalg.inv(self.mat_M_inv_img2stg)
        
        return

    def get_calibration_asdict(self) -> dict:
        """
        Returns the calibration parameters as a dictionary
        
        Returns:
            dict: Calibration parameters dictionary
        """
        self.mat_M_inv_img2stg = self.mat_M_inv_img2stg.tolist()
        self.mat_M_stg2img = self.mat_M_stg2img.tolist()
        
        dict_ret = asdict(self)
        
        self.mat_M_inv_img2stg = np.array(self.mat_M_inv_img2stg)
        self.mat_M_stg2img = np.array(self.mat_M_stg2img)
        return dict_ret
    
    def set_calibration_fromdict(self,cal_id:str,dict_calibration:dict) -> None:
        """
        Sets the calibration parameters from a dictionary
        
        Args:
            cal_id (str): Calibration ID
            dict_calibration (dict): Calibration parameters dictionary
        """
        if not all([key in asdict(self).keys() for key in dict_calibration.keys()]): 
            try: self.set_calibration_fromfile_legacy(cal_id,dict_calibration)
            except: raise ImportError('Legacy: Dictionary keys must match the calibration keys')
        
        [self.__setattr__(key,dict_calibration[key]) for key in dict_calibration.keys()]
        
        self.mat_M_inv_img2stg = np.array(self.mat_M_inv_img2stg)
        self.mat_M_stg2img = np.array(self.mat_M_stg2img)
        
        return
        
    def get_calibration_only_tuple(self) -> NotImplementedError:
        raise NotImplementedError('This method is not implemented')
        
    def generate_dummy_params(self):
        """
        Generates a dummy calibration parameters for testing purposes
        """
        self.id = 'dummy'
        self.scale_x_pixelPerMm = 19
        self.scale_y_pixelPerMm = 24
        self.laser_coor_x_mm = 0.03
        self.laser_coor_y_mm = 0.02
        self.rotation_rad = 0.02
        self.flip_y = -1
        
        S_inv = np.array(
            [[self.scale_x_pixelPerMm, 0],
             [0, self.scale_y_pixelPerMm]]
        )
        
        F_inv = np.array(
            [[1, 0],
             [0, self.flip_y]]
        )
        
        R_inv = np.array(
            [[np.cos(self.rotation_rad), -np.sin(self.rotation_rad)],
             [np.sin(self.rotation_rad), np.cos(self.rotation_rad)]]
        )
        
        self.mat_M_inv_img2stg = S_inv @ F_inv @ R_inv
        self.mat_M_stg2img = np.linalg.inv(self.mat_M_inv_img2stg)
    
class ImgMea_Cal_Hub():
    """
    A class to manage the calibration parameters loaded in a session
    """
    
    def __init__(self):
        self._dict_calibrations = {
            'calibration_id':[],
            'calibration':[]
        }
        self._last_path = None
        
        self._list_observers = []
        
    def add_observer(self,callback_func) -> None:
        """
        Adds an observer callback function to be notified when the calibration hub is updated
        
        Args:
            callback_func (function): Callback function to be called when the calibration hub is updated
        """
        assert callable(callback_func), 'Callback function must be callable'
        self._list_observers.append(callback_func)
        
    def remove_observer(self,callback_func) -> None:
        """
        Removes an observer callback function
        
        Args:
            callback_func (function): Callback function to be removed
        """
        assert callable(callback_func), 'Callback function must be callable'
        try: self._list_observers.remove(callback_func)
        except Exception as e: print(f'Error removing observer (ImgCalHub): {e}')
        
    def notify_observers(self) -> None:
        """
        Notifies all observers that the calibration hub has been updated
        """
        for callback in self._list_observers:
            try: callback()
            except Exception as e: print(f'Error notifying observer (ImgCalHub): {e}')
        
    def load_calibration_folder(self, uselastpath:bool=False) -> None:
        """
        Prompts the user to select a folder to load the calibration files
        
        Args:
            uselastpath (bool): Use the last dir path. Default is False
        
        Raises:
            AssertionError: No directory selection is made
        """
        if uselastpath:
            try: self.load_calibration_folder(self._last_path); return
            except: pass
            
        path_folder = filedialog.askdirectory(title='Choose a folder to load the calibration files from')
        assert path_folder != '', 'No directory selection is made'
        
        self.load_calibrations(path_folder)
        
    def load_calibrations(self,path_folder:str) -> None:
        """
        Loads all the calibration files from a folder

        Args:
            path_folder (str): Path to the folder containing the calibration files
            
        Raises:
            AssertionError: Path is not a directory
            AssertionError: Path does not exist
        """
        assert os.path.exists(path_folder), 'Path does not exist'
        assert os.path.isdir(path_folder), 'Path is not a directory'
        
        self.reset_calibrations()
        
        list_json = glob.glob(os.path.join(path_folder,'*.json'))
        
        for path in list_json:
            try:
                cal = ImgMea_Cal()
                cal.load_calibration_json(path)
                cal_id = cal.id
                
                self._dict_calibrations['calibration_id'].append(cal_id)
                self._dict_calibrations['calibration'].append(cal)
            except: pass
            
        self._last_path = path_folder
    
    def reset_calibrations(self) -> None:
        """
        Empty the stored calibrations
        """
        self._dict_calibrations['calibration_id'].clear()
        self._dict_calibrations['calibration'].clear()
            
    def get_calibration(self,cal_id:str) -> ImgMea_Cal:
        """
        Returns the calibration parameters
        
        Args:
            cal_id (str): Calibration ID
        
        Returns:
            ImageMeasurement_Calibration: Calibration parameters
        """
        assert cal_id in self._dict_calibrations['calibration_id'], 'Calibration ID does not exist'
        
        idx = self._dict_calibrations['calibration_id'].index(cal_id)
        return self._dict_calibrations['calibration'][idx]
    
    def get_calibration_ids(self) -> list[str]:
        """
        Returns the list of calibration IDs
        
        Returns:
            list[str]: List of calibration IDs
        """
        return self._dict_calibrations['calibration_id']
    
    def generate_dummy_calibrations(self, n:int=1) -> None:
        """
        Generates dummy calibration parameters for testing purposes
        
        Args:
            n (int): Number of dummy calibrations to generate. Default is 1
        """
        for i in range(n):
            cal = ImgMea_Cal()
            cal.generate_dummy_params()
            cal_id = f'dummy_{i}'
            
            self._dict_calibrations['calibration_id'].append(cal_id)
            self._dict_calibrations['calibration'].append(cal)
    
def generate_dummy_calibrationHub() -> ImgMea_Cal_Hub:
    """
    Generates a dummy calibration hub with dummy calibration parameters for testing purposes.
    A dummy calibration is created and appended to the calibration hub.
    
    Returns:
        ImageMeasurement_Calibration_Hub: Dummy calibration hub with dummy calibration parameters
    """
    calhub = ImgMea_Cal_Hub()
    calhub.reset_calibrations()
    
    cal = ImgMea_Cal()
    cal.generate_dummy_params()
    
    calhub._dict_calibrations['calibration_id'].append(cal.id)
    calhub._dict_calibrations['calibration'].append(cal)
    
    return calhub
    
def test_calibration_save():
    cal = ImgMea_Cal()
    cal.generate_dummy_params()
    try:
        cal.save_calibration_json(r'.\sandbox\dummy.json')
    except Exception as e: print(e)
        
def test_calibration_load():
    cal = ImgMea_Cal()
    cal.load_calibration_json(r'.\sandbox\dummy.json')
    
    print(cal)
    return cal
    
def test_calibration_conversions():
    cal = test_calibration_load()
    
    coor_stg = np.array([0.1,0.5])
    coor_point = np.array([[19],[0.05]])
    
    coor_mea = cal.convert_stg2mea(coor_stg)
    coor_img = cal.convert_stg2imgpt(coor_stg,coor_point)
    coor_stg2 = cal.convert_imgpt2stg(coor_img,coor_stg)
    
    print(coor_mea)
    print(coor_img)
    print(coor_stg2)
    
if __name__ == '__main__':
    test_calibration_conversions()