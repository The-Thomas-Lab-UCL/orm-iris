import sys
import os

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog

from dataclasses import dataclass, fields
import pickle
from glob import glob
from uuid import uuid1
import threading
from typing import Callable, Literal

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

from iris.gui.submodules.meaCoor_generator.rectangle_endToEnd import Rect_EndToEnd as Map1
from iris.gui.submodules.meaCoor_generator.rectangle_aroundCentre import Rect_AroundCentre as Map2
from iris.gui.submodules.meaCoor_generator.rectangle_video import Rect_Video as Map3
from iris.gui.submodules.meaCoor_generator.rectangle_image import Rect_Image as Map4
from iris.gui.submodules.meaCoor_generator.points_image import Points_Image as Map5
from iris.gui.submodules.meaCoor_generator.singlePoint_zScan import singlePoint_zScan as Map6
from iris.gui.submodules.meaCoor_generator.line_zScan import ZScanMethod_linear as ZScan1

from iris.gui.submodules.meaCoor_modifier.every_z import EveryZ as MapMod1
from iris.gui.submodules.meaCoor_modifier.zInterpolate import ZInterpolate as MapMod2
from iris.gui.submodules.meaCoor_modifier.topology_visualiser import TopologyVisualizer as MapMod3
from iris.gui.submodules.meaCoor_modifier.translateXYZ import TranslateXYZ as MapMod4
from iris.gui.submodules.meaCoor_modifier.gridify import Gridify as MapMod5

from iris.utils.general import *
from iris.gui import AppRamanEnum, AppPlotEnum

from iris.gui.motion_video import Frm_MotionController
from iris.gui.dataHub_MeaImg import Frm_DataHub_Image, Frm_DataHub_ImgCal
from iris.gui.dataHub_MeaRMap import Frm_DataHub_Mapping

from iris.data.measurement_image import ImgMea_Cal_Hub, MeaImg_Hub
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub
    
