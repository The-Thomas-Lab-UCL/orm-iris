"""
This is a Python script that handles the control of the Physik Instrumente (PI)
U-751.24 XY stage controller. To be used with the Open Raman Microscopy (ORM) controller
app.
"""
import os
import sys

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

# from pipython import GCSDevice
from pipython import GCSDevice
from pipython import GCS2Device
from pipython import GCS30Commands
from pipython import pitools, datarectools

from iris.utils.general import thread_assign, get_timestamp_us_int
from iris.controllers.class_xy_stage_controller import Class_XYController

from typing import OrderedDict, Literal

import numpy as np
import pandas as pd
import threading
import time

from multiprocessing import Lock, Event
from multiprocessing.synchronize import Event as Event_class

from iris.controllers import ControllerConfigEnum, ControllerSpecificConfigEnum, ControllerDirectionEnum

def test():
    TRACE_ID_1 = 1
    TRACE_ID_2 = 2

    PARAMETER_1 = [ 'AXIS_1', '-', '0x102' ]
    PARAMETER_2 = [ 'AXIS_1', '-', '0x103' ]
    
    timestamp_header = 'SAMPLE_TIME'
    axis1_pos_header = 'NAME0'
    axis2_pos_header = 'NAME1'
    
    with GCSDevice() as pidevice:
        # for typehinting
        pidevice:GCS30Device
        
    # >> Test connection <<
        pidevice.ConnectUSB(serialnum='')
        print('connected: {}'.format(pidevice.qIDN().strip()))
    
    # >> Test axes names <<
        axis1 = pidevice.axes[0]
        axis2 = pidevice.axes[1]
        allaxes = pidevice.allaxes
        print(pitools.getmintravelrange(pidevice, pidevice.axes[:2]))
        print(pitools.getmaxtravelrange(pidevice, pidevice.axes[:2]))
        
        # Get max velocity
        pidevice.VEL(allaxes, [10]*2)
        # print('Max velocity 1: {}'.format(pidevice.qSPA(axis1, 0xA)))
        # print('Max velocity 2: {}'.format(pidevice.qSPA(axis2, 0xA)))
        
        # print('Max acceleration 1: {}'.format(pidevice.qSPA(axis1, 0xB)))
        # print('Max acceleration 2: {}'.format(pidevice.qSPA(axis2, 0xB)))
        
        # print('Max deceleration 1: {}'.format(pidevice.qSPA(axis1, 0xC)))
        # print('Max deceleration 2: {}'.format(pidevice.qSPA(axis2, 0xC)))

        # print('Profile mode 1: {}'.format(pidevice.qSPA(axis1, 0x1B)))  # 0: trapezoidal, 1: piont to point
        # print('Profile mode 2: {}'.format(pidevice.qSPA(axis2, 0x1B)))  # 0: trapezoidal, 1: piont to point
        
        # print(pidevice.qHPV())
        print(pidevice.qSEP(axis1,0xE000102))
        
        # pidevice.SPA(axis1, 0xE002712, 1)
        # pidevice.SPA(axis2, 0xE002712, 1)
        
        # pidevice.SPA(axis1, 0xE002702, 1)
        # pidevice.SPA(axis2, 0xE002702, 1)
        
        # print('Active features: {}'.format(pidevice.qVER()))
        
        # print('Current velocity: {} and {}'.format(pidevice.qVEL(axis1), pidevice.qVEL(axis2)))
        
        # print(pidevice.qHDR())
        return
        
    # >> Recording setup <<

        pidevice.RTR(10)     # Record every servo cycle
        
        # Set up data recorder
        pidevice.DRC(1,axis1,44)
        pidevice.DRC(2,axis1,2)
        pidevice.DRC(3,axis2,2)
        
        # pidevice.DRT(0,2,0)
        # pidevice.STE(axis1,0)
        
        def get_data():
            pidevice.DRT(0,2,0) # Trigger on next command
            odict_len = pidevice.qDRL()
            len = odict_len[1]
            print('Length: {}'.format(len))
            header = pidevice.qDRR([1,2,3],len,1)
            while not pidevice.bufstate:
                data = pidevice.bufdata
            print(pd.DataFrame(data).head())
            timestamp_mm = data[0][-1]
            axis1_pos_mm = data[1][-1]
            axis2_pos_mm = data[2][-1]
            return timestamp_mm, axis1_pos_mm, axis2_pos_mm
        
        # Wait for the recording to be ready
        init_time = time.time()
        timestamp, axis1_pos, axis2_pos = get_data()
        init_ts = timestamp
        print('Initial time: {}'.format(init_time))
        print('Timestamp, Axis 1, Axis 2: {}, {}, {}'.format(timestamp, axis1_pos, axis2_pos))
        time.sleep(0.01)
            
        
    # # >> Test moving with varying velocity <<
    #     @thread_assign
    #     def report_position(flg_stop:threading.Event):
    #         while not flg_stop.is_set():
    #             print('Position: {}'.format(pidevice.qPOS(allaxes)))
    #             time.sleep(0.5)

    #     # flag setup for position report
    #     flg_stop = threading.Event()

    #     # Set velocity and 1st target
    #     pidevice.VEL('1', 10)
    #     pidevice.MOV('1', 0)
    #     pidevice.MOV('2', 0)
    #     # report_position(flg_stop)
    #     pitools.waitontarget(pidevice, axis1)
    #     flg_stop.set()

    #     # Set velocity and 2nd target
    #     pidevice.VEL('1', 3)
    #     pidevice.MOV('1', 25)
    #     pidevice.MOV('2', 25)

    #     # Check if axis is moving and how the controller behaves
    #     flg_stop = threading.Event()
    #     ordered_dict = pidevice.IsMoving(axis1)
    #     movingstate = ordered_dict[axis1]
    #     print('Axis {} is moving: {}'.format(axis1, movingstate))

    #     # Wait until target is reached
    #     # report_position(flg_stop)
    #     pitools.waitontarget(pidevice, axis1)
    #     flg_stop.set()
    #     print(pidevice.IsMoving(axis1))
        
        # Test readout
        # pidevice.DRT(0, 2, 0)  # Trigger on next command
        # pidevice.STE(axis1,0)
        # Read the last 16384 data points from both axes
        
        print(pidevice.qDRL())
        timestamp, axis1_pos, axis2_pos = get_data()
        final_ts = timestamp
        final_time = time.time()
        print('Final time: {}'.format(final_time))
        print('Timestamp, Axis 1, Axis 2: {}, {}, {}'.format(timestamp, axis1_pos, axis2_pos))
        
        print('Time difference: {}'.format(final_time-init_time))
        print('Timestamp difference: {}'.format(final_ts-init_ts))
        
        print('>>> Test complete <<<\n')
        
        # print(pidevice.qPOS('1'))
        

