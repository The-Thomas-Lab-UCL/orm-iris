"""
A hub that stores the measurement from the spectrometer.
The hub is a multiprocessing process that runs in the background and is responsible for collecting the coordinates from 
the stage controllers and storing them in a dictionary. The hub also provides a method to retrieve the coordinates based
on the timestamp.

Idea:
    - The hub will constantly run in the background, collecting the measurement and timestamp from the spectrometer.
    - When required, e.g., for the mapping measurements, the hub can be queried for the measurements based on the timestamp.

Note:
    - The timestamp is in [us] integer format. See library/general_functions.py for the timestamp conversion functions.

Usage:
    1. Create a central base manager using the MyManager class from the basemanager.py file.
    2. Register the classes and the dictionary with the manager using the initialise_manager() function.
    3. Register any other classes and dictionary from other hubs/use cases.
    4. Start the manager.
    5. Create the proxies for the controllers and the dictionary using the initialise_proxy() function.
    6. Add any other proxies from other hubs/use cases.
    7. Pass the proxies into the hubs/other classes that require them.

!!! Note that the manager.start() has to be called after the all the manager initialisations (register()) and before the proxies are created.

Techinical notes (for myself):
    - The controllers passed into the hub have to be proxies from the multiprocessing manager.
    - The multithreading has to be run within the hub's run() method.
    - The dictionary also has to be a proxy from the multiprocessing manager.
    - There can only be 1 manager for the entire program. The manager has to be started before the any other instances is created.
    - Note on the order of the initialisation:
        1. The manager has to be registered with the classes and the dictionary before the proxies are created and only after the proxy creations can the manager be started.
        2. The hub has to be started after the proxies are created.
"""

import os

import multiprocessing as mp
from multiprocessing.synchronize import Event as EventClass
import multiprocessing.managers as mpm
import multiprocessing.connection as mpc
import multiprocessing.pool as mpp

import threading
import queue

import pandas as pd
import numpy as np

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))


from iris.utils.general import *
from iris.calibration.calibration_generator import CalibrationParams, SpectrometerCalibrator, Frm_SpectrometerCalibrationGenerator
from iris.data.measurement_Raman import MeaRaman, MeaRaman_Plotter
from iris.multiprocessing.basemanager import MyManager,get_my_manager

from iris.controllers import Controller_Spectrometer

from iris import DataAnalysisConfigEnum
from iris.multiprocessing import MPMeaHubEnum

