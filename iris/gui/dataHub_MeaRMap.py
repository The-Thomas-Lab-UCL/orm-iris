"""
A class that stores the all the measurement data in the current experiment.
- Shows the stored data in a table format
- Allows the user to add new data to the table
- Allows the user to delete data from the table
"""
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk

import os
from typing import Callable

import queue
import threading

from rapidfuzz import process, fuzz

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))


from iris.utils.general import *
from iris.data.measurement_Raman import MeaRaman
from iris.data.measurement_RamanMap import MeaRMap_Hub, MeaRMap_Unit, MeaRMap_Handler

from iris.data import SaveParamsEnum

SEARCHBAR_INIT = 'Search by typing here...'

class Frm_DataHub_Mapping(tk.Frame):
    def __init__(self, master, mappingHub:MeaRMap_Hub|None=None,width_rel:float=1, height_rel:float=1,autosave:bool=False):
        """
        Initialises the data hub frame. This frame stores all the data from the measurement session.
        
        Args:
            master (tk.Tk): The master window
            mappingHub (MeaRMap_Hub|None): The MappingMeasurement_Hub instance. Defaults to None.
            width_rel (float, optional): The relative width of the frame. Defaults to 1.
            height_rel (float, optional): The relative height of the frame. Defaults to 1.
            autosave (bool, optional): If True, will enable autosaving of the MappingMeasurement_Hub. Defaults to False.

        Note: mappingHub will be used during the refresh callback to get the latest MappingMeasurement_Hub.
        """
        if width_rel < 0 or height_rel < 0: width_rel, height_rel = 1, 1
        self._width_rel = width_rel
        self._height_rel = height_rel
        
        tk.Frame.__init__(self, master)
        frm_tree = tk.Frame(self)
        frm_control = tk.Frame(self)
        frm_autosave = tk.Frame(self)
        
        frm_tree.grid(row=0, column=0, sticky="nsew")
        frm_control.grid(row=1, column=0, sticky="nsew")
        frm_autosave.grid(row=2, column=0, sticky="nsew")
        
        # Storage to store the data
        if isinstance(mappingHub, MeaRMap_Hub): self._MappingHub = mappingHub
        else: self._MappingHub = MeaRMap_Hub()
        
        # Save parameters
        self._sessionid = get_timestamp_us_str()
        self._flg_issaved = True   # Indicate if the stored data has been saved
        self._list_pickled = []    # List of pickled files
        self._temp_savedir = SaveParamsEnum.DEFAULT_SAVE_PATH.value + r'\temp'
        if not os.path.exists(self._temp_savedir): os.makedirs(self._temp_savedir)
        
        # Widgets to show the stored data
        self._str_search = tk.StringVar(value=SEARCHBAR_INIT)
        entry_searchbar = tk.Entry(frm_tree, textvariable=self._str_search)
        self._tree_hub = ttk.Treeview(frm_tree, columns=("Unit ID", "Unit name", "Metadata", "# Measurements"), show="headings",
                                      height=int(10*self._height_rel))
        self._tree_scroll_v = ttk.Scrollbar(frm_tree, orient=tk.VERTICAL, command=self._tree_hub.yview)
        self._tree_scroll_h = ttk.Scrollbar(frm_tree, orient=tk.HORIZONTAL, command=self._tree_hub.xview)
        self._init_tree()
        entry_searchbar.grid(row=0, column=0, sticky="ew")
        self._tree_hub.grid(row=1, column=0, sticky="nsew")
        self._tree_scroll_v.grid(row=1, column=1, sticky="ns")
        self._tree_scroll_h.grid(row=2, column=0, sticky="ew")
        
        # Bind keypresses to search
        entry_searchbar.bind("<KeyRelease>", lambda event: self.update_tree(keep_selection=False))
        
        # Bind ctrl+all to select all items in the treeview
        self._tree_hub.bind('<Control-a>', lambda event: self._tree_hub.selection_set(self._tree_hub.get_children()))
        
        # Widgets to manipulate entries
        self._bool_save_raw_MappingUnit_ext = tk.BooleanVar(value=True)
        btn_refresh = tk.Button(frm_control, text="Refresh", command=self.update_tree)
        btn_rename_entry = tk.Button(frm_control, text="Rename Entry", command=self.rename_unit)
        btn_delete_entry = tk.Button(frm_control, text="Remove Entry", command=self.delete_unit)
        self._btn_save_MappingUnit_ext = tk.Button(frm_control, text="Save selected [.csv, etc]", command=self.save_selected_mappingUnit_ext)
        self._chk_save_raw_MappingUnit_txt = tk.Checkbutton(frm_control, text="Save raw [.csv, etc]", variable=self._bool_save_raw_MappingUnit_ext)
        self._btn_save_MappingHub = tk.Button(frm_control, text="Save Mapping Hub [.db]", command=self.save_dataHub)
        self._btn_load_MappingHub = tk.Button(frm_control, text="Load Mapping Hub [.db]", command=self.load_dataHub)
        
        btn_refresh.grid(row=0, column=0, sticky="nsew")
        btn_rename_entry.grid(row=1, column=0, sticky="nsew")
        btn_delete_entry.grid(row=1, column=1, sticky="nsew")
        self._btn_save_MappingUnit_ext.grid(row=0, column=2, sticky="nsew")
        self._chk_save_raw_MappingUnit_txt.grid(row=1, column=2, sticky="nsew")
        self._btn_save_MappingHub.grid(row=0, column=3, sticky="nsew")
        self._btn_load_MappingHub.grid(row=1, column=3, sticky="nsew")
        
        # Grid configuration
        frm_tree.grid_columnconfigure(0, weight=1)
        frm_tree.grid_rowconfigure(0, weight=1)

        [frm_control.grid_columnconfigure(i, weight=1) for i in range(4)]
        frm_control.grid_rowconfigure(0, weight=1)
        
    # > Autosave info <
        # Autosave parameters
        self._autosave_path = os.path.abspath(SaveParamsEnum.AUTOSAVE_PATH.value)
        if not os.path.exists(self._autosave_path): os.makedirs(self._autosave_path)
        
        # Autosave widgets
        self._flg_autosave = SaveParamsEnum.AUTOSAVE_ENABLED.value and autosave
        self._autosave_interval = SaveParamsEnum.AUTOSAVE_INTERVAL_HOURS.value
        autosave_interval_str = str(self._autosave_interval) if self._flg_autosave else "Disabled"
        lbl_autosave_interval = tk.Label(frm_autosave, text=f"Autosave interval: {autosave_interval_str} hours")
        lbl_autosave_path = tk.Label(frm_autosave, text=f"Autosave path: {self._autosave_path}")
        
        lbl_autosave_interval.grid(row=0, column=0, sticky="w")
        lbl_autosave_path.grid(row=1, column=0, sticky="w")
        
        # Autosave thread setup
        self._flg_isrunning = threading.Event()
        self._flg_isrunning.set()
        self._flg_issaving = threading.Event()
        self._thread_autosave = self._autosave_dataHub(suppress_errors=not autosave)
        
        # Interaction/callback setup
        self._list_observer_load = []
        self._list_observer_selection = []
        
        self._tree_hub.bind("<<TreeviewSelect>>", lambda event: self._notify_observer_selection())
        
    @thread_assign
    def _autosave_dataHub(self, suppress_errors:bool=False) -> threading.Thread:
        """
        Autosaves the MappingMeasurement_Hub to a pickle file every AUTOSAVE_INTERVAL_HOURS hours.
        
        Args:
            suppress_errors (bool, optional): If True, will suppress errors in the autosave thread. Defaults to False.
        """
        if not self._flg_autosave and not suppress_errors:
            print("Autosave is disabled. Exiting autosave thread.")
            return
        
        while self._flg_isrunning.is_set():
            try:
                self._flg_issaving.set()  # Set the saving flag
                if not self._MappingHub.check_measurement_exist(): raise AssertionError("No measurements in the Mapping Hub to autosave")
                MeaRMap_Handler().save_MappingHub_database(
                    mappingHub=self._MappingHub,
                    savedirpath=self._autosave_path,
                    savename=self._sessionid + "_autosave",
                )
                print(f"Autosaved Mapping Hub to {self._autosave_path}/{self._sessionid}_autosave.db")
            except AssertionError: pass
            except Exception as e: print (f"Error in autosave thread: {e}")
            finally:
                self._flg_issaving.clear()
                time.sleep(SaveParamsEnum.AUTOSAVE_INTERVAL_HOURS.value * 3600)  # Wait for the autosave interval
            
        
    def _refresh_dataHub(self):
        """
        Gets the latest MappingMeasurement_Hub from the getter function and updates the tree
        """
        self.update_tree()
        
    def _init_tree(self):
        self._tree_hub.heading("Unit ID", text="Unit ID", anchor=tk.W)
        self._tree_hub.heading("Unit name", text="Unit name", anchor=tk.W)
        self._tree_hub.heading("Metadata", text="Metadata", anchor=tk.W)
        self._tree_hub.heading("# Measurements", text="# Measurements", anchor=tk.W)
        
        self._tree_hub.column("Unit ID", width=int(50*self._width_rel), stretch=tk.NO)
        self._tree_hub.column("Unit name", width=int(300*self._width_rel), stretch=tk.NO)
        self._tree_hub.column("Metadata", width=int(300*self._width_rel), stretch=tk.NO)
        self._tree_hub.column("# Measurements", width=int(100*self._width_rel), stretch=tk.NO)
        
        self._tree_hub.configure(yscrollcommand=self._tree_scroll_v.set)
        self._tree_hub.configure(xscrollcommand=self._tree_scroll_h.set)
        self._tree_scroll_v.config(command=self._tree_hub.yview)
        self._tree_scroll_h.config(command=self._tree_hub.xview)
        
    def add_observer_load(self, callback:Callable):
        """
        Sets a callback function to run after loading the MappingMeasurement_Hub
        """
        assert callable(callback), "callback must be a callable function"
        self._list_observer_load.append(callback)
        
    def remove_observer_selection(self, callback:Callable):
        """
        Removes a callback function from the list of selection callbacks
        """
        if callback in self._list_observer_selection:
            try: self._list_observer_selection.remove(callback)
            except Exception as e: print('Error in removing selection callback:', e)
        
    def _notify_observer_selection(self):
        """
        Run all the callbacks in the list when a MappingMeasurement_Unit is selected
        """
        for callback in self._list_observer_selection:
            try: callback()
            except Exception as e: print('Error in selection callback:', e)
        
    def add_observer_selection(self, callback:Callable):
        """
        Sets a callback function to run when the user selects a MappingMeasurement_Unit in the treeview
        """
        assert callable(callback), "callback must be a callable function"
        self._list_observer_selection.append(callback)
        
    def get_tree(self) -> ttk.Treeview:
        return self._tree_hub
        
    def get_selected_MappingUnit(self) -> list[MeaRMap_Unit]:
        """
        Returns the selected MappingMeasurement_Unit in the treeview
        
        Returns:
            list[MappingMeasurement_Unit]: The selected MappingMeasurement_Unit
        """
        selections = self._tree_hub.selection()
        
        list_units = []
        for item in selections:
            unit_id = self._tree_hub.item(item, "values")[0]
            try: unit = self._MappingHub.get_MappingUnit(unit_id)
            except ValueError: continue
            list_units.append(unit)

        return list_units
        
    def get_MappingHub(self) -> MeaRMap_Hub:
        return self._MappingHub

    def _filter_by_search(self) -> list[str]:
        """
        Filters the treeview items based on the search query.
        
        Returns:
            list[str]: The filtered list of unit IDs
        """
        search_query = self._str_search.get().lower()
        dict_unit_IdNames = {unit.get_unit_id(): unit.get_unit_name().lower()\
            for unit in self._MappingHub.get_list_MappingUnit()}
        list_unit_ids = self._MappingHub.get_list_MappingUnit_ids()

        # Return all if the search query is empty
        if not search_query or search_query == "" or search_query == SEARCHBAR_INIT.lower():
            return list_unit_ids
        
        # Perform fuzzy matching on the unit names
        list_matches = process.extract(search_query, dict_unit_IdNames.values(), scorer=fuzz.token_ratio, limit=None)
        list_matches = sorted(list_matches, key=lambda x: x[1], reverse=True)
        
        list_matches_id = [
            unit_id
            for name, _, _ in list_matches
            for unit_id, unit_name in dict_unit_IdNames.items()
            if unit_name == name
        ]
        
        return list_matches_id

    def update_tree(self, keep_selection:bool=True):
        # Store the current selections
        list_unitID = [unit.get_unit_id() for unit in self.get_selected_MappingUnit()]
        list_matched_ids = self._filter_by_search()
        
        self._tree_hub.delete(*self._tree_hub.get_children())
        list_unit_ids, list_unit_names, list_metadata, list_num_measurements = self._MappingHub.get_summary_units()
        
        for unit_id in list_matched_ids:
            idx = list_unit_ids.index(unit_id)
            self._tree_hub.insert("", "end", values=(
                unit_id,
                list_unit_names[idx],
                list_metadata[idx],
                list_num_measurements[idx]
            ))
        # for id, name, metadata, num_measurements in zip(list_unit_ids, list_unit_names, list_metadata, list_num_measurements):
        #     self._tree_hub.insert("", "end", values=(id, name, metadata, num_measurements))
            
        # Set the selection back to the previous selection
        if keep_selection: self.set_selection_unitID(list_unitID)
        
    def set_selection_unitID(self, list_unitID:list[str]|str, clear_previous:bool=True):
        """
        Sets the selection in the treeview to the given unit IDs.

        Args:
            list_unitID (list[str]|str): The list of unit IDs to select or a single unit ID.
            clear_previous (bool): Whether to clear the previous selection.
        """
        if not isinstance(list_unitID, list): list_unitID = [list_unitID]
        if clear_previous:
            [self._tree_hub.selection_remove(item) for item in self._tree_hub.get_children()]
            
        for item in self._tree_hub.get_children():
            if self._tree_hub.item(item, "values")[0] in list_unitID:
                self._tree_hub.selection_add(item)
                
    def append_MappingUnit(self, unit: MeaRMap_Unit, persist:bool=True):
        """
        Append a MappingMeasurement_Unit to the MappingMeasurement_Hub
        
        Args:
            unit (MappingMeasurement_Unit): The unit to append
            persist (bool, optional): If True, will ask for a new unit ID. Defaults to True.
        """
        while True:
            try:
                self._MappingHub.append_mapping_unit(unit)
                self._flg_issaved = False
                self.update_tree()
                break
            except FileExistsError as e:
                if not persist:
                    messagebox.showerror("Unit ID already exists", str(e))
                    break
                
                new_unitName = messagebox_request_input(\
                    "'Unit name' already exists", "'Unit name' already exists!\nEnter a new 'unit name':",
                    default=unit.get_unit_name())
                unit.set_unitName_and_unitID(new_unitName)
    
    def extend_MappingUnit(self, list_unit:list[MeaRMap_Unit], persist:bool=True):
        """
        Extend a MappingMeasurement_Unit in the MappingMeasurement_Hub
        
        Args:
            list_unit (list[MappingMeasurement_Unit]): The unit to extend
            persist (bool, optional): If True, will ask for a new unit ID if the unit ID does not exist. Defaults to True.
        """
        for unit in list_unit: self.append_MappingUnit(unit, persist=persist)
    
    @thread_assign
    def rename_unit(self):
        """
        Rename the selected MappingMeasurement_Unit in the MappingMeasurement_Hub
        """
        try:
            selections = self._tree_hub.selection()
            
            if len(selections) == 0:
                messagebox.showerror("Error", "No unit selected")
                return
            elif len(selections) > 1:
                messagebox.showerror("Error", "Multiple units selected. Please select only one unit to rename")
                return
            
            unit_id = self._tree_hub.item(selections[0], "values")[0]
            unit = self._MappingHub.get_MappingUnit(unit_id)
            new_name = messagebox_request_input("Rename Mapping Unit", "Enter the new name for the selected Mapping Unit:",
                                                default=unit.get_unit_name())
            
            self._MappingHub.rename_mapping_unit(unit_id,new_name)
            self._flg_issaved = False
            self.update_tree()
            
        except Exception as e:
            messagebox.showerror("Error", "Error in renaming the Mapping Unit\n" + str(e))
    
    @thread_assign
    def delete_unit(self):
        """
        Delete the selected MappingMeasurement_Unit from the MappingMeasurement_Hub
        """
        # Get the currently selected units
        selections = self._tree_hub.selection()
        
        if len(selections) == 0:
            messagebox.showerror("Error", "No unit selected")
            return
        
        flg_remove = messagebox.askyesno("Mapping Unit deletion", "Are you sure you want to delete the selected units?\n!!! This action cannot be undone !!!", default=messagebox.NO)
        if not flg_remove: return
        
        for item in selections:
            unit_id = self._tree_hub.item(item, "values")[0]
            self._MappingHub.remove_mapping_unit_id(unit_id)
        
        if len(selections) > 0: self._flg_issaved = False
        self.update_tree()
        
    @thread_assign
    def save_temp_dataHub_pickle(self) -> threading.Thread:
        """
        Save the MappingMeasurement_Hub stored internally to a temporary pickle file
        
        Returns:
            threading.Thread: The thread that saves the data.
        
        Note:
            This function pops up an internal error so it will return a thread regardless.
            The error will be shown in the console.
        """
        try:
            savedirpath = os.path.abspath(self._temp_savedir)
            savename = self._sessionid + "_temp.pkl"
            handler = MeaRMap_Handler()
            q_savepath = queue.Queue()
            
            handler.save_MappingHub_pickle(self._MappingHub, savedirpath, savename, q_savepath)
            savepath = q_savepath.get()
            if savepath is None: raise Exception("Error in saving the Mapping Hub")
            else: self._list_pickled.append(savepath)
        except Exception as e:
            print('Error in save_temp_dataHub_pickle:\n', e)
        
    @thread_assign
    def load_dataHub(self) -> threading.Thread:
        try:
            self._btn_load_MappingHub.config(state=tk.DISABLED, text="Loading...")
            MeaRMap_Handler().load_choose(mappingHub=self._MappingHub)
            messagebox.showinfo("Load Mapping Hub", "Mapping Hub loaded successfully")
        except Exception as e:
            print('Error in load_dataHub:\n', e)
            messagebox.showerror("Error", "Error in loading Mapping Hub\n" + str(e))
        finally:
            self.update_tree()
            [callback() for callback in self._list_observer_load]
            self._btn_load_MappingHub.config(state=tk.NORMAL, text="Load Mapping Hub")
        
    @thread_assign
    def save_dataHub(self,callback=None) -> threading.Thread:
        """
        Save the MappingMeasurement_Hub stored internally to the local disk.
        
        Args:
            callback (function, optional): The callback function to run after saving the data. Defaults to None."""
        try:
            self._btn_save_MappingHub.config(state=tk.DISABLED, text="Saving...")
            thread = MeaRMap_Handler().save_MappingMeasurementHub_choose(self._MappingHub)
            thread.join()
            messagebox.showinfo("Save Mapping Hub", "Mapping Hub saved successfully")
            self._flg_issaved = True
        except Exception as e:
            messagebox.showerror("Error", "Error in saving Mapping Hub\n" + str(e))
            print('Error in save_dataHub:\n', e)
        finally:
            if callback is not None: callback()
            self._btn_save_MappingHub.config(state=tk.NORMAL, text="Save Mapping Hub")
    
    @thread_assign
    def save_selected_mappingUnit_ext(self,callback:Callable=None):
        """
        Saves the selected MappingMeasurement_Unit in the treeview to a text file
        
        Args:
            callback (Callable, optional): The callback function to run after saving the data. Defaults to None.
        """
        button = self._btn_save_MappingUnit_ext
        try:
            button.config(state=tk.DISABLED, text="Saving...")
            flg_saveraw = self._bool_save_raw_MappingUnit_ext.get()
            list_selection = self._tree_hub.selection()
            assert len(list_selection) != 0, "No unit selected"
            assert len(list_selection) == 1, "Multiple units selected. Please select only one unit to save"
            unit_id = self._tree_hub.item(self._tree_hub.selection()[0], "values")[0]
            unit = self._MappingHub.get_MappingUnit(unit_id)
            unit_name = unit.get_unit_name()
            thread = MeaRMap_Handler().save_MappingUnit_ext_prompt(unit,flg_saveraw=flg_saveraw)
            thread.join()
            messagebox.showinfo("Save complete", f"{unit_name} saved successfully")
        except AssertionError as e:
            messagebox.showwarning("Selection Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", "Error in saving Mapping Unit to .txt\n" + str(e))
            print('Error in save_selected_mappingUnit_txt:\n', e)
        finally:
            if callback is not None: callback()
            button.config(state=tk.NORMAL, text="Save selected Mapping Unit [.ext]")
            
    def set_MappingHub(self, mappingHub:MeaRMap_Hub):
        """
        Set the MappingMeasurement_Hub for the dataHub, which will be referred to for all the MappingMeasurement_Unit
        retrieval and storage.

        Args:
            mappingHub (MappingMeasurement_Hub): The MappingMeasurement_Hub to set
        """
        self._MappingHub = mappingHub
        self.update_tree()
        for callback in self._list_observer_load:
            try: callback()
            except Exception as e: print('set_mappingHub: Error in callback: ', e)
    
    def append_RamanMeasurement_multi(self, measurement:MeaRaman, coor:tuple=(0,0,0)):
        """
        Append a RamanMeasurement to the MappingMeasurement_Hub by assigning it to a unit.
        
        Args:
            measurement (RamanMeasurement): The RamanMeasurement to append
            coor (tuple, optional): The coordinates of the measurement. Defaults to (0,0,0).
        """
        # Mapping ID request and check
        while True:
            unit_name = messagebox_request_input("Unit ID", "Enter the ID for the added Raman measurement:")
            if isinstance(unit_name,str) and not unit_name == '': break
        
        unit = MeaRMap_Unit(unit_name=unit_name)
        
        timestamp = measurement.get_latest_timestamp()
        unit.append_ramanmeasurement_data(timestamp=timestamp, coor=coor, measurement=measurement)
        
        self.append_MappingUnit(unit)
        
    def terminate(self):
        """
        App termination sequence:
        Force the user to save the data before closing the app
        """
        while not self._flg_issaved:
            flg_save = messagebox.askyesno("Save Mapping Hub", "There are unsaved changes to the Mapping Data Hub. Do you want to save the before closing?")
            if flg_save:
                thread=self.save_dataHub()
                thread.join()
            else: break
            
        if self._flg_issaved and SaveParamsEnum.DELETE_PICKLE_POST_MEASUREMENT.value:
            try: [os.remove(file) for file in self._list_pickled]
            except Exception as e: print('Error in deleting temp files:\n', e)
            
        self._flg_isrunning.clear()  # Stop the autosave thread
        while self._flg_issaving.is_set():
            wait_for_autosave = messagebox.askyesno("Autosave", "Autosave thread is still running. Do you want to wait for it to finish?")
            messagebox.showinfo("Autosave", "Waiting (up to) 1 minute for autosave thread to finish...")
            if not wait_for_autosave or not self._thread_autosave.is_alive() or not self._flg_issaving.is_set():
                break
            self._thread_autosave.join(timeout=60)  # Wait for the autosave thread to finish
        
        return
        
