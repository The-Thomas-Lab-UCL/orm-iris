import os

import multiprocessing.pool as mpp

import PySide6.QtWidgets as qw
import PySide6.QtCore as qc
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer

import queue
from enum import Enum

import math
import numpy as np
import random

from dataclasses import dataclass

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

import threading
import time
from iris.utils.general import messagebox_request_input, get_all_widgets, get_timestamp_us_int
from iris.utils.scan_progress import ScanPathProgress, continuous_group_labels
from iris.utils.mea_pause import MeasurementPauseGate

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

MINIMUM_RELATIVE_SPEED_PERCENT = 1e-5  # Minimum relative speed percentage for mapping

# Base stall-timeout for stage movement during mapping: how long the stage may report no position
# change before a "go to coordinate" is considered stalled/failed. This is NOT an absolute cap on
# the move duration (a move at a very low relative speed can legitimately take minutes) - see
# Motion_GoToCoor_Worker._notify_finish for the actual stall-detection logic. It is extended per
# point by that point's total integration time, since acquisition-related pauses in stage telemetry
# updates should not be mistaken for a stall.
GOTO_STALL_TIMEOUT_BASE_SEC = 15.0

# Timeout for the velocity-set synchronisation event used during continuous mapping. Unlike
# reaching a coordinate, setting the velocity is not distance/speed-dependent, so a flat timeout
# is appropriate here (it's a last-resort safety net against a genuinely hung hardware call -
# Wdg_MotionController.set_vel_relative always releases this event promptly on its own otherwise).
CONTINUOUS_SETVEL_WAIT_TIMEOUT_SEC = 5.0

# Safety factor on the data streamers' storage requested for a continuous scan: the Raman streamer keeps
# this many times the spectra of the longest scan line, and the stage streamer keeps this many times its
# duration of coordinates. A line's spectra are only retrieved (and their coordinates looked up) once the
# line is finished, so the streamers must hold at least one whole line, plus margin for an autosaver backlog.
STREAMER_STORAGE_SAFETY_FACTOR = 2.0

# Mapping speed auto-adjustment (continuous mapping): the longest scan line is scanned while the speed factor
# is re-estimated from every new spectrum, and the test line is stopped as soon as the estimate converges.
AUTO_ADJUST_POLL_INTERVAL_SEC = 0.1         # How often the new spectra are checked [s]
AUTO_ADJUST_MIN_SPECTRA = 10                # Minimum number of spectra before an estimate is made
AUTO_ADJUST_CONVERGENCE_WINDOW = 5          # Number of consecutive estimates that must agree
AUTO_ADJUST_CONVERGENCE_TOLERANCE = 0.01    # Relative spread (max-min)/mean allowed within the window to count as converged

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

