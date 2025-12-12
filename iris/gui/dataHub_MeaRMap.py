"""
A class that stores the all the measurement data in the current experiment.
- Shows the stored data in a table format
- Allows the user to add new data to the table
- Allows the user to delete data from the table
"""
import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer, QCoreApplication

import os
from typing import Any, Callable

import queue
import threading

from fuzzywuzzy import fuzz, process

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.utils.general import *
from iris.data.measurement_Raman import MeaRaman
from iris.data.measurement_RamanMap import MeaRMap_Hub, MeaRMap_Unit, MeaRMap_Handler

from iris.data import SaveParamsEnum

from iris.resources.dataHub_Raman_ui import Ui_DataHub_mapping
from iris.resources.dataHubPlus_Raman_ui import Ui_DataHubPlus_mapping

class Save_worker(QObject):
    
    sig_save_done = Signal(str)
    save_success = "Saved the data successfully."
    load_success = "Loaded the data successfully."

    def __init__(self, mapping_hub:MeaRMap_Hub):
        super().__init__()
        self._mappinghub = mapping_hub
        self._handler = MeaRMap_Handler()
        
        self._flg_issaved = True

    @Slot(str,str)
    def save_database(self,savedirpath:str,savename:str) -> None:
        """
        Save the MappingMeasurement_Hub stored internally to the local disk.
        
        Args:
            savedirpath (str): The directory path to save the database to
            savename (str): The name of the database file
        """
        try:
            thread = MeaRMap_Handler().save_MappingHub_database(
                mappingHub=self._mappinghub,
                savedirpath=savedirpath,
                savename=savename,
            )
            thread.join()
            self._flg_issaved = True
            self.sig_save_done.emit(self.save_success)
        except Exception as e:
            self.sig_save_done.emit("Error in saving Mapping Hub database:\n" + str(e))

    @Slot(str, str, str)
    def save_unit_ext(self, unit_id:str, savepath:str, extension:str) -> None:
        """
        Saves the selected MappingMeasurement_Unit in the treeview to a text file
        
        Args:
            unit_id (str): The ID of the MappingMeasurement_Unit to save
            savepath (str): The path to save the file to
            extension (str): The file extension to save as
        """
        try:
            flg_saveraw = True
            filepath = os.path.abspath(savepath)
            if not filepath.endswith(f".{extension}"):
                filepath += f".{extension}"
                
            unit = self._mappinghub.get_MappingUnit(unit_id)
            thread = self._handler.save_MappingUnit_ext(
                mappingUnit=unit,
                filepath=filepath,
                flg_saveraw=flg_saveraw,
                extension=extension,
            )
            thread.join()
            self.sig_save_done.emit(self.save_success)
        except AssertionError as e:
            self.sig_save_done.emit("Error in saving Mapping Unit to .txt:\n" + str(e))
        except Exception as e:
            self.sig_save_done.emit("Error in saving Mapping Unit to .txt:\n" + str(e))
    
    @Slot(str)
    def load_database(self, loadpath: str) -> None:
        """
        Load a MappingMeasurement_Hub from a database file
        """
        try:
            self._handler.load_MappingMeasurementHub_database(
                self._mappinghub, loadpath=loadpath, flg_readraw=True)
            self.sig_save_done.emit(self.load_success)
        except Exception as e:
            self.sig_save_done.emit("Error in loading Mapping Hub database:\n" + str(e))
    
    def set_MappingHub(self, mappingHub:MeaRMap_Hub):
        """
        Set the MappingMeasurement_Hub for the dataHub, which will be referred to for all the MappingMeasurement_Unit
        retrieval and storage.

        Args:
            mappingHub (MappingMeasurement_Hub): The MappingMeasurement_Hub to set
        """
        self._mappinghub = mappingHub

class Wdg_DataHub_Mapping_Ui(qw.QWidget, Ui_DataHub_mapping):
    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.setupUi(self)
        lyt = qw.QVBoxLayout()
        self.setLayout(lyt)