class Frm_Treeview_MappingCoordinates(tk.Frame):
    """
    A class to create a treeview for the mapping coordinates.
    """
    def __init__(self, master:tk.Tk|tk.Frame, mappingCoorHub:List_MeaCoor_Hub):
        """
        Initialises the treeview for the mapping coordinates.
        
        Args:
            master (tk.Tk | tk.Frame): The parent frame or window.
            mappingCoorHub (MappingCoordinatesHub): The hub for the mapping coordinates.
        """
        super().__init__(master)
        self._mappingCoorHub = mappingCoorHub
        
        # > Top level frame setup <
        frm_treeview = tk.Frame(self)
        self._frm_control = tk.Frame(self)
        
        frm_treeview.grid(row=0,column=0,sticky='nsew')
        self._frm_control.grid(row=1,column=0,sticky='ew')
        
        # > Treeview and scrollbar setup <
        self._tree_listMappingCoor = ttk.Treeview(frm_treeview)
        self._tree_listMappingCoor_vbar = ttk.Scrollbar(frm_treeview, orient=tk.VERTICAL, command=self._tree_listMappingCoor.yview)
        self._tree_listMappingCoor_hbar = ttk.Scrollbar(frm_treeview, orient=tk.HORIZONTAL, command=self._tree_listMappingCoor.xview)
        self._init_multiCoor_tree()
        
        self._tree_listMappingCoor.grid(row=0,column=0,sticky='nsew')
        self._tree_listMappingCoor_vbar.grid(row=0,column=1,sticky='wns')
        self._tree_listMappingCoor_hbar.grid(row=1,column=0,sticky='ew')
        
        # > Control widgets <
        self._btn_select_all_mappingCoor = tk.Button(self._frm_control,text='Select all coordinates',\
            command=lambda: self._tree_listMappingCoor.selection_set(self._tree_listMappingCoor.get_children()))
        self._btn_remove_selected_mappingCoor = tk.Button(self._frm_control,text='Remove selected coordinates',
                                                         command=lambda: self._remove_selected_mapping_coordinate())
        self._btn_rename_mappingCoor = tk.Button(self._frm_control,text='Rename selected coordinates',
            command=self.rename_MappingCoordinate)
        self._btn_load_mappingCoor = tk.Button(self._frm_control,text='Load a coordinate',
                                                command=lambda: self._load_MappingCoordinates())
        self._btn_save_a_mappingCoor_pickle = tk.Button(self._frm_control,text='Save selected coordinates (pickle)',
                                                command=lambda: self.save_MappingCoordinates(autosave=False,type='pickle'))
        self._btn_save_a_mappingCoor_csv = tk.Button(self._frm_control,text='Save selected coordinates (csv)',
                                                command=lambda: self.save_MappingCoordinates(autosave=False,type='csv'))
        
        row=0
        self._btn_select_all_mappingCoor.grid(row=row,column=0,sticky='ew',pady=(5,0))
        self._btn_remove_selected_mappingCoor.grid(row=row,column=1,sticky='ew',pady=(5,0));row+=1
        self._btn_rename_mappingCoor.grid(row=row,column=0,sticky='ew',pady=(5,0))
        self._btn_load_mappingCoor.grid(row=row,column=1,sticky='ew',pady=(5,0));row+=1
        self._btn_save_a_mappingCoor_pickle.grid(row=row,column=0,sticky='ew',pady=(5,0))
        self._btn_save_a_mappingCoor_csv.grid(row=row,column=1,sticky='ew',pady=(5,0))
        
        [self._frm_control.grid_columnconfigure(i, weight=1) for i in range(2)]
        [self._frm_control.grid_rowconfigure(i, weight=0) for i in range(row)]
        
        # > Run parameters setup <
        self._mappingCoorHub.add_observer(self._update_multi_mapping_tree)
        
    def _init_multiCoor_tree(self):
        """
        Initialises the tree view for the multi-coordinate mapping
        """
        self._tree_listMappingCoor['columns'] = ('Unit name','Number of coordinates')
        self._tree_listMappingCoor.heading('#0',text='Index')
        self._tree_listMappingCoor.heading('Unit name',text='Unit name')
        self._tree_listMappingCoor.heading('Number of coordinates',text='#coors')
        
        self._tree_listMappingCoor.column('#0',width=60)
        self._tree_listMappingCoor.column('Unit name',width=320)
        self._tree_listMappingCoor.column('Number of coordinates',width=60)
        
        # Bind ctrl+all to select all items in the treeview
        self._tree_listMappingCoor.bind('<Control-a>', lambda event: self._tree_listMappingCoor.selection_set(self._tree_listMappingCoor.get_children()))
        
        self._tree_listMappingCoor_vbar.config(command=self._tree_listMappingCoor.yview)
        self._tree_listMappingCoor_hbar.config(command=self._tree_listMappingCoor.xview)
        self._tree_listMappingCoor.config(yscrollcommand=self._tree_listMappingCoor_vbar.set)
        self._tree_listMappingCoor.config(xscrollcommand=self._tree_listMappingCoor_hbar.set)
        
    def get_selected_mappingCoor(self, flg_message:bool=False) -> list[MeaCoor_mm]:
        """
        Gets the selected mapping coordinates from the tree view
        
        Args:
            message (bool): If True, a message box will be shown to notify the user of the selected units. Defaults to False.

        Returns:
            list[MappingCoordinates]: The list of selected mapping coordinates
        """
        list_sel_mapCoor_unitnames = [self._tree_listMappingCoor.item(selection)['values'][0]\
            for selection in self._tree_listMappingCoor.selection()]
        list_sel_mapCoor = self._mappingCoorHub.get_list_MappingCoordinates(list_sel_mapCoor_unitnames)
        
        if flg_message:
            if len(list_sel_mapCoor) == 0:
                messagebox.showerror('Error','No mapping coordinates selected')
            list_show_names = list_sel_mapCoor_unitnames[:]
            if len(list_sel_mapCoor) > 3:
                list_show_names = list_sel_mapCoor_unitnames[:3].extend(['...'])
            messagebox.showinfo('Selected mapping coordinates',
                                f'The following mapping coordinates have been selected:\n\n{list_show_names}')
        return list_sel_mapCoor
    
    @thread_assign
    def offload_mappingCoor(self,mapping_unitName:str,list_coor:list,idx:int) -> threading.Thread:
        """
        Saves the unfinished mapping coordinates to the local disk in the temporary folder. It will
        save it with the mapping_unitName as the filename and overwrite it if it already exists.

        Args:
            mapping_unitName (str): The name of the mapping unit
            list_coor (list): The list of coordinates to be saved, in the format [(x1, y1, z1), (x2, y2, z2), ...].
            idx (int): The index of the mapping coordinates in the list indicating the measurements done.
                (Convention: Up to idx-1 are done).
        """
        # > Save the mapping coordinates to the local disk
        if not isinstance(list_coor, list) or len(list_coor) == 0:
            print('No coordinates to save')
            return
        
        idx = idx-1 if idx!=0 else 0
        list_coor_temp = list_coor.copy()[idx:]  # Create a copy to avoid modifying the original list
        
        mappingCoor = MeaCoor_mm(mapping_unitName,list_coor_temp)
        
        # Check if the file already exists and renames it if it does
        file_path = os.path.join(AppRamanEnum.TEMPORARY_FOLDER.value, mapping_unitName + '.pkl')
        flg_exist = False
        if os.path.exists(file_path):
            flg_exist = True
            old_file_path = os.path.join(AppRamanEnum.TEMPORARY_FOLDER.value, uuid1().hex + '.pkl')
            os.rename(file_path, old_file_path)
        
        try:
            mappingCoor.save_pickle(file_path)
            # Delete the old file if it exists
            if flg_exist: os.remove(old_file_path)
        except Exception as e:
            print('Error in saving the mapping coordinates:',e)
            os.rename(old_file_path, file_path)  # Rename back to the original name
            
    @thread_assign
    def delete_offload_mappingCoor(self,mapping_unitName:str):
        """
        Deletes the offloaded mapping coordinates from the local disk in the temporary folder.
        It will delete the file with the mapping_unitName as the filename.

        Args:
            mapping_unitName (str): The name of the mapping unit
        """
        # > Delete the mapping coordinates from the local disk
        file_path = os.path.join(AppRamanEnum.TEMPORARY_FOLDER.value, mapping_unitName + '.pkl')
        if os.path.exists(file_path): os.remove(file_path)
    
    @thread_assign
    def _load_MappingCoordinates(self,list_loadpath:list[str]|None=None):
        """
        Loads the mapping coordinates from a pickle file and adds them to the list of mapping coordinates.
        
        Args:
            list_loadpath (list[str]|None): The path to load the coordinates from. Defaults to None.
        
        Returns:
            MappingCoordinates: The loaded mapping coordinates.
        """
        def reset():
            nonlocal self
            self._btn_load_mappingCoor.config(state='normal')
            
        self._btn_load_mappingCoor.config(state='disabled')
        
        if list_loadpath is None:
            list_loadpath = filedialog.askopenfilenames(
                title='Select the mapping coordinates files to load',
                filetypes=[('Pickle files', '*.pkl'),('csv files', '*.csv')])
        if len(list_loadpath) == 0: return None
        
        if not isinstance(list_loadpath, (list,tuple)): messagebox.showerror('Error',f"Expected list, got {type(list_loadpath)}"); reset(); return
        if not all(isinstance(path, str) for path in list_loadpath): messagebox.showerror('Error',f"Expected list of str, got {type(list_loadpath)}"); reset(); return
        if not all(os.path.exists(path) for path in list_loadpath): messagebox.showerror('Error',f"Some files do not exist");  reset(); return
        
        for path in list_loadpath:
            try:
                mappingCoor = MeaCoor_mm(loadpath=path)
                self._mappingCoorHub.append(mappingCoor)
            except Exception as e:
                messagebox.showerror('Error',f"Failed to load mapping coordinates: {e}")
        
        reset()
        messagebox.showinfo('Info','Mapping coordinates loaded')
        return
    
    @thread_assign
    def load_last_MappingCoordinates(self):
        """
        Loads the mapping coordinates from the previous sessions saved in the temporary folder.
        """
        search_path = os.path.abspath(AppRamanEnum.TEMPORARY_FOLDER.value)+r'\*.pkl'
        # print(f'_load_last_MappingCoordinates: search path: {search_path}')
        list_paths = glob(search_path)
        if len(list_paths) == 0:
            # print('_load_last_MappingCoordinates: No previous mapping coordinates found')
            return
        
        for path in list_paths:
            try:
                mappingCoor = MeaCoor_mm(loadpath=path)
                self._mappingCoorHub.append(mappingCoor)
            except Exception as e: print(f"_load_last_MappingCoordinates: {e}")
        
        messagebox.showinfo('Unfinished measurement(s) found','Previous unfinished mapping coordinates found and has been loaded.')
        for path in list_paths: os.remove(path)
        return
    
    @thread_assign
    def save_MappingCoordinates(self,autosave:bool=False,type:Literal['pickle','csv']='pickle'):
        """
        Saves the selected mapping coordinates to a pickle file.
        
        Args:
            autosave (bool): If True, suppresses the message box and uses the temporary folder. Defaults to False.
            type (Literal['pickle','csv']): The type of file to save the coordinates to. Defaults to 'pickle'.
        """
        def reset():
            nonlocal self
        
        if autosave: list_selection = self._tree_listMappingCoor.get_children()
        else: list_selection = self._tree_listMappingCoor.selection()
        
        if len(list_selection) == 0:
            if not autosave: messagebox.showerror('Error','No mapping coordinates selected')
            return
        
        if autosave:
            dirpath = os.path.abspath(AppRamanEnum.TEMPORARY_FOLDER.value)
            if not os.path.exists(dirpath): os.makedirs(dirpath)
        else:
            dirpath = filedialog.askdirectory(title='Select the directory to save the mapping coordinates')
        if not os.path.exists(dirpath):
            if not autosave: messagebox.showerror('Error',f"Directory {dirpath} does not exist")
            reset()
            return
        
        if type=='pickle': extension = '.pkl'
        elif type=='csv': extension = '.csv'
        
        # Save all selected mapping coordinates
        for selection in list_selection:
            unitname = self._tree_listMappingCoor.item(selection)['values'][0]
            idx = self._mappingCoorHub.search_mappingCoor(unitname)
            mappingCoor:MeaCoor_mm = self._mappingCoorHub[idx]
            filename = os.path.join(dirpath,mappingCoor.mappingUnit_name+extension)
            while True:
                if os.path.exists(filename):
                    # Remove the extension and add a UUID to the filename
                    filename = os.path.splitext(filename)[0]
                    filename += '_'+str(uuid1())+'.pkl'
                else: break
            if type == 'csv':
                mappingCoor.save_csv(filename)
            elif type == 'pickle':
                mappingCoor.save_pickle(filename)
            
        reset()
        if not autosave: messagebox.showinfo('Info','Mapping coordinates saved')
        return
    
    def rename_MappingCoordinate(self):
        """
        Renames the selected mapping coordinate in the list.
        """
        list_selection = self._tree_listMappingCoor.selection()
        if len(list_selection) == 0:
            messagebox.showerror('Error','No mapping coordinates selected')
            return
        
        list_unitnames = [self._tree_listMappingCoor.item(selection)['values'][0] for selection in list_selection].copy()
        
        while len(list_unitnames) > 0:
            unitname = list_unitnames.pop(0)
            while True:
                try:
                    new_unitname = messagebox_request_input(
                        'Rename mapping coordinate',f'Enter the new name for the mapping coordinate for\n"{unitname}":',
                        default=unitname)
                    if new_unitname is None or new_unitname == '': raise ValueError("New unit name cannot be empty")
                    self._mappingCoorHub.rename_mappingCoor(unitname, new_unitname)
                    break
                except ValueError as e:
                    messagebox.showerror('Error',f"Invalid unit name: {e}")
    
    def _update_multi_mapping_tree(self):
        """
        Refreshes the tree view for the multi-coordinate mapping with the data stored in the dictionary
        """
        self._tree_listMappingCoor.delete(*self._tree_listMappingCoor.get_children())
        for i, mappingCoor in enumerate(self._mappingCoorHub):
            self._tree_listMappingCoor.insert('','end',text=str(i),values=(mappingCoor.mappingUnit_name,len(mappingCoor.mapping_coordinates)))
    
    def _remove_selected_mapping_coordinate(self):
        """
        Removes the selected mapping coordinate from the list
        """
        list_selection = self._tree_listMappingCoor.selection()
        list_unitname = [self._tree_listMappingCoor.item(selection)['values'][0] for selection in list_selection]
        
        for unitname in list_unitname:
            self._mappingCoorHub.remove_mappingCoor(unitname)
    