class DataStreamer_Raman(mp.Process):
    """
    A class to automatically run scans and store the results and its timestamps.
    Designed to be opearted with raman_measurement_hub_processor.
    
    Note:
        !!! This class operates with timestamps that are stored is in the format of get_timestamp_us(),
        which is in integer format of microseconds (instead of the default %y%m%d_%H%M%S_%f) !!!
    
    Merged from another class: A class to run the measurements and store then in the raman_measurement_hub.
    
    VERY IMPORTANT NOTES:
        - Only 1 instance of this class should be running at a time.
        - Once terminated, the instance cannot be restarted.
        - This class should be initialised first before any multithreading/multiprocessing methods/functions.
        
    """
    
    def __init__(self,controller:Controller_Spectrometer,dict_measurements:mpm.DictProxy):
        """
        Args:
            controller (raman_spectrometer_controller): The controller for the spectrometer
            dict_measurements (mpm.DictProxy): A dictionary to store the measurements
            pipe_cal_update (mpc.PipeConnection): A pipe to update the calibration
        """
        super().__init__()
        self._controller = controller
        
    # >>> Calibrator setup <<<
        self._pipe_cal_update_front,self._pipe_cal_update_back = mp.Pipe()
        self._pipe_cal_mea_front,self._pipe_cal_mea_back = mp.Pipe()
        self._calibrator: SpectrometerCalibrator = None
        
    # >>> Storage setup <<<
        # Labels for the measurements
        self._lbl_ts = 'timestamp_us_int'
        self._lbl_mea = 'raw_spectrum'
        self._lbl_inttime = 'integration_time_ms'
        self._lbl_flg_retrieved = 'flg_retrieved'
        
        # Measurement parameters
        self._max_measurement = MPMeaHubEnum.RAMANHUB_MAXSTORAGE.value     # Maximum number of measurements stored
        self._list_measurements_updater = []            # A list to store the measuremets
        self._q_SelfUpdate:mp.Queue = mp.Queue()        # A queue to update self
        
        # Flags
        self._flg_process_updater = mp.Event()          # A flag to control the updater
        self._flg_pause_updater = mp.Event()            # A flag to pause the updater
        self._flg_pause_updater.clear()
        self._flg_PauseMeasurement = None     # A flag to autorestart the measurements 
                                                        # (will be set up automatically by the processor)
        self._flg_ListReady = mp.Event()                # A flag to indicate that the list is ready for access.
                                                        # This prevents the list from being accessed when it's still being updated.
        self._flg_ListReady.set()
        
        # Stores the measurements
        assert type(self._max_measurement) == int and self._max_measurement > 0,\
            "The maximum number of measurements has to be an integer greater than 0"
            
        self._list_timestamps:list = dict_measurements[self._lbl_ts]
        self._list_measurements:list = dict_measurements[self._lbl_mea]
        self._list_integrationtime:list = dict_measurements[self._lbl_inttime]
        self._list_flg_retrieved:list = dict_measurements[self._lbl_flg_retrieved]

        # Other parameters
        self._pause_interval_updater = 10   # The interval between checks for new measurements [ms]
        
    # >>> Processor setup <<<
        # Flags
        self._flg_process_measurement = mp.Event()              # A flag to control the continuous measurement. set() to stop
        self._flg_pause_measurement = mp.Event()                # A flag to pause the continuous measurement. set() to pause, clear() to resume
        self._flg_pause_measurement.set()
        
        self._pause_interval_measurement = 10   # The pause interval the continuous measurement [ms] (if the pause flag is raised)
        
        # Locks
        self._lock_meaCal_pipe = mp.Lock() # A lock for the pipe to calibrate a measurement
        
    def get_calibrator_pipe(self) -> mpc.PipeConnection:
        """
        Returns the pipe to update the calibrator
        
        Returns:
            mpc.PipeConnection: The pipe to update the calibrator
        """
        return self._pipe_cal_update_front
        
    def run(self):
        """
        Runs the continuous measurement
        """
        self._calibrator = SpectrometerCalibrator(pipe_update=self._pipe_cal_update_back,pipe_measurement=self._pipe_cal_mea_back)
        threading.Thread(target=self._auto_update_measurements).start()
        threading.Thread(target=self._auto_collect_measurement).start()
        
    def _auto_update_measurements(self):
        """
        Sets the measurements from the continuous measurements of the 
        raman_measurement_hub_processor
        """
        try:
            self._flg_process_updater.set()
            while self._flg_process_updater.is_set():
                if self._flg_pause_updater.is_set():
                    time.sleep(self._pause_interval_updater/1000)
                    self._flg_ListReady.set()
                    continue
                try:
                    self._flg_ListReady.clear()
                    package = self._list_measurements_updater.pop(0)
                    self._set_measurement_childProc(*package)
                except IndexError:
                # except queue.Empty:
                    time.sleep(self._pause_interval_updater/1000)
                except Exception as e:
                    print('update_continuous_measurements_package:')
                    print(e)
        finally:
            self._flg_process_updater.set()
            
    def _pause_updater(self):
        """
        Pauses the updater. Automatically waits for the list to be ready for access.
        !!! Note that if the process is paused, the list will wait indefinitely for the process to resume.
        """
        self._flg_pause_updater.set()
        if not self._flg_pause_measurement.is_set():
            self._flg_ListReady.wait()
        
    def _resume_updater(self):
        """
        Resumes the updater
        """
        self._flg_pause_updater.clear()
        
    def wait_MeasurementUpdate(self):
        """
        Waits for a new measurement to be stored. Automatically restarts the measurement.
        """
        timestamp_initial = self._list_timestamps.__getitem__(-1) if len(self._list_timestamps) > 0 else 0
        
        self.resume_auto_measurement()
        while len(self._list_timestamps) == 0 or timestamp_initial == self._list_timestamps.__getitem__(-1):
            time.sleep(self._pause_interval_updater/1000)
            
    def _get_measurement_idx(self,timestamp:int) -> int:
        """
        Returns the measurement based on the closest timestamp.
        Scans from the latest to the oldest for speed.
        
        Args:
            timestamp (int): The timestamp to be searched for [us] in integer format
        
        Returns:
            int: index of the measurement in the list.
        """
        idx_min = 0
        length = len(self._list_timestamps)
        for i in range(length):
            # Check for a smaller timestamp, scans from the latest to the oldest
            idx_check = i+1
            comparator = self._list_timestamps.__getitem__(-idx_check)
            if comparator < timestamp:
            # if self._list_timestamps.__getitem__(-idx_check) < timestamp:
                idx_min=length-(idx_check)
                break
            
        if idx_min == length-1:
            return idx_min
        else:
            return idx_min+1
        
    def get_measurement(self,timestamp_start:int,timestamp_end:int=None,WaitForMeasurement:bool=True,
                        getNewOnly:bool=False)\
        -> tuple[list,list,list]:
        """
        Returns the measurements based on the range of timestamps. Automatically pauses the updater.
        
        Args:
            timestamp_start (int): The start timestamp [us] in integer format
            timestamp_end (int, optional): The end timestamp [us] in integer format. If None, returns the measurement based on the start timestamp
            WaitForMeasurement (bool, optional): If True, waits for a new measurement to be stored
            getNewOnly (bool, optional): If True, only returns the new measurements (not retrieved yet)
        
        Returns:
            tuple: (timestamp_list (int), raw_spectrum_list (df), integration_time_ms_list (int))
            
        Note:
            - The returned timestamp is in the integer format of [us]
            - The getNewOnly is ONLY OPTIMISED FOR SINGLE MEASUREMENT RETRIEVAL. For multiple measurement retrievals, it's better to use the normal method.
            
        """
        assert all([type(timestamp_start) == int, type(timestamp_end) == int or timestamp_end == None]),\
            "The timestamps have to be in integer format"
        
        # Waits for a new measurement to be stored if requested or if there are no measurements
        if WaitForMeasurement or len(self._list_timestamps)==0: self.wait_MeasurementUpdate()
        
        self._pause_updater() # Pauses the updater to prevent index change during the process
        
        # Get lock on the lists
        
    # >>> If the end timestamp is not provided, returns the measurement based on the start timestamp
        if timestamp_end == timestamp_start or timestamp_end == None:
            mea_idx = self._get_measurement_idx(timestamp=timestamp_start)
            if getNewOnly and self._list_flg_retrieved.__getitem__(mea_idx):
                self._resume_updater()
                self.wait_MeasurementUpdate()
                self._pause_updater()
                mea_idx = self._get_measurement_idx(timestamp=timestamp_start)
            timestamp = self._list_timestamps.__getitem__(mea_idx)
            raw_spectrum = self._list_measurements.__getitem__(mea_idx)
            integration_time_ms = self._list_integrationtime.__getitem__(mea_idx)
            self._list_flg_retrieved.__setitem__(mea_idx,True)
            self._resume_updater()
            return ([timestamp],[raw_spectrum],[integration_time_ms])
        
        # Makes sure that the start timestamp is before the end timestamp
        assert timestamp_start < timestamp_end, "The start timestamp has to be before the end timestamp"
        
        idx_start = self._get_measurement_idx(timestamp=timestamp_start)
        idx_end = self._get_measurement_idx(timestamp=timestamp_end)
        
        if not getNewOnly:
            # Returns the measurements based on the range
            sliceobj = slice(idx_start,idx_end)
            ts_list:list = self._list_timestamps.__getitem__(sliceobj)
            mea_list:list = self._list_measurements.__getitem__(sliceobj)
            inttime_list:list = self._list_integrationtime.__getitem__(sliceobj)
        else:
            print('getNewOnly')
            num_measurements = len([self._list_flg_retrieved.__getitem__(i) for i in range(idx_start,idx_end) if not self._list_flg_retrieved.__getitem__(i)])
            if num_measurements == 0:
                print('waiting getNewOnly')
                self._resume_updater()
                self.wait_MeasurementUpdate()
                self._pause_updater()
            ts_list = [self._list_timestamps.__getitem__(i) for i in range(idx_start,idx_end) if not self._list_flg_retrieved.__getitem__(i)]
            mea_list = [self._list_measurements.__getitem__(i) for i in range(idx_start,idx_end) if not self._list_flg_retrieved.__getitem__(i)]
            inttime_list = [self._list_integrationtime.__getitem__(i) for i in range(idx_start,idx_end) if not self._list_flg_retrieved.__getitem__(i)]
        
        # Flag the measurements as retrieved
        [self._list_flg_retrieved.__setitem__(i,True) for i in range(idx_start,idx_end)]
        
        result = (ts_list,mea_list,inttime_list)
        
        if idx_start < int(0.1*len(self._list_timestamps)):
            print('\n!!!!! Warning !!!!!\n>>>>> raman_measurement_hub: Running out of measurement reserve. Increase self._max_measurements. <<<<<\n!!!!! Warning !!!!!\n')
        
        self._resume_updater()
        return result
    
    def _set_measurement_childProc(self,timestamp:int,raw_spectrum:pd.DataFrame,integration_time_ms:int):
        """
        Sets a measurement based on the timestamp. Designed to be used in the child process.
        If not used in the child process, the calibration won't work properly.
        
        Args:
            timestamp (int): The timestamp in the format of get_timestamp_us()
            raw_spectrum (pd.DataFrame): The raw spectrum
            integration_time_ms (int): The integration time in [ms]
        
        Note:
            - The timestamp has to be in the format of get_timestamp_us()
            (defaults to %y%m%d_%H%M%S_%f)
        """
        # Calibrate the measurements
        cal_spectrum = self._calibrator.calibrate_measurement(raw_spectrum)
        
        # # ><>< Debugging part starts here ><><
        # print('Calibrated spectrum:')
        # print(cal_spectrum.head(5))
        
        # print('Raw spectrum:')
        # print(raw_spectrum.head(5))
        # # ><>< Debugging part ends here ><><
        
        self._list_timestamps.append(timestamp)
        self._list_measurements.append(cal_spectrum)
        self._list_integrationtime.append(integration_time_ms)
        self._list_flg_retrieved.append(False)
        
        # Removes the oldest measurement if the maximum number of measurements is reached
        if len(self._list_timestamps) > self._max_measurement:
            self._list_timestamps.pop(0)
            self._list_measurements.pop(0)
            self._list_integrationtime.pop(0)
            self._list_flg_retrieved.pop(0)
    
    def terminate_process(self):
        """
        Stops the continuous measurement
        """
        self._flg_process_measurement.clear()
        self._flg_process_updater.clear()
        
    def pause_auto_measurement(self):
        """
        Pauses the continuous measurement
        """
        self._flg_pause_measurement.set()
        
    def resume_auto_measurement(self):
        """
        Resumes the continuous measurement
        """
        self._flg_pause_measurement.clear()
        
    def isrunning_auto_measurement(self) -> bool:
        """
        Returns the status of the auto measurement (continuous)
        
        Returns:
            bool: True if the auto measurement is running
        """
        return not self._flg_pause_measurement.is_set()
        
    def get_single_measurement(self) -> tuple[int,pd.DataFrame,int]|None:
        """
        Performs a single measurement and returns the results. Designed to be used
        manually, separate from the auto measurement. For this, the auto measurement
        has to be off (or use the get_measurement() instead).

        Returns:
            tuple: (timestamp (int), raw_spectrum (pd.DataFrame), integration_time_ms (int))
        """
        assert self._flg_pause_measurement.is_set(), "The continuous measurement is running. Use get_measurement() instead."
        
        # Performs a measurement
        result = self._controller.measure_spectrum()
        raw_spectrum, ts_us_int, int_time_us = result
        
        # Calibrate the measurements
        with self._lock_meaCal_pipe:
            self._pipe_cal_mea_front.send(raw_spectrum)
            cal_spectrum = self._pipe_cal_mea_front.recv()
        
        int_time_ms = int_time_us/1000
        
        # Stores the measurement
        if isinstance(cal_spectrum,pd.DataFrame): measurements = ts_us_int, cal_spectrum, int_time_ms
        else: measurements = None
        
        return measurements
        
    def _auto_collect_measurement(self):
        """
        Performs a continuous measurement. Designed to be used in a separate 
        multiprocessing physical core/thread.
        
        Note:
            !!! The timestamp stored is in the format of get_timestamp_us(), which is
            in integer format of microseconds (instead of the default %y%m%d_%H%M%S_%f) !!!
        """
        try:
            self._flg_process_measurement.set()
            list_timestamps_debug = []
            while self._flg_process_measurement.is_set():
                try:
                    # Pauses the continuous measurement
                    if self._flg_pause_measurement.is_set(): # Prevents deadlocks
                        time.sleep(self._pause_interval_measurement/1000)
                        continue
                    
                    # Performs a measurement
                    # ts_start = get_timestamp_us_int()
                    result = self._controller.measure_spectrum()
                    raw_spectrum, ts_mea, int_time_us = result
                    int_time_ms = int_time_us/1000
                    # ts_end = get_timestamp_us_int()
                    # ts_mea = (int((ts_start+ts_end)/2))
                    # ts_mea = ts_start
                    
                    # Stores the measurement
                    measurements = ts_mea, raw_spectrum, int_time_ms
                    self._list_measurements_updater.append(measurements)
                    
                    # ## ><>< Debugging part starts here ><><
                    # list_timestamps_debug.append(ts_avg_us_int)
                    # if len(list_timestamps_debug) > 3:
                    #     gap_current = list_timestamps_debug[-1]-list_timestamps_debug[-2]
                    #     gap_previous = list_timestamps_debug[-2]-list_timestamps_debug[-3]
                    #     if gap_current > gap_previous*1.75:
                    #         print('Gap: {}, Previous gap: {}'.format(gap_current,gap_previous))
                    # list_timestamps_debug.pop(0)
                    # ## ><>< Debugging part ends here ><><
                except Exception as e:
                    print('_auto_collect_measurement: ',e)
        finally:
            self._flg_process_measurement.set()
            
    def join(self):
        """
        Joins the process
        """
        self.terminate_process()
        self._flg_process_updater.wait()
        self._flg_process_measurement.wait()
        self._calibrator.terminate()
        super().join()

