"""
A hub to manage all the ImageMeasurement_Units stored in an ImageMeasurement_Hub
captured in the session. This is modeled after the sframe_dataHubMapping module.
"""
import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer, QCoreApplication, QMetaType, QMutex, QMutexLocker, QWaitCondition

import sys
import os
from typing import Callable

import queue
import threading
if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.utils.general import *
from iris import LibraryConfigEnum
from iris.data.measurement_image import MeaImg_Unit, MeaImg_Hub, MeaImg_Handler
from iris.data.calibration_objective import ImgMea_Cal, ImgMea_Cal_Hub

from iris.resources.dataHub_image_ui import Ui_dataHub_image
from iris.resources.objectives_ui import Ui_wdg_objectives

class Objective_Design(Ui_wdg_objectives,qw.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)

class DataHub_Image_Design(Ui_dataHub_image,qw.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)

class Wdg_DataHub_ImgCal(qw.QWidget):
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
        super().__init__(*args, **kwargs)
        
        # > Main widget <
        self._widget = Objective_Design(self)
        lyt = qw.QVBoxLayout(self)
        lyt.addWidget(self._widget)
        self.setLayout(lyt)
        wdg = self._widget
        
        # Main attributes
        self._getter_CalHub = getter_ImageCalHub
        self._CalHub = self._getter_CalHub() if self._getter_CalHub is not None else ImgMea_Cal_Hub()
        
        # List of the available calibrations
        self._list_cals = []
        self._empty_cal = ImgMea_Cal()
        self._lastdirpath = None
        
        # Setup the combobox and button
        self._combo_cal = wdg.combo_objective
        self._btn_loaddir = wdg.btn_load
        self._btn_refreshdir = wdg.btn_refresh
        
        self._btn_loaddir.clicked.connect(lambda: self._load_calibration_folder())
        self._btn_refreshdir.clicked.connect(lambda: self._refresh_calibration_folder())
        
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
        cal_id = self._combo_cal.currentText()
        if cal_id: return self._CalHub.get_calibration(cal_id)
        else: return self._empty_cal
        
    def update_combobox(self) -> None:
        """
        Updates the combo box list of values based on the calibrations in the ImageMeasurement_Calibration_Hub.
        """
        list_cals = self._CalHub.get_calibration_ids()
        
        if list_cals == self._list_cals: return # No need to update
        
        self._list_cals = list_cals.copy()
        
        # Add the new itmes
        self._combo_cal.setEditable(False)
        self._combo_cal.clear()
        self._combo_cal.addItems(self._list_cals)
        
        if self._combo_cal.currentText() not in self._list_cals:
            self._combo_cal.setCurrentIndex(0)
        
    def _refresh_calibration_folder(self, supp_msg:bool=False) -> None:
        """
        Refreshes the combobox list by re-scanning the calibration folder.
        
        Args:
            supp_msg (bool): Flag to suppress the success message. Defaults to False.
        """
        if not self._lastdirpath:
            qw.QMessageBox.warning(self, 'Error', 'No previously selected folder.'); return
            
        ori_text = self._btn_refreshdir.text()
        try:
            self._btn_refreshdir.setText('Refreshing...')
            self._btn_refreshdir.setEnabled(False)
            
            self._CalHub.load_calibrations(self._lastdirpath)
            self.update_combobox()
            if not supp_msg:
                qw.QMessageBox.information(self, 'Success', 'Calibration folder refreshed successfully.')
            print(f'Refreshed calibration folder: {self._lastdirpath}')
        except Exception as e:
            if not supp_msg: qw.QMessageBox.critical(self, 'Error', str(e))
            print(f'Error refreshing calibration folder: {e}')
        finally:
            self._btn_refreshdir.setEnabled(True)
            self._btn_refreshdir.setText(ori_text)
        
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
            dirpath = qw.QFileDialog.getExistingDirectory(self, 'Select the objective folder', initdir or '')
                    
        if not os.path.isdir(dirpath) and not supp_msg: qw.QMessageBox.critical(self, 'Error', 'Invalid folder selected.'); return
        
        self._lastdirpath = dirpath
        
        ori_text = self._btn_loaddir.text()
        try:
            self._btn_loaddir.setEnabled(False)
            self._btn_loaddir.setText('Loading...')
            self._CalHub.load_calibrations(dirpath)
            self.update_combobox()
            if not supp_msg: qw.QMessageBox.information(self, 'Success', 'Calibration folder loaded successfully.')
            print(f'Loaded calibration folder: {dirpath}')
        except Exception as e:
            if not supp_msg: qw.QMessageBox.critical(self, 'Error', str(e))
            print(f'Error loading calibration folder: {e}')
        finally:
            self._btn_loaddir.setEnabled(True)
            self._btn_loaddir.setText(ori_text)
        

