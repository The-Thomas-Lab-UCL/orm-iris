import os
from glob import glob

import multiprocessing as mp
import multiprocessing.pool as mpp

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer, QCoreApplication, QMetaType

import queue
from typing import Callable, Literal
from enum import Enum

from copy import deepcopy
from uuid import uuid1

import numpy as np
import math
import random

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.utils.general import *

from iris.gui.motion_video import Wdg_MotionController, Motion_GoToCoor_Worker
from iris.gui.raman import Wdg_SpectrometerController, RamanMeasurement_Worker, AcquisitionParams
from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping
# from iris.gui.dataHub_MeaImg import Frm_DataHub_Image, Frm_DataHub_ImgCal
from iris.gui.hilvl_coorGen import Wdg_Treeview_MappingCoordinates, Wdg_Hilvl_CoorGenerator

from iris.gui.submodules.heatmap_plotter_MeaRMap import Wdg_MappingMeasurement_Plotter
# from iris.gui.submodules.image_tiling import Frm_HiLvlTiling

from iris.data.measurement_RamanMap import MeaRMap_Unit, MeaRMap_Hub, MeaRMap_Handler
from iris.data.measurement_Raman import MeaRaman,MeaRaman_Handler
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.multiprocessing.dataStreamer_StageCam import DataStreamer_StageCam
from iris.multiprocessing.dataStreamer_Raman import DataStreamer_Raman

# from iris.gui.image_calibration.plotter_heatmap_overlay import Frm_HeatmapOverlay

from iris.gui import AppRamanEnum, AppPlotEnum

from iris.resources.hilvl_Raman_ui import Ui_Hilvl_Raman

# QMetaType.registerType(MeaRMap_Hub)  # pyright: ignore[reportArgumentType] ; register custom type for signal-slot mechanism
# QMetaType.registerType(MeaRMap_Unit) # pyright: ignore[reportArgumentType] ; register custom type for signal-slot mechanism

class Hilvl_Raman_Design(Ui_Hilvl_Raman,qw.QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)

class Enum_ScanMthd(Enum):
    """
    Enum for the scan options for the mapping measurement.
    
    Attributes:
        SNAKE (str): Snake scan option
        RASTER (str): Raster scan option
    """
    SNAKE = 'snake'
    RASTER = 'raster'

class Enum_ScanDir(Enum):
    """
    Enum for the scan direction options for the mapping measurement.
    
    Attributes:
        XDIR (str): X-direction scan option
        YDIR (str): Y-direction scan option
    """
    XDIR = 'x-direction'
    YDIR = 'y-direction'

class Hilvl_MeasurementStorer_Worker(QObject):
    
    sig_gotmea = Signal() # Emitted when a measurement is received from the queue
    sig_error = Signal(str)
    sig_finished = Signal()
    
    def __init__(self, mapping_unit:MeaRMap_Unit, queue_measurement:queue.Queue):
        super().__init__()
        self._mapping_unit = mapping_unit
        self._queue_measurement = queue_measurement
        
        self._isrunning = True
        
    @Slot()
    def stop_autosaver(self):
        """
        Stops the measurement autosaver
        """
        self._isrunning = False
    
    def _schedule_next_autosave(self):
        """
        Schedules the next autosave measurement
        """
        try:
            self._autosave_measurement()
        except Exception as e:
            self.sig_error.emit(f'Error in scheduling autosave: {e}')
            print(f'Error in scheduling autosave: {e}')
        finally:
            if self._isrunning or not self._queue_measurement.empty():
                QTimer.singleShot(1, self._schedule_next_autosave)
            else:
                self.sig_finished.emit()
    
    def _autosave_measurement(self):
        """
        A function to automatically grabs the measurement data form the
        measurement queue and stores it in the storage class.
        
        Args:
            mapping_unit (MappingMeasurement_Unit): The mapping unit to store the measurement data
            flg_isrunning (threading.Event): The flag to stop the measurement
            queue_measurement (queue.Queue): The queue to store the measurement data
        """
        # print(f'Autosaver checking queue, size: {self._queue_measurement.qsize()}')
        for _ in range(self._queue_measurement.qsize()):
            try:
                result=self._queue_measurement.get(timeout=0.05)
                self.sig_gotmea.emit()
            except queue.Empty: return
            except Exception as e: self.sig_error.emit(f'Error in autosaver: {e}'); return
            
            try:
                timestamp_mea,coor,measurement = result
                
                timestamp_mea:int
                measurement:MeaRaman
                
                measurement.check_uptodate(autoupdate=True)
                self._mapping_unit.append_ramanmeasurement_data(
                    timestamp=timestamp_mea,
                    coor=coor,
                    measurement=measurement
                )
            except Exception as e: self.sig_error.emit(f'Error in autosaver: {e}')