class sFrm_CoorModifier(tk.Frame):
    def __init__(
        self,
        master:tk.Tk|tk.Frame,
        motion_controller:Frm_MotionController,
        coor_Hub:List_MeaCoor_Hub):
        """
        Displays the GUI for the coordinate modifier methods.
        
        Args:
            master (tk.Tk | tk.Frame): The parent frame or window.
            motion_controller (Frm_MotionController): The motion controller to use.
            coor_Hub (MappingCoordinatesHub): The hub for the mapping coordinates.
        """
        super().__init__(master)
        self._motion_controller = motion_controller
        self._coorHub = coor_Hub
        
        # > Top level frame setup <
        self._frm_options = tk.Frame(self)
        self._frm_methods = tk.Frame(self)
        
        row=0; col=0
        self._frm_options.grid(row=row,column=0,sticky='nsew'); row+=1
        self._frm_methods.grid(row=row,column=0,sticky='nsew')
        
        [self.grid_rowconfigure(i, weight=1) for i in range(row+1)]
        [self.grid_columnconfigure(i, weight=1) for i in range(col+1)]
        
        # > Options setup <
        self._dict_mapModMethods_kwargs = {
            'parent': self._frm_methods,
            'motion_controller': self._motion_controller,
            'mappingCoorHub': self._coorHub,
            'motion_controller': self._motion_controller,
        }
        self._dict_mapModMethods = {
            '1. Every Z': MapMod1,
            '2. Z Interpolate': MapMod2,
            '3. Topology visualiser': MapMod3,
            '4. Translate XYZ': MapMod4,
            '5. Gridify': MapMod5
        }   # Mapping methods, to be programmed manually

        self._combo_mapModMethods = ttk.Combobox(self._frm_options,
            values=list(self._dict_mapModMethods.keys()), width=50,
            state='readonly')
        self._combo_mapModMethods.current(0)
        self._combo_mapModMethods.bind("<<ComboboxSelected>>", func=lambda event: self.show_frm_mapModMethod())
        self._combo_mapModMethods.grid(row=0, column=0, sticky='ew', padx=10, pady=10)
        
        self._frm_options.grid_rowconfigure(0, weight=0)
        self._frm_options.grid_columnconfigure(0, weight=1)
        
        # > Initial map modifier method setup <
        self._current_mapModMethod = MapMod1(**self._dict_mapModMethods_kwargs)
        self._dict_mappingmethods_grid_params = {
            'row':0,
            'column':0,
            'columnspan':2,
            'sticky':'nsew'
        }
        
        # > Initialisations <
        self.show_frm_mapModMethod()
        
    def show_frm_mapModMethod(self):
        """
        Shows the options for the selected mapping method
        
        Args:
            frm_master(Tkinter frame): The frame that will house the widget
        """
        widgets = get_all_widgets(self._frm_methods)
        
        method = self._combo_mapModMethods.get()
        self._current_map_method:Map1 = self._dict_mapModMethods[method](**self._dict_mapModMethods_kwargs)
        self._current_map_method.grid(**self._dict_mappingmethods_grid_params)
        
        row = self._dict_mappingmethods_grid_params['row']
        col = self._dict_mappingmethods_grid_params['column']
        
        self._frm_methods.grid_rowconfigure(row, weight=1)
        self._frm_methods.grid_columnconfigure(col, weight=1)
        
        for widget in widgets:
            if isinstance(widget,(tk.Frame,tk.LabelFrame)) and widget != self._current_map_method:
                widget.grid_forget()

    
