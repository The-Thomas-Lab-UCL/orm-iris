"""
A hub to manage all the ImageMeasurement_Units stored in an ImageMeasurement_Hub
captured in the session. This is modeled after the sframe_dataHubMapping module.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk

import os
from typing import Callable

import queue
import threading
if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))


from iris.utils.general import *
from iris import LibraryConfigEnum
from iris.data.measurement_image import MeaImg_Unit, MeaImg_Hub, MeaImg_Handler
from iris.data.calibration_objective import ImgMea_Cal, ImgMea_Cal_Hub

class Frm_DataHub_ImgCal(tk.LabelFrame):
    """
    GUI to show all the ImageMeasurement_Calibration objs stored in the ImageMeasurement_Calibration_Hub.
    It has a combobox to show the available calibrations in a selected folder, and a button to load the
    calibration folder.
    
    Note: the term calibration and objective are used interchangeably in this object docstrings/attributes/methods.
    """
    def __init__(self, main, getter_ImageCalHub:Callable[[], ImgMea_Cal_Hub]|None=None,
                 *args, **kwargs) -> None:
        """
        Initialize the frame. The getter is used to get the ImageMeasurement_Calibration_Hub to update the data in the
        object when required. Especially useful when creating an instance outside the controller (i.e., to connect with other
        modules). If none is provided, the default object is created and these updates will be unavailable.
        
        Args:
            main (tk.Tk|tk.Frame): Main window or frame
            getter_ImageCalHub (Callable[[], ImageMeasurement_Calibration_Hub]): Function to get the ImageMeasurement_Calibration_Hub
        """
        super().__init__(main, text='Objective control', *args, **kwargs)
        
        self._getter_CalHub = getter_ImageCalHub
        self._CalHub = self._getter_CalHub() if self._getter_CalHub is not None else ImgMea_Cal_Hub()
        
        # List of the available calibrations
        self._list_cals = []
        self._empty_cal = ImgMea_Cal()
        self._lastdirpath = None
        
        # Setup the combobox and button
        self._combo_cal = ttk.Combobox(self, state='disabled')
        self._btn_loaddir = tk.Button(self, text='Load objective folder', command=self._load_calibration_folder)
        self._btn_refreshdir = tk.Button(self, text='Refresh objetive folder', command=self._refresh_calibration_folder)
        
        self._combo_cal.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self._btn_loaddir.grid(row=1, column=0, sticky='nsew')
        self._btn_refreshdir.grid(row=1, column=1, sticky='nsew')
        
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        
    def get_ImageMeasurement_Calibration_Hub(self) -> ImgMea_Cal_Hub:
        """
        Get the ImageMeasurement_Calibration_Hub object.
        
        Returns:
            ImageMeasurement_Calibration_Hub: ImageMeasurement_Calibration_Hub object
        """
        return self._CalHub
        
    def get_selected_calibration(self) -> ImgMea_Cal:
        """
        Get the selected calibration from the combobox.

        Returns:
            ImageMeasurement_Calibration: Selected calibration object
        """
        cal_id = self._combo_cal.get()
        if cal_id: return self._CalHub.get_calibration(cal_id)
        else: return self._empty_cal
        
    @thread_assign
    def update_combobox(self) -> None:
        """
        Updates the combo box list of values based on the calibrations in the ImageMeasurement_Calibration_Hub.
        """
        list_cals = self._CalHub.get_calibration_ids()
        
        if list_cals == self._list_cals: return # No need to update
        
        self._list_cals = list_cals.copy()
        self._combo_cal.config(values=self._list_cals, state='readonly')
        if self._combo_cal.get() not in self._list_cals:
            self._combo_cal.current(0)
        
    @thread_assign
    def _refresh_calibration_folder(self, supp_msg:bool=False) -> None:
        """
        Refreshes the combobox list by re-scanning the calibration folder.
        
        Args:
            supp_msg (bool): Flag to suppress the success message. Defaults to False.
        """
        if not self._lastdirpath: messagebox.showerror('Error', 'No previously selected folder.'); return
        try:
            self._btn_refreshdir.config(state='disabled', text='Refreshing...')
            self._CalHub.load_calibrations(self._lastdirpath)
            thread = self.update_combobox()
            thread.join()
            if not supp_msg: messagebox.showinfo('Success', 'Calibration folder refreshed successfully.')
            print(f'Refreshed calibration folder: {self._lastdirpath}')
        except Exception as e:
            if not supp_msg: messagebox.showerror('Error', str(e))
            print(f'Error refreshing calibration folder: {e}')
        finally:
            self._btn_refreshdir.config(state='normal', text='Refresh objetive folder')
        
    @thread_assign
    def _load_calibration_folder(self,dirpath:str|None=None,supp_msg:bool=False) -> None:
        """
        Prompts the user to select a folder containing the calibration files.
        
        Args:
            dirpath (str|None): Path to the folder, if none is provided, it will
                prompt the user for one. Defaults to None.
            supp_msg (bool): Flag to suppress the success message. Defaults to False.
        """
        if dirpath is None:
            initdir = LibraryConfigEnum.OBJECTIVE_CALIBRATION_DIR.value
            initdir = initdir if os.path.isdir(initdir) else None
            dirpath = filedialog.askdirectory(title='Select the objective folder',initialdir=initdir)
        
        if not os.path.isdir(dirpath) and not supp_msg: messagebox.showerror('Error', 'Invalid folder selected.'); return
        
        self._lastdirpath = dirpath
        
        try:
            self._btn_loaddir.config(state='disabled', text='Loading...')
            self._CalHub.load_calibrations(dirpath)
            thread = self.update_combobox()
            thread.join()
            if not supp_msg: messagebox.showinfo('Success', 'Calibration folder loaded successfully.')
            print(f'Loaded calibration folder: {dirpath}')
        except Exception as e:
            if not supp_msg: messagebox.showerror('Error', str(e))
            print(f'Error loading calibration folder: {e}')
        finally:
            self._btn_loaddir.config(state='normal', text='Load Calibration Folder')
        
        
class Frm_DataHub_Image(tk.Frame):
    """
    GUI to show all the data being stored in the ImageMeasurement_Hub and ImageMeasurement_Calibration_Hub.
    Modeled after the Frm_DataHub_Mapping class.
    """
    def __init__(self, main, getter_ImageHub: Callable[[], MeaImg_Hub]|None=None,
                 width_rel:float=1, height_rel:float=1, **kwargs):
        """
        Initialize the Frame. The getters are used to get the ImageMeasurement_Hub and ImageMeasurement_Calibration_Hub
        to update the data in the object when required. If none are provided, the default objects are created and these
        updates will be unavailable.
        
        Args:
            main (tk.Tk|tk.Frame): Main window or frame
            getter_ImageHub (Callable[[], ImageMeasurement_Hub]): Function to get the ImageMeasurement_Hub
            width_rel (float): Relative width of the frame. Defaults to 1
            height_rel (float): Relative height of the frame. Defaults to 1
        """
        super().__init__(main, **kwargs)
        
        if width_rel < 0 or height_rel < 0: width_rel, height_rel = 1, 1
        self._getter_ImageHub = getter_ImageHub
        
        self.width_rel = width_rel
        self.height_rel = height_rel
        
    # >>> Top layout setup <<<
        frm_tree = tk.Frame(self)
        frm_control = tk.Frame(self)
        
        frm_tree.grid(row=0, column=0, sticky='nsew')
        frm_control.grid(row=1, column=0, sticky='nsew')
        
    # >>> Hub setups <<<
        self.ImageHub = self._getter_ImageHub() \
            if self._getter_ImageHub is not None else MeaImg_Hub()
            
    # >>> Save parameters setup <<<
        self._sessionid = get_timestamp_us_str()    # Session ID
        self._flg_issaved = True    # Flag to indicate if the data is saved
        
    # >>> Treeview setup <<<
        self._tree_hub = ttk.Treeview(frm_tree, columns=('unit_id', 'unit_name', 'num_measurements', 'metadata'),
                                      show='headings', height=int(10*self.height_rel))
        self._init_tree()
        self._tree_hub.grid(row=0, column=0, sticky='nsew')
        
    # >>> Other control widgets <<<
        # Widgets to manipulate the entries
        self._btn_save = tk.Button(frm_control, text='Save Image Hub', command=self.save_ImageMeasurementHub)
        self._btn_load = tk.Button(frm_control, text='Load Image Hub', command=self.load_ImageMeasurementHub)
        self._btn_remove = tk.Button(frm_control, text='Remove Selected', command=self.remove_selected_ImageMeasurementUnit)
        
        self._btn_save.grid(row=0, column=0, sticky='ew')
        self._btn_load.grid(row=0, column=1, sticky='ew')
        self._btn_remove.grid(row=0, column=2, sticky='ew')
        
        frm_control.grid_rowconfigure(0, weight=0)
        frm_control.grid_columnconfigure(0, weight=1)
        frm_control.grid_columnconfigure(1, weight=1)
        frm_control.grid_columnconfigure(2, weight=1)
        
    def _init_tree(self):
        """
        Initialises the treeview widget headings and size.
        """
        tree = self._tree_hub
        tree.heading('unit_id', text='Unit ID', anchor='w')
        tree.heading('unit_name', text='Unit Name', anchor='w')
        tree.heading('num_measurements', text='# Pictures', anchor='w')
        tree.heading('metadata', text='Metadata', anchor='w')
        
        tree.column('unit_id', width=int(50*self.width_rel))
        tree.column('unit_name', width=int(100*self.width_rel))
        tree.column('num_measurements', width=int(100*self.width_rel))
        tree.column('metadata', width=int(600*self.width_rel))
        
    @thread_assign
    def load_ImageMeasurementHub(self):
        """
        Load the ImageMeasurement_Hub data from the database file.
        """
        try:
            self._btn_load.config(state='disabled',text='Loading...')
            file_path = filedialog.askopenfilename(title='Open Image Measurement Hub',
                                                filetypes=[('Database files', '*.db')])
            
            if not file_path: messagebox.showerror('Error', 'No file selected.'); return
            
            self.ImageHub.reset_ImageMeasurementUnits()
            handler = MeaImg_Handler()
            handler.load_ImageMeasurementHub_database(file_path,self.ImageHub)
            
            self._flg_issaved = True
            
            self.update_tree()
            messagebox.showinfo('Success', 'Image Measurement Hub loaded successfully.')
        except Exception as e:
            messagebox.showerror('Error', str(e))
        finally:
            self._btn_load.config(state='normal',text='Load Image Hub')
        
    @thread_assign
    def save_ImageMeasurementHub(self) -> threading.Thread:
        """
        Save the ImageMeasurement_Hub data to a database file.
        """
        try:
            self._btn_save.config(state='disabled',text='Saving...')
            file_path = filedialog.asksaveasfilename(title='Save Image Measurement Hub',
                                                    filetypes=[('Database files', '*.db')],
                                                    defaultextension='.db')
            
            if not file_path: raise Exception('No file selected.')
            
            initdir = os.path.dirname(file_path)
            savename = os.path.basename(file_path)
            
            handler = MeaImg_Handler()
            thread = handler.save_ImageMeasurementHub_database(hub=self.ImageHub,initdir=initdir,savename=savename)
            
            ts = time.time()
            while thread.is_alive():
                time.sleep(1)
                ts2 = time.time()
                elapsed = ts2-ts
                self._btn_save.config(text=f'Saving... ({elapsed:.1f}s)')
                
            thread.join()
            self._flg_issaved = True
            messagebox.showinfo('Success', 'Image Measurement Hub saved successfully.')
        except Exception as e:
            messagebox.showerror('Error', str(e))
        finally:
            self._btn_save.config(state='normal',text='Save Image Hub')
        
    def append_ImageMeasurementUnit(self, unit:MeaImg_Unit, flg_nameprompt:bool=True):
        """
        Appends the given ImageMeasurement_Unit to the ImageMeasurement_Hub and
        update the treeview

        Args:
            unit (ImageMeasurement_Unit): ImageMeasurement_Unit object
            flg_nameprompt (bool): Flag to prompt the user for the name of the unit. Defaults to True
        """
        try:
            self._btn_save.config(state='disabled',text='Saving...')
            if flg_nameprompt:
                imgname = messagebox_request_input('Image Name', 'Enter the name of the image:')
                unit.set_name(imgname)
            self.ImageHub.append_ImageMeasurementUnit(unit)
            self._flg_issaved = False
            self.update_tree()
        except Exception as e:
            messagebox.showerror('Error', str(e))
        finally:
            self._btn_save.config(state='normal',text='Save Image Hub')
        
    def remove_selected_ImageMeasurementUnit(self):
        """
        Remove the selected ImageMeasurementUnit from the ImageMeasurement_Hub.
        """
        tree = self._tree_hub
        selected = tree.selection()
        if len(selected) == 0:
            messagebox.showerror('Error', 'No entry selected.')
            return
        
        for item in selected:
            unit_id = tree.item(item, 'values')[0]
            self.ImageHub.remove_ImageMeasurementUnit(unit_id)
        
        self._flg_issaved = False
        
        self.update_tree()
        
    def get_ImageMeasurement_Calibration_Hub(self) -> ImgMea_Cal_Hub:
        """
        Get the ImageMeasurement_Calibration_Hub object.
        
        Returns:
            ImageMeasurement_Calibration_Hub: ImageMeasurement_Calibration_Hub object
        """
        return self.ImageCalibHub
        
    def get_ImageMeasurement_Hub(self) -> MeaImg_Hub:
        """
        Get the ImageMeasurement_Hub object.
        
        Returns:
            ImageMeasurement_Hub: ImageMeasurement_Hub object
        """
        return self.ImageHub
        
    def update_ImageMeasurementHub(self):
        """
        Update the ImageMeasurement_Hub and ImageMeasurement_Calibration_Hub with the data from the getters.
        """
        if self._getter_ImageHub is not None:
            self.ImageHub = self._getter_ImageHub()
            
        self._flg_issaved = False
        self.update_tree()
        
    def update_tree(self):
        """
        Update the treeview widget with the data from the ImageMeasurement_Hub.
        """
        tree = self._tree_hub
        tree.delete(*tree.get_children())
        
        list_id, list_name, list_num_measurements, list_metadata = self.ImageHub.get_summary_units()
        
        for id,name,num,meta in zip(list_id, list_name, list_num_measurements, list_metadata):
            tree.insert('', 'end', text='', values=(str(id), str(name), str(num), str(meta)))

    def terminate(self):
        """
        Termination protocol for the Image data hub.
        """
        while not self._flg_issaved:
            flg_save = messagebox.askyesno('Save Image Hub', 'There are unsaved changes to the Image Data Hub. Do you want to save before closing?')
            if flg_save:
                thread = self.save_ImageMeasurementHub()
                thread.join()
            else: break
            
    def test_generate_dummy(self):
        """
        Generate dummy data for testing purposes.
        """
        self.ImageHub.test_generate_dummy()
        self.update_tree()
            

def generate_dummy_frmImageHub(parent:tk.Tk|tk.Frame) -> Frm_DataHub_Image:
    """
    Generate a dummy Frm_DataHub_Image for testing purposes.
    
    Args:
        parent (tk.Tk|tk.Frame): Parent window or frame
    
    Returns:
        Frm_DataHub_Image: Dummy Frm_DataHub_Image object
    """
    frm_imgHub = Frm_DataHub_Image(parent)
    frm_imgHub.test_generate_dummy()
    return frm_imgHub

def generate_dummy_frmImgCalHub(parent:tk.Tk|tk.Frame) -> Frm_DataHub_ImgCal:
    """
    Generate a dummy Frm_DataHub_ImgCal for testing purposes.
    Dummy calibrations are automatically generated.
    
    Args:
        parent (tk.Tk|tk.Frame): Parent window or frame
    
    Returns:
        Frm_DataHub_ImgCal: Dummy Frm_DataHub_ImgCal object
    """
    frm_imgCal = Frm_DataHub_ImgCal(parent)
    frm_imgCal.get_ImageMeasurement_Calibration_Hub().generate_dummy_calibrations()
    return frm_imgCal

def test_DataHubImage():
    """
    Test the Frm_DataHub_Image class.
    """
    root = tk.Tk()
    root.title('Data Hub Image Test')
    
    frm = Frm_DataHub_Image(root, width_rel=1, height_rel=1)
    frm.pack(expand=True, fill='both')
    
    root.mainloop()
    
if __name__ == '__main__':
    test_DataHubImage()