class Image_SaverLoader_Worker(QObject):
    """
    Worker class to save ImageMeasurement_Hub data in a separate thread.
    """
    finished = Signal(str)
    error = Signal(str)
    
    msg_save_db = 'ImageMeasurementHub saved successfully (.db).'
    msg_load_db = 'ImageMeasurementHub loaded successfully (.db).'
    msg_save_png = 'ImageMeasurementUnit saved successfully as PNG.'
    
    def __init__(self):
        super().__init__()
        
    @Slot(MeaImg_Hub,str,str)
    def save_ImageMeasurementHub(self, hub:MeaImg_Hub, initdir:str, savename:str):
        """
        Save the ImageMeasurement_Hub data to a database file.
        
        Args:
            hub (ImageMeasurement_Hub): ImageMeasurement_Hub object to save
            initdir (str): Directory to save the database file
            savename (str): Name of the database file
        """
        try:
            handler = MeaImg_Handler()
            thread = handler.save_ImageMeasurementHub_database(hub=hub,initdir=initdir,savename=savename)
            thread.join()
            self.finished.emit(self.msg_save_db)
        except Exception as e:
            self.error.emit(str(e))
            
    @Slot(MeaImg_Hub,str)
    def load_ImageMeasurementHub(self, hub:MeaImg_Hub, file_path:str):
        """
        Load the ImageMeasurement_Hub data from the database file.
        
        Args:
            hub (ImageMeasurement_Hub): ImageMeasurement_Hub object to load data into
            file_path (str): Path to the database file
        """
        try:
            hub.reset_ImageMeasurementUnits()
            handler = MeaImg_Handler()
            handler.load_ImageMeasurementHub_database(file_path,hub)
            self.finished.emit(self.msg_load_db)
        except Exception as e:
            self.error.emit(str(e))
            
    @Slot(MeaImg_Unit,str,float)
    def save_ImageMeasurementUnit_png(self, unit:MeaImg_Unit, dirpath:str, resolution:float):
        """
        Save the ImageMeasurement_Unit data as PNG files in the specified directory.
        
        Args:
            unit (ImageMeasurement_Unit): ImageMeasurement_Unit object to save
            dirpath (str): Directory to save the PNG files
            resolution (float): Resolution percentage for the PNG files
        """
        try:
            stitched_img = unit.get_image_all_stitched(low_res=False)[0]
            stitched_img.thumbnail((int(stitched_img.width*resolution/100), int(stitched_img.height*resolution/100)))
            stitched_img.save(os.path.join(dirpath, f'{unit.get_IdName()[1]}.png'))
            self.finished.emit(f'{self.msg_save_png} {unit.get_IdName()[1]}')
        except Exception as e:
            self.error.emit(str(e))

