import sys
import os

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QThread, QTimer, QObject

from typing import Literal
from uuid import uuid1

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(SCRIPT_DIR))

from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.resources.dataHub_coor_ui import Ui_dataHub_coor

class DataHub_Coor_UiDesign(qw.QWidget, Ui_dataHub_coor):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

class Coor_saveload_worker(QObject):
    
    sig_save_done = Signal() # Emitted when the mapping coordinates are saved.
    sig_load_done = Signal() # Emitted when the mapping coordinates are loaded.
    
    sig_save_error = Signal(str) # Emitted when there is an error in saving the mapping coordinates.
    sig_load_error = Signal(str) # Emitted when there is an error in loading the mapping coordinates.
    
    message_loaded_lastsession = "Previous unfinished mapping coordinates found and has been loaded"
    
    def __init__(self,mappingCoorHub:List_MeaCoor_Hub):
        """
        Initialises the treeview for the mapping coordinates.
        
        Args:
            mappingCoorHub (MappingCoordinatesHub): The hub for the mapping coordinates.
        """
        super().__init__()
        self._mappingCoorHub = mappingCoorHub
    
    @Slot(list)
    def load_MappingCoordinates(self,list_loadpath:list[str]):
        """
        Loads the mapping coordinates from a pickle file and adds them to the list of mapping coordinates.
        
        Args:
            list_loadpath (list[str]|None): The path to load the coordinates from. Defaults to None.
        
        Returns:
            MappingCoordinates: The loaded mapping coordinates.
        """
        for path in list_loadpath:
            try:
                mappingCoor = MeaCoor_mm(loadpath=path)
                self._mappingCoorHub.append(mappingCoor)
            except Exception as e: self.sig_load_error.emit(f"Failed to load mapping coordinates: {e}")
        return
    
    @Slot(list, str, str)
    def save_MappingCoordinates(self,list_coorNames:list[str],dirpath:str,type:Literal['pickle','csv']='pickle'):
        """
        Saves the selected mapping coordinates to a pickle file.
        
        Args:
            list_coorNames (list[str]): The list of mapping coordinate names to save.
            dirpath (str): The directory path to save the coordinates to.
            type (Literal['pickle','csv']): The type of file to save the coordinates to. Defaults to 'pickle'.
        """
        if type=='pickle': extension = '.pkl'
        elif type=='csv': extension = '.csv'
        
        # Save all selected mapping coordinates
        for unitname in list_coorNames:
            mappingCoor = self._mappingCoorHub.get_mappingCoor(unitname)
            if mappingCoor is None: continue
            filename = os.path.join(dirpath,mappingCoor.mappingUnit_name+extension)
            
            if not os.path.exists(dirpath): os.makedirs(dirpath) # Create directory if it does not exist
            
            while True:
                if os.path.exists(filename):
                    # Remove the extension and add a UUID to the filename
                    filename = os.path.splitext(filename)[0]
                    filename += '_'+str(uuid1())
                else: break
                
            if type == 'csv':
                mappingCoor.save_csv(filename)
            elif type == 'pickle':
                mappingCoor.save_pickle(filename)
        return
    