@dataclass
class MappingSpeedParam:
    init_mapping_speed_mmPerSec:float
    auto_adjust:bool
    auto_adjust_coor_start:tuple[float,float,float] = (0.0,0.0,0.0)
    auto_adjust_coor_end: tuple[float,float,float] = (0.0,0.0,0.0)
    auto_adjust_expected_number_of_points:int = 1
    mapping_speed_rel_percent:float = 100.0
    mapping_speed_multiplier:float = 1.0

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
    sig_autoAdjSpeed_newMultiplier = Signal(float)  # Signal to update the auto-adjusted speed value
    
    sig_error_during_mea = Signal(str)  # Signal emitted when an error occurs during measurement
    sig_mea_done = Signal() # Signal emitted when measurement is done (no differentiation between success, cancelled, or error)
    sig_mea_done_msg = Signal(str)  # Signal emitted when measurement is done with a message
    
    msg_mea_error = "An error occurred during the mapping measurement: "
    msg_mea_cancelled = "Mapping measurement was cancelled by the user"
    msg_mea_finished = "Mapping measurement finished successfully"
    
    err_msg_ismeasuring = "Cannot start a new mapping measurement while another is running."
    
    _sig_stop_autosaver = Signal()
    _sig_gotocor = Signal(tuple, threading.Event, float, queue.Queue)
    _sig_setvelrel = Signal(float, float, threading.Event)
    _sig_stop_xy = Signal(threading.Event)
    _sig_acquire_discrete_mea = Signal(AcquisitionParams, queue.Queue)
    _sig_acquire_continuous_mea = Signal(AcquisitionParams, queue.Queue, queue.Queue, queue.Queue)
    _sig_acquire_list_coors = Signal(list, threading.Event)

    def __init__(self, mapping_hub:MeaRMap_Hub, syncer_raman:Syncer_Raman, event_isacquiring:threading.Event,
                 pause_gate:MeasurementPauseGate|None=None, stageHub:DataStreamer_StageCam|None=None,
                 ramanHub:DataStreamer_Raman|None=None):
        """
        Worker to perform the measurement acquisition for Raman imaging. For the slots details, refer to the
        methods in RamanMeasurement_Worker class in raman.py.

        Args:
            mapping_hub (MeaRMap_Hub): The mapping measurement hub to store the measurement data
            syncer_raman (Syncer_Raman): The synchronization object for Raman measurements
            event_isacquiring (threading.Event): The event flag to indicate if a measurement is ongoing
            pause_gate (MeasurementPauseGate|None): Gate used to park the scan while the data hub
                writes a database file, so that the scan cannot append to a unit mid-write.
                Defaults to None, which runs the scan without ever pausing.
            stageHub (DataStreamer_StageCam|None): The stage data streamer, asked to keep enough coordinates
                for a continuous scan. Defaults to None, which leaves it at its config value.
            ramanHub (DataStreamer_Raman|None): The Raman data streamer, asked to keep enough spectra for a
                continuous scan. Defaults to None, which leaves it at its config value.
        """
        super().__init__()
        self.mapping_hub = mapping_hub
        self._syncer = syncer_raman
        self._event_isacquiring = event_isacquiring
        self._pause_gate = pause_gate
        self._stageHub = stageHub
        self._ramanHub = ramanHub

    def _request_streamer_storage(self, num_points_line:int, line_duration_sec:float) -> None:
        """
        Asks the data streamers to hold enough data for the longest scan line (times
        STREAMER_STORAGE_SAFETY_FACTOR). A request only ever extends the streamers' config values and
        replaces the previous request. Pair it with _clear_streamer_storage_request().

        Args:
            num_points_line (int): Number of spectra in the longest scan line
            line_duration_sec (float): Duration of the longest scan line [s]
        """
        num_spectra = int(math.ceil(STREAMER_STORAGE_SAFETY_FACTOR * num_points_line))
        duration_sec = STREAMER_STORAGE_SAFETY_FACTOR * line_duration_sec
        try:
            if self._ramanHub is not None: self._ramanHub.request_storage(num_spectra)
            if self._stageHub is not None: self._stageHub.request_coordinate_retention(duration_sec)
            print(f'Data streamer storage requested: at least {num_spectra} spectra and {duration_sec:.0f} s of stage coordinates')
        except Exception as e:
            print(f'Error in _request_streamer_storage: {e}')

    def _clear_streamer_storage_request(self) -> None:
        """
        Returns the data streamers to their config storage values.
        """
        try:
            if self._ramanHub is not None: self._ramanHub.clear_storage_request()
            if self._stageHub is not None: self._stageHub.clear_coordinate_retention_request()
        except Exception as e:
            print(f'Error in _clear_streamer_storage_request: {e}')

    def _pause_checkpoint(self, progress:ScanPathProgress|None=None) -> None:
        """
        Parks the scan if the data hub is writing a database file, and discounts the time spent
        parked from the progress estimate so the pause is not mistaken for a slow stage.

        Args:
            progress (ScanPathProgress|None): The scan's progress estimator, if any
        """
        if self._pause_gate is None: return
        duration_paused = self._pause_gate.checkpoint(self._event_isacquiring)
        if duration_paused > 0:
            if progress is not None: progress.add_paused_time(duration_paused)
            print(f'Scan resumed after being paused for {duration_paused:.1f} s by a data hub save')
    
    def _calculate_goto_stall_timeout(self, params:AcquisitionParams) -> float:
        """
        Calculates the stall-timeout to use for a "go to coordinate" movement during a mapping
        scan. This is added on top of the base config value so that per-point acquisition pauses
        (which can briefly delay the next movement command) are never mistaken for a genuine stage
        stall - see GOTO_STALL_TIMEOUT_BASE_SEC and Motion_GoToCoor_Worker._notify_finish.

        Args:
            params (AcquisitionParams): The acquisition parameters for the measurement

        Returns:
            float: The stall-timeout [s] to use for this scan's movement commands
        """
        total_integration_sec = params['accumulation'] * params['int_time_ms'] / 1000.0
        return GOTO_STALL_TIMEOUT_BASE_SEC + total_integration_sec

    @staticmethod
    def _get_goto_result(result_goto:queue.Queue) -> str|None:
        """
        Retrieves the result message put there by Motion_GoToCoor_Worker (see its `work()`/
        `_notify_finish()` docstrings), after the corresponding event has already been waited on.

        Args:
            result_goto (queue.Queue): The queue passed alongside the _sig_gotocor emission

        Returns:
            str|None: The result message, or None if nothing was put (should not normally happen)
        """
        try: return result_goto.get_nowait()
        except queue.Empty: return None

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
        goto_timeout = self._calculate_goto_stall_timeout(params)

        # Pre-compute the XY path of the scan, so that the progress/time estimates can be based on
        # the distance actually travelled rather than on the plain point count. The per-point
        # integration time is a known, distance-independent cost, so it is given to the estimator.
        progress = ScanPathProgress(
            mapping_coordinates,
            fixed_time_per_point_sec=accumulation * int_time / 1000.0,
        )
        self.sig_progress_update_str.emit(progress.initial_message('points'))

        self._event_isacquiring.set()
        if self._pause_gate is not None: self._pause_gate.scan_started()
        msg = self.msg_mea_finished
        progress.start()
        for i, coor in enumerate(mapping_coordinates):
            try:
                # time1 = time.time()
                if not self._event_isacquiring.is_set():
                    msg = self.msg_mea_cancelled
                    break

                # Hold here while the data hub is writing a database file. Between points is a
                # safe place to park: nothing is being integrated and the stage is stationary.
                self._pause_checkpoint(progress)
                if not self._event_isacquiring.is_set():
                    msg = self.msg_mea_cancelled
                    break

                # Go to the requested coordinates
                event_finish = threading.Event()
                result_goto:queue.Queue = queue.Queue()
                # print('\nMoving to coordinates:',coor)
                # print('Emitting _sig_gotocor signal...')
                self._sig_gotocor.emit(
                    (float(coor[0]),float(coor[1]),float(coor[2])),
                    event_finish,
                    goto_timeout,
                    result_goto,
                )
                # print('Waiting for movement to complete...')
                # No externally-imposed cap here: Motion_GoToCoor_Worker guarantees the event is always
                # eventually set (bounded by its own stall-detection using goto_timeout), so this can't hang.
                event_finish.wait()
                # time2 = time.time()

                goto_result_msg = self._get_goto_result(result_goto)
                if goto_result_msg != Motion_GoToCoor_Worker.msg_target_reached:
                    raise TimeoutError(f"Failed to reach the target coordinate: {goto_result_msg or 'unknown error'}")
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
                self.sig_progress_update_str.emit(progress.update(i + 1).message('points'))
        
        self._event_isacquiring.clear()
        if self._pause_gate is not None: self._pause_gate.scan_finished()
        self.emit_finish_signals(msg)
        return

    @Slot(AcquisitionParams, list, MappingSpeedParam, queue.Queue)
    def run_scan_continuous(
        self,
        params:AcquisitionParams,
        mapping_coordinates_ends:list[tuple[float,float,float]],
        mapping_speed_param:MappingSpeedParam,
        q_mea_out:queue.Queue):
        """
        Scans the mapping coordinates continuously based on the given scan coordinates.

        Args:
            params (AcquisitionParams): The acquisition parameters for the measurement
            mapping_coordinates_ends (list[tuple[float,float,float]]): List of scan coordinates (end coordinates of each scan lines)
            mapping_speed_param (MappingSpeedParam): The mapping speed parameters for the measurement
            q_mea_out (queue.Queue): The queue to store the measurement data
        """
        print("Starting continuous mapping measurement...")
        # Prepare the events to synchronise the movement and measurement
        event_finish_setvel = threading.Event()
        event_finish_goto = threading.Event()
        
        # Prepare the measurement queue to save the measurement data into
        # the mapping unit (set up in the main thread)
        q_trig = queue.Queue()  # Queue to send the measurement trigger commands
        q_test = queue.Queue()  # Queue to send the measurement trigger commands for testing purposes
        self._sig_acquire_continuous_mea.emit(params, q_trig, q_mea_out, q_test)
        
        print('Acquisition started, moving to start position...')
        # >>> Perform the mapping measurement <<<
        # Pre-compute the XY path of the scan for the progress/time estimates. There is no
        # distance-independent per-line cost here (the spectra are acquired while the stage moves),
        # but the scan lines and the retraces are travelled at very different speeds, so they are
        # labelled as separate groups and get their own measured travel rate.
        progress = ScanPathProgress(
            mapping_coordinates_ends,
            group_labels=continuous_group_labels(len(mapping_coordinates_ends)),
        )
        self.sig_progress_update_str.emit(progress.initial_message('lines'))

        self._event_isacquiring.set()
        if self._pause_gate is not None: self._pause_gate.scan_started()
        goto_timeout = self._calculate_goto_stall_timeout(params)

        # Size the data streamers' storage for the longest scan line, whose spectra are only retrieved
        # once the line is done. First estimated from the integration time, refined after the speed
        # auto-adjustment below with the measured spectrum rate (which includes the readout overheads).
        num_points_line = max(1, int(mapping_speed_param.auto_adjust_expected_number_of_points))
        line_duration_sec = num_points_line * params['accumulation'] * params['int_time_ms'] / 1000.0
        self._request_streamer_storage(num_points_line, line_duration_sec)

        # Prepare the start of the measurement
        self._syncer.set_notready()
        q_trig.put(EnumTrig.START)
        self._syncer.wait_ready()

        try:
            spectrum_period_sec = self._auto_adjust_mapping_speed(
                mapping_speed_param=mapping_speed_param,
                event_finish_setvel=event_finish_setvel,
                event_finish_goto=event_finish_goto,
                q_trig=q_trig,
                goto_timeout=goto_timeout,
            )
            if spectrum_period_sec is not None and num_points_line * spectrum_period_sec > line_duration_sec:
                self._request_streamer_storage(num_points_line, num_points_line * spectrum_period_sec)
        except Exception as e:
            # Don't let a failure here (e.g. a stage comms timeout) silently kill the whole scan
            # thread before it even starts the main loop - report it and continue with the
            # un-adjusted speed instead.
            self.sig_error_during_mea.emit(self.msg_mea_error + str(e))
            print('Error in _auto_adjust_mapping_speed:',e)

        msg = self.msg_mea_finished
        # Start the scan clock only now, so the speed auto-adjustment above is excluded from both the
        # elapsed time and the measured travel rate
        progress.start()
        for i, coor in enumerate(mapping_coordinates_ends):
            try:
                if not self._event_isacquiring.is_set(): msg = self.msg_mea_cancelled; break
                # Hold here while the data hub is writing a database file. Only park before going to a
                # line START (even i), i.e. after the previous line was STOREd: the IGNORE issued on
                # arrival then discards the spectra acquired while parked. Parking before a line END
                # (odd i) would leave the stage sitting at the line start after its IGNORE, so the whole
                # pause gets stored with that line and its oldest spectra outlive the stage hub's
                # coordinate history (dropped by the autosaver -> missing left side of the map).
                if i % 2 == 0: self._pause_checkpoint(progress)
                if not self._event_isacquiring.is_set(): msg = self.msg_mea_cancelled; break
                self._execute_scan_continuous_step(mapping_speed_param, q_mea_out, event_finish_setvel, event_finish_goto, q_trig, i, coor, goto_timeout)
            except Exception as e:
                self.sig_error_during_mea.emit(self.msg_mea_error + str(e))
                print('Error in run_scan_continuous:',e)
            finally:
                # Update progress
                self.sig_progress_update_str.emit(progress.update(i + 1).message('lines'))
        
        # Stop raman frame's continuous measurement and store the final measurements
        q_trig.put(EnumTrig.STORE)
        q_trig.put(EnumTrig.FINISH)

        # Restore the stage speed to normal (100%), whether the scan finished or was stopped early.
        # Otherwise the stage is left at whatever reduced mapping_speed_rel_percent was last set
        # inside _execute_scan_continuous_step, depending on the parity of the last coordinate index.
        event_finish_setvel.clear()
        self._sig_setvelrel.emit(100.0, -1.0, event_finish_setvel)
        event_finish_setvel.wait()

        self._event_isacquiring.clear()
        self._clear_streamer_storage_request()
        if self._pause_gate is not None: self._pause_gate.scan_finished()
        self.emit_finish_signals(msg)

    def _execute_scan_continuous_step(
        self,
        mapping_speed_param:MappingSpeedParam,
        q_mea_out:queue.Queue,
        event_finish_setvel:threading.Event,
        event_finish_goto:threading.Event,
        q_trig:queue.Queue,
        coor_idx:int,
        coor:tuple,
        goto_timeout:float,
        ) -> None:
        """
        Executes a single step in the continuous mapping measurement.

        Args:
            mapping_speed_param (MappingSpeedParam): The mapping speed parameters for the measurement
            q_mea_out (queue.Queue): The queue to store the measurement data
            event_finish_setvel (threading.Event): Event to signal the completion of setting velocity
            event_finish_goto (threading.Event): Event to signal the completion of going to coordinates
            q_trig (queue.Queue): Queue to send the measurement trigger commands
            i (int): The index of the current coordinate
            coor (tuple): The target coordinate
            goto_timeout (float): Stall-timeout [s] to use for the movement - see _calculate_goto_stall_timeout
        """
        # Go to the requested coordinates
        # time1 = time.time()
        # print(f'\nMoving to coordinates: {coor} (Index {coor_idx}), distance from last: {math.dist(self._last_coor, coor) if hasattr(self, "_last_coor") else "N/A"}')
        self._last_coor = coor
        event_finish_goto.clear()
        result_goto:queue.Queue = queue.Queue()
        self._sig_gotocor.emit(
                    (float(coor[0]),float(coor[1]),float(coor[2])),
                    event_finish_goto,
                    goto_timeout,
                    result_goto,
                )
        # No externally-imposed cap: Motion_GoToCoor_Worker guarantees the event is always
        # eventually set, bounded by its own stall-detection using goto_timeout.
        event_finish_goto.wait()
        goto_result_msg = self._get_goto_result(result_goto)
        if goto_result_msg != Motion_GoToCoor_Worker.msg_target_reached:
            raise TimeoutError(f"Failed to reach the target coordinate: {goto_result_msg or 'unknown error'}")
        # time2 = time.time()

        event_finish_setvel.clear()
        if coor_idx%2 == 0:
            # print('Moving to next line end position (odd line)...')
            self._syncer.set_notready()
            q_trig.put(EnumTrig.IGNORE)
            self._sig_setvelrel.emit(mapping_speed_param.mapping_speed_rel_percent, -1.0, event_finish_setvel)   # Set actual speed to move between x-coordinates
            # print('Reached line end position.')
        else:
            # print('Moving to next line end position (even line)...')
            self._syncer.set_notready()
            q_trig.put(EnumTrig.STORE)
            self._sig_setvelrel.emit(100.0, -1.0, event_finish_setvel) # Set max speed to move between each scan line
            # print('Reached line end position.')
        self._syncer.wait_ready()
        if not event_finish_setvel.wait(CONTINUOUS_SETVEL_WAIT_TIMEOUT_SEC):
            raise TimeoutError('Failed to set the stage velocity. Setting velocity timed out.')
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
        
    def _auto_adjust_mapping_speed(
        self,
        mapping_speed_param:MappingSpeedParam,
        event_finish_setvel:threading.Event,
        event_finish_goto:threading.Event,
        q_trig:queue.Queue,
        goto_timeout:float,
        ) -> float|None:
        """
        Auto adjusts the mapping speed by scanning the longest line and monitoring the spectra while the
        stage moves. The speed factor is re-estimated with every new spectrum from the actual spacing between
        the spectra (stage displacement between their timestamps), and the test stops as soon as the estimate
        converges (see AUTO_ADJUST_* constants), instead of always scanning the whole line. The stage is then
        left at full speed, ready for the mapping to move to its first line.
        
        If the estimate never converges, the latest estimate at the end of the line is used.

        Args:
            mapping_speed_param (MappingSpeedParam): The mapping speed parameters for the measurement
            event_finish_setvel (threading.Event): Event to signal the completion of setting velocity
            event_finish_goto (threading.Event): Event to signal the completion of going to coordinates
            q_trig (queue.Queue): Queue to send the measurement trigger commands
            goto_timeout (float): Stall-timeout [s] to use for the movements - see _calculate_goto_stall_timeout

        Returns:
            float|None: The measured time per spectrum [s] during the test, or None if no estimate was made
        """
        if self._stageHub is None or self._ramanHub is None:
            raise RuntimeError('The stage and Raman data streamers are required for the mapping speed auto-adjustment')
        
        coor_start = mapping_speed_param.auto_adjust_coor_start
        coor_end = mapping_speed_param.auto_adjust_coor_end
        num_points = mapping_speed_param.auto_adjust_expected_number_of_points
        if num_points < 2 or math.dist(coor_start, coor_end) <= 0:
            raise ValueError('The auto-adjustment line must have at least 2 points and a non-zero length')
        spacing_target_mm = math.dist(coor_start, coor_end) / (num_points - 1)  # The grid pitch along the line

        # Go to the start of the test line
        event_finish_goto.clear()
        result_goto:queue.Queue = queue.Queue()
        self._sig_gotocor.emit(
                    (float(coor_start[0]),float(coor_start[1]),float(coor_start[2])),
                    event_finish_goto,
                    goto_timeout,
                    result_goto,
                )
        event_finish_goto.wait()
        goto_result_msg = self._get_goto_result(result_goto)
        if goto_result_msg != Motion_GoToCoor_Worker.msg_target_reached:
            raise TimeoutError(f"Failed to reach the auto-adjust start coordinate: {goto_result_msg or 'unknown error'}")

        # Set the initial mapping speed
        event_finish_setvel.clear()
        self._sig_setvelrel.emit(mapping_speed_param.mapping_speed_rel_percent, -1.0, event_finish_setvel)
        if not event_finish_setvel.wait(CONTINUOUS_SETVEL_WAIT_TIMEOUT_SEC):
            raise TimeoutError('Failed to set the stage velocity for auto-adjust. Setting velocity timed out.')

        # Discard the spectra so far, so the acquisition worker's next retrieval stays small
        self._syncer.set_notready()
        q_trig.put(EnumTrig.IGNORE)
        self._syncer.wait_ready()

        # Start the test line and monitor it while the stage moves
        event_finish_goto.clear()
        result_goto = queue.Queue()
        self._sig_gotocor.emit(
                    (float(coor_end[0]),float(coor_end[1]),float(coor_end[2])),
                    event_finish_goto,
                    goto_timeout,
                    result_goto,
                )
        
        ts_monitor_start:int|None = None    # Spectra are only used after the stage has started moving (skips the start-up/acceleration)
        num_spectra_last = 0
        list_factors:list[float] = []       # Speed factor estimates, one per new spectrum
        spectrum_period_sec:float|None = None
        flg_converged = False
        flg_stopped = False
        while not event_finish_goto.wait(AUTO_ADJUST_POLL_INTERVAL_SEC):
            if not self._event_isacquiring.is_set(): break  # Cancelled: stop the stage below
            
            if ts_monitor_start is None:
                ts_now = get_timestamp_us_int()
                coor_now = self._stageHub.get_coordinates_closest(ts_now)
                if coor_now is not None and math.dist(coor_now, coor_start) >= spacing_target_mm: ts_monitor_start = ts_now
                continue
            
            list_ts = self._ramanHub.get_timestamps(ts_monitor_start)
            if len(list_ts) <= num_spectra_last or len(list_ts) < AUTO_ADJUST_MIN_SPECTRA: continue
            num_spectra_last = len(list_ts)
            
            # Actual spacing between the spectra: stage displacement between the first and last spectrum
            coor_first = self._stageHub.get_coordinates_interpolate(list_ts[0])
            coor_last = self._stageHub.get_coordinates_interpolate(list_ts[-1])
            if coor_first is None or coor_last is None: continue
            spacing_actual_mm = math.dist(coor_first, coor_last) / (len(list_ts) - 1)
            if spacing_actual_mm <= 0: continue
            
            list_factors.append(spacing_target_mm / spacing_actual_mm)  # More spectra than wanted (smaller spacing) -> speed up
            spectrum_period_sec = (list_ts[-1] - list_ts[0]) / 1e6 / (len(list_ts) - 1)
            
            # Converged once the latest estimates agree within the tolerance
            window = list_factors[-AUTO_ADJUST_CONVERGENCE_WINDOW:]
            if len(window) == AUTO_ADJUST_CONVERGENCE_WINDOW:
                mean = sum(window) / len(window)
                if (max(window) - min(window)) / mean <= AUTO_ADJUST_CONVERGENCE_TOLERANCE:
                    flg_converged = True
                    break
        
        # Stop the test line early (converged or cancelled), then wait for the movement to wind down so the
        # stage is free for the next command. A stopped move is expected to report not reaching its target.
        if not event_finish_goto.is_set():
            flg_stopped = True
            event_finish_stop = threading.Event()
            self._sig_stop_xy.emit(event_finish_stop)
            event_finish_stop.wait(CONTINUOUS_SETVEL_WAIT_TIMEOUT_SEC)
        event_finish_goto.wait()
        goto_result_msg = self._get_goto_result(result_goto)
        if not flg_stopped and goto_result_msg != Motion_GoToCoor_Worker.msg_target_reached:
            raise TimeoutError(f"Failed to reach the auto-adjust end coordinate: {goto_result_msg or 'unknown error'}")
        
        # Leave the stage at full speed so the mapping moves to its first line straight away
        event_finish_setvel.clear()
        self._sig_setvelrel.emit(100.0, -1.0, event_finish_setvel)
        if not event_finish_setvel.wait(CONTINUOUS_SETVEL_WAIT_TIMEOUT_SEC):
            raise TimeoutError('Failed to set the stage velocity after auto-adjust. Setting velocity timed out.')
        
        if not self._event_isacquiring.is_set(): return None
        if len(list_factors) == 0:
            print('Auto adjust mapping speed: Not enough measurements collected, cannot adjust speed.')
            self.sig_autoAdjSpeed_newMultiplier.emit(mapping_speed_param.mapping_speed_multiplier)
            return None
        
        # Apply the latest estimate
        speed_adjust_factor = list_factors[-1]
        new_modifier = mapping_speed_param.mapping_speed_multiplier * speed_adjust_factor
        new_speed_percent = mapping_speed_param.mapping_speed_rel_percent * speed_adjust_factor
        new_speed_percent = max(MINIMUM_RELATIVE_SPEED_PERCENT, min(new_speed_percent, 100.0))   # Clamp between a minimum and 100%
        status = f'converged after {num_spectra_last} measurements' if flg_converged else \
            f'did not converge within the line ({num_spectra_last} measurements), using the latest estimate'
        print(f'Auto adjust mapping speed: {status}. Speed factor {speed_adjust_factor:.3f}. '
              f'Adjusting stage-speed from {mapping_speed_param.mapping_speed_rel_percent:.2f}% to {new_speed_percent:.2f}%.')
        mapping_speed_param.mapping_speed_rel_percent = new_speed_percent
        mapping_speed_param.mapping_speed_multiplier = new_modifier
        self.sig_autoAdjSpeed_newMultiplier.emit(mapping_speed_param.mapping_speed_multiplier)
        
        return spectrum_period_sec
        
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
        hilvlacq_worker._sig_stop_xy.connect(
            motion_controller.stop_xy,
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
    sig_run_scan_continuous = Signal(AcquisitionParams, list, MappingSpeedParam, queue.Queue)

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
        
    # >>> Auto speed adjustment setup <<<
        QTimer.singleShot(0, lambda: self._widget.spin_continuousSpeedMod.setValue(AppRamanEnum.CONTINUOUS_SPEED_MODIFIER.value*100.0))
        
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
        # Shared with the data hub: every database write parks the scan for its duration, and
        # the scan in turn tells the hub when it is safe to write.
        self._pause_gate = MeasurementPauseGate()
        self._dataHub_map.set_pause_gate(self._pause_gate)
        self._worker_hilvlacq = Hilvl_MeasurementAcq_Worker(
            self._dataHub_map.get_MappingHub(),
            self.raman_controller.get_syncer_acquisition(),
            self._event_isacquiring,
            pause_gate=self._pause_gate,
            stageHub=self._stageHub,
            ramanHub=self._ramanHub)
        
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
        
        # Auto speed adjustment handling
        self._worker_hilvlacq.sig_autoAdjSpeed_newMultiplier.connect(self.handle_auto_speedmod_update)
        
    # >>> Autosaver worker setup <<<
        # Signal to stop the autosaver
        self._worker_hilvlacq.sig_mea_done.connect(self._worker_autoMeaStorer.stop_autosaver)
        
        # The measurement is over (finished, cancelled or failed alike), so its unit may now be
        # autosaved and offloaded by the data hub
        self._worker_hilvlacq.sig_mea_done.connect(self._dataHub_map.clear_unit_in_progress)
        
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
        
        self._thread_autoMeaStorer.start(QThread.Priority.HighPriority)
        
    def _init_autoMeaStorer_worker(self, mapping_unit:MeaRMap_Unit) -> queue.Queue:
        q_storage = queue.Queue()
        self.sig_set_autosaver.emit(mapping_unit, q_storage)
        self.sig_start_autosaver.emit()
        return q_storage
    
    @Slot(float)
    def handle_auto_speedmod_update(self, new_modifier:float):
        """
        Handles updates to the auto speed modifier from the worker

        Args:
            new_modifier (float): The new speed modifier
        """
        self._widget.spin_continuousSpeedMod.setValue(new_modifier*100.0)
    
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

    def _convertCoor_byScanOptions(
        self,
        mapping_speeed_param:MappingSpeedParam,
        mapping_coor:list|None=None,
        precision:int=4,
        ends_only:bool=False
        ) -> list|None:
        """
        Converts coordinates to raster scan format and modifies the mapping_speed_param for auto speed adjustment.

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
            
            # Prepare auto speed adjustment parameters
            list_scan_distance = [math.dist(group_coor[x][0], group_coor[x][-1]) for x in sorted_x] # List of distances for each scan line
            idx_max_scan = list_scan_distance.index(max(list_scan_distance))    # Index of the line with the maximum scan distance
            num_max_scan = len(group_coor[sorted_x[idx_max_scan]])  # Number of points in the line with the maximum scan distance
            mapping_speeed_param.auto_adjust_coor_start = group_coor[sorted_x[idx_max_scan]][0]
            mapping_speeed_param.auto_adjust_coor_end = group_coor[sorted_x[idx_max_scan]][-1]
            mapping_speeed_param.auto_adjust_expected_number_of_points = num_max_scan
            
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
            
            # Prepare auto speed adjustment parameters
            list_scan_distance = [math.dist(group_coor[y][0], group_coor[y][-1]) for y in sorted_y] # List of distances for each scan line
            idx_max_scan = list_scan_distance.index(max(list_scan_distance))    # Index of the line with the maximum scan distance
            num_max_scan = len(group_coor[sorted_y[idx_max_scan]])  # Number of points in the line with the maximum scan distance
            mapping_speeed_param.auto_adjust_coor_start = group_coor[sorted_y[idx_max_scan]][0]
            mapping_speeed_param.auto_adjust_coor_end = group_coor[sorted_y[idx_max_scan]][-1]
            mapping_speeed_param.auto_adjust_expected_number_of_points = num_max_scan
            
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
                                       mappingUnit_name:str|None=None) -> tuple[list,float,str]|None:
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
            tuple|None: mapping coordinates, mapping speed (mm/sec), mapping ID.
                None if the user cancelled the mapping ID request.
            
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
        if mappingUnit_name is None and mapping_coordinates_mm.mappingUnit_name != '':
            mappingUnit_name = mapping_coordinates_mm.mappingUnit_name
        
        def validator(name:str) -> bool: return name.strip() != '' and mappingHub.validate_new_unit_name(name)
        
        if mappingUnit_name is None or not validator(mappingUnit_name):
            message = 'Enter the ID for the mapping measurement:' if mappingUnit_name is None else \
                f"The mapping ID '{mappingUnit_name}' already exists.\nEnter a new ID for the mapping measurement:"
            mappingUnit_name = messagebox_request_input(
                parent=self,
                title='Mapping ID',
                message=message,
                default=mappingUnit_name or '',
                validator=validator,
                invalid_msg="Invalid 'mappingUnit name'. The name cannot be empty or already exist. Please try again.",
                loop_until_valid=True
            )
            if mappingUnit_name is None: return None    # User cancelled
            
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

        # Guard: beam dump checked but no coordinate stored
        if self._widget.chk_beamdump.isChecked() and self.motion_controller.beamdump_coor is None:
            qw.QMessageBox.warning(
                self,
                'Beam dump location not set',
                'The option "Go to the beam-dump location after measurements" is enabled, '
                'but no beam dump coordinate has been stored yet.\n\n'
                'Please either:\n'
                '  • Set a beam dump location in the Stage Controller → Memory tab, or\n'
                '  • Uncheck the beam dump option before starting.\n\n'
                'The measurement has been cancelled.'
            )
            self._list_sel_mapCoor.clear()
            return
        
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
            self._widget.chk_contMap_autoAdjustSpeed.setChecked(True)
            if self._widget.chk_beamdump.isChecked():
                self.motion_controller.go_to_beamdump()
            qw.QMessageBox.information(self,'Mapping measurement complete','The mapping measurement is complete and added to the data hub')
        elif msg == self._worker_hilvlacq.msg_mea_finished:
            self.initiate_mapping(method=self._last_mappingmethod)
        else: raise ValueError("Invalid mapping completion message")

    def _perform_mapping(self, method:MappingMethods):
        """
        Performs discrete mapping based on the mapping coordinates stored in the list
        """
        def reset():
            self._list_sel_mapCoor.clear()
            self.raman_controller.reset_enable_widgets()
            self.motion_controller.enable_widgets()
            self.reset_mapping_widgets()
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
        if result is None:  # User cancelled the mapping ID request
            reset()
            qw.QMessageBox.warning(self,'Mapping measurement cancelled','The mapping measurement was cancelled by the user')
            return
        
        list_coor, mapping_speed_mmPerSec, unit_name = result
        if method == MappingMethods.CONTINUOUS: ends_only = True
        else: ends_only = False
        
        mappingSpeedParam = MappingSpeedParam(auto_adjust=self._widget.chk_contMap_autoAdjustSpeed.isChecked(), init_mapping_speed_mmPerSec=mapping_speed_mmPerSec)
        list_coor = self._convertCoor_byScanOptions(mappingSpeedParam, list_coor, ends_only=ends_only)
        if list_coor is None:
            qw.QMessageBox.critical(self,'Error',f"Failed to convert mapping coordinates for '{mappingUnit_name}'")
            reset()
            return
                
        try:
            self._widget.chk_contMap_autoAdjustSpeed.setEnabled(False)
            self._btn_stop.setEnabled(True)
            assert list_coor is not None and len(list_coor)>0, "No coordinates to perform mapping"
            if not self._request_Mapping(mapping_coordinates=list_coor, unit_name=unit_name, method=method, mapping_speed_param=mappingSpeedParam):
                reset()
                qw.QMessageBox.warning(self,'Mapping measurement cancelled','The mapping measurement was cancelled by the user')
        except Exception as e:
            qw.QMessageBox.critical(self,'Error',f"Failed to perform mapping for '{mappingUnit_name}': {e}")
            reset()
            if not self._flg_meaCancelled: self._coorHub.remove_mappingCoor(mappingUnit_name)
        
    def _request_Mapping(
        self,
        mapping_coordinates:list,
        unit_name:str,
        method:MappingMethods,
        mapping_speed_param:MappingSpeedParam,
        ) -> bool:
        """
        Requests the mapping measurement from the worker.
        
        Returns:
            bool: True if the measurement was requested, False if it was cancelled
                (e.g., the user cancelled the unit renaming prompt)
        """
        assert method in MappingMethods, "Invalid mapping method. Check the MappingMethods enum."
    # >>> Initialisations <<<
        # Generate the extra metadata for the mapping measurement
        extra_metadata = self._generate_metadata_dict(method)
        
        # Initialise the mapping measurement data class
        mea_unit = MeaRMap_Unit(unit_name, extra_metadata=extra_metadata)
        if not self._dataHub_map.append_MappingUnit(mea_unit): return False
        # Tell the data hub this unit is live, so its autosave leaves it out and its offload
        # never drops it from memory while the scan is still writing into it
        self._dataHub_map.mark_unit_in_progress(mea_unit.get_unit_id())

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
            mapping_speed_rel = self.motion_controller.calculate_vel_relative(vel_xy_mmPerSec=mapping_speed_param.init_mapping_speed_mmPerSec)
            mapping_speed_rel *= self._widget.spin_continuousSpeedMod.value()/100.0
            mapping_speed_rel = max(MINIMUM_RELATIVE_SPEED_PERCENT, min(100.0, mapping_speed_rel))  # Clamp between a minimum and 100%
            mapping_speed_param.mapping_speed_multiplier = self._widget.spin_continuousSpeedMod.value()/100.0
            mapping_speed_param.mapping_speed_rel_percent = mapping_speed_rel
            self.sig_run_scan_continuous.emit(
                self.raman_controller.generate_acquisition_params(),
                mapping_coordinates,
                mapping_speed_param,
                q_autosave,
                )
        return True

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