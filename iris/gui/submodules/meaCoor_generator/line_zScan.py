"""
An instance that manages the linear z-scan method for the mapping methods.
To be used in conjunction with the 2D mapping coordinate generators.
"""
if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

import tkinter as tk
import numpy as np
from typing import Callable
    
from iris.gui.motion_video import Wdg_MotionController
from iris.utils.general import *

class ZScanMethod_linear(tk.Frame):
    """
    A class that manages the linear z-scan method for the mapping methods.
    """
    def __init__(self,container_frame,getter_stagecoor:Callable[[],tuple[float,float,float]],
                 status_bar:tk.Label, *args, **kwargs) -> None:
        """
        Initialises the class with the necessary parameters.

        Args:
            container_frame (tk.Frame): The frame in which the class will be embedded.
            getter_stagecoor (Callable[[],tuple[float,float,float]]): A function that returns the current stage coordinates.
            status_bar (tk.Label): The statusbar to use
        """
        super().__init__(container_frame)
        
        # Set the motion controller
        self._getter_stagecoor = getter_stagecoor
        self._statbar:tk.Label = status_bar
        self._bg_color = self._statbar.cget('background')
        
        # Frame setup
        self._frm = tk.LabelFrame(self,text='Z-scan parameters',padx=5,pady=5)
        self._frm.grid(row=0,column=0,sticky='nswe')
        
        # Scan parameters
        self._zResolution = 1
        self._zStart_mm = None
        self._zEnd_mm = None
        
        # Widgets
        self._str_zStart = tk.StringVar(value='Z-start coordinate [μm]: {}'.format(self._zStart_mm))
        self._str_zEnd = tk.StringVar(value='Z-end coordinate [μm]: {}'.format(self._zEnd_mm))
        self._str_zResolution = tk.StringVar(value='Z-resolution [a.u.]: {}'.format(self._zResolution))
        
        lbl_zStart = tk.Label(self._frm,textvariable=self._str_zStart)
        lbl_zEnd = tk.Label(self._frm,textvariable=self._str_zEnd)
        lbl_zResolution = tk.Label(self._frm,textvariable=self._str_zResolution)
        
        wid = 10
        self._entry_zStart=tk.Entry(self._frm,width=wid)
        self._entry_zEnd=tk.Entry(self._frm,width=wid)
        self._spin_zResolution=tk.Spinbox(self._frm,from_=1,to=1000,increment=1,width=wid)
        
        func_getcoor = lambda:self._getter_stagecoor()[2]
        func_set_entry_zstart = lambda:self._update_params(zstart_mm=self._convert_numeric(self._entry_zStart.get())/1e3)
        func_set_entry_zend = lambda:self._update_params(zend_mm=self._convert_numeric(self._entry_zEnd.get())/1e3)
        func_set_entry_zres = lambda:self._update_params(zres=self._convert_numeric(self._spin_zResolution.get(),ret_float=False))
        func_set_getcoor_zstart = lambda:self._update_params(zstart_mm=func_getcoor())
        func_set_getcoor_zend = lambda:self._update_params(zend_mm=func_getcoor())
        
        btn_set_zStart = tk.Button(self._frm,text='Set',command=func_set_entry_zstart)
        btn_set_zEnd = tk.Button(self._frm,text='Set',command=func_set_entry_zend)
        btn_set_zRes = tk.Button(self._frm,text='Set',command=func_set_entry_zres)
        
        btn_get_zStart = tk.Button(self._frm,text='Get stage-coor',command=func_set_getcoor_zstart)
        btn_get_zEnd = tk.Button(self._frm,text='Get stage-coor',command=func_set_getcoor_zend)
        
        self._entry_zStart.bind('<Return>',lambda e:func_set_entry_zstart())
        self._entry_zEnd.bind('<Return>',lambda e:func_set_entry_zend())
        self._spin_zResolution.bind('<Return>',lambda e:func_set_entry_zres())
        
        # Grid
        lbl_zStart.grid(row=0,column=0,sticky='w',columnspan=3)
        self._entry_zStart.grid(row=1,column=0,sticky='w')
        btn_set_zStart.grid(row=1,column=1,sticky='w')
        btn_get_zStart.grid(row=1,column=2,sticky='w')
        
        lbl_zEnd.grid(row=2,column=0,sticky='w',columnspan=3)
        self._entry_zEnd.grid(row=3,column=0,sticky='w')
        btn_set_zEnd.grid(row=3,column=1,sticky='w')
        btn_get_zEnd.grid(row=3,column=2,sticky='w')
        
        lbl_zResolution.grid(row=4,column=0,sticky='w',columnspan=3)
        self._spin_zResolution.grid(row=5,column=0,sticky='w')
        btn_set_zRes.grid(row=5,column=1,sticky='w')
        
    def check_params(self) -> bool:
        """
        Checks if the parameters are set.

        Returns:
            bool: True if the parameters are set, False otherwise.
        """
        if all([isinstance(self._zStart_mm,float),isinstance(self._zEnd_mm,float),isinstance(self._zResolution,int)]):
            return True
        else:
            return False
        
    def get_coordinates_mm(self,mapping_coor:list[tuple[float,float,float]]) -> list[list[tuple[float,float,float]]]|None:
        """
        Converts the 2D mapping coordinates to 3D coordinates for the z-scan method.

        Args:
            mapping_coor (list[tuple[float,float,float]]): The mapping coordinates

        Returns:
            list[list[tuple[float,float,float]]]|None: List of 2D mapping coordinates with varying z-scan coordinates OR
                None if the z-scan parameters are not set.
        """
        try:
            if not self.check_params():
                self._statbar.configure(text='Error: Z-scan parameters not set',bg='yellow')
                return None
            mapping_coor_3D = []
            zcoors = np.linspace(self._zStart_mm,self._zEnd_mm,self._zResolution)
            for z in zcoors:
                mapping_coor_2D = [(coor[0],coor[1],z) for coor in mapping_coor]
                mapping_coor_3D.append(mapping_coor_2D)
            return mapping_coor_3D
        except Exception as e:
            self._statbar.configure(text='Error: {}'.format(e),bg='red')
            return None
        
    def _convert_numeric(self,val,ret_float:bool=True) -> float|int|None:
        """
        Converts the input to a float or int if possible.
        
        Args:
            val: The value to convert
            ret_float (bool, optional): Whether to return a float or int. Defaults to True.
        """
        try:
            if ret_float: return float(val)
            else: return int(float(val))
        except:
            return None
    
    def _update_params(self,zstart_mm:float=None,zend_mm:float=None,zres:int=None):
        """
        Updates the parameters of the z-scan method.
        
        Args:
            zstart (float, optional): The start z-coordinate. Defaults to None.
            zend (float, optional): The end z-coordinate. Defaults to None.
            zres (int, optional): The z-resolution. Defaults to None.
        
        Note:
            If the parameter is None, the parameter is not updated.
        """
        if isinstance(zstart_mm,(int,float)):
            self._zStart_mm = float(zstart_mm)
            self._str_zStart.set('Z-start coordinate [μm]: {:.1f}'.format(self._zStart_mm*1e3))
            self._entry_zStart.delete(0,tk.END)
            self._entry_zStart.insert(0,'{:.1f}'.format(self._zStart_mm*1e3))
        if isinstance(zend_mm,(int,float)):
            self._zEnd_mm = float(zend_mm)
            self._str_zEnd.set('Z-end coordinate [μm]: {:.1f}'.format(self._zEnd_mm*1e3))
            self._entry_zEnd.delete(0,tk.END)
            self._entry_zEnd.insert(0,'{:.1f}'.format(self._zEnd_mm*1e3))
        if isinstance(zres,int):
            self._zResolution = zres
            self._str_zResolution.set('Z-resolution [a.u.]: {}'.format(self._zResolution))
            self._spin_zResolution.delete(0,tk.END)
            self._spin_zResolution.insert(0,self._zResolution)
            
    def report_params(self) -> None:
        """
        Prints the current parameters to the console.
        """
        try:
            print('Z-scan parameters: {}'.format(get_timestamp_us_str()))
            print(f'Z-start: {self._zStart_mm}')
            print(f'Z-end: {self._zEnd_mm}')
            print(f'Z-resolution: {self._zResolution}')
            print('Z-scan coors: {}'.format(np.linspace(self._zStart_mm,self._zEnd_mm,self._zResolution)))
        except:
            pass
            
if __name__ == '__main__':
    import time
    
    root = tk.Tk()
    root.title('Z-scan method')
    
    def get_stagecoor():
        return np.random.rand(3)
    
    status_bar = tk.Label(root,text='Ready',bd=1,relief=tk.SUNKEN,anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM,fill=tk.X)
    
    frm_zscan = ZScanMethod_linear(root,get_stagecoor,status_bar)
    frm_zscan.pack()
    
    def constant_report():
        while True:
            frm_zscan.report_params()
            time.sleep(1)
    threading.Thread(target=constant_report).start()
    
    root.mainloop()