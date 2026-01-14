"""
A class to control the XY stage using the Zaber ASCII protocol.

Notes:
- For better coordinate retrieval, a timestamp of the uptime of the device is used as a reference.
- This uptime is then converted by adding its difference to the reference timestamp 'self.uptime_TsRef_us'
"""
import os
import sys

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

from iris.utils.general import get_timestamp_us_int

from iris.controllers.class_xy_stage_controller import Class_XYController

import numpy as np
from multiprocessing import Lock
import time

import zaber_motion as zm
import zaber_motion.ascii as zma

from zaber_motion import Units, ascii
from zaber_motion.ascii import Connection

from iris.controllers import ControllerConfigEnum, ControllerSpecificConfigEnum, ControllerDirectionEnum

class XYController_Zaber(Class_XYController):
    def __init__(self,**kwargs) -> None:
        self.conn:Connection = None         # Connection to the device
        self.dev:zma.device.Device = None          # Device object (for the motors)
        
        self.unit_vel = Units.VELOCITY_MILLIMETRES_PER_SECOND
        self.unit_len = Units.LENGTH_MILLIMETRES
        
        # Remapping of the controls
        self.dict_ctrl_remap = {
            'xfwd':ControllerDirectionEnum.XFWD.value,
            'xrev':ControllerDirectionEnum.XREV.value,
            'yfwd':ControllerDirectionEnum.YFWD.value,
            'yrev':ControllerDirectionEnum.YREV.value,
        }   # Dictionary to remap the controls (only for the continuous and jog movements)
        
        self._flipxy = ControllerConfigEnum.STAGE_FLIPXY.value      # Flag to indicate if the x and y axes are flipped in referece to the image capture
        self._invertx = ControllerConfigEnum.STAGE_INVERTX.value    # Flag to indicate if the x axis is flipped (inverted)
        self._inverty = ControllerConfigEnum.STAGE_INVERTY.value    # Flag to indicate if the y axis is flipped (inverted)
        
        # Motor parameters
        self.motorx:zma.Axis = None
        self.motory:zma.Axis = None
        self.motorx_sett:zma.AxisSettings = None # ascii setting for the motor
        self.motory_sett:zma.AxisSettings = None # ascii setting for the motor
        
        self.motorx_maxvel_mms = 0    # mm/s
        self.motory_maxvel_mms = 0    # mm/s
        self.motorx_vel_mms = 0       # mm/s
        self.motory_vel_mms = 0       # mm/s
        self.motorx_state = 0     # 0: stopped, 1: running
        self.motory_state = 0     # 0: stopped, 1: running
        
        self.motorx_max_coor = 0    # max coordinate in [mm] of motor x
        self.motory_max_coor = 0    # max coordinate in [mm] of motor y
        self.motorx_min_coor = 0    # min coordinate in [mm] of motor x
        self.motory_min_coor = 0    # min coordinate in [mm] of motor x
        
        self._jog_step_mm = 0.25        # jog step in [mm]
        self._jog_step_min_um = 0.001   # minimum jog step in [mm]
        
        # Setup parameters for coordinate retrievals
        self._init_uptime_us = None                      # Uptime of the device in [us]
        self._init_uptime_TsRef_us = None                # Timestamp reference for the uptime in [us]
        self._getsettings:list[ascii.GetSetting] = []   # List of settings to retrieve
        self._getsettings.append(ascii.GetSetting('system.uptime',unit=Units.TIME_MICROSECONDS,axes=[0]))
        self._getsettings.append(ascii.GetSetting('pos',unit=Units.LENGTH_MILLIMETRES,axes=[1,2]))
        self._delay_ms = 0     # Uptime delay in [ms] for the coordinate retrieval
        
        self._max_vel_mmS = 85          # Maximum velocity of the motor in mm/s
        self._min_vel_mmS = 0.000095    # Minimum velocity of the motor in mm/s
        
        # Lock for multiprocessing safety
        self._lock = Lock()
        
        # Start by initializing the connection, device, motors, and their parameters
        self._identifier = None
        try:
            self.initialisation(ControllerSpecificConfigEnum.ZABER_COMPORT.value)
        except Exception as e:
            print('Run ABORTED due to error in intialization:')
            print(e)
            self.terminate()
        
        # Continue by setting up the motors and initializing (calibrating) the coordinate system of the motors
        try:
            if self.motorx.is_homed() == False or self.motory.is_homed() == False:
                self.homing_n_coor_calibration()
        except Exception as e:
            print('Coordinate calibration has failed:')
            print(e)
            self.terminate()
    
    def get_identifier(self) -> str:
        if self._identifier is None:
            self._identifier = self._get_hardware_identifier()
        return self._identifier
    
    def _get_hardware_identifier(self) -> str:
        """
        Returns the hardware identifier of the stage.

        Returns:
            str: The hardware identifier of the stage
        """
        device_info = self.dev.identify()
        name = device_info.name
        dev_id = device_info.device_id
        firmware = device_info.firmware_version
        serial = device_info.serial_number
        return f"Zaber XY Stage, Name: {name}, ID: {dev_id}, firmware: {firmware}, S/N: {serial}"
        
    
    def reinitialise_connection(self):
        """
        Reinitialises the connection to the device and the motors.
        This is useful when the connection is lost or needs to be reset.
        """
        try: self.terminate()
        except Exception as e: print('Error in closing the connection:\n{}'.format(e))
        
        try: self.initialisation(ControllerSpecificConfigEnum.ZABER_COMPORT.value)
        except Exception as e: print('Error in initialisation:\n{}'.format(e))
        
        try: self.homing_n_coor_calibration()
        except Exception as e: print('Error in coordinate calibration:\n{}'.format(e))
        
        print('Reinitialisation complete')
    
    def _remap_coordinates_flip_get(self,coor:tuple[float,float]) -> tuple[float,float]:
        """
        Remaps the coordinates based on the flip flags for getting the coordinates
        This is because matrix operations are not commutative.
        
        Args:
            coor (tuple[float,float]): The coordinate to be remapped
            
        Returns:
            tuple[float,float]: the remapped coordinate
        """
        x,y = coor
        if self._flipxy:
            x,y = y,x
        if self._invertx:
            x = -1*x
        if self._inverty:
            y = -1*y
        return (x,y)
    
    def _remap_coordinates_flip_set(self,coor:tuple[float,float]) -> tuple[float,float]:
        """
        Remaps the coordinates based on the flip flags for setting the coordinates (moving the motors).
        This is because matrix operations are not commutative.
        
        Args:
            coor (tuple[float,float]): The coordinate to be remapped
            
        Returns:
            tuple[float,float]: the remapped coordinate
        """
        x,y = coor
        if self._invertx:
            x = -1*x
        if self._inverty:
            y = -1*y
        if self._flipxy:
            x,y = y,x
        return (x,y)
        
    def initialisation(self,commport:str):
        """
        Initialises the device, setup the connection, channels, motors and their parameters, etc.
        
        Args:
            commport (str): the communication port for the device
        """
        self._lock.acquire()
        
        self.conn = Connection.open_serial_port(commport)
        self.conn.enable_alerts()

        device_list = self.conn.detect_devices()
        print("Found {} devices".format(len(device_list)))

        self.dev:zma.Device = device_list[0]

        self.motorx:zma.Axis = self.dev.get_axis(1)
        self.motory:zma.Axis = self.dev.get_axis(2)
        
        self.motorx_sett = self.motorx.settings
        self.motory_sett = self.motory.settings
        
        self.motorx_maxvel_mms = self.motorx_sett.get('limit.approach.maxspeed',unit=self.unit_vel)
        self.motory_maxvel_mms = self.motory_sett.get('limit.approach.maxspeed',unit=self.unit_vel)
        
        self.motorx_vel_mms = self.motorx_sett.get('maxspeed',unit=self.unit_vel)
        self.motory_vel_mms = self.motory_sett.get('maxspeed',unit=self.unit_vel)
        self.motorx_vel_rel = self.motorx_vel_mms/self.motorx_maxvel_mms*100
        self.motory_vel_rel = self.motory_vel_mms/self.motory_maxvel_mms*100
        self.motorx_state = 0     # 0: stopped, 1: running
        self.motory_state = 0     # 0: stopped, 1: running
        
        self.motorx_max_coor = self.motorx_sett.get('limit.max',unit=self.unit_len)
        self.motory_max_coor = self.motory_sett.get('limit.max',unit=self.unit_len)
        self.motorx_min_coor = self.motorx_sett.get('limit.min',unit=self.unit_len)
        self.motory_min_coor = self.motory_sett.get('limit.min',unit=self.unit_len)
        
        # Set the parameters for coordinate retrievals
        self._init_uptime_us = self.dev.settings.get('system.uptime',unit=Units.TIME_MICROSECONDS)
        self._init_uptime_TsRef_us = get_timestamp_us_int()
        
        # Update the max velocity for data analysis accordingly
        self._max_vel_mmS = min(self.motorx_maxvel_mms,self.motory_maxvel_mms)
        
        self._lock.release()
        
        print('\n>>>>> Device and motor initialisation complete <<<<<')
    
    def _convert_uptime_to_timestamp(self,uptime_us:int) -> int:
        """
        Converts the uptime of the device to a timestamp
        
        Args:
            uptime_us (int): the uptime of the device in [us]
            
        Returns:
            int: the timestamp in [us]
        """
        diff_us = uptime_us - self._init_uptime_us
        timestamp_us = self._init_uptime_TsRef_us + diff_us + self._delay_ms*1000
        return timestamp_us
    
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
        if vel_move <= 0:
            raise ValueError("Velocity and acceleration parameters must be larger than 1%")
        if vel_move > 100:
            raise ValueError("Velocity and acceleration parameters must be less than 100%")
        
        # Convert the percentage to the actual value
        self.motorx_vel_rel = vel_move
        self.motory_vel_rel = vel_move
        
        self.motorx_vel_mms = self.motorx_maxvel_mms * vel_move / 100
        self.motory_vel_mms = self.motory_maxvel_mms * vel_move / 100
        
    def get_vel_acc_relative(self):
        """
        Returns the current velocity and acceleration parameters of the motors

        Returns:
            tuple of floats: 3 elements: (vel_homing, vel_move, acc_move)
        """
        relvel = min(self.motorx_vel_rel,self.motory_vel_rel) # Get the minimum relative velocity
        return (relvel,relvel,float(100))
    
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
            with self._lock: res = self.dev.settings.get_many(*self._getsettings)
            uptime_return = int(res[0].values[0])
            ts_return_temp = self._convert_uptime_to_timestamp(uptime_return)
            ts_return.append(ts_return_temp)
            coor_x_return.append(float(res[1].values[0]))
            coor_y_return.append(float(res[1].values[1]))
            if ts_return[-1] >= ts_request:
                break
            time.sleep(1/1000) # delay to prevent overloading the comm port
        
        if len(ts_return) == 1:
            coor_x = coor_x_return[-1]
            coor_y = coor_y_return[-1]
        else:
            coor_x,coor_y = interpolate_coor(ts_request,
                ts_return[-2:],coor_x_return[-2:],coor_y_return[-2:])
        
        # Remap the coordinates, ensure the returned coordinates are correct
        coor_x,coor_y = self._remap_coordinates_flip_get((coor_x,coor_y))
        return (coor_x,coor_y)
        
    def get_coordinates_old(self):
        """
        Returns the current motor coordinates. This is the old version of the function,
        which is less accurate (due to the delay between the request and the device response).
        
        Returns:
            tuple of floats: 2 elements: (coor_x, coor_y), in millimetre (float)
        """
        with self._lock:
            coor_x = self.motorx.get_position(unit=self.unit_len)
            coor_y = self.motory.get_position(unit=self.unit_len)
        
        # Remap the coordinates, ensure the returned coordinates are correct
        coor_x,coor_y = self._remap_coordinates_flip_get((coor_x,coor_y))
        return (coor_x,coor_y)
    
    def homing_n_coor_calibration(self):
        """
        A function to recalibrate the coordinate system of the device.
        - Also called as 'homing'
        """
        if self.motorx_state != 0 or self.motory_state != 0:
                print("!!!!! Motor is running, homing request BLOCKED !!!!!")
                return
        
        print("\n!!!!! Coordinate calibration/Homing starting !!!!!")
        # Home the device, use multithreading to operate both motors at once
        with self._lock:
            self.motorx_state = 1
            self.motory_state = 1
            self.motorx.home(wait_until_idle=False)
            self.motory.home(wait_until_idle=False)
            
            self.motorx.wait_until_idle()
            self.motory.wait_until_idle()
            
            self.motorx_state = 0
            self.motory_state = 0
        print(">>>>> Coordinate calibration/Homing finished <<<<<")

    
    def move_direct(self,coor_abs:tuple[float,float]):
        """
        Function to direct the motors to move at the same time towards a certain coordinate.

        Args:
            coor_abs (tuple[float,float]): the absolute coordinate to move to in [mm]
        """
        if self.motorx_state != 0 or self.motory_state != 0:
            print("!!!!! Motor is currently running, movement request BLOCKED !!!!!")
            return
        
        self.motorx_state = 1
        self.motory_state = 1
        
        # Remap the coordinates, ensure the motors move in the correct direction
        coor_x,coor_y = self._remap_coordinates_flip_set(coor_abs)
        
        with self._lock:
            # Use multithreading to operate both motors at once
            self.motorx.move_absolute(coor_x,unit=self.unit_len,
                velocity=self.motorx_vel_mms,velocity_unit=self.unit_vel,
                wait_until_idle=False)
            self.motory.move_absolute(coor_y,unit=self.unit_len,
                velocity=self.motory_vel_mms,velocity_unit=self.unit_vel,
                wait_until_idle=False)
        
        self.motorx.wait_until_idle()
        self.motory.wait_until_idle()
        
        self.motorx_state = 0
        self.motory_state = 0
        
    def move_continuous(self,dir:str):
        """
        Moves the motor with a continuous motion until a stop command

        Args:
            dir (str): 'xfwd', 'xrev', 'yfwd', 'yrev' for the direction of the movement
        """
        # Check if the motor is running, prevents command overlap
        if self.motorx_state != 0 or self.motory_state != 0:
            print("!!!!! Motor is currently running, movement request BLOCKED !!!!!")
            return
        
        dir = self.dict_ctrl_remap[dir] # Remap the control
        
        with self._lock:
            if dir == 'xfwd':
                self.motorx_state = 1
                self.motorx.move_velocity(self.motorx_vel_mms,unit=self.unit_vel)
            elif dir == 'xrev':
                self.motorx_state = 1
                self.motorx.move_velocity(-1*self.motorx_vel_mms,unit=self.unit_vel)
            elif dir == 'yfwd':
                self.motory_state = 1
                self.motory.move_velocity(self.motory_vel_mms,unit=self.unit_vel)
            elif dir == 'yrev':
                self.motory_state = 1
                self.motory.move_velocity(-1*self.motory_vel_mms,unit=self.unit_vel)
            
    def stop_move(self):
        """
        Stops the continuous movement of the motors
        """
        
        with self._lock:
            self.motorx.stop(wait_until_idle=False)
            self.motory.stop(wait_until_idle=False)
        
        self.motorx.wait_until_idle()
        self.motory.wait_until_idle()
        
        # Update the motor test
        self.motorx_state = 0
        self.motory_state = 0
    
    def get_jog(self):
        """
        Returns the current jog step in [mm]:
        
        Returns:
            tuple of floats: 6 elements:
            (jog_step_x, jog_step_y, jog_vel_x, jog_vel_y, jog_acc_x, jog_acc_y)
        """
        jog_step_x = self._jog_step_mm
        jog_step_y = self._jog_step_mm
        jog_vel_x = self.motorx_vel_mms/self.motorx_maxvel_mms*100
        jog_vel_y = self.motory_vel_mms/self.motory_maxvel_mms*100
        jog_acc_x = float(100)
        jog_acc_y = float(100)
        return (jog_step_x, jog_step_y, jog_vel_x, jog_vel_y, jog_acc_x, jog_acc_y)
    
    def set_jog(self,dist_mm:float,vel_rel:int=100,acc_rel:int=100):
        """
        Set the jog parameters for the motor
        
        Args:
            dist_mm (float): distance to jog in mm
            vel_rel (int, optional): Legacy parameter. Is ignored.
            acc_rel (int, optional): Legacy parameter. Is ignored.
        """
        if not isinstance(dist_mm, float) and not isinstance(dist_mm, int):
            raise ValueError("Distance must be a float")
        
        if dist_mm < self._jog_step_min_um:
            raise ValueError("Minimum jog step size is {}".format(self._jog_step_min_um))
        
        # Set the jog step size
        self._jog_step_mm = float(dist_mm)
        
    def move_jog(self,direction:str):
        """
        Moves the motor with a single jogging motion.
        
        Args:
            direction (str): 'xfwd', 'xrev', 'yfwd', 'yrev' for the direction of the jog.
        """
        
        if not isinstance(direction, str):
            raise ValueError("Direction must be a string")
        
        if direction not in ['xfwd','xrev','yfwd','yrev']:
            raise ValueError("Direction must be 'xfwd', 'xrev', 'yfwd', 'yrev'")
        
        if self.motorx_state != 0 or self.motory_state != 0:
            print("!!!!! Motor is currently running, movement request BLOCKED !!!!!")
            return
        
        direction = self.dict_ctrl_remap[direction] # Remap the control
        
        self.motorx_state = 1
        self.motory_state = 1
        with self._lock:
            if direction == 'xfwd':
                self.motorx.move_relative(self._jog_step_mm,unit=self.unit_len,
                    velocity=self.motorx_vel_mms,velocity_unit=self.unit_vel,
                    wait_until_idle=True)
            elif direction == 'xrev':
                self.motorx.move_relative(-1*self._jog_step_mm,unit=self.unit_len,
                    velocity=self.motorx_vel_mms,velocity_unit=self.unit_vel,
                    wait_until_idle=True)
            elif direction == 'yfwd':
                self.motory.move_relative(self._jog_step_mm,unit=self.unit_len,
                    velocity=self.motory_vel_mms,velocity_unit=self.unit_vel,
                    wait_until_idle=True)
            elif direction == 'yrev':
                self.motory.move_relative(-1*self._jog_step_mm,unit=self.unit_len,
                    velocity=self.motory_vel_mms,velocity_unit=self.unit_vel,
                    wait_until_idle=True)
        self.motorx_state = 0
        self.motory_state = 0
        
    def terminate(self):
        """
        Terminates the operation and closes the connection to the device
        """
        try:
            self.conn.close()
            print('xy_stage_controller: Connection closed')
        except Exception as e:
            print('xy_stage_controller: Error in closing the connection:\n{}'.format(e))
        
    def movementtest(self):
        print("\n>>>>> MOTOR TEST: CIRCULAR MOTION <<<<<")
        # Create circle coordinates
        angles = np.arange(0, 2 * np.pi, 0.25)
        radius = 10.0    # mm
        xs = radius * np.cos(angles)+radius
        ys = radius * np.sin(angles)+radius
        
        for i in range(len(angles)):
            print(i, float(xs[i]))
            coor = [float(xs[i]), float(ys[i])]
            self.move_direct(coor)
            
            
def get_coordinate_test():
    xystage = XYController_Zaber(sim=True)
    print('Coordinate test')
    coor = xystage.get_coordinates()
    print('Current coordinates: {}'.format(coor))
    xystage.terminate()
    print('Termination complete')
    
if __name__ == "__main__":
    xystage = XYController_Zaber(sim=False)
    # xystage.movementtest()
    # time.sleep(2)
    
    print('Continuous movement test')
    time.sleep(1)
    xystage.move_continuous(dir='xfwd')
    time.sleep(5)
    xystage.stop_move()
    print('Continuous movement test finished')
    xystage.terminate()
    print('Termination complete')
    get_coordinate_test()