class Wdg_DataHub_Image(qw.QWidget):
    """
    GUI to show all the data being stored in the ImageMeasurement_Hub and ImageMeasurement_Calibration_Hub.
    Modeled after the Frm_DataHub_Mapping class.
    """
    sig_save = Signal(MeaImg_Hub, str, str)
    sig_load = Signal(MeaImg_Hub, str)
    sig_save_png = Signal(MeaImg_Unit, str, float)
    
    def __init__(self, main, getter_ImageHub: Callable[[], MeaImg_Hub]|None=None, **kwargs) -> None:
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
        self._getter_ImageHub = getter_ImageHub
        
    # >>> Top layout setup <<<
        self._widget = DataHub_Image_Design(self)
        lyt = qw.QVBoxLayout(self)
        lyt.addWidget(self._widget)
        self.setLayout(lyt)
        wdg = self._widget
        
    # >>> Hub setups <<<
        self.ImageHub = self._getter_ImageHub() \
            if self._getter_ImageHub is not None else MeaImg_Hub()
            
    # >>> Save parameters setup <<<
        self._sessionid = get_timestamp_us_str()    # Session ID
        self._flg_issaved = True    # Flag to indicate if the data is saved
        
    # >>> Treeview setup <<<
        self._tree = wdg.tree
        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels(['Unit ID', 'Unit Name', '# Pictures', 'Metadata'])
        
    # >>> Other control widgets <<<
        # Widgets to manipulate the entries
        self._btn_save = wdg.btn_save
        self._btn_load = wdg.btn_load
        self._btn_remove = wdg.btn_remove
        self._btn_save_png = wdg.btn_save_png
        
        self._btn_save.clicked.connect(lambda: self.save_ImageMeasurementHub())
        self._btn_load.clicked.connect(lambda: self.load_ImageMeasurementHub())
        self._btn_remove.clicked.connect(lambda: self.remove_selected_ImageMeasurementUnit())
        self._btn_save_png.clicked.connect(lambda: self.export_selected_as_png())
        
        self._txt_btn_save = self._btn_save.text()
        self._txt_btn_load = self._btn_load.text()
        self._txt_btn_remove = self._btn_remove.text()
        self._txt_btn_save_png = self._btn_save_png.text()
        
    # >>> Worker setup <<<
        self._init_workers()
        
    def _init_workers(self):
        """
        Initialize the worker threads for saving and loading ImageMeasurement_Hub data.
        """
        self._thread = QThread()
        self._worker = Image_SaverLoader_Worker()
        self._worker.moveToThread(self._thread)
        
        self.sig_save.connect(self._worker.save_ImageMeasurementHub)
        self.sig_load.connect(self._worker.load_ImageMeasurementHub)
        self.sig_save_png.connect(self._worker.save_ImageMeasurementUnit_png)
        
        self._worker.finished.connect(self.on_worker_finished)
        self._worker.error.connect(lambda msg: qw.QMessageBox.critical(self, 'Error', msg))
        
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._worker.deleteLater)
        
        self._thread.start()
        
    def on_worker_finished(self, msg:str):
        """
        Slot to handle the finished signal from the worker.
        
        Args:
            msg (str): Message from the worker
        """
        if msg == self._worker.msg_save_db:
            self._flg_issaved = True
        elif msg == self._worker.msg_load_db:
            self._flg_issaved = True
            self.update_tree()
        
        qw.QMessageBox.information(self, 'Success', msg)
        
        self.reset_buttons()
        
    def reset_buttons(self):
        """
        Reset the button texts and states to their original values.
        """
        self._btn_save.setEnabled(True)
        self._btn_save.setText(self._txt_btn_save)
        
        self._btn_load.setEnabled(True)
        self._btn_load.setText(self._txt_btn_load)
        
        self._btn_remove.setEnabled(True)
        self._btn_remove.setText(self._txt_btn_remove)
        
        self._btn_save_png.setEnabled(True)
        self._btn_save_png.setText(self._txt_btn_save_png)
        
    def disable_buttons(self):
        """
        Disable all buttons in the frame.
        """
        self._btn_save.setEnabled(False)
        self._btn_load.setEnabled(False)
        self._btn_remove.setEnabled(False)
        self._btn_save_png.setEnabled(False)
        
    def load_ImageMeasurementHub(self) -> None:
        """
        Load the ImageMeasurement_Hub data from the database file.
        """
        self.disable_buttons()
        self._btn_load.setText('Loading...')
        file_path = qw.QFileDialog.getOpenFileName(self, 'Open Image Measurement Hub',
                                                    filter='Database files (*.db)')[0]
        
        if os.path.isfile(file_path) is False:
            qw.QMessageBox.warning(self, 'Error', 'No file selected or file doesn\'t exist.')
            return
        
        self._flg_issaved = True
        self.sig_load.emit(self.ImageHub, file_path)
        
    def save_ImageMeasurementHub(self) -> None:
        """
        Save the ImageMeasurement_Hub data to a database file.
        """
        self.disable_buttons()
        self._btn_save.setText('Saving to .db ...')
        file_path = qw.QFileDialog.getSaveFileName(
            self, 'Save Image Measurement Hub',
            filter='Database files (*.db)'
        )[0]
        
        if not file_path: raise Exception('No file selected.')
        
        initdir = os.path.dirname(file_path)
        savename = os.path.basename(file_path)
        
        self.sig_save.emit(self.ImageHub, initdir, savename)
        
    def export_selected_as_png(self):
        """
        Exports the selected ImageMeasurement_Units as PNG files.
        """
        self.disable_buttons()
        self._btn_save_png.setText('Saving to .png ...')
        
        res = qw.QInputDialog.getDouble(
            self, 'Export Resolution', 'Enter the resolution (percentage) for the PNG export:', 100, 0.1, 100, 1
        )
        if not res[1]: self.reset_buttons(); return
        
        resolution = res[0]
        
        # Prompt for the directory to save the PNG files
        dirpath = qw.QFileDialog.getExistingDirectory(
            self, 'Select the folder to save the PNG files'
        )
        if not os.path.isdir(dirpath):
            qw.QMessageBox.critical(self, 'Error', 'Invalid folder selected.'); self.reset_buttons(); return
        
        tree = self._tree
        selections = tree.selectedItems()
        if len(selections) == 0:
            qw.QMessageBox.critical(self, 'Error', 'No entry selected.'); self.reset_buttons()
            return
        
        for item in selections:
            unit_id = item.text(0)
            unit = self.ImageHub.get_ImageMeasurementUnit(unit_id=unit_id)
            self.sig_save_png.emit(unit, dirpath, resolution)
                
    def append_ImageMeasurementUnit(self, unit:MeaImg_Unit, flg_nameprompt:bool=True):
        """
        Appends the given ImageMeasurement_Unit to the ImageMeasurement_Hub and
        update the treeview

        Args:
            unit (ImageMeasurement_Unit): ImageMeasurement_Unit object
            flg_nameprompt (bool): Flag to prompt the user for the name of the unit. Defaults to True
        """
        try:
            if flg_nameprompt:
                imgname = qw.QInputDialog.getText(
                    self, 'Image Name', 'Enter the name of the image:'
                )[0]
                
                # Validation
                if not imgname:
                    raise ValueError('Image name cannot be empty.')
                if imgname in self.ImageHub.get_list_ImageUnit_names():
                    raise ValueError('Image name already exists in the hub.')
                
                unit.set_name(imgname)
            self.ImageHub.append_ImageMeasurementUnit(unit)
            self._flg_issaved = False
            self.update_tree()
            
        except Exception as e:
            qw.QMessageBox.warning(self, 'Error', str(e))
            retry = qw.QMessageBox.question(
                self, 'Retry', 'Do you want to retry adding the ImageMeasurement_Unit?',
                qw.QMessageBox.Yes | qw.QMessageBox.No # pyright: ignore[reportAttributeAccessIssue] ; QMessageBox.Yes/No exists
            )
            if retry == qw.QMessageBox.Yes: # pyright: ignore[reportAttributeAccessIssue] ; QMessageBox.Yes exists
                self.append_ImageMeasurementUnit(unit, True)
        
    def remove_selected_ImageMeasurementUnit(self):
        """
        Remove the selected ImageMeasurementUnit from the ImageMeasurement_Hub.
        """
        tree = self._tree
        selection = tree.selectedItems()
        if len(selection) == 0:
            qw.QMessageBox.warning(self, 'Error', 'No entry selected.')
            return
        
        for item in selection:
            unit_id = item.text(0)
            self.ImageHub.remove_ImageMeasurementUnit(unit_id)
        
        self._flg_issaved = False
        self.update_tree()
        
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
        tree = self._tree
        tree.clear()
        
        list_id, list_name, list_num_measurements, list_metadata = self.ImageHub.get_summary_units()
        
        for id,name,num,meta in zip(list_id, list_name, list_num_measurements, list_metadata):
            # Add to the treeview
            item = qw.QTreeWidgetItem()
            item.setText(0, str(id))
            item.setText(1, str(name))
            item.setText(2, str(num))
            item.setText(3, str(meta))
            tree.addTopLevelItem(item)
            
    def terminate(self):
        """
        Termination protocol for the Image data hub.
        """
        while not self._flg_issaved:
            flg_save = qw.QMessageBox.question(
                self, 'Save Image Hub',
                'There are unsaved changes to the Image Data Hub. Do you want to save before closing?',
                qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel # pyright: ignore[reportAttributeAccessIssue] ; QMessageBox.Yes/No/Cancel exists
            )
            if flg_save == qw.QMessageBox.Yes: # pyright: ignore[reportAttributeAccessIssue] ; QMessageBox.Yes exists
                self.save_ImageMeasurementHub()
                qw.QMessageBox.information(self, 'Info', 'The program will attempt to save the data in the background.')
            
    def test_generate_dummy(self):
        """
        Generate dummy data for testing purposes.
        """
        self.ImageHub.test_generate_dummy()
        self.update_tree()