def initialise_manager_raman(manager:MyManager):
    """
    Registers the classes and the dictionary with the manager.
    """
    manager.register('raman_controller_proxy',callable=Controller_Spectrometer)
    manager.register('dict_raman_proxy',callable=dict,proxytype=mpm.DictProxy)
    manager.register('list_raman_timestamp_proxy',callable=list,proxytype=mpm.ListProxy)
    manager.register('list_raman_measurement_proxy',callable=list,proxytype=mpm.ListProxy)
    manager.register('list_raman_integrationtime_proxy',callable=list,proxytype=mpm.ListProxy)
    manager.register('list_raman_flg_retrieved_proxy',callable=list,proxytype=mpm.ListProxy)
    
def initialise_proxy_raman(manager:MyManager):
    """
    Initialises the proxies for the controllers and the dictionary.
    
    Args:
        manager (MyManager): The central base manager
    
    Returns:
        tuple: (raman_ctrl_proxy,dict_raman_proxy)
    """
    raman_ctrl_proxy = manager.raman_controller_proxy()
    dict_raman_proxy = manager.dict_raman_proxy()
    
    list_raman_timestamp_proxy = manager.list_raman_timestamp_proxy()               # Proxy list for the timestamps
    list_raman_measurement_proxy = manager.list_raman_measurement_proxy()           # Proxy list for the measurements
    list_raman_integrationtime_proxy = manager.list_raman_integrationtime_proxy()   # Proxy list for the integration times
    list_raman_flg_retrieved_proxy = manager.list_raman_flg_retrieved_proxy()       # Proxy list for the flags (True if the measurement is retrieved)
    
    dict_raman_proxy.update({
        'timestamp_us_int':list_raman_timestamp_proxy,
        'raw_spectrum':list_raman_measurement_proxy,
        'integration_time_ms':list_raman_integrationtime_proxy,
        'flg_retrieved':list_raman_flg_retrieved_proxy,
    })
    return raman_ctrl_proxy,dict_raman_proxy
    
