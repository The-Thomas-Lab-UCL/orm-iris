import os

import multiprocessing.pool as mpp

import PySide6.QtWidgets as qw
import PySide6.QtCore as qc
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer

import queue
from enum import Enum

import math
import random

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

import threading
import time
from iris.utils.general import messagebox_request_input, get_all_widgets

from iris.gui.motion_video import Wdg_MotionController, Motion_GoToCoor_Worker
from iris.gui.raman import Wdg_SpectrometerController, RamanMeasurement_Worker, AcquisitionParams, Enum_ContinuousMeasurementTrigger as EnumTrig, Syncer_Raman
from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping
from iris.gui.dataHub_MeaImg import Wdg_DataHub_Image, Wdg_DataHub_ImgCal
from iris.gui.hilvl_coorGen import Wdg_Hilvl_CoorGenerator
from iris.gui.submodules.mappingCoordinatesTreeview import Wdg_Treeview_MappingCoordinates

from iris.gui.submodules.heatmap_plotter_MeaRMap import Wdg_MappingMeasurement_Plotter

from iris.data.measurement_RamanMap import MeaRMap_Unit, MeaRMap_Hub, MeaRMap_Handler
from iris.data.measurement_Raman import MeaRaman,MeaRaman_Handler
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.multiprocessing.dataStreamer_StageCam import DataStreamer_StageCam
from iris.multiprocessing.dataStreamer_Raman import DataStreamer_Raman

from iris.gui import AppRamanEnum

from iris.resources.hilvl_Raman_ui import Ui_Hilvl_Raman

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
    sig_finished_relay_msg = Signal(str)    # To relay finished messages once the imaging and the saving are both done. The message is obtained from the acquisition worker.
    
    def __init__(self, datastreamer_stage:DataStreamer_StageCam):
        super().__init__()
        self._ds_stage = datastreamer_stage
        self._isrunning = True
        
    @Slot(MeaRMap_Unit, queue.Queue)
    def set_save_params(
        self,
        mapping_unit:MeaRMap_Unit,
        queue_measurement:queue.Queue[MeaRaman]):
        """
        Sets the parameters for the autosaver
        
        Args:
            mapping_unit (MeaRMap_Unit): The mapping unit to store the measurement data
            queue_measurement (queue.Queue): The queue to store the measurement data
        """
        self._mapping_unit = mapping_unit
        self._queue_measurement = queue_measurement
        
    @Slot()
    def start_autosaver(self):
        """
        Starts the measurement autosaver
        """
        self._isrunning = True
        self._schedule_next_autosave()
        
    @Slot()
    def stop_autosaver(self):
        """
        Stops the measurement autosaver
        """
        self._isrunning = False
    
    @Slot()
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
                print('Autosaver finished all measurements.')
                self.sig_finished.emit()
    
    @Slot()
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
                result:MeaRaman|tuple[MeaRaman,tuple]=self._queue_measurement.get(timeout=0.05)
                self.sig_gotmea.emit()
            except queue.Empty:
                return
            except Exception as e:
                self.sig_error.emit(f'Error in autosaver: {e}')
                return
            
            try:
                if isinstance(result,MeaRaman):
                    mea = result
                    # mea = mea.copy()
                    ts = mea.get_latest_timestamp()
                    coor = self._ds_stage.get_coordinates_interpolate(ts)
                else:
                    mea, coor = result
                    # mea = mea.copy()
                    ts = mea.get_latest_timestamp()
                assert coor is not None, 'No stage coordinates found for the measurement timestamp'
                
                mea.check_uptodate(autoupdate=True)
                self._mapping_unit.append_ramanmeasurement_data(
                    timestamp=ts,
                    coor=coor,
                    measurement=mea
                )
            except Exception as e:
                self.sig_error.emit(f'Error in autosaver: {e}')
            
    @Slot(str)
    def relay_finished_message(self, msg:str):
        """
        Relays the finished message when the autosaver is done

        Args:
            msg (str): The message to relay
        """
        if not self._isrunning and self._queue_measurement.empty():
            self.sig_finished_relay_msg.emit(msg)
        else:
            QTimer.singleShot(100, lambda: self.relay_finished_message(msg))