class Wdg_DataHub_Mapping(qw.QWidget):
    
    _sig_modify_tree = Signal()     # Emitted when the treeview needs to be modified (internal)
    sig_tree_changed = Signal()     # Emitted when the treeview is changed
    sig_tree_selection = Signal()   # Emitted when the treeview selection is changed

    sig_save_ext = Signal(str,str,str)  # Emitted to save the selected MappingMeasurement_Unit externally
    sig_save_db = Signal(str,str)       # Emitted to save the MappingMeasurement_Hub to the database
    sig_load_db = Signal(str)           # Emitted to load the MappingMeasurement_Hub from the database

    def __init__(self, parent:Any, mappingHub:MeaRMap_Hub|None=None,autosave:bool=False):
        """
        Initialises the data hub frame. This frame stores all the data from the measurement session.
        
        Args:
            parent (Any): The parent widget
            mappingHub (MeaRMap_Hub|None): The MappingMeasurement_Hub instance. Defaults to None.
            autosave (bool, optional): If True, will enable autosaving of the MappingMeasurement_Hub. Defaults to False.

        Note: mappingHub will be used during the refresh callback to get the latest MappingMeasurement_Hub.
        """
        super().__init__(parent)
        # Main GUI setup
        lyt = qw.QVBoxLayout()
        self.setLayout(lyt)
        self._widget = Wdg_DataHub_Mapping_Ui(self)
        lyt.addWidget(self._widget)
        wdg = self._widget
        
        # Storage to store the data
        if isinstance(mappingHub, MeaRMap_Hub): self._MappingHub = mappingHub
        else: self._MappingHub = MeaRMap_Hub()
        self._MappingHub.add_observer(self._sig_modify_tree.emit)
        
        # Save parameters
        self._sessionid = get_timestamp_us_str()
        self._flg_issaved = True   # Indicate if the stored data has been saved
        self._list_pickled = []    # List of pickled files
        self._temp_savedir = SaveParamsEnum.DEFAULT_SAVE_PATH.value + r'\temp'
        if not os.path.exists(self._temp_savedir): os.makedirs(self._temp_savedir)
        
        # Widgets to show the stored data
        self._tree = wdg.tree_data
        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels(["Region of interest name", "Metadata", "Number of samplings"])
        
        # Set up the searchbar
        wdg.ent_searchbar.textChanged.connect(lambda: self.update_tree(keep_selection=False))
        
        # Widgets to manipulate entries
        wdg.btn_refresh.clicked.connect(self.update_tree)
        wdg.btn_rename.clicked.connect(self.rename_unit)
        wdg.btn_delete.clicked.connect(self.delete_unit)
        self._btn_save_ext = wdg.btn_save_ext
        self._btn_save_db = wdg.btn_save_db
        self._btn_load_db = wdg.btn_load_db
        
        self._btn_save_ext_ori = self._btn_save_ext.text()
        self._btn_save_db_ori = self._btn_save_db.text()
        self._btn_load_MappingHub_ori = self._btn_load_db.text()
        
        # Other connection setups
        self._tree.itemSelectionChanged.connect(lambda: self.sig_tree_selection.emit())
        
    # > Save/load worker and thread setup <
        self._save_worker = Save_worker(self._MappingHub)
        self._thread_save = QThread(self)
        self._save_worker.moveToThread(self._thread_save)
        self.destroyed.connect(self._thread_save.quit)
        self.destroyed.connect(self._save_worker.deleteLater)
        self.destroyed.connect(self._thread_save.deleteLater)
        self._thread_save.start()
        
        # Button connection setup
        self._btn_save_ext.clicked.connect(self._save_unit_ext)
        self._btn_save_db.clicked.connect(self._save_hub_database)
        self._btn_load_db.clicked.connect(self._load_hub_database)
        
        self._save_worker.sig_save_done.connect(self._reset_reenable_saveload_buttons)
        self.sig_save_ext.connect(self._save_worker.save_unit_ext)
        self.sig_save_db.connect(self._save_worker.save_database)
        self.sig_load_db.connect(self._save_worker.load_database)

        # Other connection setup
        self._save_worker.sig_save_done.connect(self._handle_saveload_result)
        self._sig_modify_tree.connect(self.update_tree)
        
    # > Autosave info <
        # Autosave parameters
        self._autosave_path = os.path.abspath(SaveParamsEnum.AUTOSAVE_PATH.value)
        if not os.path.exists(self._autosave_path): os.makedirs(self._autosave_path)
        
        # Autosave widgets
        self._flg_autosave = SaveParamsEnum.AUTOSAVE_ENABLED.value and autosave
        self._autosave_interval = SaveParamsEnum.AUTOSAVE_INTERVAL_HOURS.value
        if self._autosave_interval <= 0.0: self._flg_autosave = False
        if self._flg_autosave:
            wdg.lbl_autosave.setText(f'Autosave: every {self._autosave_interval} hours to\n{self._autosave_path}')
        
    def get_tree(self) -> qw.QTreeWidget:
        return self._tree
        
    def get_selected_MappingUnit(self) -> list[MeaRMap_Unit]:
        """
        Returns the selected MappingMeasurement_Unit in the treeview
        
        Returns:
            list[MappingMeasurement_Unit]: The selected MappingMeasurement_Unit
        """
        selections = self._tree.selectedItems()
        
        list_units = []
        for item in selections:
            unit_name = item.text(0)
            try: unit = self._MappingHub.get_MappingUnit(unit_name=unit_name)
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
        search_query = self._widget.ent_searchbar.text().lower()
        dict_unit_IdNames = {unit.get_unit_id(): unit.get_unit_name().lower()\
            for unit in self._MappingHub.get_list_MappingUnit()}
        list_unit_ids = self._MappingHub.get_list_MappingUnit_ids()

        # Return all if the search query is empty
        if not search_query or search_query == "":
            return list_unit_ids
        
        # Perform fuzzy matching on the unit names
        list_matches = process.extract(
            search_query, dict_unit_IdNames.values(), scorer=fuzz.partial_token_set_ratio, limit=None)
        list_matches = sorted(list_matches, key=lambda x: x[1], reverse=True)
        
        list_matches_id = [
            unit_id
            for name, _ in list_matches
            for unit_id, unit_name in dict_unit_IdNames.items()
            if unit_name == name
        ]
        
        return list_matches_id
    
    @Slot()
    def update_tree(self, keep_selection:bool=True):
        # Store the current selections
        list_unitID = [unit.get_unit_id() for unit in self.get_selected_MappingUnit()]
        list_matched_ids = self._filter_by_search()
        
        self._tree.clear()
        list_unit_ids, list_unit_names, list_metadata, list_num_measurements = self._MappingHub.get_summary_units()
        
        for unit_id in list_matched_ids:
            idx = list_unit_ids.index(unit_id)
            qw.QTreeWidgetItem(self._tree,
                [list_unit_names[idx], str(list_metadata[idx]), str(list_num_measurements[idx])])
            
        # Set the selection back to the previous selection
        if keep_selection: self.set_selection_unitID(list_unitID)
        
        self.sig_tree_changed.emit()
        
    def set_selection_unitID(self, list_unitID:list[str]|str, clear_previous:bool=True):
        """
        Sets the selection in the treeview to the given unit IDs.

        Args:
            list_unitID (list[str]|str): The list of unit IDs to select or a single unit ID.
            clear_previous (bool): Whether to clear the previous selection.
        """
        if not isinstance(list_unitID, list): list_unitID = [list_unitID]
        list_name = [self._MappingHub.get_MappingUnit(unit_id).get_unit_name() for unit_id in list_unitID]
        
        self._tree.blockSignals(True)
        
        if clear_previous: self._tree.clearSelection()
            
        # Get the invisible root item (parent of all top-level items)
        root = self._tree.invisibleRootItem()
        
        # Iterate through all top-level items
        for i in range(root.childCount()):
            item = root.child(i)
            unit_name_in_tree = item.text(0) 
            
            # Check if the item's ID is in our target list
            if unit_name_in_tree in list_name: item.setSelected(True) 
                
        self._tree.blockSignals(False)
        
        self.sig_tree_selection.emit()
                
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
                if not persist: qw.QErrorMessage().showMessage("Unit ID already exists:\n" + str(e)); break
                new_unitName, ok = qw.QInputDialog.getText(
                    None, "Unit name already exists", "Unit name already exists!\nEnter a new 'unit name':",
                    text=unit.get_unit_name())
                if ok: unit.set_unitName_and_unitID(new_unitName)
                else: break
                
        self._sig_modify_tree.emit()
                
    def extend_MappingUnit(self, list_unit:list[MeaRMap_Unit], persist:bool=True):
        """
        Extend a MappingMeasurement_Unit in the MappingMeasurement_Hub
        
        Args:
            list_unit (list[MappingMeasurement_Unit]): The unit to extend
            persist (bool, optional): If True, will ask for a new unit ID if the unit ID does not exist. Defaults to True.
        """
        for unit in list_unit: self.append_MappingUnit(unit, persist=persist)
    
    def rename_unit(self):
        """
        Rename the selected MappingMeasurement_Unit in the MappingMeasurement_Hub
        """
        try:
            selections = self._tree.selectedItems()
            
            if len(selections) == 0:
                qw.QErrorMessage().showMessage("No unit selected")
                return
            elif len(selections) > 1:
                qw.QErrorMessage().showMessage("Multiple units selected. Please select only one unit to rename")
                return
            
            unit_name = selections[0].text(0)
            unit = self._MappingHub.get_MappingUnit(unit_name=unit_name)
            new_name, ok = qw.QInputDialog.getText(None, "Rename Mapping Unit", "Enter the new name for the selected Mapping Unit:",
                                                    text=unit.get_unit_name())
            if ok: self._MappingHub.rename_mapping_unit(unit_name, new_name)
            self._flg_issaved = False
        except Exception as e: qw.QErrorMessage().showMessage("Error in renaming the Mapping Unit\n" + str(e))
        finally: self._sig_modify_tree.emit()
    
    def delete_unit(self):
        """
        Delete the selected MappingMeasurement_Unit from the MappingMeasurement_Hub
        """
        # Get the currently selected units
        selections = self._tree.selectedItems()

        if len(selections) == 0:
            qw.QErrorMessage().showMessage("No unit selected")
            return

        flg_remove = qw.QMessageBox.question(
            None,
            "Mapping Unit deletion",
            "Are you sure you want to delete the selected units?"
            "\n!!! This action cannot be undone !!!",
            qw.QMessageBox.Yes | qw.QMessageBox.No, qw.QMessageBox.No) # type: ignore
        if flg_remove != qw.QMessageBox.Yes: return  # type: ignore
        
        list_names = [item.text(0) for item in selections]
        for unit_name in list_names:
            self._MappingHub.remove_mapping_unit_name(unit_name)
        
        if len(selections) > 0: self._flg_issaved = False
        self._sig_modify_tree.emit()
        
    @Slot()
    def _save_unit_ext(self) -> None:
        """
        Save the selected MappingMeasurement_Unit in the treeview to a text file
        """
        self._btn_save_ext.setEnabled(False)
        self._btn_save_ext.setText("Saving...")
        
        list_units = self.get_selected_MappingUnit()
        list_ids = [unit.get_unit_id() for unit in list_units]
        
        if len(list_ids) != 1:
            qw.QErrorMessage().showMessage("Please select only one unit to save")
            self._reset_reenable_saveload_buttons()
            return
        
        dict_ext_options = MeaRMap_Handler().get_dict_extensions()
        save_path, save_ext = qw.QFileDialog.getSaveFileName(
            None,
            "Save Mapping Unit as...",
            "",
            ";;".join([f"{value.upper()} files (*.{key})" for key,value in dict_ext_options.items()]),
        )
        save_ext = save_ext.split('(')[1].split('*.')[1].split(')')[0]
        
        self.sig_save_ext.emit(list_ids[0], save_path, save_ext)
        
    @Slot()
    def _save_hub_database(self) -> None:
        """
        Save the MappingMeasurement_Hub stored internally to the local disk as a database
        """
        self._btn_save_db.setEnabled(False)
        self._btn_save_db.setText("Saving...")
        
        savepath = qw.QFileDialog.getSaveFileName(
            None,
            "Save Mapping Hub database...",
            "",
            "Database files (*.db)"
        )[0]
        
        savedirpath, savename = os.path.split(savepath)
        self.sig_save_db.emit(savedirpath, savename)

    @Slot()
    def _load_hub_database(self) -> None:
        """
        Load a MappingMeasurement_Hub from a database file
        """
        self._btn_load_db.setEnabled(False)
        self._btn_load_db.setText("Loading...")
        
        loadpath = qw.QFileDialog.getOpenFileName(
            None,
            "Load Mapping Hub database...",
            "",
            "Database files (*.db)"
        )[0]
        
        self.sig_load_db.emit(loadpath)

    @Slot()
    def _disable_saveload_buttons(self):
        list_widgets = get_all_widgets_from_layout(self._widget.lyt_saveload)
        list_buttons = [wdg for wdg in list_widgets if isinstance(wdg, qw.QPushButton)]
        
        for wdg in list_buttons: wdg.setEnabled(False)
        
    @Slot()
    def _reset_reenable_saveload_buttons(self):
        list_widgets = get_all_widgets_from_layout(self._widget.lyt_saveload)
        list_buttons = [wdg for wdg in list_widgets if isinstance(wdg, qw.QPushButton)]
        
        for wdg in list_buttons:
            wdg.setEnabled(True)
            if wdg == self._btn_save_ext: wdg.setText(self._btn_save_ext_ori)
            elif wdg == self._btn_save_db: wdg.setText(self._btn_save_db_ori)
            elif wdg == self._btn_load_db: wdg.setText(self._btn_load_MappingHub_ori)
            wdg.setStyleSheet("")
        
    @Slot(str)
    def _handle_saveload_result(self, message:str):
        """
        Handle the result of the save/load operation
        
        Args:
            message (str): The message to display
        """
        if message != Save_worker.save_success and message != Save_worker.load_success:
            qw.QErrorMessage().showMessage(message)
        else: qw.QMessageBox.information(None, "Save/Load operation", message)
        self._reset_reenable_saveload_buttons()
        self._sig_modify_tree.emit()
        
    def _handle_hub_change(self):
        """
        Handle changes in the MappingMeasurement_Hub
        """
        self._flg_issaved = False
        self._sig_modify_tree.emit()
        
    def append_RamanMeasurement_multi(self, measurement:MeaRaman, coor:tuple=(0,0,0)):
        """
        Append a RamanMeasurement to the MappingMeasurement_Hub by assigning it to a unit.
        
        Args:
            measurement (RamanMeasurement): The RamanMeasurement to append
            coor (tuple, optional): The coordinates of the measurement. Defaults to (0,0,0).
        """
        # Mapping ID request and check
        unit_name = None
        while unit_name == None:
            unit_name = messagebox_request_input(
                parent=self,
                title= "Unit ID",
                message="Enter the ID for the added Raman measurement:",
                default=f"Single point measurement at {coor}: ",
                )
            if isinstance(unit_name,str) and not unit_name == '': break
        
        unit = MeaRMap_Unit(unit_name=unit_name)
        
        timestamp = measurement.get_latest_timestamp()
        unit.append_ramanmeasurement_data(timestamp=timestamp, coor=coor, measurement=measurement)
        
        self.append_MappingUnit(unit)
        
    def check_safeToTerminate(self) -> bool:
        """
        Check if the data has been saved before terminating the app.
        
        Returns:
            bool: True if the app can be terminated, False otherwise
        """
        if self._flg_issaved: return True
        elif len(self._MappingHub.get_list_MappingUnit()) == 0: return True
        
        flg_close = qw.QMessageBox.question(
            None,
            "Unsaved data",
            "There is unsaved data in the Mapping Hub.\nAre you sure you want to exit without saving?",
            qw.QMessageBox.Yes | qw.QMessageBox.Cancel, # pyright: ignore[reportAttributeAccessIssue]
            qw.QMessageBox.Cancel) # type: ignore
        
        if flg_close == qw.QMessageBox.Yes:   # type: ignore
            return True
        else:
            return False
        
    def terminate(self):
        """
        App termination sequence:
        Force the user to save the data before closing the app
        """
        return
        