class Hilvl_MeasurementAcq_Worker(QObject):
    """
    Worker class for performing measurements in a separate thread.
    
    Signals:
        sig_progress_update (int): Signal to update progress percentage
        sig_mea_error (str): Signal emitted when an error occurs during measurement
        sig_mea_cancelled: Signal emitted when measurement is cancelled
        sig_mea_done: Signal emitted when measurement is done
    """
    sig_progress_update = Signal(int)   # Signal to update progress (number of points measured)
    
    sig_mea_done = Signal() # Signal emitted when measurement is done (no differentiation between success, cancelled, or error)
    sig_mea_done_msg = Signal(str)  # Signal emitted when measurement is done with a message
    
    msg_mea_error = "An error occurred during the mapping measurement: "
    msg_mea_cancelled = "Mapping measurement was cancelled by the user"
    msg_mea_finished = "Mapping measurement finished successfully"
    
    err_msg_ismeasuring = "Cannot start a new mapping measurement while another is running."
    
    _sig_stop_autosaver = Signal()
    _sig_gotocor = Signal(tuple, threading.Event)
    _sig_setvelrel = Signal(float)
    _sig_append_queue_mea = Signal(queue.Queue, threading.Event)
    _sig_remove_queue_mea = Signal(queue.Queue)
    _sig_acquire_discrete_mea = Signal(AcquisitionParams)
    _sig_acquire_continuous_mea = Signal(AcquisitionParams)

    def __init__(self, mapping_hub:MeaRMap_Hub):
        """
        Worker to perform the measurement acquisition for Raman imaging. For the slots details, refer to the
        methods in RamanMeasurement_Worker class in raman.py.

        Args:
            mapping_hub (MeaRMap_Hub): The mapping measurement hub to store the measurement data
        """
        super().__init__()
        self.mapping_hub = mapping_hub
        self._isacquiring = True
        
        self._q_mea_acq:queue.Queue = queue.Queue() # Queue for the acquisition to store the measurement data
        
    @Slot()
    def stop_measurement(self):
        """
        Stops the measurement acquisition
        """
        self._isacquiring = False
    
    @Slot(AcquisitionParams, list, queue.Queue)
    def run_scan_discrete(self, params:AcquisitionParams, mapping_coordinates:list, q_mea_out:queue.Queue):
        # Go through all the coordinates
        print('Starting discrete mapping measurement...')
        while not self._q_mea_acq.empty(): self._q_mea_acq.get()   # Clear the acquisition queue
        
        print(params)
        int_time = params['int_time_ms']
        
        # Append the measurement queue to the acquisition controller
        event_append_done = threading.Event()
        self._sig_append_queue_mea.emit(self._q_mea_acq, event_append_done)
        event_append_done.wait()
        self._isacquiring = True
        for coor in mapping_coordinates:
            try:
                if not self._isacquiring:
                    self.sig_mea_done.emit()
                    self.sig_mea_done_msg.emit(self.msg_mea_cancelled)
                    break
                
                # Go to the requested coordinates
                event_finish = threading.Event()
                self._sig_gotocor.emit(
                    (float(coor[0]),float(coor[1]),float(coor[2])),
                    event_finish
                )
                event_finish.wait(10)
                
                # Trigger the acquisition and wait for the return queue to be filled
                self._sig_acquire_discrete_mea.emit(params)
                mea:MeaRaman = self._q_mea_acq.get(timeout=int_time/1000 * 10) # Waits up to 10x the integration time for the measurement
                
                ts = mea.get_latest_timestamp()
                
                # Send the measurement data to the autosaver
                q_mea_out.put((ts,coor,mea))
                
            except Exception as e:
                self.sig_mea_done_msg.emit(self.msg_mea_error + str(e))
                print('Error in run_scan_discrete:',e)
        
        self._sig_remove_queue_mea.emit(self._q_mea_acq)
        self.sig_mea_done.emit()
        self.sig_mea_done_msg.emit(self.msg_mea_finished)
        return
    
    # def run_scan_continuous(self, mapping_coordinates_ends:list,mapping_speed_rel:int):
    #     """
    #     Scans the mapping coordinates continuously based on the given scan coordinates.

    #     Args:
    #         mapping_coordinates_ends (list): List of scan coordinates (end coordinates of each scan lines)
    #         mapping_speed_rel (int): The relative speed to move between the coordinates
    #     """
    # # > Prep for the loop Calculate the number of measurements to be done <
    #     total_coordinates = len(mapping_coordinates_ends)  # Total number of coordinates
    #     total_lines = int(total_coordinates/2)  # Total number of lines to be scanned
        
    # # >>> Perform the mapping measurement <<<
    #     for i, coor in enumerate(mapping_coordinates_ends):
    #         if not self._isacquiring: break   # Stops the measurement immediately when required.
            
    #         if i == 0: func_start_Raman()
    #         elif i%2 == 1:
    #             func_ignore_Raman()
    #             self.motion_controller.set_vel_relative(vel_xy=mapping_speed_rel)   # Set actual speed to move between x-coordinates
    #         else:
    #             func_store_Raman()
    #             self.motion_controller.set_vel_relative(vel_xy=100) # Set actual speed to move between x-coordinates
            
    #         # Wait for the previous batch processing to finish
    #         q_size = queue_measurement.qsize()
    #         flg_restart_Raman = False
    #         if q_size > AppRamanEnum.CONTINUOUS_MEASUREMENT_BUFFER_SIZE.value:
    #             while not queue_measurement.empty():
    #                 print(f'Measurement buffer full:\nAdjust [APP - RAMAN MEASUREMENT CONTROLLER] "continuous_measurement_buffer_size"\nin the config.ini file to adjust the buffer size')
    #                 self.status_update(f'Measurement buffer full: Processing previous measurements {q_size} remaining',bg_colour='yellow')
    #                 time.sleep(0.1)
    #                 if queue_measurement.qsize() < q_size: q_size = queue_measurement.qsize(); continue
                    
    #                 # Restart the continuous measurement
    #                 func_store_Raman()
    #                 func_stop_Raman()
    #                 thread_continuous.join()
    #                 flg_restart_Raman = True
                    
    #                 thread_continuous,queue_measurement_new,func_start_Raman,func_store_Raman,func_ignore_Raman,\
    #                     func_stop_Raman = self.raman_controller.perform_ContinuousMeasurement_trigger()
                        
    #                 self.init_measurement_autosaver(
    #                     mapping_unit=self.measurement_data_2D_unit,
    #                     flg_isrunning=flg_isrunning_autosaver,
    #                     q_measurement_old=queue_measurement,
    #                     q_measurement_new=queue_measurement_new,
    #                     mode='continuous',
    #                     thread_autosaver=thread_autosaver,
    #                 )
    #                 queue_measurement = queue_measurement_new
    #             if flg_restart_Raman: func_start_Raman()
    #             func_ignore_Raman()
                
                
    #         # Go to the requested coordinates
    #         thread_movement = threading.Thread(target=self.motion_controller.go_to_coordinates,kwargs=({
    #             'coor_x_mm': float(coor[0]),
    #             'coor_y_mm': float(coor[1]),
    #             'coor_z_mm': float(coor[2]),
    #             'override_controls': True,
    #             }))
    #         thread_movement.start()
    #         thread_movement.join()
            
    #         # Check if the target is reached and retry the coordinate if not
    #         if not self.motion_controller.isontarget_gotocoor() and not retry_flag:
    #             retry_flag = True
    #             print('Target coordinate not reached, retrying once')
    #             continue
    #         retry_flag = False
            
    #         # Status update
    #         self._dataHub_map.update_tree()
    #         time_elapsed = time.time()-time_start
    #         self.status_update('Performing mapping line: {} of {}. Elapsed time: {} min {} sec. Queue size: {}'\
    #             .format(int((i+1)/2),total_lines,math.floor(time_elapsed/60),math.floor(time_elapsed%60),
    #                     queue_measurement.qsize()),bg_colour='yellow')
            
    #         i+=1
        
    #     # Stop raman frame's continuous measurement
    #     func_store_Raman()
    #     func_stop_Raman()
    #     thread_continuous.join(timeout=1)
        
    #     # Stop the measurement autosaver and wait for it to finish
    #     self.motion_controller.enable_controls()
    #     flg_isrunning_autosaver.clear()   # Stops the continuous measurement
    #     thread_autosaver.join(timeout=1)     # Wait for the autosaver to finish
        
    #     self._frm_coorHub_treeview.delete_offload_mappingCoor(unit_name)  # Deletes the offloaded mapping coordinates
    #     if i != len(mapping_coordinates_ends):
    #         ans = messagebox.askyesno('Save mapping coordinates','The measurement was stopped abruptly.\nDo you want to save the mapping coordinates?')
    #         if ans:
    #             if self._coorHub.search_mappingCoor(unit_name) != None: unit_name += '_remaining_{}'.format(get_timestamp_us_str())
    #             self._coorHub.append(MeaCoor_mm(unit_name,mapping_coordinates_ends[i+1:]))
        
    #     self._flg_meaCancelled = True if i < len(mapping_coordinates_ends) else False
        
    #     return thread_plot

