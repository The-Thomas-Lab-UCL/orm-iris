"""
This program is to control a Raman imaging microscope consisting of an XY stage, Z stage, brightfield camera, and a spectrometer.
"""
if __name__ == "__main__":
    print('>>>>> IRIS: IMPORTING LIBRARIES <<<<<')
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))
    
import sys
import multiprocessing as mp
import multiprocessing.pool as mpp
import time

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QTimer, QThread

from iris.controllers import Controller_Spectrometer, Controller_XY, Controller_Z

from iris import LibraryConfigEnum
from iris.gui import ShortcutsEnum
from iris.controllers import ControllerConfigEnum

from iris.gui.motion_video import Wdg_MotionController
from iris.gui.raman import Wdg_SpectrometerController
from iris.gui.hilvl_Raman import Wdg_HighLvlController_Raman
from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image, Wdg_DataHub_ImgCal
from iris.gui.hilvl_Brightfield import Wdg_HighLvlController_Brightfield
from iris.gui.hilvl_coorGen import Wdg_Hilvl_CoorGenerator, List_MeaCoor_Hub

from iris.gui.shortcut_handler import ShortcutHandler

from iris.data.measurement_coordinates import List_MeaCoor_Hub

from iris.calibration.calibration_generator import Wdg_SpectrometerCalibrationGenerator, MainWindow_SpectrometerCalibrationGenerator

from iris.multiprocessing.basemanager import MyManager
from iris.multiprocessing.dataStreamer_Raman import DataStreamer_Raman,initialise_manager_raman,initialise_proxy_raman
from iris.multiprocessing.dataStreamer_StageCam import DataStreamer_StageCam,initialise_manager_stage,initialise_proxy_stage

from iris.utils.general import *

from iris.main_analyser import main_analyser

# NOTE: controller classes and enums imported lazily inside MainWindow_Controller.__init__
# to avoid importing hardware SDKs / creating OS handles at module import time
# (which breaks multiprocessing spawn on Windows).
from iris.resources.main_controller_ui import Ui_main_controller