class Wdg_DataHubPlus_Mapping_Ui(qw.QWidget, Ui_DataHubPlus_mapping):
    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.setupUi(self)
        lyt = qw.QVBoxLayout()
        self.setLayout(lyt)
        
class Frm_DataHub_Mapping_Plus(qw.QWidget):
    """
    Like the Frm_DataHub, but also shows the data of a single MappingMeasurement_Unit.
    """
    sig_mea_selection_changed = Signal()   # Emitted when the RamanMeasurement selection is changed
    
    _sig_modify_tree = Signal()         # Emitted when the treeview needs to be modified (internal)
    _sig_tree_rebuild_done = Signal()   # Emitted when the treeview has been rebuilt (internal)
    
    def __init__(self, master,dataHub:Wdg_DataHub_Mapping):
        """
        Initialises the data hub frame. This frame stores all the data from the measurement session.
        
        Args:
            master (tk.Tk): The master window
            dataHub (Frm_DataHub): The data hub to get the data from
            width_rel (float, optional): The relative width of the frame. Defaults to 1.
            height_rel (float, optional): The relative height of the frame. Defaults to 1.
        """
        super().__init__(master)
        assert isinstance(dataHub, Wdg_DataHub_Mapping), "dataHub must be a Frm_DataHub object"
        
        # DataHub setup
        self._dataHub = dataHub
        self._tree_MappingHub = self._dataHub.get_tree()
        
        # Main widget
        self._widget = Wdg_DataHubPlus_Mapping_Ui(self)
        lyt = qw.QVBoxLayout()
        self.setLayout(lyt)
        lyt.addWidget(self._widget)
        wdg = self._widget
        
        # Storage parameters setup
        self._mappingUnit:MeaRMap_Unit|None = None
        self._lock_dict_RMid_treeid = threading.Lock()
        self._dict_RMid_treeid = {}     # Dict to map: RamanMeasurement ID -> treeview item ID
        self._lock_dict_RMid_RM = threading.Lock()
        self._dict_RMid_RM = {}     # Dict to map: RamanMeasurement -> RamanMeasurement ID
        
        # Unit tree setup
        columns = ("Timestamp", "Coor-x", "Coor-y", "Coor-z", "Metadata")
        self._unit_id:str|None = None
        self._tree_unit = wdg.tree_data
        self._tree_unit.setColumnCount(len(columns))
        self._tree_unit.setHeaderLabels(columns)
        
        # Status bar setup
        self._lbl_statusbar = wdg.lbl_info
        
        # Interactive widget setup
        self._sig_modify_tree.connect(self.update_tree_unit)
        self._tree_unit.clicked.connect(lambda: self.sig_mea_selection_changed.emit())
        self._dataHub.sig_tree_selection.connect(self._set_unit_dataHub)
        
    def set_selected_RamanMeasurement(self, measurement_id:str):
        """
        Sets the selected RamanMeasurement in the unit treeview
        
        Args:
            measurement_id (str): The id of the RamanMeasurement to select
        """
        assert isinstance(measurement_id, str), "measurement_id must be a string"
        list_selections = self._tree_unit.selectedItems()
        list_ts = [item.text(0) for item in list_selections]
        if not isinstance(self._mappingUnit, MeaRMap_Unit): return
        self._mappingUnit.get_RamanMeasurement(list_ts[0])
        
    def get_selected_RamanMeasurement_summary(self) -> dict:
        """
        Returns the summary of the selected RamanMeasurement in the unit treeview
        from the MappingMeasurement_Unit.
        
        Returns:
            dict: The summary of the selected RamanMeasurement
        """
        selections = self._tree_unit.selectedItems()
        
        if not isinstance(self._mappingUnit, MeaRMap_Unit): return {}
        mea_id = selections[0].text(0)
        return self._mappingUnit.get_dict_RamanMeasurement_summary(mea_id,exclude_id=True)
        
    def get_selected_RamanMeasurement(self) -> MeaRaman|None:
        """
        Returns the selected RamanMeasurement in the unit treeview
        
        Returns:
            RamanMeasurement: The selected RamanMeasurement
        """
        selections = self._tree_unit.selectedItems()
        if not isinstance(self._mappingUnit, MeaRMap_Unit): return None
        mea_id = selections[0].text(0)
        return self._mappingUnit.get_RamanMeasurement(mea_id)
            
    @Slot()
    def _set_unit_dataHub(self):
        """
        Sets the unit based on the dataHub selection.
        If there is no selection, nothing happens and if there are multiple selections, the first one is selected
        """
        list_unit = self._dataHub.get_selected_MappingUnit()
        
        if len(list_unit) == 0: return
        self._mappingUnit = list_unit[0]
        
        self._sig_modify_tree.emit()
        
    @Slot()
    def update_tree_unit(self):
        """
        Refreshes the unit treeview with the data in the MappingMeasurement_Unit
        """
        self._lbl_statusbar.setText("Updating the Data Hub Plus. Interactive features not ready.")
        self._lbl_statusbar.setStyleSheet("background-color: yellow")
        
        self._tree_unit.clear()
        if self._mappingUnit is None: return
        
        dict_metadata = self._mappingUnit.get_dict_measurement_metadata()
        dict_measurement = self._mappingUnit.get_dict_measurements()
        mea_id_key, coorx_key, coory_key, coorz_key, _, _ = self._mappingUnit.get_keys_dict_measurement()
        
        list_timestamp = dict_measurement[mea_id_key]
        list_coorx = dict_measurement[coorx_key]
        list_coory = dict_measurement[coory_key]
        list_coorz = dict_measurement[coorz_key]
        list_metadata = [str(dict_metadata)] * len(list_timestamp)
        
        for ts, x, y, z, meta in zip(list_timestamp, list_coorx, list_coory, list_coorz, list_metadata):
            qw.QTreeWidgetItem(self._tree_unit,
                [str(ts), str(x), str(y), str(z), meta])
            
        self._lbl_statusbar.setText("Data Hub Plus updated. Ready.")
        self._lbl_statusbar.setStyleSheet("")
    