class Frm_DataHub_Mapping_Plus(tk.Frame):
    """
    Like the Frm_DataHub, but also shows the data of a single MappingMeasurement_Unit.
    """
    def __init__(self, master,dataHub:Frm_DataHub_Mapping,width_rel:float=1,height_rel:float=1):
        """
        Initialises the data hub frame. This frame stores all the data from the measurement session.
        
        Args:
            master (tk.Tk): The master window
            dataHub (Frm_DataHub): The data hub to get the data from
            width_rel (float, optional): The relative width of the frame. Defaults to 1.
            height_rel (float, optional): The relative height of the frame. Defaults to 1.
        """
        super().__init__(master)
        assert isinstance(dataHub, Frm_DataHub_Mapping), "dataHub must be a Frm_DataHub object"
        assert isinstance(width_rel, (int, float)), "width_rel must be an integer or float"
        assert isinstance(height_rel, (int, float)), "height_rel must be an integer or float"
        if width_rel <= 0: width_rel=1
        if height_rel <= 0: height_rel=1
        self._width_rel = width_rel
        
        # Main frames setup
        frm_tree_unit = tk.LabelFrame(self, text="Selected mapping unit preview")
        frm_tree_unit.grid(row=1, column=0, sticky="nsew")
        
        # DataHub setup
        self._dataHub = dataHub
        self._tree_MappingHub = self._dataHub.get_tree()
        
        # Storage parameters setup
        self._mappingUnit:MeaRMap_Unit = None
        self._lock_dict_RMid_treeid = threading.Lock()
        self._dict_RMid_treeid = {}     # Dict to map: RamanMeasurement ID -> treeview item ID
        self._lock_dict_RMid_RM = threading.Lock()
        self._dict_RMid_RM = {}     # Dict to map: RamanMeasurement -> RamanMeasurement ID
        
        # Unit tree setup
        columns = ("Timestamp", "Coor-x", "Coor-y", "Coor-z", "Metadata")
        self._unit_id:str = None
        self._tree_MappingUnit = ttk.Treeview(frm_tree_unit, columns=columns, show="headings",
                                              height=int(20*height_rel))
        self._init_tree_unit()
        
        # Status bar setup
        self._lbl_statusbar = tk.Label(frm_tree_unit, text="Ready")
        self._lbl_bg = self._lbl_statusbar.cget("background")
        
        # Grid setup
        self._tree_MappingUnit.grid(row=0, column=0, sticky="nsew")
        self._lbl_statusbar.grid(row=1, column=0, sticky="nsew")
        
        # Interactive widget setup
        self._tree_MappingHub.bind("<ButtonRelease-1>", lambda event: self._notify_observer_unit_selection())
        self._tree_MappingUnit.bind("<ButtonRelease-1>", lambda event: self._notify_observer_RM_selection())
        self._list_observer_unit_selection = [self._set_unit_dataHub]
        self._list_observer_RamanMea_selection = []
        
        # Grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        frm_tree_unit.grid_columnconfigure(0, weight=1)
        frm_tree_unit.grid_rowconfigure(0, weight=1)
        
        # Flags for status updates
        self._flg_updated_dictRM = threading.Event()
        self._flg_updated_dictTree = threading.Event()
        
    def _notify_observer_RM_selection(self):
        """
        Run all the callbacks in the list when a RamanMeasurement is selected
        """
        for callback in self._list_observer_RamanMea_selection: callback()
        
    def _notify_observer_unit_selection(self):
        """
        Run all the callbacks in the list when a unit is selected
        """
        for callback in self._list_observer_unit_selection: callback()
        
    def add_observer_RM_selection(self, callback):
        """
        Sets a callback function to run when the user selects a RamanMeasurement in the unit treeview
        """
        assert callable(callback), "callback must be a callable function"
        self._list_observer_RamanMea_selection.append(callback)
        
    def add_observer_unit_selection(self, callback):
        """
        Sets a callback function to run when the user selects a MappingMeasurement_Unit in the hub treeview
        """
        assert callable(callback), "callback must be a callable function"
        self._list_observer_unit_selection.append(callback)
        
    def set_mappingHub(self, mappingHub:MeaRMap_Hub):
        """
        Sets the MappingMeasurement_Hub for the dataHub
        """
        assert isinstance(mappingHub, MeaRMap_Hub), "mappingHub must be a MappingMeasurement_Hub object"
        self._dataHub.set_MappingHub(mappingHub)
        self.update_tree_unit()
        
    def get_selected_MappingUnit(self) -> MeaRMap_Unit:
        """
        Returns the selected MappingMeasurement_Unit in the hub treeview
        
        Returns:
            MappingMeasurement_Unit: The selected MappingMeasurement_Unit
        """
        return self._mappingUnit
        
    def set_selected_RamanMeasurement(self, measurement_id:str):
        """
        Sets the selected RamanMeasurement in the unit treeview
        
        Args:
            measurement_id (str): The id of the RamanMeasurement to select
        """
        assert isinstance(measurement_id, str), "measurement_id must be a string"
        mapping_unit_items = self._tree_MappingUnit.get_children()
        
        # New search using the dictionary
        with self._lock_dict_RMid_treeid:
            if measurement_id in self._dict_RMid_treeid:
                item_id = self._dict_RMid_treeid[measurement_id]
                current_selections = self._tree_MappingUnit.selection()
                [self._tree_MappingUnit.selection_remove(item) for item in current_selections]
                self._tree_MappingUnit.selection_add(item_id)
                self._tree_MappingUnit.see(item_id)
                return
        
    def get_selected_RamanMeasurement_summary(self) -> list[dict]:
        """
        Returns the summary of the selected RamanMeasurement in the unit treeview
        from the MappingMeasurement_Unit.
        
        Returns:
            list[dict]: The summary of the selected RamanMeasurement
        """
        selections = self._tree_MappingUnit.selection()
        list_dict_mea = []
        with self._lock_dict_RMid_RM:
            for item in selections:
                RM_id = self._tree_MappingUnit.item(item, "values")[0]
                list_dict_mea.append(self._mappingUnit.get_dict_RamanMeasurement_summary(RM_id,exclude_id=True))
            return list_dict_mea
        
    def get_selected_RamanMeasurement(self) -> list[MeaRaman]:
        """
        Returns the selected RamanMeasurement in the unit treeview
        
        Returns:
            list[RamanMeasurement]: The selected RamanMeasurement
        """
        selections = self._tree_MappingUnit.selection()
        
        with self._lock_dict_RMid_RM:
            list_measurements = []
            for item in selections:
                RM_id = self._tree_MappingUnit.item(item, "values")[0]
                RM = self._dict_RMid_RM[RM_id]
                list_measurements.append(RM)
            return list_measurements
        
    def _init_tree_unit(self):
        """
        Initialises the unit treeview with the columns and headings
        """
        self._tree_MappingUnit.heading("Timestamp", text="Timestamp", anchor=tk.W)
        self._tree_MappingUnit.heading("Coor-x", text="Coor-x", anchor=tk.W)
        self._tree_MappingUnit.heading("Coor-y", text="Coor-y", anchor=tk.W)
        self._tree_MappingUnit.heading("Coor-z", text="Coor-z", anchor=tk.W)
        self._tree_MappingUnit.heading("Metadata", text="Metadata", anchor=tk.W)
        
        self._tree_MappingUnit.column("Timestamp", width=int(100*self._width_rel))
        self._tree_MappingUnit.column("Coor-x", width=int(100*self._width_rel))
        self._tree_MappingUnit.column("Coor-y", width=int(100*self._width_rel))
        self._tree_MappingUnit.column("Coor-z", width=int(100*self._width_rel))
        self._tree_MappingUnit.column("Metadata", width=int(300*self._width_rel))
        
    def _build_dict_RMid_RM(self):
        """
        Builds a dictionary that maps the RamanMeasurement ID to the RamanMeasurement object
        """
        self._flg_updated_dictRM.clear()
        with self._lock_dict_RMid_RM:
            for item_id in self._tree_MappingUnit.get_children():
                RM_id = self._tree_MappingUnit.item(item_id, "values")[0]
                RM = self._mappingUnit.get_RamanMeasurement(RM_id)
                self._dict_RMid_RM[RM_id] = RM
        self._flg_updated_dictRM.set()
        
    def _build_dict_RMid_treeid(self):
        """
        Builds a dictionary that maps the RamanMeasurement ID to the treeview item ID
        """
        self._flg_updated_dictTree.clear()
        with self._lock_dict_RMid_treeid:
            for item_id in self._tree_MappingUnit.get_children():
                RM_id = self._tree_MappingUnit.item(item_id, "values")[0]
                self._dict_RMid_treeid[RM_id] = item_id
        self._flg_updated_dictTree.set()
            
    def _set_unit_dataHub(self):
        """
        Sets the unit based on the dataHub selection.
        If there is no selection, nothing happens and if there are multiple selections, the first one is selected
        """
        list_unit = self._dataHub.get_selected_MappingUnit()
        
        if len(list_unit) == 0: return
        self._mappingUnit = list_unit[0]
        threading.Thread(target=self._build_dict_RMid_treeid).start()
        threading.Thread(target=self._build_dict_RMid_RM).start()
        self.update_tree_unit()
        
    def update_tree_unit(self):
        """
        Refreshes the unit treeview with the data in the MappingMeasurement_Unit
        """
        self._lbl_statusbar.config(text="Updating the Data Hub Plus. Interactive features not ready.",bg="yellow")
        
        self._tree_MappingUnit.delete(*self._tree_MappingUnit.get_children())
        if self._mappingUnit is None: return
        
        dict_metadata = self._mappingUnit.get_dict_measurement_metadata()
        dict_measurement = self._mappingUnit.get_dict_measurements()
        mea_id_key, coorx_key, coory_key, coorz_key, _, _ = self._mappingUnit.get_keys_dict_measurement()
        
        list_timestamp = dict_measurement[mea_id_key]
        list_coorx = dict_measurement[coorx_key]
        list_coory = dict_measurement[coory_key]
        list_coorz = dict_measurement[coorz_key]
        list_metadata = [str(dict_metadata)] * len(list_timestamp)
        
        for timestamp, coorx, coory, coorz, metadata in zip(list_timestamp, list_coorx, list_coory, list_coorz, list_metadata):
            self._tree_MappingUnit.insert("", "end", values=(timestamp, coorx, coory, coorz, metadata))
            
        threading.Thread(target=self.reset_statusbar).start()
    
    def reset_statusbar(self):
        """
        Resets the status bar after updating the treeview
        """
        self._flg_updated_dictRM.wait()
        self._flg_updated_dictTree.wait()
        self._lbl_statusbar.config(text="Ready", bg=self._lbl_bg)
    