class MainWindow_Controller(Ui_main_controller,qw.QMainWindow):
    """
    Import the tkinter app class
    
    Args:
        tk (None): tkinter library
    """
    def __init__(self,
                 processor:mpp.Pool,
                 raman_controller:'Controller_Spectrometer',
                 xy_controller:'Controller_XY',
                 z_controller:'Controller_Z',
                 raman_hub:DataStreamer_Raman,
                 stage_hub:DataStreamer_StageCam):
        
        # Set the app windows name and inherit all the properties
        screenName = 'ORM-IRIS: Open-source Raman microscope controller'
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(screenName)
        
        # > Hub setups
        self._processor = processor
        self._ramanHub = raman_hub
        self._stageHub = stage_hub
        self._coorHub = List_MeaCoor_Hub()
        
        # Data hub setups
        self._dataHub_map = Wdg_DataHub_Mapping(self,autosave=True)
        self._dataHub_img = Wdg_DataHub_Image(self)
        self._dataHub_imgcal = Wdg_DataHub_ImgCal(self)
        
        self.lytDataHubMap.addWidget(self._dataHub_map)
        self.lytDataHubImg.addWidget(self._dataHub_img)
        self.lytObjCalHub.addWidget(self._dataHub_imgcal)
        
        # > Menu bar setup
        self._menubar = self.menubar
        
        # Initialise the app subframes
        self._motion = Wdg_MotionController(
            parent=self,
            xy_controller=xy_controller,
            z_controller=z_controller,
            stageHub=stage_hub,
            getter_imgcal=self._dataHub_imgcal.get_selected_calibration,
            flg_issimulation=ControllerConfigEnum.SIMULATION_MODE.value)
        self.lytMotionVideo.addWidget(self._motion)
        
        self._raman = Wdg_SpectrometerController(
            parent=self,
            processor=self._processor,
            controller=raman_controller,
            ramanHub=raman_hub,
            dataHub=self._dataHub_map)
        self.lytRaman.addWidget(self._raman)
        
        self._hilvl_coorGen = Wdg_Hilvl_CoorGenerator(
            parent=self,
            coorHub=self._coorHub,
            motion_controller=self._motion,
            dataHub_map=self._dataHub_map,
            dataHub_img=self._dataHub_img,
            dataHub_imgcal=self._dataHub_imgcal)
        self.lytCoorGen.addWidget(self._hilvl_coorGen)
        
        self._hilvl_raman = Wdg_HighLvlController_Raman(
            parent=self,
            motion_controller=self._motion,
            stageHub=stage_hub,
            raman_controller=self._raman,
            ramanHub=raman_hub,
            dataHub_map=self._dataHub_map,
            dataHub_img=self._dataHub_img,
            dataHub_imgcal=self._dataHub_imgcal,
            coorHub=self._coorHub,
            wdg_coorGen=self._hilvl_coorGen,
            processor=self._processor)
        self.lytRamanMapping.addWidget(self._hilvl_raman)
        
        self._hilvl_brightfield = Wdg_HighLvlController_Brightfield(
            parent=self,
            processor=self._processor,
            dataHub_map=self._dataHub_map,
            dataHub_img=self._dataHub_img,
            dataHub_imgcal=self._dataHub_imgcal,
            motion_controller=self._motion,
            stageHub=self._stageHub,
            coorHub=self._coorHub)
        self.lytBrightfield.addWidget(self._hilvl_brightfield)
        
    # # >> Set up the data manager <<
    #     if flg_import_extension:
    #         self._extension_intermediary = Ext_DataIntermediary(
    #             raman_controller=raman_controller,
    #             camera_controller=self._stageHub.get_camera_controller(),
    #             xy_controller=xy_controller,
    #             z_controller=z_controller,
    #             frm_motion_controller=self._motion,
    #             frm_raman_controller=self._raman,
    #             frm_highlvl_raman=self._hilvl_raman,
    #             frm_highlvl_brightfield=self._hilvl_brightfield,
    #             frm_datahub_mapping=self._dataHub_map,
    #             frm_datahub_image=self._dataHub_img,
    #             frm_datahub_imgcal=self._dataHub_imgcal,
    #             )
        
    # >> Set up the calibration generator <<
        mw_spectrometerCalibration = MainWindow_SpectrometerCalibrationGenerator(
            pipe_update=self._ramanHub.get_calibrator_pipe()
        )
        self.frm_calibrator = mw_spectrometerCalibration.get_WdgCalibrator()
        
    # >> Set up the analysers <<
    #     self.toplevel_analyser = tk.Toplevel(self)
    #     self.toplevel_analyser.title('IRIS analyser')
    #     self.frm_iris_analyser = main_analyser(self.toplevel_analyser,
    #         processor=self._processor,dataHub=self._dataHub_map)
    #     self.frm_iris_analyser.pack()
        
    #     # Set up a list for top level instances
    #     self._list_analyser_toplevel = []
    #     self._list_analyser_instances = []
        
    # # >> Set up the menu bars on all the main top level windows <<
    #     self.toplevel_analyser.config(menu=self.winfo_toplevel().config('menu')[-1])
        
    #     # Override the close button for the main app to allow proper termination
    #     self.protocol("WM_DELETE_WINDOW",self.terminate)
        
    #     # Override the close button to not destroy the top level
    #     self.toplevel_analyser.protocol("WM_DELETE_WINDOW",self.toplevel_analyser.withdraw)
    #     self.toplevel_analyser.withdraw()
        
    #     # Set up the menu bar
    #     menu_window = tk.Menu(self._menubar,tearoff=0)
    #     menu_window.add_command(label='Show "Main controller"',command=self.deiconify)
    #     menu_window.add_command(label='Show "Main analyser"',command=self.toplevel_analyser.deiconify)
    #     menu_window.add_command(label='Show "Spectrometer calibration"',command=self.toplevel_calibrator.deiconify)
    #     self._menubar.add_cascade(label='Windows',menu=menu_window)
        
    #     menu_analyser = tk.Menu(self._menubar,tearoff=0)
    #     menu_analyser.add_command(label='Show "Main analyser"',command=self.toplevel_analyser.deiconify)
    #     menu_analyser.add_command(label='Create a new [destructible] "analyser"',command=self._set_IRIS_analyser)
    #     self._menubar.add_cascade(label='Analyser',menu=menu_analyser)
        
    # # >> Set up the extensions <<
    #     self._list_extensions_toplevel:list[Extension_TopLevel] = []
        
    #     if flg_import_extension: self._set_extensions()
    #     menu_extensions = tk.Menu(self._menubar,tearoff=0)
    #     for i,ext in enumerate(self._list_extensions_toplevel):
    #         ext:tk.Toplevel
    #         menu_extensions.add_command(label='Show "{}"'.format(ext.title()),command=ext.deiconify)
    #     self._menubar.add_cascade(label='Extensions',menu=menu_extensions)
        
        # self.initialise_after_visible()
        
    # # >> Set up the controllers menubar <<
    #     menu_controllers = tk.Menu(self._menubar,tearoff=0)
    #     menu_controllers.add_command(label='Set camera exposure time',command=self._motion.set_camera_exposure)
    #     menu_controllers.add_command(label='Set the stage timestamp offset [ms]',command=self.set_RamanStage_offset)
    #     self._menubar.add_cascade(label='Controllers',menu=menu_controllers)
        
    # # >> Set up the keybindings <<
    #     self._shortcutHandler = ShortcutHandler()
    #     self._set_keybindings()
        
    # def _set_keybindings(self):
    #     """
    #     Set up the keybindings for the main controller
    #     """
    #     # Set up the keybindings for the motion controller continuous movement
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.XY_UP.value,lambda: self._motion.motion_button_manager('yfwd'))
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.XY_DOWN.value,lambda: self._motion.motion_button_manager('yrev'))
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.XY_RIGHT.value,lambda: self._motion.motion_button_manager('xfwd'))
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.XY_LEFT.value,lambda: self._motion.motion_button_manager('xrev'))
        
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.Z_UP.value,lambda: self._motion.motion_button_manager('zfwd'))
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.Z_DOWN.value,lambda: self._motion.motion_button_manager('zrev'))
        
    #     self._shortcutHandler.set_keybinding_release(ShortcutsEnum.XY_UP.value,lambda: self._motion.motion_button_manager('ystop'))
    #     self._shortcutHandler.set_keybinding_release(ShortcutsEnum.XY_DOWN.value,lambda: self._motion.motion_button_manager('ystop'))
    #     self._shortcutHandler.set_keybinding_release(ShortcutsEnum.XY_RIGHT.value,lambda: self._motion.motion_button_manager('xstop'))
    #     self._shortcutHandler.set_keybinding_release(ShortcutsEnum.XY_LEFT.value,lambda: self._motion.motion_button_manager('xstop'))
        
    #     self._shortcutHandler.set_keybinding_release(ShortcutsEnum.Z_UP.value,lambda: self._motion.motion_button_manager('zstop'))
    #     self._shortcutHandler.set_keybinding_release(ShortcutsEnum.Z_DOWN.value,lambda: self._motion.motion_button_manager('zstop'))
        
    #     # Set up the keybindings for the motion controller jogging
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.XY_JOG_UP.value,lambda: self._motion.move_jog('yfwd'))
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.XY_JOG_DOWN.value,lambda: self._motion.move_jog('yrev'))
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.XY_JOG_RIGHT.value,lambda: self._motion.move_jog('xfwd'))
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.XY_JOG_LEFT.value,lambda: self._motion.move_jog('xrev'))
        
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.Z_JOG_UP.value,lambda: self._motion.move_jog('zfwd'))
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.Z_JOG_DOWN.value,lambda: self._motion.move_jog('zrev'))
        
    #     # Set up the keybindings for the motion controller speed
    #     self._shortcutHandler.set_keybinding_presshold(ShortcutsEnum.XY_SPEED_UP.value,lambda: self._motion.incrase_decrease_speed('xy',True))
    #     self._shortcutHandler.set_keybinding_presshold(ShortcutsEnum.XY_SPEED_DOWN.value,lambda: self._motion.incrase_decrease_speed('xy',False))
        
    #     self._shortcutHandler.set_keybinding_presshold(ShortcutsEnum.Z_SPEED_UP.value,lambda: self._motion.incrase_decrease_speed('z',True))
    #     self._shortcutHandler.set_keybinding_presshold(ShortcutsEnum.Z_SPEED_DOWN.value,lambda: self._motion.incrase_decrease_speed('z',False))
        
    #     self._shortcutHandler.set_keybinding_press(ShortcutsEnum.JOG_MODE_SWITCH.value,self._motion._chkbox_jog_enabled.toggle)
        
    def set_RamanStage_offset(self):
        """
        Set the time offset between the stage and the Raman spectrometer reported timestamps
        """
        current_offset_ms = self._stageHub.get_measurement_offset_ms()
        offset_ms = messagebox_request_input('Stage and Raman Hub offset setup [ms]','Enter the time offset between the stage and the Raman Hub in [ms]',str(current_offset_ms))
        try: offset_ms = float(offset_ms)
        except: qw.QMessageBox.warning(self, 'Error', 'The input must be a number')
        else: self._stageHub.set_measurement_offset_ms(offset_ms); qw.QMessageBox.information(self, 'Success', f'The offset has been set to {offset_ms} ms')
        
    def initialise_after_visible(self):
        """
        PySide equivalent of waiting for visibility before performing setup.
        """
        # If the widget is already visible, proceed immediately.
        if self.isVisible():
            self.initialisations()
            return

        # Otherwise, set up a short timer to check again.
        self._visibility_timer = QTimer(self)
        self._visibility_timer.setSingleShot(True)
        self._visibility_timer.timeout.connect(self._check_and_setup)
        
        # Start the timer with a very small delay (e.g., 50ms)
        self._visibility_timer.start(50) 
        
    @Slot()
    def _check_and_setup(self):
        """
        Checks visibility and executes the final setup if ready.
        """
        if self.isVisible():
            print("Widget is now visible. Proceeding with setup.")
            self.initialisations()
        else:
            self._visibility_timer.start(200)
        
    def initialisations(self):
        """
        Turns on all the auto-updaters once all the widgets are initialised
        """
        print('>>>>> IRIS: PERFORMING FINAL INITIALISATIONS <<<<<')
        self._motion._init_workers()
        self._raman.initialise_spectrometer_n_analyser()
        # [extension.initialise() for extension in self._list_extensions_toplevel]
        
        self._dataHub_imgcal._load_calibration_folder(dirpath=LibraryConfigEnum.OBJECTIVE_CALIBRATION_DIR.value,supp_msg=True)
        
        self._hilvl_coorGen.initialise()
        self._hilvl_raman.initialise()
        print('>>>>> IRIS: INITIALISATIONS COMPLETE <<<<<')
        
    # def _set_extensions(self):
    #     """
    #     Add the extensions to the main controller
    #     """
    #     # > Optics calibration extension
    #     optics_calibration_extension = Ext_OpticsCalibrationAid(
    #         master=self,
    #         intermediary=self._extension_intermediary)
        
    #     self._list_extensions_toplevel.append(optics_calibration_extension)
        
    #     for ext in self._list_extensions_toplevel:
    #         ext:Extension_TopLevel
    #         ext.initialise()
    #         ext.withdraw()
            
    #         # Override the close button for the extension to minimise
    #         ext.protocol("WM_DELETE_WINDOW",ext.withdraw)
        
    # def _set_IRIS_analyser(self):
    #     """
    #     Creates more IRIS analyser instances as new top level windows
    #     """
    #     number_analyser = len(self._list_analyser_toplevel)
    #     toplevel_analyser = tk.Toplevel(self)
    #     toplevel_analyser.title('[destructible] IRIS analyser {}'.format(number_analyser+1))
    #     toplevel_analyser.config(menu=self.winfo_toplevel().config('menu')[-1])
        
    #     iris_analyser = main_analyser(toplevel_analyser,processor=self._processor)
    #     iris_analyser.pack()
        
    #     self._list_analyser_toplevel.append(toplevel_analyser)
    #     self._list_analyser_instances.append(iris_analyser)
        
    def terminate(self):
        print('\n>>>>>>>>>> Terminating the program <<<<<<<<<<')
        try: self._dataHub_map.terminate()
        except Exception as e: print('Error in closing the data hub:\n{}'.format(e))
        
        try: self._dataHub_img.terminate()
        except Exception as e: print('Error in closing the data hub:\n{}'.format(e))
        
        try: self._hilvl_coorGen.terminate()
        except Exception as e: print('Error in closing the coordinate hub:\n{}'.format(e))
        
        try: self._hilvl_raman.terminate()
        except Exception as e: print('Error in closing the high level controller:\n{}'.format(e))
        
        # try: [toplevel_extension.withdraw() for toplevel_extension in self._list_extensions_toplevel if isinstance(toplevel_extension,tk.Toplevel)]
        # except Exception as e: print('Error in closing the extensions:\n{}'.format(e))
        
        # try: [toplevel_extension.terminate() for toplevel_extension in self._list_extensions_toplevel if isinstance(toplevel_extension,Extension_TopLevel)]
        # except Exception as e: print('Error in closing the extensions:\n{}'.format(e))
        
        # try: self.toplevel_calibrator.withdraw()
        # except Exception as e: print('Error in closing the calibrator:\n{}'.format(e))
        
        # try: self.toplevel_analyser.withdraw()
        # except Exception as e: print('Error in closing the analyser:\n{}'.format(e))
        
        # try: [toplevel_analyser.withdraw() for toplevel_analyser in self._list_analyser_toplevel if isinstance(toplevel_analyser,tk.Toplevel)]
        # except Exception as e: print('Error in closing the analyser windows:\n{}'.format(e))
        
        # try: self.withdraw()
        # except Exception as e: print('Error in closing the main controller:\n{}'.format(e))
        
        try: self._raman.terminate()
        except Exception as e: print('Error in closing the spectrometer controller:\n{}'.format(e))
        
        try: self._motion.terminate()
        except Exception as e: print('Error in closing the motion controller:\n{}'.format(e))
                
        try:
            print('Terminating the motion controller connections')
            self._stageHub.terminate()  # Terminates all continuous measurement and processes
            self._stageHub.join(3)       # Waits for the processes to be terminated
        except Exception as e: print('Error in closing the motion controller:\n{}'.format(e))
        
        try:
            print('Terminating the spectrometer controller connection')
            self._ramanHub.terminate()
            self._ramanHub.join(3)       # Waits for the processes to be terminated
        except Exception as e: print('Error in closing the spectrometer controller:\n{}'.format(e))
        
        
        # try: self.toplevel_analyser.destroy()
        # except Exception as e: print('Error in closing the analyser:\n{}'.format(e))
        
        print('Terminating the processes')
        self._processor.terminate()
        self.destroy()
        
        # Force close all the threads in this session
        print('---------- PROGRAM TERMINATED SUCCESSFULLY ----------')
        os._exit(0)

