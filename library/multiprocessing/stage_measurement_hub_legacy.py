"""
A hub that stores the coordinates from the stage controllers.
The hub is a multiprocessing process that runs in the background and is responsible for collecting the coordinates from 
the stage controllers and storing them in a dictionary. The hub also provides a method to retrieve the coordinates based
on the timestamp.

Idea:
- The hub will constantly run in the background, collecting the coordinates from the stage controllers.
- When required, e.g., for the mapping coordinate reference, the hub can be queried for the coordinates based on the timestamp.

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
import multiprocessing.managers as mpm
import types

from typing import cast

import threading

if __name__ == '__main__':
    import sys
    import os
    SCRIPT_DIR = os.path.abspath(r'.\library')
    sys.path.append(os.path.dirname(SCRIPT_DIR))


from library.general_functions import *
from library.multiprocessing.basemanager import MyManager, get_my_manager, StageNamespace

from library.controllers import ControllerConfigEnum
from library.controllers import XYController, ZController
    
from library.multiprocessing import MPMeaHubEnum

class stage_measurement_hub(mp.Process):
    def __init__(self,xy_controller:XYController,z_controller:ZController,dict_coor_proxy:mpm.DictProxy,
                 stage_namespace:StageNamespace):
        super().__init__()
        self.xy_controller = xy_controller
        self.z_controller = z_controller
        self._stg_namespc = stage_namespace
        
        # Setup operation parameters
        self._flg_process = mp.Event() # Flag for the process. Clear to terminate the entire process
        
        # Refresh rate
        # !!! Be careful with the refresh rate as it may overload the stage controllers !!!
        # To be save, set self._pause_interval to a value greater than 150 ms
        self._pause_interval = MPMeaHubEnum.STAGEHUB_REQUEST_INTERVAL.value # Interval between each coordinate collections in [ms]
        self._max_interval = MPMeaHubEnum.STAGEHUB_MAXINTERVAL.value # Maximum interval between each coordinate collections in [ms]
        self._stg_namespc.stage_offset_ms # Time offset between the get_coordinate() request and the retrieved coordinate in [ms]
        # self._measurement_offset_ms = MPMeaHubEnum.STAGEHUB_TIME_OFFSET_MS.value # Time offset between the get_coordinate() request and the retrieved coordinate in [ms]
        
        # Labels for the measurements
        self._lbl_ts = 'timestamp_us_int'
        self._lbl_coor = 'coordinates_xyz'
        
        self._max_measurement = MPMeaHubEnum.STAGEHUB_MAXSTORAGE.value # Maximum number of coordinates stored
        
        assert type(self._max_measurement) == int and self._max_measurement > 0,\
            'Maximum measurement has to be an integer'
        
        # Flags
        self._flg_pause_auto_collect = mp.Event() # Flag to pause the auto-collector. set to pause, clear to resume
        self._flg_pause_auto_collect.clear()
        self._flg_pause_updater = mp.Event()    # Flag to stop the updater. set to pause, clear to resume
        self._flg_pause_updater.clear()
        
        self._pause_interval_updater = 2      # Interval between each coordinate collections in [ms]
        
        # Set error margins
        self._allowable_timegap_ms = 10 # Allowable time gap between the requested timestamp and the closest timestamp in [ms]
        
        self._dict_measurements:mpm.DictProxy = dict_coor_proxy
        self._dict_measurements.update({self._lbl_ts: [], self._lbl_coor: []})  # Update using dict.update()
        
        self._list_measurements = []    # List of measurements to be updated
        
    def set_measurement_offset_ms(self,offset_ms:float):
        """
        Set the time offset between the get_coordinate() request and the retrieved coordinate in [ms]

        Args:
            offset_ms (float): Time offset in [ms]
        """
        assert isinstance(offset_ms,(float,int)), 'Offset has to be a float or an integer'
        self._stg_namespc.stage_offset_ms = offset_ms
        
    def get_measurement_offset_ms(self) -> float:
        """
        Get the time offset between the get_coordinate() request and the retrieved coordinate in [ms]

        Returns:
            float: Time offset in [ms]
        """
        return self._stg_namespc.stage_offset_ms
        
    def wait_CoorUpdate(self):
        """
        Waits for the coordinate to be updated. Automatically resumes the auto-updater.
        """
        self._resume_updater()
        length_ts = len(self._dict_measurements.get(self._lbl_ts))
        if length_ts > 0:
            timestamp_last = self._dict_measurements.get(self._lbl_ts)[-1]
            timestamp_init = timestamp_last
        else:
            timestamp_last = 0
            timestamp_init = 0
        
        # For debugging
        # print('Waiting for the coordinate to be updated...')
        # print('length_ts: {}, timestamp_last: {}, timestamp_init: {}'.format(length_ts,timestamp_last,timestamp_init))
        
        while len(self._dict_measurements.get(self._lbl_ts)) == 0 \
            or self._dict_measurements.get(self._lbl_ts)[-1] == timestamp_init:
            time.sleep(self._pause_interval_updater/1000)
        
    def _get_measurement_idx(self,timestamp:int):
        """
        Get the index of the measurement closest to the timestamp
        
        Args:
            timestamp (int): Timestamp in us
        """
        idx_min = 0
        list_ts = self._dict_measurements.get(self._lbl_ts)
        length = len(list_ts)
        for i in range(length):
            # Check for a smaller timestamp, scans from the latest to the oldest
            idx_check = i+1
            if list_ts[-idx_check] < timestamp:
                idx_min=length-(idx_check)
                break
            
        if idx_min == length-1:
            return idx_min
        else:
            return idx_min+1
        
    def get_coordinates_closest(self,timestamp_start:int,timestamp_end:int=None,WaitForCoor:bool=False) -> tuple[list,list]:
        """
        Get the coordinates between the timestamps.
        
        Args:
            timestamp_start (int): Timestamp in us
            timestamp_end (int): Timestamp in us. If None, return the coordinate closest to the timestamp_start
            WaitForCoor (bool): If True, wait until the coordinate is available.
            
        Returns:
            tuple[list,list]: Timestamps, Coordinates in [x,y,z]
            
        Note:
            Timestamps are in [us] integer format
        """
        try:
            assert all([type(timestamp_start) == int, timestamp_start >= 0,\
                type(timestamp_end)==int or timestamp_end==None]), 'Timestamp start has to be an integer'
            
            # Waits for a new coordinate to be stored if requested of if there is no measurement
            list_ts = self._dict_measurements.get(self._lbl_ts)
            if WaitForCoor or len(list_ts) == 0: self.wait_CoorUpdate()
            
            self._pause_updater() # Pause the updater to prevent the index conflicts
            # Waits for the coordinate to be stored by the updater if the latest stored timestamp
            # is still too far from the requested timestamp
            list_ts = self._dict_measurements.get(self._lbl_ts)
            if list_ts[-1] - timestamp_start < self._allowable_timegap_ms*1000:
                self.wait_CoorUpdate()
                self._pause_updater()
            
            if timestamp_end == None:
                idx = self._get_measurement_idx(timestamp_start)
                ts_list = [self._dict_measurements.get(self._lbl_ts)[idx]]
                coor_list = [self._dict_measurements.get(self._lbl_coor)[idx]]
                    
            else:
                # Makes sure that the start timestamp is smaller than the end timestamp
                assert timestamp_start <= timestamp_end, 'Start timestamp has to be smaller than the end timestamp'
                idx_start = self._get_measurement_idx(timestamp_start)
                idx_end = self._get_measurement_idx(timestamp_end)
                
                ts_list = self._dict_measurements.get(self._lbl_ts)[idx_start:idx_end+1]
                coor_list = self._dict_measurements.get(self._lbl_coor)[idx_start:idx_end+1]
                
            self._resume_updater()
            return (ts_list,coor_list)
        finally: # Automatically resume the updater even if an error occurs
            self._resume_updater()
        
    def get_coordinates_interpolate(self,timestamp:int,WaitForCoor:bool=False,InterpolateFuture:bool=False) -> tuple:
        """
        Get the coordinates by interpolating the coordinates between the timestamps (linear)
        
        Args:
            timestamp (int): Timestamp in us
            WaitForCoor (bool): If True, wait until the coordinate is available.
            InterpolateFuture (bool): If True, interpolate the future coordinates. If False, waits for a coordinate update
            such that it only interpolates the past coordinates.
        
        Returns:
            tuple: Coordinates in [x,y,z]
        """
        try:
            while True:
                assert type(timestamp) == int and timestamp >= 0, 'Timestamp has to be an integer'
                
                # Waits for a new coordinate to be stored if requested of if there is no measurement
                list_ts = self._dict_measurements.get(self._lbl_ts)
                if WaitForCoor:
                    self.wait_CoorUpdate()
                    
                [self.wait_CoorUpdate() for _ in range(2-len(list_ts))]
                
                self._pause_updater() # Pause the updater to prevent the index conflicts
                idx = self._get_measurement_idx(timestamp)
                
                if idx == len(self._dict_measurements.get(self._lbl_ts))-1:
                    self.wait_CoorUpdate()
                    self._pause_updater()
                    idx = self._get_measurement_idx(timestamp)
                
                coor1 = self._dict_measurements.get(self._lbl_coor)[idx]
                coor2 = self._dict_measurements.get(self._lbl_coor)[idx-1]
                
                ts1 = self._dict_measurements.get(self._lbl_ts)[idx]
                ts2 = self._dict_measurements.get(self._lbl_ts)[idx-1]
                
                if not timestamp < ts1:
                    if not InterpolateFuture:
                        self._resume_updater()
                        time.sleep(self._pause_interval/5)
                        continue
                    else:
                        ts_req_str = convert_timestamp_us_int_to_str(timestamp)
                        ts1_str = convert_timestamp_us_int_to_str(ts1)
                        ts2_str = convert_timestamp_us_int_to_str(ts2)
                        print('get_coordinates_interpolate: Interpolation outside the range of the measurements')
                        print('Requested timestamp: {}, Timestamps used: {} to {}'.format(
                            ts_req_str,ts1_str,ts2_str))
                    
                if idx < int(self._max_measurement/10) and len(self._dict_measurements.get(self._lbl_ts)) >= self._max_measurement:
                    print('!!!!! stage_measurement_hub: Coordinate reserve low -> increase self._max_measurement !!!!!')
                
                coor1x,coor1y,coor1z = coor1
                coor2x,coor2y,coor2z = coor2
                
                coorx_interp = coor1x + (coor2x-coor1x)*(timestamp-ts1)/(ts2-ts1)
                coory_interp = coor1y + (coor2y-coor1y)*(timestamp-ts1)/(ts2-ts1)
                coorz_interp = coor1z + (coor2z-coor1z)*(timestamp-ts1)/(ts2-ts1)
                
                # ## ><>< Debugging part
                # ts_req_str = convert_timestamp_us_int_to_str(timestamp)
                # ts1_str = convert_timestamp_us_int_to_str(ts1)
                # ts2_str = convert_timestamp_us_int_to_str(ts2)
                # print('Gap: {} ms, Requested timestamp: {}, Timestamps used: {} to {}'.format(
                #     (timestamp-ts1)/1000,ts_req_str,ts1_str,ts2_str))
                # print('coor1: {}, coor_interp: {}, coor2: {}'.format(coor1, (coorx_interp,coory_interp,coorz_interp), coor2))
                # ## ><>< Debugging part ends
                
                self._resume_updater()
                break
            return (coorx_interp,coory_interp,coorz_interp)
        finally: # Automatically resume the updater even if an error occurs
            self._resume_updater()
        
    def pause_auto_collect(self):
        """
        Pause the auto-collector (device to the temporary list)
        """
        self._flg_pause_auto_collect.set()
        
    def resume_auto_collect(self):
        """
        Resume the auto-collector (device to the temporary list)
        """
        self._flg_pause_auto_collect.clear()
        
    def _pause_updater(self):
        """
        Pause the updater (temporary list to the storage)
        """
        self._flg_pause_updater.set()
        
    def _resume_updater(self):
        """
        Resume the updater (temporary list to the storage)
        """
        self._flg_pause_updater.clear()
        
    def _auto_update(self):
        """
        Automatically update the measurements
        """
        while True:
            if self._flg_pause_updater.is_set():
                time.sleep(self._pause_interval_updater/1000)
                continue
            try:
                measurements = self._list_measurements.pop(0)
                self._set_coordinates(*measurements)
            except IndexError:
                time.sleep(self._pause_interval_updater/1000)
            except Exception as e:
                print('_auto_update:')
                print(e)
                time.sleep(self._pause_interval_updater/1000)
                
    def _set_coordinates(self,timestamp,coor_xyz):
        """
        Stores the coordinates in the dictionary
        
        Args:
            timestamp (int): Timestamp in us
            coor_xyz (tuple): Coordinates in [x,y,z]
        """
        list_ts:list = self._dict_measurements.get(self._lbl_ts)
        list_coor:list = self._dict_measurements.get(self._lbl_coor)
        
        # Store the measurements
        list_ts.append(timestamp)
        list_coor.append(coor_xyz)
        
        self._dict_measurements.update({self._lbl_ts: list_ts, self._lbl_coor: list_coor})
        
        # Remove the oldest measurement if the maximum number of measurements is reached
        if len(list_ts) > self._max_measurement:
            cols = self._dict_measurements.keys()
            for col in cols:
                self._dict_measurements.get(col).pop(0)
        
        # # For debugging
        # list_ts:list = self._dict_measurements.get(self._lbl_ts)
        # list_coor:list = self._dict_measurements.get(self._lbl_coor)
        # print('Timestamp: {}, Coordinates: {}'.format(list_ts[-1],list_coor[-1]))
        
    def run(self):
        print('>>>>>> Stage hub is running <<<<<<')
        threading.Thread(target=self._collect_coordinate).start()
        threading.Thread(target=self._auto_update).start()
    
    def _collect_coordinate(self):
        try:
            self._flg_process.set()
            last_timestamp = 0
            while self._flg_process.is_set():
                if self._flg_pause_auto_collect.is_set():
                    time.sleep(self._pause_interval*1e-3)
                    continue
                try:
                    timestamp = get_timestamp_us_int() + self._stg_namespc.stage_offset_ms*1e3
                    coorx,coory = self.xy_controller.get_coordinates()
                    coorz = self.z_controller.get_coordinates()
                    
                    # Store the measurements
                    coor = (coorx,coory,coorz)
                    measurements = (timestamp,coor)
                    
                    if len(self._dict_measurements.get(self._lbl_coor,[])) > 0:
                        gap = int((timestamp-self._dict_measurements.get(self._lbl_ts,[])[-1])/1000)
                        if coor == self._dict_measurements.get(self._lbl_coor,[])[-1] \
                            and gap < self._max_interval:
                            time.sleep(self._pause_interval*1e-3)
                            continue
                        
                    # # ><>< Debugging part ><><
                    #     print('timestamp gap: {}, coor_xyz: {}'.format(gap,coor))
                    # print('timestamp: {}, coorx: {}, coory: {}, coorz: {}'.format(timestamp,coorx,coory,coorz))
                    # # ><>< Debugging part ends ><><
                    
                    self._list_measurements.append(measurements)
                    
                    # Pause for a while to prevent overloading the system
                    time.sleep(self._pause_interval*1e-3)
                except Exception as e:
                    print('_collect_coordinate:')
                    print(e)
                    time.sleep(self._pause_interval*1e-3)
                    continue
        finally: # Automatically terminate the process
            self.join()
            
    def join(self, timeout: float | types.NoneType = None) -> types.NoneType:
        self._flg_process.clear()
        return super().join(timeout)

def initialise_manager_stage(manager:MyManager):
    """
    Register the classes and the dictionary with the manager
    
    Args:
        manager (MyManager): The central base manager
    """
    manager.register('xyctrl',callable=XYController)
    manager.register('zctrl',callable=ZController)
    manager.register('dict_coor',dict)

def initialise_proxy_stage(manager:MyManager) -> tuple[XYController,ZController,dict,mpm.ValueProxy,StageNamespace]:
    """
    Initialise the proxies for the stage controllers and the dictionary
    
    Args:
        manager (MyManager): Manager instance
    
    Returns:
        tuple: xyproxy, zproxy, dict_coor_proxy, namespace
    """
    zproxy:ZController = manager.zctrl(sim=ControllerConfigEnum.SIMULATION_MODE.value)
    xyproxy:XYController = manager.xyctrl(sim=ControllerConfigEnum.SIMULATION_MODE.value)
    dict_coor_proxy:dict = manager.dict_coor()
    
    stg_namespace:StageNamespace = manager.Namespace()
    stg_namespace.stage_offset_ms = MPMeaHubEnum.STAGEHUB_TIME_OFFSET_MS.value
    
    return xyproxy,zproxy,dict_coor_proxy,stg_namespace

def test_basic():
    manager_base:mpm.SyncManager = get_my_manager()
    initialise_manager_stage(manager_base)
    manager_base.start()
    xyproxy,zproxy,dict_coor_proxy,stage_namespace = initialise_proxy_stage(manager_base)
    
    hub = stage_measurement_hub(xyproxy,zproxy,dict_coor_proxy,stage_namespace)
    hub.start()
    
    threading.Thread(target=xyproxy.movementtest).start()
    # while True:
    #     try:
    #         ts_req = get_timestamp_us_int()
    #         ts_list,coor_list = hub.get_coordinates_closest(ts_req)
    #         ts_res,coor = ts_list[-1],coor_list[-1]
    #         gap_ms = (ts_res-ts_req)/1000
    #         ts_req = convert_timestamp_us_int_to_str(ts_req)
    #         ts_res = convert_timestamp_us_int_to_str(ts_res)
    #         print('Gap: {} ms, Timestamp request {} -> return {}, Coordinates: {}'
    #               .format(gap_ms,ts_req,ts_res,coor))
    #     except Exception as e:
    #         print('test_basic:')
    #         print(e)
    #     time.sleep(0.05)
    
    while True:
        try:
            ts_req = get_timestamp_us_int()
            coor = hub.get_coordinates_interpolate(ts_req,WaitForCoor=False,InterpolateFuture=False)
            ts_req = convert_timestamp_us_int_to_str(ts_req)
            print('Timestamp request {}, Coordinates: {}'.format(ts_req,coor))
        # except Exception as e:
        #     print('test_basic:')
        #     print(e)
        finally:
            time.sleep(0.05)
    
if __name__ == '__main__':
    test_basic()