def generate_dummy_frmMappingHub(parent) -> Frm_DataHub_Mapping:
    """
    Generates a dummy Frm_DataHub_Mapping for testing purposes.
    
    Args:
        parent (tk.Tk): The parent window to attach the frame to.
    
    Returns:
        Frm_DataHub_Mapping: The generated data hub mapping frame.
    """
    frm = Frm_DataHub_Mapping(parent)
    frm.get_MappingHub().test_generate_dummy()
    return frm
    
def test_dataHub_Plus():
    root = tk.Tk()
    datahub = Frm_DataHub_Mapping(root)
    frm = Frm_DataHub_Mapping_Plus(root,datahub)
    frm.pack()
    
    root.mainloop()

def test_dataHub():
    from iris.data.measurement_RamanMap import generate_dummy_mappingHub
    
    root = tk.Tk()
    datahub = Frm_DataHub_Mapping(root)
    datahub.pack()
    
    mappinghub = MeaRMap_Hub()
    mappinghub.test_generate_dummy()
    datahub.set_MappingHub(mappinghub)
    datahub.add_observer_selection(lambda: print("Selection changed:", [unit.get_unit_name() for unit in datahub.get_selected_MappingUnit()]))
    
    root.mainloop()
    
    os._exit(0)  # Force exit to kill all threads
    
if __name__ == '__main__':
    test_dataHub()
    # test_dataHub_Plus()