class WorkerPipelineManager(QObject):
    """
    Manages the signal and slot connections between workers
    """
    
    def __init__(
        self,
        hilvlacq_worker:Hilvl_MeasurementAcq_Worker,
        raman_worker: RamanMeasurement_Worker,
        motion_controller: Wdg_MotionController,
        motion_goto_worker:Motion_GoToCoor_Worker,
        ):
        """
        Initialises the signal-slot connections for the controller.
        """
        hilvlacq_worker._sig_gotocor.connect(motion_goto_worker.work)
        hilvlacq_worker._sig_setvelrel.connect(motion_controller.set_vel_relative)
        hilvlacq_worker._sig_append_queue_mea.connect(raman_worker.append_queue_observer_measurement)
        hilvlacq_worker._sig_remove_queue_mea.connect(raman_worker.remove_queue_observer_measurement)
        hilvlacq_worker._sig_acquire_discrete_mea.connect(raman_worker.acquire_single_measurement)
        # hilvlacq_worker._sig_acquire_continuous_mea.connect()

class MappingMethods(Enum):
    DISCRETE = 'discrete'
    CONTINUOUS = 'continuous'

class Wdg_HighLvlController_Raman(qw.QWidget):
    """
    A higher level controller ruling over the motion controller and raman spectroscopy controller.
    
    Houses the:
        1. Plot (auto-update)
        2. Mapping functionalities
        3. Raman spectroscopy save functions
    """
    
    sig_stop_measurement = Signal() # Signal to trigger measurement collection
    sig_run_scan_discrete = Signal(AcquisitionParams,list,queue.Queue)
    
    def __init__(self,
                 parent,
                 motion_controller:Wdg_MotionController,
                 stageHub:DataStreamer_StageCam,
                 raman_controller:Wdg_SpectrometerController,
                 ramanHub:DataStreamer_Raman,
                 dataHub_map:Wdg_DataHub_Mapping,
                #  dataHub_img:Frm_DataHub_Image,
                #  dataHub_imgcal:Frm_DataHub_ImgCal,
                 coorHub:List_MeaCoor_Hub,
                 wdg_coorGen:Wdg_Hilvl_CoorGenerator,
                 processor:mpp.Pool):
        """
        Initialises the higher level controller, which needs access to most (if not all)
        other modules used in the app

        Args:
            parent (qw.QWidget): The parent widget
            motion_controller (Frm_MotionController): The stage and video controller for motion controls
            stageHub (stage_measurement_hub): The stage measurement hub for coordinate retrievals
            raman_controller (Frm_RamanSpectrometerController): The spectrometer controllers
            ramanHub (RamanMeasurementHub): The Raman measurement hub (NOT the DataHub!) for spectra retrievals
            dataHub_map (Frm_DataHub_Mapping): The mapping data hub
            dataHub_img (Frm_DataHub_Image): The image data hub
            dataHub_imgcal (Frm_DataHub_ImgCal): The image calibration data hub
            coorHub (MappingCoordinatesHub): The mapping coordinates hub
            wdg_coorGen (Wdg_Hilvl_CoorGenerator): The coordinate generator GUI
            processor (mpp.Pool): The multiprocessing pool
        """
        super().__init__(parent)
        self.processor = processor
        
    # >>> Measurement hubs setup <<<
        self._stageHub = stageHub
        self._ramanHub = ramanHub
        self._dataHub_map = dataHub_map
        # self._dataHub_img = dataHub_img
        # self._dataHub_imgcal = dataHub_imgcal
        self._coorHub = coorHub
        self._wdg_coorGen = wdg_coorGen
        
    # >>> Controller initialisation <<<
        # To gain access to the other 2 controllers and data save manager
        self.motion_controller = motion_controller
        self.raman_controller = raman_controller
        self.save_manager_dot = MeaRaman_Handler()
        self._mappingHub_Handler = MeaRMap_Handler()
        
    # >>> Main widget/layout setup <<<
        self._widget = Hilvl_Raman_Design(self)
        self._main_layout = qw.QVBoxLayout(self)
        self._main_layout.addWidget(self._widget)
        wdg = self._widget
        
    # >>> Frame setup: top layout <<<
        # Status bar
        self.statbar = qw.QStatusBar(self)
        self.statbar.showMessage('Initialising controls')
        self._main_layout.addWidget(self.statbar)
        
    # >>> Frame setup: Notebook (heatmap and mapping controls) <<<
        # Setup: Heatmap plotter
        self.mdl_plot = Wdg_MappingMeasurement_Plotter(
            self,self._dataHub_map.get_MappingHub())
        wdg.lyt_heatmap_holder.addWidget(self.mdl_plot)
        
        # Setup: Mapping controls
        self._frm_coorHub_treeview = Wdg_Treeview_MappingCoordinates(
            parent=self,mappingCoorHub=self._coorHub)
        wdg.lyt_coorHub_holder.addWidget(self._frm_coorHub_treeview)
        
    # >>> Mapping widgets and parameters setups <<<
        # Parameters
        self._list_sel_mapCoor = []
        self._flg_meaCancelled = False # Flag to indicate if the measurement was cancelled
        
        # >> Mapping options widgets setup <<
        self._btn_discrete = wdg.btn_discrete
        self._btn_discrete.clicked.connect(lambda: self.initiate_mapping(MappingMethods.DISCRETE))
        self._btn_continuous = wdg.btn_continuous
        # self._btn_continuous.clicked.connect(lambda: self.perform_continuousMapping_multi())
        self._btn_stop = wdg.btn_stop
        self._btn_stop.clicked.connect(lambda: self.sig_stop_measurement.emit())
        
    # >>> Mapping scrambler options setup <<<
        self._rb_snake = wdg.rb_snake
        self._rb_raster = wdg.rb_raster
        self._rb_xdir = wdg.rb_xdir
        self._rb_ydir = wdg.rb_ydir

        self._chk_randomise = wdg.chk_randomise
        self._chk_skipover = wdg.chk_skipover
        self._spin_skipover = wdg.spin_skipover
        
    # >>> Overlay heatmap plotter setup <<<
        # Heatmap plotter widgets setup
        # self._frm_heatmapOverlay = Frm_HeatmapOverlay(
        #     master=frm_mappingoverlay,
        #     processor=self.processor,
        #     mappingHub=self._dataHub_map.get_MappingHub(),
        #     imghub_getter=self._dataHub_img.get_ImageMeasurement_Hub,
        #     dataHub_imgcal=self._dataHub_imgcal,
        #     figsize_pxl=AppPlotEnum.IMGCAL_IMG_SIZE.value
        # )
        
        # # Pack the widgets
        # self._frm_heatmapOverlay.grid(row=0, column=0)
        
    # >>> Workers and connections setup <<<
        self._init_workers_connections()
        
    # >>> Controller widgets setup <<<
        self.statbar.showMessage('Ready')
    
    def initialise(self):
        """
        Initialises the controller, loading the last mapping coordinates from the temporary folder.
        """
        pass
        
    def terminate(self):
        """
        Terminates the controller, saving the mapping coordinates to the temporary folder.
        """
        pass
    
    def _init_workers_connections(self):
        """
        Initialises the workers and their connections
        """
        self._thread_hilvlacq = QThread()
        self._worker_hilvlacq = Hilvl_MeasurementAcq_Worker(self._dataHub_map.get_MappingHub())
        self._worker_manager = WorkerPipelineManager(
            hilvlacq_worker=self._worker_hilvlacq,
            raman_worker=self.raman_controller.get_mea_worker(),
            motion_controller=self.motion_controller,
            motion_goto_worker=self.motion_controller.get_goto_worker()
        )
        
        # Connection: Mapping acquisition signals
        self.sig_stop_measurement.connect(self._worker_hilvlacq.stop_measurement)
        self.sig_run_scan_discrete.connect(self._worker_hilvlacq.run_scan_discrete)
        self._worker_hilvlacq.sig_mea_done_msg.connect(self.handle_mapping_completion)
        
        # Connection: Thread and worker management
        self._worker_hilvlacq.moveToThread(self._thread_hilvlacq)
        self.destroyed.connect(self._thread_hilvlacq.quit)
        self.destroyed.connect(self._thread_hilvlacq.deleteLater)
        self.destroyed.connect(self._worker_hilvlacq.deleteLater)
        self._thread_hilvlacq.start()
        
    def _init_autoMeaStorer_worker(self, mapping_unit:MeaRMap_Unit) -> queue.Queue:
        self._q_storage = queue.Queue()
        self._worker_autoMeaStorer = Hilvl_MeasurementStorer_Worker(
            mapping_unit=mapping_unit, queue_measurement=self._q_storage
        )
        self._thread_autoMeaStorer = QThread()
        self._worker_autoMeaStorer.moveToThread(self._thread_autoMeaStorer)
        
        # Signal to start the autosaver
        self._thread_autoMeaStorer.started.connect(self._worker_autoMeaStorer._schedule_next_autosave)
        
        # Signal to stop the autosaver
        self._worker_hilvlacq.sig_mea_done.connect(self._worker_autoMeaStorer.stop_autosaver)
        
        # Signal to delete the thread and worker when finished
        self._worker_autoMeaStorer.sig_finished.connect(self._thread_autoMeaStorer.quit)
        self._worker_autoMeaStorer.sig_finished.connect(self._worker_autoMeaStorer.deleteLater)
        self._worker_autoMeaStorer.sig_finished.connect(self._thread_autoMeaStorer.deleteLater)
        
        self._thread_autoMeaStorer.start()
        return self._q_storage
    
    def _get_scan_options(self) -> tuple[str,str]:
        """
        Retrieves the scan options from the GUI widgets
        
        Returns:
            tuple: (scan_method, scan_direction)
        """
        if self._rb_raster.isChecked():
            scan_method = Enum_ScanMthd.RASTER.value
        elif self._rb_snake.isChecked():
            scan_method = Enum_ScanMthd.SNAKE.value
        else:
            raise ValueError("Invalid scan method selected")
        
        if self._rb_xdir.isChecked():
            scan_direction = Enum_ScanDir.XDIR.value
        elif self._rb_ydir.isChecked():
            scan_direction = Enum_ScanDir.YDIR.value
        else:
            raise ValueError("Invalid scan direction selected")
        
        return (scan_method, scan_direction)
        
    def _generate_metadata_dict(self, map_method:Literal['discrete', 'continuous']) -> dict:
        """
        Generates extra metadata for the mapping measurement
        
        Returns:
            dict: The extra metadata
        """
        controller_ids = self.motion_controller.get_controller_identifiers()
        
        method,dir = self._get_scan_options()
        
        extra_metadata = {
            'camera_id': controller_ids[0],
            'xystage_id': controller_ids[1],
            'zstage_id': controller_ids[2],
            'mapping_method': map_method,
            'scan_method': method,
            'scan_direction': dir,
            'scramble_random': self._widget.chk_randomise.isChecked(),
            'scramble_skipover': self._widget.chk_skipover.isChecked(),
            'scramble_skipover_value': self._widget.spin_skipover.value(),
        }
        return extra_metadata
    
    def _map_check_coor_min_max(self,mapping_coor:list):
        """
        Checks if the coordinates are within the minimum and maximum limits
        
        Args:
            mapping_coor (list): The list of coordinates to be checked, should be in the format of [(x1,y1,z1),(x2,y2,z2),...]
        
        Returns:
            bool: True if the coordinates are within the limits
        """
        pass #TODO: Implement coordinate checking (that every coordinate is within the stage limits)
        return True

    def _convertCoor_byScanOptions(self,mapping_coor:list|None=None,precision:int=4,ends_only:bool=False) -> list|None:
        """
        Converts coordinates to raster scan format.

        Args:
            mapping_coor (list): The list of coordinates to be checked, in the format [(x1, y1, z1), (x2, y2, z2), ...].
            precision (int): The number of decimal places to round the coordinates to. Defaults to 4.
            ends_only (bool): If True, only the ends of the coordinates for every line will be returned. Defaults to False.

        Returns:
            list: The coordinates reordered for the raster scan, or None if the input is None.
        """
        
        mthd,dir = self._get_scan_options()
        
        flg_snake = mthd == Enum_ScanMthd.SNAKE.value
        dir_scan = dir
        
        if not isinstance(mapping_coor, list) or len(mapping_coor) == 0:
            print('No coordinates to convert')
            return None

        mapping_coor = mapping_coor.copy()  # Create a copy to avoid modifying the original list
        
        # Sort the coordinates based on the scan direction
        group_coor = {}
        if dir_scan == Enum_ScanDir.YDIR.value:
            for coor in mapping_coor:
                x = round(coor[0], precision)
                if x not in group_coor:
                    group_coor[x] = []
                group_coor[x].append(coor)
            sorted_x = sorted(group_coor.keys())
            if flg_snake:
                for x in sorted_x[1::2]: group_coor[x].reverse()
            if ends_only: 
                final_coor =    [(x, coor[1], coor[2]) for x in sorted_x for coor in group_coor[x][:1]] + \
                                [(x, coor[1], coor[2]) for x in sorted_x for coor in group_coor[x][-1:]]
                final_coor = sorted(final_coor, key=lambda c: c[0])  # Sort by x-coordinate
            else: final_coor = [(x, coor[1], coor[2]) for x in sorted_x for coor in group_coor[x]]
        elif dir_scan == Enum_ScanDir.XDIR.value:
            for coor in mapping_coor:
                y = round(coor[1], precision)
                if y not in group_coor:
                    group_coor[y] = []
                group_coor[y].append(coor)
            sorted_y = sorted(group_coor.keys())
            if flg_snake:
                for y in sorted_y[1::2]: group_coor[y].reverse()
            if ends_only:
                final_coor =    [(coor[0], y, coor[2]) for y in sorted_y for coor in group_coor[y][:1]] + \
                                [(coor[0], y, coor[2]) for y in sorted_y for coor in group_coor[y][-1:]]
                final_coor = sorted(final_coor, key=lambda c: c[1])  # Sort by y-coordinate
            else: final_coor = [(coor[0], y, coor[2]) for y in sorted_y for coor in group_coor[y]]
        else:
            raise ValueError("Invalid scan direction. Use 'x-direction' or 'y-direction'.")
        return final_coor

    def _calculate_total_XYdistance(self,mapping_coor:list) -> float:
        """
        Calculates the total distance to be travelled for the mapping measurement 
        (only for the XY plane).
        
        Args:
            mapping_coor (list): The list of coordinates to be checked, in the format [(x1, y1, z1), (x2, y2, z2), ...].
        
        Returns:
            float: The total distance to be travelled
        """
        total_distance = 0
        for i in range(len(mapping_coor)-1):
            total_distance += math.sqrt((mapping_coor[i][0]-mapping_coor[i+1][0])**2+
                                        (mapping_coor[i][1]-mapping_coor[i+1][1])**2)
        return total_distance
    
    def _initialise_mapping_parameters(self, mappingHub:MeaRMap_Hub, mapping_coordinates_mm:MeaCoor_mm,
                                       mappingUnit_name:str|None=None) -> tuple[list,float,str]:
        """
        Performs the initial checks prior to the mapping measurement:
            1. Running status check
            2. Coordinates check
            3.1. Mapping speed calculation
            3.2. Mapping speed modifier check
            4. Mapping ID request and check
        
        Args:
            mappingHub (MappingMeasurement_Hub): The mapping hub to store the mapping data
            mapping_coordinates_mm (MappingCoordinates): The mapping coordinate list.
            mappingUnit_name (str|None): The mapping ID. If None, the user will be prompted to enter it. Defaults to None.
            
        Returns:
            tuple: mapping coordinates, mapping speed, mapping ID
            
        NOTE:
            Assumes that the mapping coordinate will be followed as a pathway
        """
        # Running status check
        assert not self.raman_controller.get_running_status(), "Please stop/finish the current measurement before starting"
        assert isinstance(mapping_coordinates_mm, MeaCoor_mm), "Please generate the mapping coordinates first"
        
        list_coor_mm = mapping_coordinates_mm.mapping_coordinates
        
        # Check that the controller can reach the coordinates
        assert self._map_check_coor_min_max(list_coor_mm), "The coordinates are out of range"
        
        # Calculates the required speed
        integration_time_ms = self.raman_controller.get_integration_time_ms()
        assert isinstance(integration_time_ms,(int,float)), "Please enter a valid integration time"
        
        total_scan_time_sec = integration_time_ms * len(list_coor_mm) / 1e3
        total_distance_mm = self._calculate_total_XYdistance(list_coor_mm)
        mapping_speed_mmPerSec = abs(total_distance_mm/total_scan_time_sec)
        
        # Mapping speed modifier check
        assert isinstance(AppRamanEnum.CONTINUOUS_SPEED_MODIFIER.value, (int,float)) and AppRamanEnum.CONTINUOUS_SPEED_MODIFIER.value > 0, \
            f"The speed modifier in the config file must be a positive number. Got {AppRamanEnum.CONTINUOUS_SPEED_MODIFIER.value}"
        
        # Mapping ID request and check
        list_mappingUnit_names = list(mappingHub.get_dict_nameToID().keys())
        if mappingUnit_name is None and mapping_coordinates_mm.mappingUnit_name != '':
            mappingUnit_name = mapping_coordinates_mm.mappingUnit_name
        while mappingUnit_name is None:
            mappingUnit_name = messagebox_request_input('Mapping ID','Enter the ID for the mapping measurement:')
            if mappingUnit_name == '' or not isinstance(mappingUnit_name,str) or mappingUnit_name in list_mappingUnit_names:
                retry = qw.QMessageBox.question(self, 'Error',"Invalid 'mappingUnit name'. The name cannot be empty or already exist. Please try again.",
                                               qw.QMessageBox.Retry | qw.QMessageBox.Cancel) # pyright: ignore[reportAttributeAccessIssue]
                if retry == qw.QMessageBox.Retry: return False # type: ignore
                mappingUnit_name = None
            else: break
        
        return (list_coor_mm, mapping_speed_mmPerSec, mappingUnit_name)
        
        
    def disable_widgets(self):
        """
        Disables the mapping widgets
        """
        widgets = get_all_widgets(self._widget.tab_mappingoptions)
        for widget in widgets:
            if isinstance(widget, (qw.QPushButton, qw.QComboBox, qw.QLineEdit, qw.QSpinBox, qw.QRadioButton, qw.QCheckBox)):
                widget.setEnabled(False)
            
    def enable_widgets(self):
        """
        Enables the mapping widgets
        """
        widgets = get_all_widgets(self._widget.tab_mappingoptions)
        for widget in widgets:
            if isinstance(widget, (qw.QPushButton, qw.QComboBox, qw.QLineEdit, qw.QSpinBox, qw.QRadioButton, qw.QCheckBox)):
                widget.setEnabled(True)
    
    def abort_mapping_run(self):
        """
        Aborts the mapping run and resets the controller status

        Args:
            btn (tk.Button): The button to be reset
            text (str): The text to be reset
            command (Callable): The command to be reset
        """
        self.flg_isrunning_mapping = False
    
    def reset_mapping_widgets(self):
        """
        Resets the mapping widgets after a mapping run

        Args:
            btn (tk.Button): The button to be reset
            text (str): The text to be reset
            command (Callable): The command to be reset
        """
        self.enable_widgets()
        self._btn_stop.setEnabled(False)
        self.statbar.showMessage('Ready')
    
    def _scramble_mapping_coordinates(self, list_mappingCoor:list, mode:Literal['discrete','continuous']) -> list:
        """
        Scrambles the mapping coordinates based on the selected mode.
        
        Args:
            list_mappingCoor (list): The list of coordinates to be scrambled
            mode (str): The mode to scramble the coordinates. Can be 'discrete' or 'continuous'.
            
        Returns:
            list: The scrambled coordinates
            
        Raises:
            ValueError: If the jump value is not a positive integer
            
        NOTE:
            The 'discrete' mode will scramble the coordinates randomly, while the 'continuous' mode will always group the
            start and end coordinates of the lines together.
        """
        list_init = list_mappingCoor.copy()
        if mode == 'continuous':
            # Convert the coordinates to a list of two coordinates (assuming that the coordinates are in pairs)
            list_temp = list_init.copy()
            list_init.clear()
            while len(list_temp)>0:
                list_init.append([list_temp.pop(0),list_temp.pop(0)])
                if len(list_temp)==1:
                    list_init.append([list_temp.pop(0),])
                    
        if self._widget.chk_randomise.isChecked(): random.shuffle(list_init)
        
        def list_remap_jump(data_list, skip_interval):
            """Remaps the list by skipping elements based on the skip_interval"""
            # Determine the actual 'step' size for slicing
            # A skip_interval of 0 means a step of 1 (every element)
            # A skip_interval of 1 means a step of 2 (every other element)
            # A skip_interval of N means a step of N+1 (every N+1th element)
            step = skip_interval + 1
            num_passes = step
            mapped_list = []
            n = len(data_list)
            for offset in range(num_passes):
                current_index = offset
                while current_index < n:
                    mapped_list.append(data_list[current_index])
                    current_index += step
            return mapped_list
        
        if self._widget.chk_skipover.isChecked():
            skip_val = self._spin_skipover.value()
            try:
                skip_val = int(skip_val)
                if skip_val < 0: raise ValueError
            except ValueError:
                raise ValueError("Jump value must be a positive integer")
            
            list_final = list_remap_jump(list_init, skip_val)
        else:
            list_final = list_init
            
        # Convert the coordinates back to the original format
        if mode == 'continuous':
            list_temp = list_final.copy()
            list_final.clear()
            while len(list_temp)>0:
                list_final.extend(list_temp.pop(0))
            
        return list_final
        
    def initiate_mapping(self, method:MappingMethods,
                         mapping_coordinates:MeaCoor_mm|None=None,):
        """
        Performs multiple mapping based on the information stored in the dictionary

        Args:
            method (str): The mapping method to be performed. Can be 'discrete' or 'continuous'.
            mapping_coordinates (MappingCoordinates|None): The mapping coordinates to be performed. If None,
                the selected mapping coordinates from the treeview will be used. Defaults to None.
        """
        # Prepare the list of measurements to be performed
        if mapping_coordinates is None and len(self._list_sel_mapCoor) == 0:
            self._list_sel_mapCoor = self._frm_coorHub_treeview.get_selected_mappingCoor(flg_message=True)
        elif len(self._list_sel_mapCoor) > 0: pass
        else: self._list_sel_mapCoor = [mapping_coordinates,]
        if len(self._list_sel_mapCoor) == 0: return
        
        self.raman_controller.disable_widgets()
        self.motion_controller.disable_widgets()
        self.disable_widgets()
        
        # Store the last mapping method used
        assert method in MappingMethods, "Invalid mapping method. Check the MappingMethods enum."
        self._last_mappingmethod = method
        
        if method == MappingMethods.DISCRETE:
            return self._perform_discreteMapping()
        # elif method == MappingMethods.CONTINUOUS:
        #     return self._perform_continuousMapping()
        else: raise ValueError("Invalid mapping method. Use 'discrete' or 'continuous'.")
        
    @Slot(str)
    def handle_mapping_completion(self, msg:str):
        """
        Handles the completion of a mapping measurement
        """
        self.raman_controller.reset_enable_widgets()
        self.motion_controller.enable_widgets()
        self.enable_widgets()
        self.statbar.showMessage('Mapping measurement complete')
        
        if msg == self._worker_hilvlacq.msg_mea_cancelled:
            self._list_sel_mapCoor.clear()
            qw.QMessageBox.warning(self,'Mapping measurement cancelled','The mapping measurement was cancelled by the user')
            return
        elif msg.startswith(self._worker_hilvlacq.msg_mea_error):
            self._list_sel_mapCoor.clear()
            qw.QMessageBox.critical(self,'Mapping measurement error',msg)
            return
        
        if msg == self._worker_hilvlacq.msg_mea_finished and len(self._list_sel_mapCoor) == 0:
            qw.QMessageBox.information(self,'Mapping measurement complete','The mapping measurement is complete and added to the data hub')
        elif msg == self._worker_hilvlacq.msg_mea_finished:
            self.initiate_mapping(method=self._last_mappingmethod)
        else: raise ValueError("Invalid mapping completion message")

    def _perform_discreteMapping(self):
        """
        Performs discrete mapping based on the mapping coordinates stored in the list
        """
        def reset(): self.enable_widgets()
        mapping_hub = self._dataHub_map.get_MappingHub()
        
        mapCoor = self._list_sel_mapCoor.pop(0)
        if not isinstance(mapCoor, MeaCoor_mm): 
            qw.QMessageBox.critical(self,'Error','Invalid mapping coordinates selected')
            reset()
            return
        mappingUnit_name = mapCoor.mappingUnit_name
        mapping_coordinates = mapCoor
        
        try: result = self._initialise_mapping_parameters(mapping_hub,mapping_coordinates,mappingUnit_name)
        except AssertionError as e: 
            qw.QMessageBox.critical(self,'Error',f"Failed to initialise mapping parameters for '{mappingUnit_name}': {e}")
            reset()
            return
        
        list_coor,_,unit_name = result
        list_coor = self._convertCoor_byScanOptions(list_coor)
        
        try:
            assert list_coor is not None and len(list_coor)>0, "No coordinates to perform mapping"
            self._request_discreteMapping(mapping_coordinates=list_coor, unit_name=unit_name)
        except Exception as e:
            qw.QMessageBox.critical(self,'Error',f"Failed to perform mapping for '{mappingUnit_name}': {e}")
            reset()
            if not self._flg_meaCancelled: self._coorHub.remove_mappingCoor(mappingUnit_name)
        
    def _request_discreteMapping(self, mapping_coordinates:list, unit_name:str):
    # >>> Initialisations <<<
        # Generate the extra metadata for the mapping measurement
        extra_metadata = self._generate_metadata_dict('discrete')
        
        # Initialise the mapping measurement data class
        mea_unit = MeaRMap_Unit(unit_name, extra_metadata=extra_metadata)
        self._dataHub_map.append_MappingUnit(mea_unit)

        # Scramble the mapping coordinates if requested
        mapping_coordinates = self._scramble_mapping_coordinates(mapping_coordinates,'discrete')
        
        # Perform the mapping measurement itself
        q_autosave = self._init_autoMeaStorer_worker(mea_unit)
        self.sig_run_scan_discrete.emit(
            self.raman_controller.generate_acquisition_params(), mapping_coordinates, q_autosave)

    # @thread_assign
    # def perform_continuousMapping(self,mapping_coordinates:MeaCoor_mm):
    #     """
    #     Performs the mapping with the main coordinates stored in the mapping methods
    #     """
    #     def reset():
    #         self.reset_mapping_widgets(
    #             self._btn_perform_continuousMapping_single,
    #             'Perform continuous mapping',
    #             lambda: self.perform_continuousMapping(self._wdg_coorGen.generate_current_mapping_coordinates())
    #         )
    #     # >>> Initial checks <<<
    #     # Disable the mapping widgets
    #     self._disable_mapping_widgets()
        
    #     ## Change the 'Perform continuous mapping' button into a stop button
    #     self.after(10,self._btn_perform_continuousMapping_single.configure(state='active',\
    #         text='STOP',command=lambda:self.abort_mapping_run(self._btn_perform_continuousMapping_single,\
    #         'Perform continuous mapping',lambda: self.perform_continuousMapping(self._wdg_coorGen.generate_current_mapping_coordinates())),bg='red'))
        
    #     # Rest of the checks
    #     mapping_hub = self._dataHub_map.get_MappingHub()
    #     result = self._initialise_mapping_parameters(mappingHub=mapping_hub,mapping_coordinates_mm=mapping_coordinates)
    #     if not result: reset(); return
    #     list_coors, mapping_speed_mmPerSec, unit_name = result
        
    #     try:
    #         self._perform_continuousMapping(
    #             mapping_hub=mapping_hub,
    #             mapping_coordinates=list_coors,
    #             mapping_speed_mmPerSec=mapping_speed_mmPerSec,
    #             unit_name=unit_name
    #         )
    #     except Exception as e:
    #         messagebox.showerror('Error',f"Failed to perform mapping: {e}")
    #         self.status_update('Error in mapping measurement',bg_colour='red')
    #         self._dataHub_map.update_tree()
    #         return
        
    #     messagebox.showinfo('Mapping measurement complete','The mapping measurement is complete and added to the data hub')
    #     reset()
    
    # @thread_assign
    # def perform_continuousMapping_multi(self):
    #     """
    #     Performs multiple continuous mapping based on the information stored in the dictionary
    #     """
    #     def reset():
    #         self.reset_mapping_widgets(self._btn_continuous,'Perform multi-continuous mapping\nof the selected coordinates',self.perform_continuousMapping_multi)
    #     # >>> Initial checks <<<
    #     # Disable the mapping widgets
    #     self._disable_mapping_widgets()
        
    #     ## Change the 'Perform discrete mapping' button into a stop button
    #     self.after(10,self._btn_continuous.configure(state='active',\
    #         text='STOP',command=lambda:self.abort_mapping_run(btn=self._btn_continuous,\
    #         text='Perform multi-continuous mapping\nof the selected coordinates',command=self.perform_continuousMapping_multi),bg='red'))
        
    #     # Check if the raman controller is currently running
    #     self.flg_isrunning_mapping = True
    #     mapping_hub = self._dataHub_map.get_MappingHub()
        
    #     list_sel_mapCoor = self._frm_coorHub_treeview.get_selected_mappingCoor(flg_message=True)
    #     if len(list_sel_mapCoor) == 0: reset(); return
        
    #     while len(list_sel_mapCoor)>0:
    #         mapCoor = list_sel_mapCoor.pop(0)
    #         mappingUnit_name = mapCoor.mappingUnit_name
    #         mapping_coordinates = mapCoor
            
    #         if not self.flg_isrunning_mapping: break
            
    #         result = self._initialise_mapping_parameters(mapping_hub,mapping_coordinates,mappingUnit_name)
    #         if not result: reset(); return
    #         mapping_coordinates, mapping_speed_mmPerSec, unit_name = result
            
    #         try:
    #             self._perform_continuousMapping(
    #                 mapping_hub=mapping_hub,
    #                 mapping_coordinates=mapping_coordinates,
    #                 mapping_speed_mmPerSec=mapping_speed_mmPerSec,
    #                 unit_name=unit_name
    #             )
    #         except Exception as e:
    #             messagebox.showerror('Error',f"Failed to perform mapping: {e}")
    #             self.status_update('Error in mapping measurement',bg_colour='red')
    #             self._dataHub_map.update_tree()
    #             break
            
    #         if not self._flg_meaCancelled: self._coorHub.remove_mappingCoor(mappingUnit_name)
            
    #     messagebox.showinfo('Mapping measurement complete','The mapping measurement is complete and added to the data hub')
    #     reset()
    
    # def _perform_continuousMapping(self, mapping_hub:MeaRMap_Hub,mapping_coordinates:list,
    #                                mapping_speed_mmPerSec:float,unit_name:str):
    #     """
    #     Performs the mapping with the main coordinates stored in the mapping methods.
        
    #     Idea:
    #         1. Retrieve the mapping coordinates and take the ends of each lines
    #         2. Move the stage following these end points
    #         3. As the stage is moving, the Raman controller is continuously measuring the data
    #             (handled by the raman_controller_frame and the raman_measurement_hub)
    #         4. Similarly, the coordinates are stored continuously
    #             (handled by the stage_measurement_hub)
    #         5. Retrieve the Raman measurements and their coordinates, and store them in the mapping_measurement_data class
            
    #     Args:
    #         mapping_hub (MappingMeasurement_Hub): The mapping hub to store the mapping data
    #         mapping_coordinates (list): The list of coordinates to be checked, in the format [(x1, y1, z1), (x2, y2, z2), ...].
    #         mapping_speed_mmPerSec (float): The speed of the mapping in mm/s
    #         unit_name (str): The name for the mapping measurement
    #     """
    #     mapping_speed_rel = self.motion_controller.calculate_vel_relative(vel_xy_mmPerSec=mapping_speed_mmPerSec)
    #     mapping_speed_rel *= AppRamanEnum.CONTINUOUS_SPEED_MODIFIER.value
        
    #     mapping_coordinates_ends = self._convertCoor_byScanOptions(mapping_coordinates,ends_only=True)
        
    # # >>> Initialisations <<<
    #     # Generate the extra metadata for the mapping measurement
    #     extra_metadata = self._generate_metadata_dict('continuous')
        
    #     # Initialise the mapping measurement data class
    #     self.measurement_data_2D_unit = MeaRMap_Unit(unit_name, extra_metadata=extra_metadata)
    #     self._dataHub_map.append_MappingUnit(self.measurement_data_2D_unit)
        
    #     # Scramble the mapping coordinates if requested
    #     mapping_coordinates_ends = self._scramble_mapping_coordinates(mapping_coordinates_ends,'continuous')
        
    #     # Set up a flag to abort the mapping measurement if needed
    #     self.flg_isrunning_mapping = True
        
    #     # Store the initial speed
    #     initial_speed_xy,initial_speed_z = self.motion_controller.get_VelocityParameters()
        
    # # >>> Perform the mapping measurement <<<
    #     thread_plot = self._scan_continuous(mapping_coordinates_ends,mapping_speed_rel)
        
    # # >>> Finalisations <<<
    #     self.status_update('Saving the measurement data',bg_colour='yellow')
    #     # Update the data hub tree view and request to save the data
    #     self._dataHub_map.update_tree()
        
    #     # Reset the speed
    #     self.motion_controller.set_vel_relative(vel_xy=initial_speed_xy,vel_z=initial_speed_z)
        
    # def _scan_continuous(self, mapping_coordinates_ends:list,mapping_speed_rel:int):
    #     """
    #     Scans the mapping coordinates continuously based on the given scan coordinates.

    #     Args:
    #         mapping_coordinates_ends (list): List of scan coordinates (end coordinates of each scan lines)
    #         mapping_speed_rel (int): The relative speed to move between the coordinates
    #     """
    #     # >> Prep the continuous measurement <<
    #     # Prep the raman controller
    #     thread_continuous,queue_measurement,func_start_Raman,func_store_Raman,func_ignore_Raman,\
    #         func_stop_Raman = self.raman_controller.perform_ContinuousMeasurement_trigger()
        
    #     # Prep the threads for movement and measurement
    #     flg_isrunning_autosaver = threading.Event()    # clear to stop the continuous measurement
    #     flg_isrunning_autosaver.set()
        
    # # > Prep for the loop Calculate the number of measurements to be done <
    #     total_coordinates = len(mapping_coordinates_ends)  # Total number of coordinates
    #     total_lines = int(total_coordinates/2)  # Total number of lines to be scanned
    #     self.status_update('Performing mapping line: 1 of {}'.format(total_lines),bg_colour='yellow')
        
    # # > Start the auto-measurement retrieval <
    #     thread_movement = threading.Thread()
    #     thread_plot = threading.Thread()
        
    #     thread_autosaver = threading.Thread(target=self.measurement_autosaver_continuous,kwargs=({
    #         'mapping_unit': self.measurement_data_2D_unit,
    #         'flg_isrunning': flg_isrunning_autosaver,
    #         'q_measurement': queue_measurement
    #         }))
    #     thread_autosaver.start()
    #     unit_name = self.measurement_data_2D_unit.get_unit_name()
    #     thread_offload = self._frm_coorHub_treeview.offload_mappingCoor(unit_name,mapping_coordinates_ends,0)
        
    #     self.motion_controller.video_terminate()
        
    # # >>> Perform the mapping measurement <<<
    #     # self.raman_controller.resume_auto_measurement()
    #     self.flg_isrunning_mapping = True
    #     time_start = time.time()
    #     self.motion_controller.disable_controls()
    #     retry_flag = False
    #     self._flg_meaCancelled = False
    #     i=0
    #     while i < len(mapping_coordinates_ends):
    #         coor = mapping_coordinates_ends[i]
    #         if not self.flg_isrunning_mapping: break   # Stops the measurement immediately when required.
    #         if i%AppRamanEnum.AUTOSAVE_FREQ_CONTINUOUS.value == 0 and i > 0 and not thread_offload.is_alive():
    #             thread_offload = self._frm_coorHub_treeview.offload_mappingCoor(unit_name,mapping_coordinates_ends,i+1)
            
    #         # >> Only perform the continuous measurement for x-rows <<
    #         # (i.e., skipped whenever moving between 1 y-coor to another)
    #         if i == 0: func_start_Raman()
    #         elif i%2 == 1:
    #             func_ignore_Raman()
    #             self.motion_controller.set_vel_relative(vel_xy=mapping_speed_rel)   # Set actual speed to move between x-coordinates
    #         else:
    #             func_store_Raman()
    #             self.motion_controller.set_vel_relative(vel_xy=100) # Set actual speed to move between x-coordinates
            
    #         # Wait for the previous batch processing to finish
    #         q_size = queue_measurement.qsize()
    #         flg_restart_Raman = False
    #         if q_size > AppRamanEnum.CONTINUOUS_MEASUREMENT_BUFFER_SIZE.value:
    #             while not queue_measurement.empty():
    #                 print(f'Measurement buffer full:\nAdjust [APP - RAMAN MEASUREMENT CONTROLLER] "continuous_measurement_buffer_size"\nin the config.ini file to adjust the buffer size')
    #                 self.status_update(f'Measurement buffer full: Processing previous measurements {q_size} remaining',bg_colour='yellow')
    #                 time.sleep(0.1)
    #                 if queue_measurement.qsize() < q_size: q_size = queue_measurement.qsize(); continue
                    
    #                 # Restart the continuous measurement
    #                 func_store_Raman()
    #                 func_stop_Raman()
    #                 thread_continuous.join()
    #                 flg_restart_Raman = True
                    
    #                 thread_continuous,queue_measurement_new,func_start_Raman,func_store_Raman,func_ignore_Raman,\
    #                     func_stop_Raman = self.raman_controller.perform_ContinuousMeasurement_trigger()
                        
    #                 self.init_measurement_autosaver(
    #                     mapping_unit=self.measurement_data_2D_unit,
    #                     flg_isrunning=flg_isrunning_autosaver,
    #                     q_measurement_old=queue_measurement,
    #                     q_measurement_new=queue_measurement_new,
    #                     mode='continuous',
    #                     thread_autosaver=thread_autosaver,
    #                 )
    #                 queue_measurement = queue_measurement_new
    #             if flg_restart_Raman: func_start_Raman()
    #             func_ignore_Raman()
                
                
    #         # Go to the requested coordinates
    #         thread_movement = threading.Thread(target=self.motion_controller.go_to_coordinates,kwargs=({
    #             'coor_x_mm': float(coor[0]),
    #             'coor_y_mm': float(coor[1]),
    #             'coor_z_mm': float(coor[2]),
    #             'override_controls': True,
    #             }))
    #         thread_movement.start()
    #         thread_movement.join()
            
    #         # Check if the target is reached and retry the coordinate if not
    #         if not self.motion_controller.isontarget_gotocoor() and not retry_flag:
    #             retry_flag = True
    #             print('Target coordinate not reached, retrying once')
    #             continue
    #         retry_flag = False
            
    #         # Status update
    #         self._dataHub_map.update_tree()
    #         time_elapsed = time.time()-time_start
    #         self.status_update('Performing mapping line: {} of {}. Elapsed time: {} min {} sec. Queue size: {}'\
    #             .format(int((i+1)/2),total_lines,math.floor(time_elapsed/60),math.floor(time_elapsed%60),
    #                     queue_measurement.qsize()),bg_colour='yellow')
            
    #         i+=1
        
    #     # Stop raman frame's continuous measurement
    #     func_store_Raman()
    #     func_stop_Raman()
    #     thread_continuous.join(timeout=1)
        
    #     # Stop the measurement autosaver and wait for it to finish
    #     self.motion_controller.enable_controls()
    #     flg_isrunning_autosaver.clear()   # Stops the continuous measurement
    #     thread_autosaver.join(timeout=1)     # Wait for the autosaver to finish
        
    #     self._frm_coorHub_treeview.delete_offload_mappingCoor(unit_name)  # Deletes the offloaded mapping coordinates
    #     if i != len(mapping_coordinates_ends):
    #         ans = messagebox.askyesno('Save mapping coordinates','The measurement was stopped abruptly.\nDo you want to save the mapping coordinates?')
    #         if ans:
    #             if self._coorHub.search_mappingCoor(unit_name) != None: unit_name += '_remaining_{}'.format(get_timestamp_us_str())
    #             self._coorHub.append(MeaCoor_mm(unit_name,mapping_coordinates_ends[i+1:]))
        
    #     self._flg_meaCancelled = True if i < len(mapping_coordinates_ends) else False
        
    #     return thread_plot