if __name__ == '__main__':
    print('>>>>> IRIS: INITIATING THE CONTROLLERS AND THE APP <<<<<')
    # Create the Qt application first (ensures QApplication exists in main thread)
    app = qw.QApplication([])
    
    # Now start manager / processes (avoid creating Qt objects in child processes)
    base_manager = MyManager()
    initialise_manager_raman(base_manager)
    initialise_manager_stage(base_manager)
    base_manager.start()
    ramanControllerProxy,ramanDictProxy=initialise_proxy_raman(base_manager)
    xyControllerProxy,zControllerProxy,camControllerProxy,stage_namespace=initialise_proxy_stage(base_manager)
    ramanHub = DataStreamer_Raman(ramanControllerProxy,ramanDictProxy)
    stageHub = DataStreamer_StageCam(xyControllerProxy,zControllerProxy,camControllerProxy,stage_namespace)
    ramanHub.start()
    stageHub.start()
    processor = mp.Pool()
    
    time.sleep(5)  # Allow some time for processes to start properly
    
    mainWindow_Controller = MainWindow_Controller(
        processor=processor,
        raman_controller=ramanControllerProxy,
        xy_controller=xyControllerProxy,
        z_controller=zControllerProxy,
        raman_hub=ramanHub,
        stage_hub=stageHub)
    mainWindow_Controller.show()
    app.exec()
    base_manager.shutdown()