class Wdg_Treeview_MappingCoordinates(qw.QWidget):
    """
    A class to create a treeview for the mapping coordinates.
    """
    sig_load_mappingCoor = Signal(list) # Emitted to load the mapping coordinates from the local disk.
    sig_save_mappingCoor = Signal(list, str, str) # Emitted to save the mapping coordinates to the local disk.
    
    _sig_update_tree = Signal() # Emitted when the treeview needs to be updated.
    
    def __init__(self,parent:qw.QWidget,mappingCoorHub:List_MeaCoor_Hub):
        """
        Initialises the treeview for the mapping coordinates.
        
        Args:
            parent (tk.Tk | tk.Frame): The parent frame or window.
            mappingCoorHub (MappingCoordinatesHub): The hub for the mapping coordinates.
        """
        super().__init__(parent)
        self._mappingCoorHub = mappingCoorHub
        
        # > Top level frame setup <
        self._widget = DataHub_Coor_UiDesign(self)
        self._layout_main = qw.QHBoxLayout(self)
        self._layout_main.addWidget(self._widget)
        wdg = self._widget
        
        self._init_multiCoor_tree()
        
        # > Control widgets <
        self._btn_remove = wdg.btn_remove
        self._btn_rename = wdg.btn_rename
        self._btn_load = wdg.btn_load
        self._btn_save = wdg.btn_save
        
        self._btn_remove.clicked.connect(lambda: self._remove_selected_mapping_coordinate())
        self._btn_rename.clicked.connect(lambda: self.rename_MappingCoordinate())
        self._btn_load.clicked.connect(lambda: self._load_MappingCoordinates())
        self._btn_save.clicked.connect(lambda: self.save_MappingCoordinates(type='csv'))
        
        # > Run parameters setup <
        self._sig_update_tree.connect(self._update_multi_mapping_tree)
        self._mappingCoorHub.add_observer(self._sig_update_tree.emit)
        QTimer.singleShot(0, self._sig_update_tree.emit) # Initial update of the treeview
        
        # > Worker and thread setup <
        self._worker = Coor_saveload_worker(self._mappingCoorHub)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        
        self.destroyed.connect(self._thread.quit)
        self.destroyed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        
        self._thread.start()
        
        self.sig_load_mappingCoor.connect(self._worker.load_MappingCoordinates)
        self.sig_save_mappingCoor.connect(self._worker.save_MappingCoordinates)
        
        self._worker.sig_save_error.connect(lambda msg: qw.QMessageBox.warning(self, 'Error', msg))
        self._worker.sig_load_error.connect(lambda msg: qw.QMessageBox.warning(self, 'Error', msg))
        
        self._worker.sig_save_done.connect(lambda: self._btn_save.setEnabled(True))
        self._worker.sig_load_done.connect(lambda: self._btn_load.setEnabled(True))
        
    def _init_multiCoor_tree(self):
        """
        Initialises the tree view for the multi-coordinate mapping
        """
        self._tree = self._widget.tree_coor
        
        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels(['Index','ROI name','Number of samplings'])
        
    def get_selected_mappingCoor(self, flg_message:bool=False) -> list[MeaCoor_mm]:
        """
        Gets the selected mapping coordinates from the tree view
        
        Args:
            message (bool): If True, a message box will be shown to notify the user of the selected units. Defaults to False.

        Returns:
            list[MappingCoordinates]: The list of selected mapping coordinates
        """
        list_sels = self._tree.selectedItems()
        list_names = [item.text(1) for item in list_sels]
        
        list_sel_mapCoor = self._mappingCoorHub.get_list_MappingCoordinates(list_names)
        
        if flg_message:
            if len(list_sel_mapCoor) == 0:
                qw.QMessageBox.information(self, 'No selection', 'No mapping coordinates have been selected.')
            list_show_names = [mc.mappingUnit_name for mc in list_sel_mapCoor]
            if len(list_sel_mapCoor) > 3:
                list_show_names = [mc.mappingUnit_name for mc in list_sel_mapCoor[:3]] + ['...']
            qw.QMessageBox.information(self, 'Selected mapping coordinates',
                                f'The following mapping coordinates have been selected:\n\n{list_show_names}')
        return list_sel_mapCoor
    
    def _load_MappingCoordinates(self):
        """
        Loads the mapping coordinates from a pickle file and adds them to the list of mapping coordinates.
        
        Args:
            list_loadpath (list[str]|None): The path to load the coordinates from. Defaults to None.
        
        Returns:
            MappingCoordinates: The loaded mapping coordinates.
        """ 
        self._btn_load.setEnabled(False)
        
        list_loadpath, _ = qw.QFileDialog.getOpenFileNames(
            self,'Select the mapping coordinates files to load',
            filter='CSV files (*.csv);;Pickle files (*.pkl)'
        )
        
        if len(list_loadpath) == 0: return None
        
        if not isinstance(list_loadpath, (list,tuple)):
            qw.QMessageBox.warning(self, 'Error',f"Expected list, got {type(list_loadpath)}")
            return
        if not all(isinstance(path, str) for path in list_loadpath):
            qw.QMessageBox.warning(self, 'Error',f"Expected list of str, got {type(list_loadpath)}")
            return
        if not all(os.path.exists(path) for path in list_loadpath):
            qw.QMessageBox.warning(self, 'Error',f"Some files do not exist")
            return
        
        self.sig_load_mappingCoor.emit(list_loadpath)
        return
    
    def save_MappingCoordinates(self,type:Literal['pickle','csv']='csv'):
        """
        Saves the selected mapping coordinates to a pickle file.
        
        Args:
            autosave (bool): If True, suppresses the message box and uses the temporary folder. Defaults to False.
            type (Literal['pickle','csv']): The type of file to save the coordinates to. Defaults to 'pickle'.
        """
        def reset():
            nonlocal self
        
        list_selection = self._tree.selectedItems()
        
        if len(list_selection) == 0:
            qw.QMessageBox.warning(self, 'Error','No mapping coordinates selected')
            return
        
        dirpath = qw.QFileDialog.getExistingDirectory(
            self,'Select the directory to save the mapping coordinates')
        if not os.path.exists(dirpath):
            qw.QMessageBox.warning(self, 'Error',f"Directory {dirpath} does not exist")
            reset()
            return
        
        # Save all selected mapping coordinates
        list_names = [item.text(1) for item in list_selection]
        self.sig_save_mappingCoor.emit(list_names,dirpath,type)
        qw.QMessageBox.information(self, 'Info','Mapping coordinates saved')
        return
    
    def rename_MappingCoordinate(self):
        """
        Renames the selected mapping coordinate in the list.
        """
        list_names = [item.text(1) for item in self._tree.selectedItems()]
        
        if len(list_names) == 0:
            qw.QMessageBox.information(self, 'No selection', 'No mapping coordinates have been selected.')
        elif len(list_names) > 1:
            qw.QMessageBox.information(self, 'Multiple selection', 'Please select only one mapping coordinate to rename at a time.')
            return
        
        init_name = list_names[0]
        while True:
            try:
                new_name,ok = qw.QInputDialog.getText(self, 'Rename mapping coordinate',
                    f'Enter the new name for the mapping coordinate for\n"{init_name}":',
                    text=init_name)
                if not ok: return
                self._mappingCoorHub.rename_mappingCoor(init_name, new_name)
                break
            except ValueError as e:
                qw.QMessageBox.warning(self, 'Error',f"Invalid unit name: {e}")
    
    def _remove_selected_mapping_coordinate(self):
        """
        Removes the selected mapping coordinate from the list
        """
        list_selection = self._tree.selectedItems()
        list_unitname = [item.text(1) for item in list_selection]
        
        for unitname in list_unitname:
            self._mappingCoorHub.remove_mappingCoor(unitname)
    
    @Slot()
    def _update_multi_mapping_tree(self):
        """
        Refreshes the tree view for the multi-coordinate mapping with the data stored in the dictionary
        """
        self._tree.clear()
        
        for i, mappingCoor in enumerate(self._mappingCoorHub):
            qw.QTreeWidgetItem(self._tree, [str(i+1), mappingCoor.mappingUnit_name, str(len(mappingCoor.mapping_coordinates))])
    
    
def test_wdgTreeview_MappingCoordinates():
    app = qw.QApplication([])
    window = qw.QMainWindow()
    window.setWindowTitle('Dummy Treeview Mapping Coordinates')
    mappingCoorHub = List_MeaCoor_Hub()
    treeview = Wdg_Treeview_MappingCoordinates(window, mappingCoorHub)
    window.setCentralWidget(treeview)
    window.show()
    mappingCoorHub.generate_dummy_data(num_units=5, num_coords=10)
    app.exec()
    
if __name__ == '__main__':
    test_wdgTreeview_MappingCoordinates()