class XYController_PI(Class_XYController):
    def __init__(self,sim=None):
        """
        Initialises the xy stage controller class.
        
        Args:
            sim (bool, optional): Not used in this case
        
        Important note:
            When developing this for use with image capture-related functionalities,
            the x-axis has to be the horizontal axis in the image capture and y-axis for 
            the vertical axis. Otherwise some of the image processing functions will not work.
        """
        self.device:GCS2Device = None
        self._serial_no = ControllerSpecificConfigEnum.PISTAGE_SERIAL.value

        # Axes names placeholder
        self._allaxes = None

        # Axes control remapping
        self.dict_ctrl_remap = {
            'xfwd':ControllerDirectionEnum.XFWD.value,
            'xrev':ControllerDirectionEnum.XREV.value,
            'yfwd':ControllerDirectionEnum.YFWD.value,
            'yrev':ControllerDirectionEnum.YREV.value,
        }   # Dictionary to remap the controls (only for the continuous and jog movements)
        
        self._flipxy = ControllerConfigEnum.STAGE_FLIPXY.value      # Flag to indicate if the x and y axes are flipped
        self._invertx = ControllerConfigEnum.STAGE_INVERTX.value   # Flag to indicate if the x-axis is flipped (inversed, *= -1)
        self._inverty = ControllerConfigEnum.STAGE_INVERTY.value   # Flag to indicate if the y-axis is flipped (inversed, *= -1)
        
        self._dict_axes = { # Placeholder for the axes names
            'x':None,
            'y':None
        }

        # Movement parameters setup
        self._max_vel_mmPerSec:float = None     # Maximum velocity in mm/s
        self._min_vel_mmPerSec:float = None     # Minimum velocity in mm/s
        self._vel_mmPerSec:float = None         # Current velocity in mm/s
        
        self._max_acc_mmPerSec2:float = 250.0   # Maximum acceleration in mm/s^2
        self._min_acc_mmPerSec2:float = 0.01    # Minimum acceleration in mm/s^2
        
        self._slow_vel_tresh_mmPerSec:float = 2.0   # Threshold velocity for slow movements
        self._slow_jogsize_mm:float = 1e-3          # Jog size for slow movements [mm]
        self._slow_minJogsize_mm:float = 1e-4       # Minimum jog size for slow movements [mm]
        self._slow_commRate_ms:float = ControllerSpecificConfigEnum.PI_SLOW_COMRATE_MS.value  # Command rate for slow movements [ms]
        self._slow_flg_stop = Event()               # Flag to stop the slow movement
        self._slow_stepsize_modifier = 1.1          # Modifier for the step size when it's too slow (to dynamically increase the step size)
        
        self._min_travelx:float = None
        self._min_travely:float = None
        self._max_travelx:float = None
        self._max_travely:float = None

        self._jog_min_mm:float = 0.001
        self._jog_max_mm:float = 1.0
        self._jog_mm:float = 1
        
        # Coordinate logging setup
        self._init_uptime_us = None         # Initial uptime in microseconds
        self._init_uptime_TsRef_us = None   # Reference timestamp in microseconds
        self._delay_ms = 0                  # Delay in milliseconds
        
        self._lock = Lock()
        
        # Calculation initialisation
        self._max_vel_mmS = self._max_vel_mmPerSec  # Maximum velocity of the motor in mm/s
        self._min_vel_mmS = self._min_vel_mmPerSec  # Minimum velocity of the motor in mm/s
        
        self._flg_isrunning_autoreconnect = threading.Event()
        self._reconnect_freq_sec = 3600 * ControllerSpecificConfigEnum.PISTAGE_AUTORECONNECT_HOURS.value
        if self._reconnect_freq_sec > 0:
            self._thread_reconnect = threading.Thread(target=self.auto_reconnect)
            self._thread_reconnect.start()
        # Data recorder setup
        self._flg_useDrec = ControllerSpecificConfigEnum.PISTAGE_DEVTIMESTAMP.value # To activate/deactivate the data recorder
        
        # Initialises the device
        self._identifier = None
        try: self.initialisation()
        except Exception as e: print(f'__init__ Error: {e}')
        
    def get_identifier(self) -> str:
        try:
            if self._identifier is None:
                self._identifier = self._get_hardware_identifier()
        except Exception as e:
            self._identifier = f'Error getting identifier: {e}'
        return self._identifier
    
    def _get_hardware_identifier(self) -> str:
        """
        Returns the hardware identifier of the stage.

        Returns:
            str: The hardware identifier of the stage
        """
        if self._devname is None:
            with self._lock: self._devname = self.device.devname
        serialnum = self._serial_no
        return f"Physik Instrumente device model: {self._devname}, S/N:{serialnum}"

    def auto_reconnect(self) -> None:
        """
        Automatically reconnect to the device after some time
        """
        self._flg_isrunning_autoreconnect.set()
        print('Auto-reconnect thread started')
        while self._flg_isrunning_autoreconnect.is_set():
            time.sleep(self._reconnect_freq_sec)
            print('Attempting to forcefully reconnect to the device...')
            try:
                self.reinitialise_connection()
                print('Forcefully reconnected the device')
            except Exception as e:
                print(f'Error during reconnection: {e}')
                continue
        
    def reinitialise_connection(self) -> None:
        """
        Reinitialise the connection to the device
        """
        coor = np.array(self.get_coordinates())
        while True:
            self._flg_movedone.wait(timeout=5)
            new_coor = np.array(self.get_coordinates())
            if np.allclose(coor, new_coor, atol=1e-3): break
            coor = new_coor
            
        print('Terminating')
        try: self.terminate()
        except Exception as e: print(f'reinitialise_connection Error: {e}')
        
        print('Reinitialising')
        try: self.initialisation()
        except Exception as e: print(f'reinitialise_connection Error: {e}')
        
    def _remap_coordinates_flip(self,coor:tuple[float,float],get:bool) -> tuple[float,float]:
        """
        Remaps the coordinates if the x and y axes are flipped
        
        Args:
            coor (tuple[float,float]): the coordinate to remap
            get (bool): True if the coordinate is to be retrieved, False if the coordinate is to be set
                this is to ensure that the flip is done before/after the inversion of the axes depending on the get flag
        
        Returns:
            tuple[float,float]: the remapped coordinate
        """
        x,y = coor
        if self._flipxy and get:
            x,y = y,x
        if self._invertx:
            x = -1*x
        if self._inverty:
            y = -1*y
        if self._flipxy and not get:
            x,y = y,x
        # Note:
        # The flip is done before/after the inversion of the axes depending on the get flag because
        # a matrix multiplication is not commutative. i.e., A*B != B*A
        return (x,y)
        
    def initialisation(self):
        self.device:GCS2Device = GCSDevice()
        
        try: self.device.ConnectUSB(serialnum=self._serial_no)
        except Exception as e: assert False, f'Error during connection (typically device serial number is not found): {e}'
        print('connected: {}'.format(self.device.qIDN().strip()))
        
        # Get axes names
        ## NOTE: Flip the axes indices if the stage is mounted in a different orientation
        ## make sure that the x-axis is the horizontal axis in the image capture and y-axis for
        self._allaxes = self.device.allaxes
        self._dict_axes = {
            'x':self.device.axes[1],
            'y':self.device.axes[0]
        }
        
        # Get max velocity
        pass # Todo: Get max velocity and acceleration from the device
        # self._max_vel_mmPerSec:float = 50.0
        # self._min_vel_mmPerSec:float = 0.01
        
        # self._max_acc:float = 250.0
        # self._min_acc:float = 0.01
        
        # Get max acceleration and deceleration 
        pass
        
        # Enable the servos
        self.device.SVO(self._allaxes, [1]*2)
        
        # Get max velocity
        self._max_vel_mmPerSec:float = 25.0
        self._min_vel_mmPerSec:float = 0.0001

        # Get max travel range
        minrange = pitools.getmintravelrange(self.device, self.device.allaxes)
        maxrange = pitools.getmaxtravelrange(self.device, self.device.allaxes)
        self._min_travelx, self._min_travely = minrange[self._dict_axes['x']], minrange[self._dict_axes['y']]
        self._max_travelx, self._max_travely = maxrange[self._dict_axes['x']], maxrange[self._dict_axes['y']]
        
        # # Set velocity and acceleration
        # self.get_vel_acc_relative()
        
    # # >> Recording setup <<
    #     self.device.RTR(1)     # Record every servo cycle
        
    #     # Set up data recorder
    #     self.device.DRC(1,self._dict_axes['x'],44)
    #     self.device.DRC(2,self._dict_axes['x'],2)
    #     self.device.DRC(3,self._dict_axes['y'],2)
        
        if self._flg_useDrec:
            # Set the initial uptime
            self._init_uptime_us = int(self.device.qTIM()*1e3)
        else: self._init_uptime_us = get_timestamp_us_int()
        
        self._init_uptime_TsRef_us = get_timestamp_us_int()
        
        # Calculation initialisation
        self._max_vel_mmS = self._max_vel_mmPerSec  # Maximum velocity of the motor in mm/s
        self._min_vel_mmS = self._min_vel_mmPerSec  # Minimum velocity of the motor in mm/s
        
        time.sleep(4)  # Wait for the device to be ready
        
        self._flg_isrunning_autoreconnect.set()
        self._flg_movedone = Event()
        self._flg_movedone.clear()
        
    def _convert_uptime_to_timestamp(self,uptime_us:int) -> int:
        """
        Converts the uptime in microseconds to a timestamp
        
        Args:
            uptime_us (int): the uptime in microseconds
        
        Returns:
            int: the timestamp in microseconds
        """
        diff_us = uptime_us - self._init_uptime_us
        timestamp_us = self._init_uptime_TsRef_us + diff_us + self._delay_ms*1e3
        return timestamp_us
        
    def _dev_ReadDataRecorder(self) -> tuple[int,float,float]:
        """
        Function to read the data recorder of the device
        
        Returns:
            tuple[int,float,float]: 3 elements: (timestamp_us, axis1_pos_mm, axis2_pos_mm)
        """
        while not self.device.IsControllerReady():
            time.sleep(0.01)
        with self._lock:
            if self._flg_useDrec:
                timestamp_us = int(self.device.qTIM()*1e3)
            else: timestamp_us = get_timestamp_us_int()
            pos = self.device.qPOS(self._allaxes)
            axis1_pos_mm = pos[self._dict_axes['x']]
            axis2_pos_mm = pos[self._dict_axes['y']]
        
        return timestamp_us, axis1_pos_mm, axis2_pos_mm
    
    def terminate(self,close_connection=True):
        """
        Terminate the operation. Returns the stage to home and disconnects the device.
        
        Args:
            close_connection (bool): True to close the connection to the device
        """
        while not self.device.IsControllerReady(): time.sleep(0.01)
        if close_connection:
            self._flg_isrunning_autoreconnect.clear()  # Stop the auto-reconnect thread
            with self._lock:
                self.device.CloseConnection()
            
    def calculate_vel_relative(self, speed_mm_s:float) -> float:
        """
        Calculates the relative velocity parameter for the motor given the speed in mm/s

        Args:
            speed_mm_s (float): The speed to be converted in mm/s

        Returns:
            float: The relative velocity parameter in percentage
        """
        # Adjust the speed to the limits if it is out of bounds
        if not abs(speed_mm_s/self._min_vel_mmS) > 1:
            speed_mm_s = self._min_vel_mmS
            print(f'!!!!! The requested speed is out of bounds. Adjusted to minimum speed {self._min_vel_mmS} [mm/s] !!!!!')
        if not abs(speed_mm_s/self._max_vel_mmS) < 1:
            speed_mm_s = self._max_vel_mmS
            print(f'!!!!! The requested speed is out of bounds. Adjusted to maximum speed {self._max_vel_mmS} [mm/s] !!!!!')
        
        # Calculate the relative speed
        speed_rel = abs(speed_mm_s/self._max_vel_mmS * 100)
        
        return speed_rel
    
    def set_vel_acc_relative(self,vel_homing:float=100, vel_move:float=100, acc_move:float=100):
        """
        Set the velocity and acceleration parameters of the motors for both homing and typical movements.
        
        Args:
            vel_homing (int, optional): Legacy parameter. Is ignored.
            vel_move (int, optional): New motor movement velocity in percentage of max velocity. Defaults to 100.
            acc_move (int, optional): Legacy parameter. Is ignored.
        """
        assert 0 < vel_move <= 100, 'Velocity must be between 0 and 100'

        # Set velocity
        vel_mmPerSec = self._max_vel_mmPerSec * vel_move / 100
        
        while not self.device.IsControllerReady(): time.sleep(0.01)
        with self._lock: self.device.VEL(self._allaxes, [vel_mmPerSec]*2)
        
        self._vel_mmPerSec = vel_mmPerSec

    def get_vel_acc_relative(self):
        """
        Returns the current velocity and acceleration parameters of the motors

        Returns:
            tuple of floats: 3 elements: (vel_homing, vel_move, acc_move)
        """
        while not self.device.IsControllerReady(): time.sleep(0.01)
        with self._lock: dict_relvel = self.device.qVEL(self._allaxes)
        relvel1 = dict_relvel[self._dict_axes['x']] / self._max_vel_mmPerSec * 100
        relvel2 = dict_relvel[self._dict_axes['y']] / self._max_vel_mmPerSec * 100

        if relvel1 != relvel2: print('Axes have different velocities'); self._vel_mmPerSec = relvel1

        return (100, relvel1, 100)

    def report_attributes(self):
        print("\n>>>>> Device and motor attributes <<<<<")
        for attr, value in vars(self).items():
            print(f"{attr}: {value}")

    def get_coordinates(self):
        """
        Returns the current motor coordinates
        
        Returns:
            tuple of floats: 2 elements: (coor_x, coor_y), in millimetre (float)
        """
        def interpolate_coor(target_ts:int,list_ts:list[int],list_coor_x:list[float],
                             list_coor_y:list[float]) -> tuple[float,float]:
            """
            Interpolates the coordinates based on the timestamps
            
            Args:
                target_ts (int): the target timestamp to retrieve the coordinates
                list_ts (list[int]): list of timestamps
                list_coor_x (list[float]): list of x coordinates
                list_coor_y (list[float]): list of y coordinates
                
            Returns:
                tuple[float,float]: the interpolated coordinates
            """
            assert len(list_ts) == len(list_coor_x) == len(list_coor_y) == 2,\
            "Length of the lists must be 2"
            assert list_ts[0] < target_ts < list_ts[1], "Target timestamp must be within the range"
            
            # Interpolate the coordinates
            coor_x = np.interp(target_ts,list_ts,list_coor_x)
            coor_y = np.interp(target_ts,list_ts,list_coor_y)
            return (coor_x,coor_y)
        
        ts_request = get_timestamp_us_int()
        ts_return = []
        coor_x_return = []
        coor_y_return = []
        
        while True:
            ts, coor_x, coor_y = self._dev_ReadDataRecorder()
            ts = self._convert_uptime_to_timestamp(ts)
            ts_return.append(ts)
            coor_x_return.append(coor_x)
            coor_y_return.append(coor_y)
            if ts >= ts_request: break
            time.sleep(1/1000)  # delay to prevent overloading the comm port
            
        if len(ts_return) == 1:
            coor_x, coor_y = coor_x_return[-1], coor_y_return[-1]
        else:
            coor_x, coor_y = interpolate_coor(ts_request,ts_return[-2:],
                coor_x_return[-2:],coor_y_return[-2:])
            
        coor_x, coor_y = self._remap_coordinates_flip((coor_x,coor_y),get=True)
        
        return (coor_x, coor_y)
    
    def get_coordinates_ts(self) -> tuple[int,float,float]:
        """
        Returns the current motor coordinates and timestamp
        
        Returns:
            tuple[int,float,float]: 3 elements: (timestamp_us, coor_x, coor_y), in microseconds and millimetre (float)
        """
        ts_request = get_timestamp_us_int()
        ts_return = []
        coor_x_return = []
        coor_y_return = []
        
        while True:
            ts, coor_x, coor_y = self._dev_ReadDataRecorder()
            ts = self._convert_uptime_to_timestamp(ts)
            ts_return.append(ts)
            coor_x_return.append(coor_x)
            coor_y_return.append(coor_y)
            if ts >= ts_request: break
            time.sleep(1/1000)  # delay to prevent overloading the comm port
            
        ts = ts_return[-1]
        coor_x, coor_y = coor_x_return[-1], coor_y_return[-1]
        
        return (ts, coor_x, coor_y)
    
    def get_coordinates_old(self):
        while not self.device.IsControllerReady(): time.sleep(0.01)
        with self._lock: positions = self.device.qPOS(self.device.allaxes)
        x,y = positions[self._dict_axes['x']], positions[self._dict_axes['y']]
        
        x,y = self._remap_coordinates_flip((x,y),get=True)
        return (x,y)
    
    def homing_n_coor_calibration(self):
        """
        A function to recalibrate the coordinate system of the device.
        - Also called as 'homing'
        """

        # Set velocity
        self.set_vel_acc_relative(vel_homing=100, vel_move=100, acc_move=100)

        # Move to home position
        while not self.device.IsControllerReady(): time.sleep(0.01)
        with self._lock: self.device.FRF(self._allaxes)
        pitools.waitontarget(self.device, self._allaxes)
        print(">>>>> Coordinate calibration/Homing finished <<<<<")

    def move_direct(self,coor_abs:tuple[float,float],remap:bool=True):
        """
        Function to direct the motors to move at the same time towards a certain coordinate.

        Args:
            coor_abs (tuple[float,float]): the absolute coordinate to move to in [mm]
            remap (bool): Option to remap the coor according to the set flip (made specifically
                for jog)
        """
        print(f'Moving to coordinates: {coor_abs}')
        
        if remap: coor_abs = self._remap_coordinates_flip(coor_abs,get=False)
        
        print(f'Remapped coordinates: {coor_abs}')
        
        assert self._min_travelx <= coor_abs[0] <= self._max_travelx, 'Coordinate x is out of range'
        assert self._min_travely <= coor_abs[1] <= self._max_travely, 'Coordinate y is out of range'
        
        # if self._vel_mmPerSec < self._slow_vel_tresh_mmPerSec:
        #     self._move_direct_slow(coor_abs)
        # else:
        #     with self._lock: self.device.MOV([self._dict_axes['x'],self._dict_axes['y']], coor_abs)
            
        #     # Wait until target is reached
        #     pitools.waitontarget(self.device, self._allaxes)
        
        while not self.device.IsControllerReady(): time.sleep(0.01)
        self._flg_movedone.clear()
        with self._lock: self.device.MOV([self._dict_axes['x'],self._dict_axes['y']], coor_abs)
        
        # Wait until target is reached
        pitools.waitontarget(self.device, self._allaxes)
        self._flg_movedone.set()
            
        return
    
    def move_continuous(self,dir:str):
        """
        Moves the motor with a continuous motion until a stop command
        
        Args:
            dir (str): 'xfwd', 'xrev', 'yfwd', 'yrev' for the direction of the movement
        """
        assert dir in ['xfwd','xrev','yfwd','yrev'], 'Invalid direction'

        dir = self.dict_ctrl_remap[dir]
        
        while not self.device.IsControllerReady(): time.sleep(0.01)
        with self._lock:
            self._flg_movedone.clear()
            if dir == 'xfwd': self.device.MOV(self._dict_axes['x'], self._max_travelx)
            elif dir == 'xrev': self.device.MOV(self._dict_axes['x'], self._min_travelx)
            elif dir == 'yfwd': self.device.MOV(self._dict_axes['y'], self._max_travely)
            elif dir == 'yrev': self.device.MOV(self._dict_axes['y'], self._min_travely)

    def stop_move(self):
        """
        Stops the continuous movement of the motors by sending a new
        target position to the current position
        """
        while not self.device.IsControllerReady(): time.sleep(0.01)
        with self._lock: self.device.HLT(self._allaxes,noraise=True)
        self._flg_movedone.set()
        return

    def get_jog(self):
        """
        Returns the current jog step in [mm]:
        
        Returns:
            tuple of floats: 6 elements:
            (jog_step_x, jog_step_y, jog_vel_x, jog_vel_y, jog_acc_x, jog_acc_y)
        """
        return (self._jog_mm, self._jog_mm, self._vel_mmPerSec, self._vel_mmPerSec, 0, 0)
    
    def set_jog(self,dist_mm:float,vel_rel:int=100,acc_rel:int=100):
        """
        Set the jog parameters for the motor
        
        Args:
            dist_mm (float): distance to jog in mm
            vel_rel (int, optional): Legacy parameter. Is ignored.
            acc_rel (int, optional): Legacy parameter. Is ignored.
        """
        assert self._jog_min_mm <= dist_mm <= self._jog_max_mm, 'Jog distance is out of range'
        assert 0 <= vel_rel <= 100, 'Velocity must be between 0 and 100'
        assert 0 <= acc_rel <= 100, 'Acceleration must be between 0 and 100'

        # Set velocity
        ## Currently not implemented. i.e., it will jog at the same velocity as
        ## the last set velocity

        self._jog_mm = dist_mm

    def move_jog(self,direction:str):
        """
        Moves the motor with a single jogging motion.
        
        Args:
            direction (str): 'xfwd', 'xrev', 'yfwd', 'yrev' for the direction of the jog.
        """
        assert direction in ['xfwd','xrev','yfwd','yrev'], 'Invalid direction'
        
        direction = self.dict_ctrl_remap[direction]
        
        coor = self.get_coordinates()
        coor = self._remap_coordinates_flip(coor,get=False)
        
        self._flg_movedone.clear()
        if direction == 'xfwd': coor = (coor[0]+self._jog_mm, coor[1])
        elif direction == 'xrev': coor = (coor[0]-self._jog_mm, coor[1])
        elif direction == 'yfwd': coor = (coor[0], coor[1]+self._jog_mm)
        elif direction == 'yrev': coor = (coor[0], coor[1]-self._jog_mm)
        self.move_direct(coor,remap=False)
        pitools.waitontarget(self.device,self._allaxes)
        self._flg_movedone.set()
        
        return
    
    def movementtest(self):
        print("\n>>>>> MOTOR TEST: CIRCULAR MOTION <<<<<")
        # Create circle coordinates
        angles = np.arange(0, 2 * np.pi, 0.25)
        radius = 10.0    # mm
        xs = radius * np.cos(angles)+radius
        ys = radius * np.sin(angles)+radius
        
        for i in range(len(angles)):
            print('{}. Moving to coordinates: ({},{})'.format(i+1,xs[i],ys[i]))
            coor = [float(xs[i]), float(ys[i])]
            self.move_direct(coor)
            print('Current coordinates: {}'.format(self.get_coordinates()))