def test_hilvl_Raman_app(processor:mpp.Pool|None=None):
    """
    Generates a dummy high-level Raman application for testing purposes.
    """
    import sys
    
    from iris.gui.motion_video import generate_dummy_motion_controller
    from iris.gui.raman import generate_dummy_spectrometer_controller
    
    from iris.gui.hilvl_coorGen import generate_dummy_wdg_hilvlCoorGenerator
    
    if processor is None:
        processor = mpp.Pool()
    
    app = qw.QApplication([])
    main_window = qw.QMainWindow()
    wdg_main = qw.QWidget()
    main_window.setCentralWidget(wdg_main)
    layout = qw.QHBoxLayout()
    wdg_main.setLayout(layout)
    
    mappingHub = MeaRMap_Hub()
    dataHub = Wdg_DataHub_Mapping(wdg_main,mappingHub)
    
    wdg_motion_video = generate_dummy_motion_controller(wdg_main)
    datastreamer_motion = wdg_motion_video._stageHub
    wdg_raman = generate_dummy_spectrometer_controller(wdg_main,processor,dataHub)
    wdg_hilvlcoorgen = generate_dummy_wdg_hilvlCoorGenerator(wdg_main,datahub_map=dataHub)
    
    hilvl_raman_app = Wdg_HighLvlController_Raman(
        parent=main_window,
        motion_controller=wdg_motion_video,
        stageHub=datastreamer_motion,
        raman_controller=wdg_raman,
        ramanHub=wdg_raman._ramanHub,
        dataHub_map=dataHub,
        coorHub=wdg_hilvlcoorgen._coorHub,
        wdg_coorGen=wdg_hilvlcoorgen,
        processor=mpp.Pool())
    
    layout.addWidget(wdg_motion_video)
    layout.addWidget(wdg_raman)
    layout.addWidget(hilvl_raman_app)
    layout.addWidget(wdg_hilvlcoorgen)
    layout.addWidget(dataHub)
    
    
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_hilvl_Raman_app()