def test_initialise_cal_hub():
    """
    Initialisation of the calibrator GUI and the RamanMeasurementHub
    for other tests.
    
    Note:
        The hub has to be started (hub.start()) and the app has to be run
        (app.mainloop())
    """
    # Manager setups
    manager:MyManager = get_my_manager()
    initialise_manager_raman(manager)
    manager.start()
    
    raman_ctrl_proxy,dict_raman_proxy=initialise_proxy_raman(manager)
    
    hub = DataStreamer_Raman(controller=raman_ctrl_proxy,
                              dict_measurements=dict_raman_proxy)
    pipe_front = hub.get_calibrator_pipe()
    
    # Calibrator setup
    app = tk.Tk()
    calibrator_gui = Frm_SpectrometerCalibrationGenerator(app,pipe_front)
    calibrator_gui.pack()
    
    return hub,app

def test_calibrator():
    """
    Tests the calibrator
    """
    hub,app = test_initialise_cal_hub()
    hub.start()
    
    # Make a toplevel to show the obtained spectrum
    import matplotlib as mpl
    mpl.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import tkinter as tk
    
    toplvl = tk.Toplevel(app)
    fig,ax = plt.subplots()
    canvas = FigureCanvasTkAgg(fig,master=toplvl)
    canvas.get_tk_widget().pack()
    
    def update_plot():
        """
        Updates the plot
        """
        while True:
            ts = get_timestamp_us_int()
            list_ts,list_mea,_ = hub.get_measurement(timestamp_start=ts,WaitForMeasurement=False)
            mea = list_mea[-1]
            ax.clear()
            ax.plot(mea[DataAnalysisConfigEnum.WAVELENGTH_LABEL.value],mea[DataAnalysisConfigEnum.INTENSITY_LABEL.value])
            canvas.draw()
            
            time.sleep(0.1)
    
    threading.Thread(target=update_plot).start()
    
    app.mainloop()