def get_coordinate_test():
    xystage = XYController_PI()
    print('Coordinate test')
    coor = xystage.get_coordinates()
    print('Current coordinates: {}'.format(coor))
    xystage.terminate()
    print('Termination complete')
    
def test_movedirect():
    xystage = XYController_PI()
    print('Move direct test')
    coor = (10,10)
    coor = xystage._remap_coordinates_flip(coor,get=True)
    xystage.move_direct(coor)
    xystage.move_direct((0,0))
    xystage.homing_n_coor_calibration()
    xystage.terminate()
    print('Termination complete')

def test_movecontinuous():
    xystage = XYController_PI()
    xystage.homing_n_coor_calibration()
    xystage.set_vel_acc_relative(vel_homing=100, vel_move=20, acc_move=100)
    print('Move continuous test')
    print('Move x forward')
    xystage.move_continuous('xfwd')
    time.sleep(2)
    print('Stop x movement')
    xystage.stop_move()
    
    print('Move x reverse')
    xystage.move_continuous('xrev')
    time.sleep(2)
    print('Stop x movement')
    xystage.stop_move()
    
    print('Move y reverse')
    xystage.move_continuous('yfwd')
    time.sleep(2)
    print('Stop x movement')
    xystage.stop_move()
    
    print('Move y reverse')
    xystage.move_continuous('yrev')
    time.sleep(1)
    print('Stop movement')
    xystage.stop_move()

    # Sleep for 2 seconds
    time.sleep(2)
    xystage.terminate()
    print('Termination complete')