def generate_dummy_frmImageHub(parent:qw.QWidget) -> Wdg_DataHub_Image:
    """
    Generate a dummy Frm_DataHub_Image for testing purposes.
    
    Args:
        parent (qw.QWidget): Parent window or frame
    
    Returns:
        Wdg_DataHub_Image: Dummy Wdg_DataHub_Image object
    """
    frm_imgHub = Wdg_DataHub_Image(parent)
    frm_imgHub.test_generate_dummy()
    return frm_imgHub

def generate_dummy_frmImgCalHub(parent:qw.QWidget) -> Wdg_DataHub_ImgCal:
    """
    Generate a dummy Frm_DataHub_ImgCal for testing purposes.
    Dummy calibrations are automatically generated.
    
    Args:
        parent (qw.QWidget): Parent window or frame
    
    Returns:
        Wdg_DataHub_ImgCal: Dummy Wdg_DataHub_ImgCal object
    """
    frm_imgCal = Wdg_DataHub_ImgCal(parent)
    frm_imgCal.get_ImageMeasurement_Calibration_Hub().generate_dummy_calibrations()
    return frm_imgCal

def test_DataHubImage():
    """
    Test the Wdg_DataHub_Image class.
    """
    app = qw.QApplication([])
    window = qw.QMainWindow()
    window.setWindowTitle('Data Hub Image Test')
    wdg = Wdg_DataHub_Image(window)
    window.setCentralWidget(wdg)
    
    wdg.test_generate_dummy()
    
    window.show()
    sys.exit(app.exec())
    
def test_DataHub_ImgCal():
    """
    Test the Wdg_DataHub_ImgCal class.
    """
    app = qw.QApplication([])
    window = qw.QMainWindow()
    window.setWindowTitle('Data Hub Image Calibration Test')
    wdg = Wdg_DataHub_ImgCal(window)
    window.setCentralWidget(wdg)
    
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    # test_DataHubImage()
    test_DataHub_ImgCal()