class Frm_CoorGenerator(tk.Frame):
    """
    A class to generate coordinates for the mapping measurement and image tiling.
    """
    def __init__(self,
                 parent:tk.Tk|tk.Frame|tk.LabelFrame|ttk.Notebook,
                 coorHub:List_MeaCoor_Hub,
                 motion_controller:Frm_MotionController,
                 dataHub_map:Frm_DataHub_Mapping,
                 dataHub_img:Frm_DataHub_Image,
                 dataHub_imgcal:Frm_DataHub_ImgCal):
        """
        Initialises the coordinate generator frame.
        
        Args:
            master (tk.Tk | tk.Frame): The parent frame or window.
            coorHub (MappingCoordinatesHub): The hub for the mapping coordinates.
            motion_controller (Frm_MotionController): The motion controller to use.
            dataHub_map (Frm_DataHub_Mapping): The mapping data hub to use.
            dataHub_img (Frm_DataHub_Image): The image measurement data hub to use.
            dataHub_imgcal (Frm_DataHub_ImgCal): The image calibration data hub to use.
        """
    # >>> Initial setup <<<
        super().__init__(parent)
        self.master = parent
        self._coorHub = coorHub
        self._motion_controller = motion_controller
        self._dataHub_map = dataHub_map
        self._dataHub_img = dataHub_img
        self._dataHub_imgcal = dataHub_imgcal
        self._updater_statusbar = None
        
        pass    # to suppress the warning of unused variables. to be removed later, changed to self._updater_statusbar
        self.statbar = tk.Label(self, text='Status bar', bd=1, relief=tk.SUNKEN, anchor=tk.W)
        
    # >>> Top level frame setup <<<
        notebook = ttk.Notebook(self)
        self._frm_shortcuts = tk.LabelFrame(self, text='Shortcuts')
        self._frm_tv_mapcoor = Frm_Treeview_MappingCoordinates(self,self._coorHub)
        frm_zscan = tk.LabelFrame(self, text='Z-scan coordinate generator (3D scan)')
        self._frm_control = tk.LabelFrame(self, text='Control panel')
        
        row=0; col=0
        notebook.grid(row=row,column=0,sticky='nsew',columnspan=2);row+=1
        self._frm_shortcuts.grid(row=row,column=0,sticky='nsew',columnspan=2);row+=1
        self._frm_tv_mapcoor.grid(row=row,column=0,sticky='nsew',rowspan=2)
        frm_zscan.grid(row=row,column=1,sticky='nsew');col+=1;row+=1
        self._frm_control.grid(row=row,column=1,sticky='ew')
        
        [self.grid_rowconfigure(i, weight=1) for i in range(row+1)]
        [self.grid_columnconfigure(i, weight=1) for i in range(col+1)]
        
        # >> Notebook setup <<
        self._sfrm_mapping_coorGen = tk.LabelFrame(notebook, text='Mapping coordinates generator')
        self._sfrm_mapping_coorMod = sFrm_CoorModifier(
            master=notebook,
            motion_controller=self._motion_controller,
            coor_Hub=self._coorHub,
        )
        notebook.add(self._sfrm_mapping_coorGen, text='Mapping coordinates generator')
        notebook.add(self._sfrm_mapping_coorMod, text='Mapping coordinates modifier')
        
    # >>> Mapping coordinate method widgets<<<
        # > Dictionaries and parameters to set up the mapping methods <
        self._dict_mappingmethods_kwargs = {
            'container_frame':self._sfrm_mapping_coorGen,
            'motion_controller':self._motion_controller,
            'status_bar':self.statbar,
            'dataHub_img':self._dataHub_img,
            'getter_imgcal':self._dataHub_imgcal.get_selected_calibration,
        }
        self._dict_mappingmethods = {
            '1. Start/End': Map1,
            '2. Around center': Map2,
            '3. Video': Map3,
            '4. Image': Map4,
            '5. Image points': Map5,
            '6. Single point Z-scan': Map6,
            }   # Mapping methods, to be programmed manually
        self._current_map_method = Map1(**self._dict_mappingmethods_kwargs)
        
        # > Widget setup <
        # Mapping method selection
        self._combo_mappingmethods = ttk.Combobox(self._sfrm_mapping_coorGen,
            values=list(self._dict_mappingmethods.keys()),width=50,
            state='readonly')
        self._combo_mappingmethods.current(0)
        self._combo_mappingmethods.bind("<<ComboboxSelected>>",func=lambda event: 
            self.show_frm_mapping_method())
        
        # Z-scan method selection
        self._zscan_method = ZScan1(
            container_frame=frm_zscan,
            getter_stagecoor=self._motion_controller.get_coordinates_closest_mm,
            status_bar=self.statbar)
        
        self._zscan_method.grid(row=0,column=1,sticky='ew')
        
        # Pack the widgets and frames
        row=0
        self._combo_mappingmethods.grid(row=row,column=0,sticky='ew',columnspan=2);row+=1
        self._dict_mappingmethods_grid_params = {
            'row':row,
            'column':0,
            'padx':10,
            'pady':10,
            'columnspan':2
        }
        self._current_map_method.grid(**self._dict_mappingmethods_grid_params)
        
        # > Control widgets <
        self._btn_generate_mappingCoor = tk.Button(self._frm_control,text='Generate 2D mapping coordinates',
                                              command=lambda: self._generate_mapping_coordinate())
        self._btn_generate_mappingCoor_zscan = tk.Button(self._frm_control,text='Generate 3D mapping coordinates\n(z-coordinates sweep)',
                                                    command=lambda: self._generate_mapping_coordinate_zscan())
        
        row=0; col=0
        self._btn_generate_mappingCoor.grid(row=row,column=0,sticky='ew',pady=(5,0));row+=1
        self._btn_generate_mappingCoor_zscan.grid(row=row,column=0,sticky='ew',pady=(5,0))
        
        [self._frm_control.grid_columnconfigure(i, weight=1) for i in range(col+1)]
        [self._frm_control.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        
    # >>> Shortcuts setup <<<
        self._list_shorcuts:list[Callable[[MeaCoor_mm,None]]] = []    # List of shortcuts for other objects to use. It will be a list of functions that take a MappingCoordinates_mm object as an argument.
        self._col_max_shortcuts = 3   # Maximum number of shortcuts to display in a row
        self._shortcut_counter = 0
        
    def initialise(self):
        """
        Initialises the treeview and loads the mapping coordinates from the hub.
        """
        self._frm_tv_mapcoor.load_last_MappingCoordinates()
        
    def terminate(self):
        """
        Terminates the treeview and removes the observer from the hub.
        """
        self._frm_tv_mapcoor.save_MappingCoordinates(autosave=True)
        
    def add_shortcut(self, btn_label:str, command:Callable[[MeaCoor_mm],None]):
        """
        Adds a shortcut to the list of shortcuts.
        
        Args:
            btn_label (str): The label for the button to be created.
            shortcut (Callable[[MappingCoordinates_mm,None]]): The shortcut function to add. Takes a MappingCoordinates_mm object as an argument and returns None.
        """
        if not callable(command): raise TypeError(f"Expected Callable, got {type(command)}")
        self._list_shorcuts.append(command)
        
        # > Create the button for the shortcut <
        row = self._shortcut_counter // self._col_max_shortcuts
        col = self._shortcut_counter % self._col_max_shortcuts
        
        btn_shortcut = tk.Button(self._frm_shortcuts, text=btn_label, command=lambda: command(self.generate_current_mapping_coordinates()))
        btn_shortcut.grid(row=row, column=col, sticky='ew')
        
        self._frm_shortcuts.grid_rowconfigure(row, weight=1)
        self._frm_shortcuts.grid_columnconfigure(col, weight=1)
        self._shortcut_counter += 1
        return btn_shortcut
        
    def generate_current_mapping_coordinates(self) -> MeaCoor_mm:
        """
        Generates the current mapping coordinates based on the selected mapping method.
        
        Returns:
            MappingCoordinates_mm: The generated mapping coordinates.
        """
        mapping_coordinates = self._current_map_method.get_mapping_coordinates_mm()
        if mapping_coordinates is None: raise ValueError("No mapping coordinates generated")
        
        unit_name = None
        while unit_name is None:
            unit_name = messagebox_request_input('Unit name','Enter the "unit name" for the measurement:')
        
        return MeaCoor_mm(mappingUnit_name=unit_name, mapping_coordinates=mapping_coordinates)
        
    def show_frm_mapping_method(self):
        """
        Shows the options for the selected mapping method
        
        Args:
            frm_master(Tkinter frame): The frame that will house the widget
        """
        widgets = get_all_widgets(self._sfrm_mapping_coorGen)
        
        method = self._combo_mappingmethods.get()
        self._current_map_method:Map1 = self._dict_mappingmethods[method](**self._dict_mappingmethods_kwargs)
        self._current_map_method.grid(**self._dict_mappingmethods_grid_params)
        
        for widget in widgets:
            if isinstance(widget,(tk.Frame,tk.LabelFrame)) and widget != self._current_map_method:
                widget.grid_forget()
                
    def _generate_mapping_coordinate(self):
        """
        Adds the mapping coordinate to the list
        """
        mapping_coordinates = self._current_map_method.get_mapping_coordinates_mm()
        if mapping_coordinates is None: return
        
        mapping_hub = self._dataHub_map.get_MappingHub()
        list_mappingUnit_names = list(mapping_hub.get_dict_nameToID().keys())
        while True:
            mappingUnit_name = messagebox_request_input('Mapping ID','Enter the ID for the mapping measurement:')
            if mappingUnit_name == '' or not isinstance(mappingUnit_name,str)\
                or mappingUnit_name in list_mappingUnit_names or self._coorHub.search_mappingCoor(mappingUnit_name) is not None:
                retry = messagebox.askretrycancel('Error',"Invalid 'mappingUnit name'. The name cannot be empty or already exist. Please try again.")
                if not retry: return
            else: break
        
        mappingCoor = MeaCoor_mm(mappingUnit_name,mapping_coordinates)
        self._coorHub.append(mappingCoor)
        
    def _generate_mapping_coordinate_zscan(self):
        """
        Adds the z-scan mapping coordinate to the list
        """
        def check_mappingUnit_name(name:str) -> bool:
            nonlocal self, list_mappingUnit_names, list_mapping_coordinates
            res = True
            if name == ''\
                or not isinstance(name,str)\
                or name in list_mappingUnit_names\
                or self._coorHub.search_mappingCoor(name) is not None:
                res = False
            return res
            
        mapping_coordinates = self._current_map_method.get_mapping_coordinates_mm()
        list_mapping_coordinates = self._zscan_method.get_coordinates_mm(mapping_coordinates)
        if list_mapping_coordinates is None: return
        
        list_zcoor = [f'z{list_coor[0][2]*1e3:.1f}um' for list_coor in list_mapping_coordinates]
        
        mapping_hub = self._dataHub_map.get_MappingHub()
        list_mappingUnit_names = list(mapping_hub.get_dict_nameToID().keys())
        while True:
            mappingUnit_name = messagebox_request_input('Mapping ID','Enter the ID for the mapping measurement:')
            list_new_mappingUnit_names = [mappingUnit_name+f'_{zcoor}' for zcoor in list_zcoor]
            if any([not check_mappingUnit_name(name) for name in list_new_mappingUnit_names]) or mappingUnit_name == '':
                retry = messagebox.askretrycancel('Error',"Invalid 'mappingUnit name'. The name cannot be empty or already exist. Please try again.")
                if not retry: return
            else: break
        
        list_mappingCoor = [
            MeaCoor_mm(mappingUnit_name=name,mapping_coordinates=coor)
            for name, coor in zip(list_new_mappingUnit_names, list_mapping_coordinates)
        ]
        
        self._coorHub.extend(list_mappingCoor)
        
        
def generate_dummy_sfrmCoorGenerator(
    parent:tk.Tk|tk.Frame,
    motion_controller:Frm_MotionController|None=None,
    datahub_map:Frm_DataHub_Mapping|None=None,
    datahub_img:MeaImg_Hub|None=None,
    datahub_imgcal:ImgMea_Cal_Hub|None=None
    ) -> Frm_CoorGenerator:
    """
    Generates a dummy coordinate generator frame for testing purposes.
    
    Args:
        parent (tk.Tk | tk.Frame): The parent frame or window.
        motion_controller (Frm_MotionController | None): The motion controller to use. If None, a dummy motion controller will be generated.
        datahub_map (Frm_DataHub_Mapping | None): The mapping data hub to use. If None, a dummy mapping data hub will be generated.
        datahub_img (ImageMeasurement_Hub | None): The image measurement hub to use. If None, a dummy image measurement hub will be generated.
        datahub_imgcal (ImageMeasurement_Calibration_Hub | None): The image calibration hub to use. If None, a dummy image calibration hub will be generated.
        
    Returns:
        sframe_CoorGenerator: The dummy coordinate generator frame.
    """
    from iris.gui.motion_video import generate_dummy_motion_controller
    from iris.data.calibration_objective import generate_dummy_calibrationHub
    from iris.gui.dataHub_MeaImg import generate_dummy_frmImageHub, generate_dummy_frmImgCalHub
    from iris.gui.dataHub_MeaRMap import generate_dummy_frmMappingHub
    
    coorHub = List_MeaCoor_Hub()
    motion_controller = generate_dummy_motion_controller(parent) if motion_controller is None else motion_controller
    dataHub_map = generate_dummy_frmMappingHub(parent) if datahub_map is None else datahub_map
    dataHub_img = generate_dummy_frmImageHub(parent) if datahub_img is None else datahub_img
    dataHub_imgcal = generate_dummy_frmImgCalHub(parent) if datahub_imgcal is None else datahub_imgcal
    
    return Frm_CoorGenerator(
        parent=parent,
        coorHub=coorHub,
        motion_controller=motion_controller,
        dataHub_map=dataHub_map,
        dataHub_img=dataHub_img,
        dataHub_imgcal=dataHub_imgcal,
    )
    
if __name__ == '__main__':
    root = tk.Tk()
    root.title('Dummy Coordinate Generator')
    
    dummy_sfrmCoorGen = generate_dummy_sfrmCoorGenerator(root)
    dummy_sfrmCoorGen.pack(fill=tk.BOTH, expand=True)
    
    root.mainloop()