def generate_dummy_frmMappingHub(parent) -> Wdg_DataHub_Mapping:
    """
    Generates a dummy Frm_DataHub_Mapping for testing purposes.
    
    Args:
        parent (tk.Tk): The parent window to attach the frame to.
    
    Returns:
        Frm_DataHub_Mapping: The generated data hub mapping frame.
    """
    frm = Wdg_DataHub_Mapping(parent)
    frm.get_MappingHub().test_generate_dummy()
    return frm
    
def test_dataHub_Plus():
    import sys
    app = qw.QApplication([])
    window = qw.QMainWindow()
    central_widget = qw.QWidget()
    window.setCentralWidget(central_widget)
    layout = qw.QVBoxLayout()
    central_widget.setLayout(layout)
    
    mappinghub = MeaRMap_Hub()
    datahub = Wdg_DataHub_Mapping(central_widget,mappingHub=mappinghub,autosave=False)
    layout.addWidget(datahub)
    
    datahubplus = Frm_DataHub_Mapping_Plus(central_widget,datahub)
    layout.addWidget(datahubplus)
    
    datahubplus.sig_mea_selection_changed.connect(lambda: print(datahubplus.get_selected_RamanMeasurement_summary()))
    
    window.show()
    mappinghub.test_generate_dummy()
    
    sys.exit(app.exec())

def test_dataHub():
    import sys
    from iris.data.measurement_RamanMap import generate_dummy_mappingHub
    
    app = qw.QApplication([])
    window = qw.QMainWindow()
    central_widget = qw.QWidget()
    window.setCentralWidget(central_widget)
    layout = qw.QVBoxLayout()
    central_widget.setLayout(layout)
    
    mappinghub = MeaRMap_Hub()
    datahub = Wdg_DataHub_Mapping(central_widget,mappingHub=mappinghub,autosave=False)
    layout.addWidget(datahub)

    window.show()
    mappinghub.test_generate_dummy()
    
    sys.exit(app.exec())
    
if __name__ == '__main__':
    # test_dataHub()
    test_dataHub_Plus()