class Hilvl_MeasurementAcq_Worker(QObject):
    """
    Worker class for performing measurements in a separate thread.
    
    Signals:
        sig_progress_update (int): Signal to update progress percentage
        sig_mea_error (str): Signal emitted when an error occurs during measurement
        sig_mea_cancelled: Signal emitted when measurement is cancelled
        sig_mea_done: Signal emitted when measurement is done
    """
    sig_progress_update_str = Signal(str)  # Signal to update progress (string message)
    
    sig_error_during_mea = Signal(str)  # Signal emitted when an error occurs during measurement
    sig_mea_done = Signal() # Signal emitted when measurement is done (no differentiation between success, cancelled, or error)
    sig_mea_done_msg = Signal(str)  # Signal emitted when measurement is done with a message
    
    msg_mea_error = "An error occurred during the mapping measurement: "
    msg_mea_cancelled = "Mapping measurement was cancelled by the user"
    msg_mea_finished = "Mapping measurement finished successfully"
    
    err_msg_ismeasuring = "Cannot start a new mapping measurement while another is running."
    
    _sig_stop_autosaver = Signal()
    _sig_gotocor = Signal(tuple, threading.Event)
    _sig_setvelrel = Signal(float, float, threading.Event)
    _sig_acquire_discrete_mea = Signal(AcquisitionParams, queue.Queue)
    _sig_acquire_continuous_mea = Signal(AcquisitionParams, queue.Queue, queue.Queue)
    _sig_acquire_list_coors = Signal(list, threading.Event)

    def __init__(self, mapping_hub:MeaRMap_Hub, syncer_raman:Syncer_Raman, event_isacquiring:threading.Event):
        """
        Worker to perform the measurement acquisition for Raman imaging. For the slots details, refer to the
        methods in RamanMeasurement_Worker class in raman.py.

        Args:
            mapping_hub (MeaRMap_Hub): The mapping measurement hub to store the measurement data
            syncer_raman (Syncer_Raman): The synchronization object for Raman measurements
            event_isacquiring (threading.Event): The event flag to indicate if a measurement is ongoing
        """
        super().__init__()
        self.mapping_hub = mapping_hub
        self._syncer = syncer_raman
        self._event_isacquiring = event_isacquiring
    
    def _calculate_time_remaining(self, points_done:int, total_points:int, time_elapsed:float) -> str:
        """
        Calculates the estimated time remaining for the measurement.

        Args:
            points_done (int): The number of points already measured
            total_points (int): The total number of points to be measured
            time_elapsed (float): The time elapsed since the start of the measurement in seconds
            
        Returns:
            str: The estimated time remaining (auto converted to hours, minutes, seconds)
        """
        if points_done == 0:
            return "Waiting for first point..."
        time_per_point = time_elapsed / points_done
        points_remaining = total_points - points_done
        time_remaining = time_per_point * points_remaining
        return self._convert_time_to_hms(time_remaining)
        
    def _convert_time_to_hms(self, time_remaining:float) -> str:
        """
        Converts time in seconds to a string in hours, minutes, and seconds.
        
        Args:
            time_remaining (float): The time remaining in seconds
        
        Returns:
            str: The time remaining in "Xh Ym Zs" format
        """
        hours = int(time_remaining // 3600)
        minutes = int((time_remaining % 3600) // 60)
        seconds = int(time_remaining % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    @Slot(AcquisitionParams, list, queue.Queue)
    def run_scan_discrete(
        self,
        params:AcquisitionParams,
        mapping_coordinates:list,
        q_mea_out:queue.Queue[tuple[MeaRaman,tuple]]):
        print("Starting discrete mapping measurement...")
        
        q_mea = queue.Queue()
        int_time = params['int_time_ms']
        accumulation = params['accumulation']
        
        time_start = time.time()
        total_points = len(mapping_coordinates)
        self._event_isacquiring.set()
        for i, coor in enumerate(mapping_coordinates):
            try:
                # time1 = time.time()
                if not self._event_isacquiring.is_set():
                    self.emit_finish_signals(self.msg_mea_cancelled)
                    break
                
                # Go to the requested coordinates
                event_finish = threading.Event()
                # print('\nMoving to coordinates:',coor)
                # print('Emitting _sig_gotocor signal...')
                self._sig_gotocor.emit(
                    (float(coor[0]),float(coor[1]),float(coor[2])),
                    event_finish
                )
                # print('Waiting for movement to complete...')
                event_finish.wait(10)
                # time2 = time.time()
                
                if not event_finish.is_set(): raise TimeoutError('Failed to reach the target coordinate. Movement to coordinates timed out.')
                # print('Movement wait finished. Event set:', event_finish.is_set())
                
                # Trigger the acquisition and wait for the return queue to be filled
                # print('Emitting _sig_acquire_discrete_mea signal...')
                self._sig_acquire_discrete_mea.emit(params,q_mea)
                
                # print('Waiting for measurement to be acquired...')
                mea:MeaRaman = q_mea.get(timeout=accumulation * int_time/1000 * 10) # Waits up to 10x the integration time for the measurement
                
                if not isinstance(mea,MeaRaman): raise TypeError('Invalid measurement data received from acquisition queue.')
                
                # Send the measurement data to the autosaver
                q_mea_out.put((mea,coor))
                # time3 = time.time()
                # print('Measurement acquired and sent to autosaver.')
                # print(f'Point {i+1}/{total_points} done. Move time: {(time2-time1)*1e3:.0f} ms, Measurement time: {(time3-time2)*1e3:.0f} ms. Total time: {(time3-time1)*1e3:.0f} ms.')
                
            except queue.Empty:
                self.sig_error_during_mea.emit(self.msg_mea_error + 'Measurement acquisition timed out.')
                print('Error in run_scan_discrete: Measurement acquisition timed out.')
                
            except Exception as e:
                self.sig_error_during_mea.emit(self.msg_mea_error + str(e))
                print('Error in run_scan_discrete:',e)
                
            finally:
                # Update progress
                points_done = i + 1
                time_elapsed = time.time() - time_start
                time_remaining_str = self._calculate_time_remaining(points_done, total_points, time_elapsed)
                progress_msg = f'Measured {points_done}/{total_points} points. Remaining: {time_remaining_str}. Elapsed: {self._convert_time_to_hms(time_elapsed)}.'
                self.sig_progress_update_str.emit(progress_msg)
        
        self._event_isacquiring.clear()
        self.emit_finish_signals(self.msg_mea_finished)
        return

    @Slot(AcquisitionParams, list, float, queue.Queue)
    def run_scan_continuous(
        self,
        params:AcquisitionParams,
        mapping_coordinates_ends:list,
        mapping_speed_rel:float,
        q_mea_out:queue.Queue):
        """
        Scans the mapping coordinates continuously based on the given scan coordinates.

        Args:
            params (AcquisitionParams): The acquisition parameters for the measurement
            mapping_coordinates_ends (list): List of scan coordinates (end coordinates of each scan lines)
            mapping_speed_rel (int): The relative speed to move between the coordinates
            q_mea_out (queue.Queue): The queue to store the measurement data
        """
        print("Starting continuous mapping measurement...")
        # Prepare the events to synchronise the movement and measurement
        event_finish_setvel = threading.Event()
        event_finish_goto = threading.Event()
        
        # Prepare the measurement queue to save the measurement data into
        # the mapping unit (set up in the main thread)
        q_trig = queue.Queue()  # Queue to send the measurement trigger commands
        self._sig_acquire_continuous_mea.emit(params, q_trig, q_mea_out)
        
        print('Acquisition started, moving to start position...')
        # >>> Perform the mapping measurement <<<
        time_start = time.time()
        total_points = len(mapping_coordinates_ends)
        self._event_isacquiring.set()
        for i, coor in enumerate(mapping_coordinates_ends):
            try:
                flg_continue = self._execute_scan_continuous_step(mapping_speed_rel, q_mea_out, event_finish_setvel, event_finish_goto, q_trig, i, coor)
                if not flg_continue: break
            except Exception as e:
                self.sig_error_during_mea.emit(self.msg_mea_error + str(e))
                print('Error in run_scan_continuous:',e)
            finally:
                # Update progress
                points_done = i + 1
                time_elapsed = time.time() - time_start
                time_remaining_str = self._calculate_time_remaining(points_done, total_points, time_elapsed)
                progress_msg = f'Measured {points_done}/{total_points} lines. Estimated time remaining: {time_remaining_str}. Elapsed time: {self._convert_time_to_hms(time_elapsed)}.'
                self.sig_progress_update_str.emit(progress_msg)
        
        # Stop raman frame's continuous measurement and store the final measurements
        q_trig.put(EnumTrig.STORE)
        q_trig.put(EnumTrig.FINISH)
        
        self._event_isacquiring.clear()
        self.emit_finish_signals(self.msg_mea_finished)

    def _execute_scan_continuous_step(
        self,
        mapping_speed_rel:float,
        q_mea_out:queue.Queue,
        event_finish_setvel:threading.Event,
        event_finish_goto:threading.Event,
        q_trig:queue.Queue,
        coor_idx:int,
        coor:tuple,
        ) -> bool:
        """
        Executes a single step in the continuous mapping measurement.

        Args:
            mapping_speed_rel (float): The relative speed to move between the coordinates
            q_mea_out (queue.Queue): The queue to store the measurement data
            event_finish_setvel (threading.Event): Event to signal the completion of setting velocity
            event_finish_goto (threading.Event): Event to signal the completion of going to coordinates
            q_trig (queue.Queue): Queue to send the measurement trigger commands
            i (int): The index of the current coordinate
            coor (tuple): The target coordinate
            
        Returns:
            bool: True if the step was executed successfully, False if the measurement was cancelled
        """
        
        if not self._event_isacquiring.is_set():
            self.emit_finish_signals(self.msg_mea_cancelled)
            return False
            
        # Go to the requested coordinates
        # time1 = time.time()
        # print(f'\nMoving to coordinates: {coor} (Index {coor_idx}), distance from last: {math.dist(self._last_coor, coor) if hasattr(self, "_last_coor") else "N/A"}')
        self._last_coor = coor
        event_finish_goto.clear()
        self._sig_gotocor.emit(
                    (float(coor[0]),float(coor[1]),float(coor[2])),
                    event_finish_goto
                )
        event_finish_goto.wait()
        # time2 = time.time()
            
        event_finish_setvel.clear()
        if coor_idx == 0:
            # print('Moving to start position...')
            self._syncer.set_notready()
            q_trig.put(EnumTrig.START)
            event_finish_setvel.set()
            # print('Reached start position.')
        elif coor_idx%2 == 0:
            # print('Moving to next line end position (odd line)...')
            self._syncer.set_notready()
            q_trig.put(EnumTrig.IGNORE)
            self._sig_setvelrel.emit(mapping_speed_rel, -1.0, event_finish_setvel)   # Set actual speed to move between x-coordinates
            # print('Reached line end position.')
        else:
            # print('Moving to next line end position (even line)...')
            self._syncer.set_notready()
            q_trig.put(EnumTrig.STORE)
            self._sig_setvelrel.emit(100.0, -1.0, event_finish_setvel) # Set max speed to move between each scan line
            # print('Reached line end position.')
        self._syncer.wait_ready()
        event_finish_setvel.wait()
        # time3 = time.time()
                
                # Check the autosave queue size and wait if necessary to prevent overflow
        q_size = q_mea_out.qsize()
        if q_size > AppRamanEnum.CONTINUOUS_MEASUREMENT_BUFFER_SIZE.value:
            while not q_mea_out.empty():
                print(f'Measurement buffer full:\nAdjust [APP - RAMAN MEASUREMENT CONTROLLER] "continuous_measurement_buffer_size"\nin the config.ini file to adjust the buffer size')
                time.sleep(0.1)
                print(f'Waiting for the measurement buffer to clear... Current size: {q_mea_out.qsize()}')
            q_trig.put(EnumTrig.IGNORE)
            
        # time4 = time.time()
        
        # print(f'Point {coor_idx+1} done. Move time: {(time2-time1)*1e3:.0f} ms, SetVel time: {(time3-time2)*1e3:.0f} ms, Sync time: {(time4-time3)*1e3:.0f} ms. Total time: {(time4-time1)*1e3:.0f} ms.')
        return True
        
    @Slot(str)
    def emit_finish_signals(self,msg:str):
        """
        Emits the measurement done signal with a message.

        Args:
            msg (str): The message to emit with the signal
        """
        self.sig_mea_done.emit()
        self.sig_mea_done_msg.emit(msg)

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
        parent=None
        ):
        """
        Initialises the signal-slot connections for the controller.
        """
        super().__init__(parent)
        
        # Store references to prevent garbage collection
        self._hilvlacq_worker = hilvlacq_worker
        self._raman_worker = raman_worker
        self._motion_controller = motion_controller
        self._motion_goto_worker = motion_goto_worker
        
        # Use Qt.QueuedConnection to ensure proper cross-thread signal delivery
        hilvlacq_worker._sig_gotocor.connect(
            motion_goto_worker.work, 
            qc.Qt.ConnectionType.QueuedConnection
        )
        hilvlacq_worker._sig_setvelrel.connect(
            motion_controller.set_vel_relative,
            qc.Qt.ConnectionType.QueuedConnection
        )
        hilvlacq_worker._sig_acquire_discrete_mea.connect(raman_worker.acquire_single_measurement)
        hilvlacq_worker._sig_acquire_continuous_mea.connect(raman_worker.acquire_continuous_burst_measurement_trigger)

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

    sig_set_autosaver = Signal(MeaRMap_Unit, queue.Queue)   # Signal to set the autosaver parameters
    sig_start_autosaver = Signal()
    
    sig_stop_measurement = Signal() # Signal to trigger measurement collection
    sig_run_scan_discrete = Signal(AcquisitionParams, list, queue.Queue)
    sig_run_scan_continuous = Signal(AcquisitionParams, list, float, queue.Queue)

    def __init__(self,
                 parent,
                 motion_controller:Wdg_MotionController,
                 stageHub:DataStreamer_StageCam,
                 raman_controller:Wdg_SpectrometerController,
                 ramanHub:DataStreamer_Raman,
                 dataHub_map:Wdg_DataHub_Mapping,
                 dataHub_img:Wdg_DataHub_Image,
                 dataHub_imgcal:Wdg_DataHub_ImgCal,
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
        self._dataHub_img = dataHub_img
        self._dataHub_imgcal = dataHub_imgcal
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
        self._btn_continuous.clicked.connect(lambda: self.initiate_mapping(MappingMethods.CONTINUOUS))
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
        # Ensure motion controller workers are initialized before connecting
        if hasattr(self.motion_controller, '_init_workers'):
            self.motion_controller._init_workers()
        
        # Re-initialize worker connections now that all workers are ready
        self._reinit_worker_connections()
        
    def _reinit_worker_connections(self):
        """
        Re-initializes the worker connections after all workers are ready.
        This is needed when running from the main app where worker initialization 
        happens after the high-level controller is created.
        """
        # Create worker manager if it doesn't exist yet
        if not hasattr(self, '_worker_manager') or self._worker_manager is None:
            try:
                motion_goto_worker = self.motion_controller.get_goto_worker()
                self._worker_manager = WorkerPipelineManager(
                    hilvlacq_worker=self._worker_hilvlacq,
                    raman_worker=self.raman_controller.get_mea_worker(),
                    motion_controller=self.motion_controller,
                    motion_goto_worker=motion_goto_worker
                )
                self._worker_manager.setParent(self)
            except AttributeError as e:
                print(f"Warning: Could not initialize worker connections: {e}")
                return
        else:
            # Disconnect old connections first
            try:
                self._worker_hilvlacq._sig_gotocor.disconnect()
                self._worker_hilvlacq._sig_setvelrel.disconnect()
            except Exception:
                pass  # Connections might not exist yet
            
            # Re-establish connections with proper thread handling
            self._worker_hilvlacq._sig_gotocor.connect(
                self.motion_controller.get_goto_worker().work,
                qc.Qt.ConnectionType.QueuedConnection
            )
            self._worker_hilvlacq._sig_setvelrel.connect(
                self.motion_controller.set_vel_relative,
                qc.Qt.ConnectionType.QueuedConnection
            )
    def terminate(self):
        """
        Terminates the controller, saving the mapping coordinates to the temporary folder.
        """
        pass
    
    def _init_workers_connections(self):
        """
        Initialises the workers and their connections
        """
    # >>> Worker setups <<<
        self._event_isacquiring = threading.Event()
        self._worker_hilvlacq = Hilvl_MeasurementAcq_Worker(
            self._dataHub_map.get_MappingHub(),
            self.raman_controller.get_syncer_acquisition(),
            self._event_isacquiring)
        
        # Try to get the goto worker, but be defensive about timing
        try:
            motion_goto_worker = self.motion_controller.get_goto_worker()
        except AttributeError:
            # Workers not initialized yet, will be connected later in initialise()
            motion_goto_worker = None
            
        if motion_goto_worker is not None:
            self._worker_manager = WorkerPipelineManager(
                hilvlacq_worker=self._worker_hilvlacq,
                raman_worker=self.raman_controller.get_mea_worker(),
                motion_controller=self.motion_controller,
                motion_goto_worker=motion_goto_worker
            )
            # Set the parent to prevent garbage collection
            self._worker_manager.setParent(self)
        self._worker_autoMeaStorer = Hilvl_MeasurementStorer_Worker(
            datastreamer_stage=self._stageHub,
        )
        
    # >>> Mapping acquisition worker setup <<<
        # Connection: Mapping acquisition signals
        self.sig_stop_measurement.connect(self._event_isacquiring.clear)
        self.sig_run_scan_discrete.connect(self._worker_hilvlacq.run_scan_discrete)
        self.sig_run_scan_continuous.connect(self._worker_hilvlacq.run_scan_continuous)
        self._worker_hilvlacq.sig_error_during_mea.connect(self.handle_error_during_mapping)
        self._worker_hilvlacq.sig_mea_done_msg.connect(self._worker_autoMeaStorer.relay_finished_message)
        
        # Connection: Thread and worker management
        self._thread_hilvlacq = QThread(self)
        self._worker_hilvlacq.moveToThread(self._thread_hilvlacq)
        self.destroyed.connect(self._thread_hilvlacq.quit)
        self.destroyed.connect(self._thread_hilvlacq.deleteLater)
        self.destroyed.connect(self._worker_hilvlacq.deleteLater)
        self._thread_hilvlacq.start(QThread.Priority.HighestPriority)
        
        # Message update handling
        self._scan_update_prefix:str = ''
        self._worker_hilvlacq.sig_progress_update_str.connect(self.handle_message_update)
        
    # >>> Autosaver worker setup <<<
        # Signal to stop the autosaver
        self._worker_hilvlacq.sig_mea_done.connect(self._worker_autoMeaStorer.stop_autosaver)
        
        # Signal to start and set the autosaver
        self.sig_start_autosaver.connect(self._worker_autoMeaStorer.start_autosaver)
        self.sig_set_autosaver.connect(self._worker_autoMeaStorer.set_save_params)
        
        # Finish signal
        self._worker_autoMeaStorer.sig_error.connect(self.handle_error_during_mapping)
        self._worker_autoMeaStorer.sig_finished_relay_msg.connect(self.handle_mapping_completion)
        
        # Signal to delete the thread and worker when finished
        self._thread_autoMeaStorer = QThread(self)
        self._worker_autoMeaStorer.moveToThread(self._thread_autoMeaStorer)
        self.destroyed.connect(self._thread_autoMeaStorer.quit)
        self.destroyed.connect(self._worker_autoMeaStorer.deleteLater)
        self.destroyed.connect(self._thread_autoMeaStorer.deleteLater)
        
        self._thread_autoMeaStorer.start(QThread.Priority.HighestPriority)
        
    def _init_autoMeaStorer_worker(self, mapping_unit:MeaRMap_Unit) -> queue.Queue:
        q_storage = queue.Queue()
        self.sig_set_autosaver.emit(mapping_unit, q_storage)
        self.sig_start_autosaver.emit()
        return q_storage
    
    @Slot(str)
    def handle_message_update(self, msg:str):
        """
        Handles message updates from workers

        Args:
            msg (str): The message to display
        """
        msg = self._scan_update_prefix + msg
        self.statbar.showMessage(msg)
        self.statbar.setStyleSheet('')
    
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

    def _generate_metadata_dict(self, map_method:MappingMethods) -> dict:
        """
        Generates extra metadata for the mapping measurement
        
        Returns:
            dict: The extra metadata
        """
        assert map_method in MappingMethods, "Invalid mapping method"
        controller_ids = self.motion_controller.get_controller_identifiers()
        
        method,dir = self._get_scan_options()
        
        extra_metadata = {
            'camera_id': controller_ids[0],
            'xystage_id': controller_ids[1],
            'zstage_id': controller_ids[2],
            'mapping_method': map_method.value,
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
            tuple: mapping coordinates, mapping speed (mm/sec), mapping ID
            
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
            mappingUnit_name = messagebox_request_input(
                parent=self,
                title='Mapping ID',
                message='Enter the ID for the mapping measurement:',
                default='',
                validator=self._dataHub_map.get_MappingHub().validate_new_unit_name,
                invalid_msg="Invalid 'mappingUnit name'. The name cannot be empty or already exist. Please try again.",
                loop_until_valid=True
            )
            
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

    def _scramble_mapping_coordinates(self, list_mappingCoor:list, mode:MappingMethods) -> list:
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
        assert mode in MappingMethods, "Invalid mapping method. Check the MappingMethods enum."
        list_init = list_mappingCoor.copy()
        if mode == MappingMethods.CONTINUOUS:
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
        if mode == MappingMethods.CONTINUOUS:
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
        
        # Update the status bar prefix
        self._scan_update_prefix = f'ROI: {len(self._list_sel_mapCoor)} remains | '
        
        # Store the last mapping method used
        assert method in MappingMethods, "Invalid mapping method. Check the MappingMethods enum."
        self._last_mappingmethod = method
        
        self._perform_mapping(method=method)
        
    @Slot(str)
    def handle_error_during_mapping(self, msg:str):
        """
        Handles errors during the mapping measurement
        """
        self.statbar.showMessage(msg,5000)
        self.statbar.setStyleSheet("QStatusBar { background-color : red; color : white; }")
        
    @Slot(str)
    def handle_mapping_completion(self, msg:str):
        """
        Handles the completion of a mapping measurement
        """
        self.raman_controller.reset_enable_widgets()
        self.motion_controller.enable_widgets()
        self.enable_widgets()
        self.statbar.showMessage('Mapping measurement complete')
        self.statbar.setStyleSheet("") # Reset to default
        
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

    def _perform_mapping(self, method:MappingMethods):
        """
        Performs discrete mapping based on the mapping coordinates stored in the list
        """
        def reset(): self.enable_widgets()
        assert method in MappingMethods, "Invalid mapping method. Check the MappingMethods enum."
        
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
        
        list_coor, mapping_speed_mmPerSec, unit_name = result
        if method == MappingMethods.CONTINUOUS: ends_only = True
        else: ends_only = False
        list_coor = self._convertCoor_byScanOptions(list_coor, ends_only=ends_only)
        
        try:
            self._btn_stop.setEnabled(True)
            assert list_coor is not None and len(list_coor)>0, "No coordinates to perform mapping"
            self._request_Mapping(mapping_coordinates=list_coor, unit_name=unit_name, method=method, mapping_speed_mmPerSec=mapping_speed_mmPerSec)
        except Exception as e:
            qw.QMessageBox.critical(self,'Error',f"Failed to perform mapping for '{mappingUnit_name}': {e}")
            reset()
            if not self._flg_meaCancelled: self._coorHub.remove_mappingCoor(mappingUnit_name)
        
    def _request_Mapping(
        self,
        mapping_coordinates:list,
        unit_name:str,
        method:MappingMethods,
        mapping_speed_mmPerSec:float,
        ) -> None:
        assert method in MappingMethods, "Invalid mapping method. Check the MappingMethods enum."
    # >>> Initialisations <<<
        # Generate the extra metadata for the mapping measurement
        extra_metadata = self._generate_metadata_dict(method)
        
        # Initialise the mapping measurement data class
        mea_unit = MeaRMap_Unit(unit_name, extra_metadata=extra_metadata)
        self._dataHub_map.append_MappingUnit(mea_unit)

        # Scramble the mapping coordinates if requested
        mapping_coordinates = self._scramble_mapping_coordinates(mapping_coordinates, method)
        
        # Perform the mapping measurement itself
        q_autosave = self._init_autoMeaStorer_worker(mea_unit)
        if method == MappingMethods.DISCRETE:
            print('Requesting discrete mapping...')
            self.sig_run_scan_discrete.emit(
                self.raman_controller.generate_acquisition_params(),
                mapping_coordinates,
                q_autosave
                )
        else:
            mapping_speed_rel = self.motion_controller.calculate_vel_relative(vel_xy_mmPerSec=mapping_speed_mmPerSec)
            mapping_speed_rel *= AppRamanEnum.CONTINUOUS_SPEED_MODIFIER.value
            self.sig_run_scan_continuous.emit(
                self.raman_controller.generate_acquisition_params(),
                mapping_coordinates,
                mapping_speed_rel,
                q_autosave,
                )

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
        dataHub_img=Wdg_DataHub_Image(wdg_main),
        dataHub_imgcal=Wdg_DataHub_ImgCal(wdg_main),
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