def test_movejog():
    xystage = XYController_PI()
    xystage.homing_n_coor_calibration()
    xystage.set_vel_acc_relative(vel_homing=100, vel_move=20, acc_move=100)
    xystage.set_jog(0.5)
    print('Move jog test')
    print('Move x forward')
    for _ in range(5): xystage.move_jog('xfwd'); time.sleep(0.1)
    for _ in range(5): xystage.move_jog('xrev'); time.sleep(0.1)
    for _ in range(5): xystage.move_jog('yfwd'); time.sleep(0.1)
    for _ in range(5): xystage.move_jog('yrev'); time.sleep(0.1)
    xystage.terminate()
    print('Termination complete')

def test_movecontinuous_slow_with_coorRecord(rel_speed=0.2):
    """
    Test the continuous movement with a slow velocity and record the coordinates at the same time.
    The coordinates are then reported at the end of the movement.
    """
    import matplotlib.pyplot as plt
    
    xystage = XYController_PI()
    xystage.homing_n_coor_calibration()
    xystage.set_vel_acc_relative(vel_homing=100, vel_move=rel_speed, acc_move=100)
    
    @thread_assign
    def record_coor(flg:threading.Event, ts_coor_list:list):
        while not flg.is_set():
            ts,coorx,coory = xystage.get_coordinates_ts()
            ts_coor_list.append((ts,coorx,coory))
            time.sleep(20/1000) # 20 ms
    
    print('Move continuous test')
    xystage.move_continuous('xfwd')
    xystage.move_continuous('yfwd')
    
    # Record the coordinates
    flg_stop = threading.Event()
    ts_coor_list = []
    record_coor(flg_stop,ts_coor_list)
    
    # Allow the stage to move for 2 seconds
    time.sleep(5)
    xystage.stop_move()
    flg_stop.set()
    
    # Plot the coordinates
    ts_coor_list = np.array(ts_coor_list)
    plt.plot(ts_coor_list[:,0],ts_coor_list[:,1],label='X-coordinate')
    plt.plot(ts_coor_list[:,0],ts_coor_list[:,2],label='Y-coordinate')
    plt.xlabel('Timestamp (us)')
    plt.ylabel('Coordinate (mm)')
    
    plt.legend()
    plt.show()
    
    xystage.terminate()
    print('Termination complete')
    
    

if __name__ == "__main__":
    get_coordinate_test()
    test_movedirect()
    test_movecontinuous()
    test_movecontinuous_slow_with_coorRecord(rel_speed=0.04)
    test_movejog()
    # test()

    # xystage = XYController_PI()
    # xystage.set_vel_acc_relative(vel_homing=100, vel_move=100, acc_move=100)
    # xystage.movementtest()
    # xystage.termination()