def test():
    hub,app = test_initialise_cal_hub()
    hub.start()
    
    def report_now(ts_request=None):
        """
        Prints the timestamp now and the requested timestamp
        """
        if ts_request==None: ts_request = get_timestamp_us_int()
        
        ts = hub.get_measurement(timestamp_start=ts_request,
            WaitForMeasurement=False)[0][0]
        
        gap_ms = (ts_request-ts)/1000
        
        ts = convert_timestamp_us_int_to_str(ts)
        ts_request = convert_timestamp_us_int_to_str(ts_request)
        print('Gap: {}, Requested timestamp: {}, Returned timestamp: {}'\
            .format(gap_ms,ts_request,ts))
    
    def report_range(ts_start,ts_end=None):
        ts_list = hub.get_measurement(timestamp_start=ts_start,
            timestamp_end=ts_end,WaitForMeasurement=False)[0]
        ts_list = [convert_timestamp_us_int_to_str(ts) for ts in ts_list]
        ts_start = convert_timestamp_us_int_to_str(ts_start)
        ts_end = convert_timestamp_us_int_to_str(ts_end)
        print('Start timestamp: {}, End timestamp: {}'.format(ts_start,ts_end))
        print('Timestamps: {}'.format(ts_list))
    
    # Check the continuous measurement
    print('\nTest: continuous measurement')
    hub.resume_auto_measurement()
    time.sleep(0.2)
    for i in range(5):
        report_now()
        time.sleep(0.1)
    
    time.sleep(1)
    report_now()
    
    # Check the pause functionality
    print('\nTest: pause functionality. Sleep for 1 sec')
    hub.pause_auto_measurement()
    time.sleep(1)
    report_now()
    hub.resume_auto_measurement()
    
    # Check the range functionality
    print('\nTest: range functionality. Sleep for 0.5 sec')
    ts_start = get_timestamp_us_int()
    time.sleep(0.5)
    ts_end = get_timestamp_us_int()
    time.sleep(0.2)
    report_range(ts_start,ts_end)
    time.sleep(0.3)
    ts_end2 = get_timestamp_us_int()
    report_range(ts_end,ts_end2)
    
    ts_lists = hub._list_timestamps
    ts_lists = [convert_timestamp_us_int_to_str(ts) for ts in ts_lists]
    print('Timestamps in the hub: {}'.format(ts_lists))
    
    # while True:
    #     time.sleep(1)
        
    # Check the stop functionality
    print('\nTest: stop functionality')
    hub.terminate_process()
    hub.join()
    print('Test completed')
    
if __name__ == '__main__':
    test_calibrator()