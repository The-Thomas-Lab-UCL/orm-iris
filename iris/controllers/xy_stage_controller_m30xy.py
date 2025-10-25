"""
A class that allows the control of the M30XY/M Thorlabs stage.
This implementation is based on the .NET Kinesis Libraries to connect to and control the stage.
"""
if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))
    
import os
import time
import sys
import clr
import numpy as np
import threading
import multiprocessing as mp


from iris.controllers.class_xy_stage_controller import Class_XYController

from iris.controllers import ControllerConfigEnum, ControllerSpecificConfigEnum, ControllerDirectionEnum

import ctypes
co_initialize = ctypes.windll.ole32.CoInitialize
co_initialize(None)

# Add References to .NET libraries
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.Benchtop.DCServoCLI.dll.")


from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.Benchtop.DCServoCLI import *
from System import Decimal  # Required for real units


class XYController_M30XYM(Class_XYController):
    def __init__(self,sim=False) -> None:
        self.serial_no = ControllerSpecificConfigEnum.M30XYM_SERIAL.value
        
        self._dev = None             # Stores the device object
        self._dev_info = None        # Stores the device information
        self._dev_sett = None        # Stores the device settings
        
        # Remapping of the controls
        self.dict_ctrl_remap = {
            'xfwd':ControllerDirectionEnum.XFWD.value,
            'xrev':ControllerDirectionEnum.XREV.value,
            'yfwd':ControllerDirectionEnum.YFWD.value,
            'yrev':ControllerDirectionEnum.YREV.value,
        }   # Dictionary to remap the controls (only for the continuous and jog movements)
        
        self._flipxy = ControllerConfigEnum.STAGE_FLIPXY.value      # Flag to indicate if the x and y axes are flipped in referece to the image capture
        self._invertx = ControllerConfigEnum.STAGE_INVERTX.value    # Flag to indicate if the x and y axes are flipped in referece to the image capture
        self._inverty = ControllerConfigEnum.STAGE_INVERTY.value    # Flag to indicate if the y axis is flipped in referece to the image capture
        
        # Motor parameters
        self._motorx = None          # Stores the x-axis motor object
        self._motory = None          # Stores the y-axis motor object
        self._isrunning_motorx = 0       # Running state of the x-motor. 1: forward, -1: backward, 0: not moving
        self._isrunning_motory = 0       # Running state of the y-motor. 1: forward, -1: backward, 0: not moving
        self._motorx_config = None   # Stores the motor config
        self._motory_config = None   # same but for y
        self._motorx_homing = None   # Motor-x homing parameters object for coordinate calibration
        self._motory_homing = None   # same but for y
        self._motorx_mvmt = None     # Motor-x movement parameters object
        self._motory_mvmt = None     # Motor-y movement parameter object
        
        self.unit_converter_x = None    # Unit converter for x-motor
        self.unit_converter_y = None    # Unit converter for y-motor
        self.convert_type_length = None # Type of conversion for length
        
        self._jog_step = None       # Stores the jog step size in [mm]
        self._jog_vel = None        # Stores the jog velocity in [mm/s]
        self._jog_acc = None        # Stores the jog acceleration in [mm/s^2]
        self._jog_step_min = 0.0025 # Minimum jog step size in [mm]
        
        self._vel_max = float(2.4)      # Maximum velocity of the device [mm/s]
        self._vel_min = float(0.1)      # Minimum velocity of the device [mm/s]
        self._acc_max = float(5.0)      # Maximum acceleration of the device [mm/s^2]
        self._acc_min = float(0.1)      # Minimum acceleration of the device [mm/s^2]
        
        self._vel_homing = float(2.4)   # Homing velocity
        self._vel_move = float(2.4)     # Other movement velocity (everything else other than homing operation)
        self._acc_move = float(5.0)     # Other movement acceleration (^^^^^ as above ^^^^^)
        self._timeout_move_fast = 10000  # Waiting time for movements to finish (in milisecond, integer)
        self._timeout_move_slow = 10000 # Waiting time for longer movements to finish (in milisecond, integer)
        self._stoptime = 0.85           # Waiting time to stop the motor [sec] > 0.75 otherwise error
        
        self.issimulation = sim     # True: To use when interacting with 'Kinesis Simulator'
        self.running = False        # Indicate the start and finish of the program.
                                    # True for start (initialization) and False for finish (termination)
        
        self._max_vel_mmS = self._vel_max   # Maximum velocity of the motor in mm/s
        self._min_vel_mmS = self._vel_min   # Minimum velocity of the motor in mm/s
        
        self._lock = mp.Lock()      # Lock to prevent simultaneous access to the motors
        
        # Start by initializing the connection, device, motors, and their parameters
        try:
            self.initialisation()
        except Exception as e:
            print('Run ABORTED due to error in intialization:')
            print(e)
            self.terminate(error_flag=True)
        
        # Continue by setting up the motors and initializing (calibrating) the coordinate system of the motors
        try:
            self._set_vel_acc()
            # if not self.issimulation or (self._motorx.NeedsHoming or self._motory.NeedsHoming):
            #     self.homing_n_coor_calibration()
        except Exception as e:
            print('Coordinate calibration has failed:')
            print(e)
            self.terminate(error_flag=True)
    
    def reinitialise_connection(self) -> None:
        """
        Reinitialise the connection to the device
        """
        try:
            self.terminate()
        except Exception as e:
            print('XYController_M30XYM reinitialise_connection error:\n{}'.format(e))
        
        try:
            self.initialisation()
        except Exception as e:
            print('XYController_M30XYM reinitialise_connection error:\n{}'.format(e))
    
    def _remap_coordinates_flip(self,coor:tuple[float,float],get:bool) -> tuple[float,float]:
        """
        Remaps the coordinates based on the flip flags
        
        Args:
            coor (tuple[float,float]): The coordinate to be remapped
            get (bool): True: get (bool): True if the coordinate is to be retrieved, False if the coordinate is to be set
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
    
    def reset_state(self):
        self._isrunning_motorx = 0       # Running state of the x-motor. 1: forward, -1: backward, 0: not moving
        self._isrunning_motory = 0       # Running state of the y-motor. 1: forward, -1: backward, 0: not moving
    
    def initialisation(self):
        """
        Initialises the device, setup the connection, channels, motors and their parameters, etc.
        """
        if self.issimulation:
            print(">>>>> INITIALISING SIMULATION <<<<<")
            SimulationManager.Instance.InitializeSimulations()
            print("<<<<< Simulation Initialised >>>>>")
        else:
            print("<<<<< NOT A SIMULATION >>>>>")
        
        DeviceManagerCLI.BuildDeviceList()
        
        # Creates the device object, based on the serial number we have
        self._dev = BenchtopDCServo.CreateBenchtopDCServo(self.serial_no)
        
        # Connect, begin polling, and enable
        self._dev.Connect(self.serial_no)
        time.sleep(0.25)  # wait statements are important to allow settings to be sent to the device

        # Get Device Information and display description
        self._dev_info = self._dev.GetDeviceInfo()
        print('Connected to: ' + self._dev_info.Description)
        
        # Get the channel for the device
        self._motorx = self._dev.GetChannel(1)  # Returns a benchtop channel object, i.e., the motors
        self._motory = self._dev.GetChannel(2)  # index: 1,2 for channel 1 and 2 respectively
        
        # Start Polling and enable channel
        self._motorx.StartPolling(ControllerSpecificConfigEnum.M30XYM_POLLING_INTERVAL.value)
        self._motory.StartPolling(ControllerSpecificConfigEnum.M30XYM_POLLING_INTERVAL.value)
        time.sleep(0.5)
        self._motorx.EnableDevice()
        self._motory.EnableDevice()
        time.sleep(0.5)

        # Check that the settings are initialised, else error.
        if not self._motorx.IsSettingsInitialized() or not self._motory.IsSettingsInitialized():
        # if not x_channel.IsSettingsInitialized():
            self._motorx.WaitForSettingsInitialized(10000)  # 10 second timeout
            self._motory.WaitForSettingsInitialized(10000)
            assert self._dev.IsSettingsInitialized() is True

        # Load the motor configuration on the channel
        self._motorx_config = self._motorx.LoadMotorConfiguration(self._motorx.DeviceID)
        self._motory_config = self._motory.LoadMotorConfiguration(self._motory.DeviceID)
        
        # Read in the device settings
        self._dev_sett = self._motorx.MotorDeviceSettings
        
        # Get the Homing Params for coordinate calibration(ccal)
        self._motorx_homing = self._motorx.GetHomingParams()
        self._motory_homing = self._motory.GetHomingParams()
        
        # Set the movement velocity and acceleration parameters
        self._motorx_mvmt = self._motorx.GetVelocityParams()
        self._motory_mvmt = self._motory.GetVelocityParams()
        
        # Set the unit converters
        self.unit_converter_x = self._motorx.UnitConverter
        self.unit_converter_y = self._motory.UnitConverter
        
        self.convert_type_length = self.unit_converter_x.UnitType(0)
        
        print('\n>>>>> Device and motor initialisation complete <<<<<')
        
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
    
    def get_vel_acc_relative(self):
        """
        Returns the current velocity and acceleration parameters of the motors

        Returns:
            tuple of floats: 3 elements: (vel_homing, vel_move, acc_move)
        """
        with self._lock:
            # Get the Homing Params for coordinate calibration(ccal)
            self._motorx_homing = self._motorx.GetHomingParams()
            self._motory_homing = self._motory.GetHomingParams()
            
            # Set the movement velocity and acceleration parameters
            self._motorx_mvmt = self._motorx.GetVelocityParams()
            self._motory_mvmt = self._motory.GetVelocityParams()
            
            # Get the maximum velocity and acceleration of the device
            self._vel_homing = float(str(self._motorx_homing.Velocity))
            self._vel_move = float(str(self._motorx_mvmt.MaxVelocity))
            self._acc_move = float(str(self._motorx_mvmt.Acceleration))
        
        # Convert the actual value to percentage
        vel_homing = self._vel_homing * 100 / self._vel_max
        vel_move = self._vel_move * 100 / self._vel_max
        acc_move = self._acc_move * 100 / self._acc_max
        
        return (vel_homing, vel_move, acc_move)
    
    def set_vel_acc_relative(self,vel_homing:int=100, vel_move:int=100, acc_move:int=100):
        """
        Set the velocity and acceleration parameters of the motors for both homing and typical movements.
        
        Args:
            vel_homing (int, optional): New motor homing velocity in percentage of max velocity. Defaults to 100.
            vel_move (int, optional): New motor movement velocity in percentage of max velocity. Defaults to 100.
            acc_move (int, optional): New motor movement acceleration in percentage of max acceleration. Defaults to 100.
        """
        if vel_homing <=0 or vel_move <=0 or acc_move <=0:
            raise ValueError("Velocity and acceleration parameters must be larger than 1%")
        if vel_homing > 100 or vel_move > 100 or acc_move > 100:
            raise ValueError("Velocity and acceleration parameters must be less than 100%")
        
        # Convert the percentage to the actual value
        vel_homing = self._vel_max * vel_homing / 100
        vel_move = self._vel_max * vel_move / 100
        acc_move = self._acc_max * acc_move / 100
        
        self._set_vel_acc(vel_homing, vel_move, acc_move)
    
    def _set_vel_acc(self,vel_homing:float=None, vel_move:float=None, acc_move:float=None):
        """
        Function to setup the velocity and acceleration parameters of the motors
        for both homing and typical movements. Will be applied equally to both x and y motors

        Args:
            vel_homing (Decimal, optional): New motor homing velocity. Defaults to None.
            vel_move (Decimal, optional): New motor movement velocity. Defaults to None.
            acc_move (Decimal, optional): New motor movement acceleration. Defaults to None.
        """
        if vel_homing == None and vel_move == None and acc_move == None:
            vel_homing = self._vel_homing
            vel_move = self._vel_move
            acc_move = self._acc_move
            
        # Modify the homing velocity if requested
        if vel_homing is not None:
            if not isinstance(vel_homing, float):
                raise ValueError("Velocity must be a float")
            
            # Set a hard limit to protect the motor
            if vel_homing > self._vel_max:
                print("Maximum device velocity is {}".format(self._vel_max))
                vel_homing = self._vel_max
            
            with self._lock:
                # Updates the stored value
                self._vel_homing = float(vel_homing)
                vel_homing = Decimal(vel_homing)
                
                # Modify the value in the motors
                self._motorx_homing.Velocity = vel_homing
                self._motory_homing.Velocity = vel_homing

        # Modify the movement velocity and acceleration parameters if requested
        if vel_move is not None:
            if not isinstance(vel_move, float) or isinstance(vel_move, int):
                raise ValueError("Velocity must be a float")
            
            if vel_move > self._vel_max:
                print("Maximum device velocity is {}".format(self._vel_max))
                vel_move = self._vel_max
            
            with self._lock:
                # Updates the stored value
                self._vel_move = float(vel_move)
                vel_move = Decimal(vel_move)
                
                # Modify the value in the motors
                self._motorx_mvmt.MaxVelocity = vel_move
                self._motory_mvmt.MaxVelocity = vel_move
        
        if acc_move is not None:
            if not isinstance(acc_move, float):
                raise ValueError("Velocity must be a float")
            
            if acc_move > self._acc_max:
                print("Maximum device velocity is {}".format(self._acc_max))
                acc_move = self._acc_max
            
            with self._lock:
                # Updates the stored value
                self._acc_move = float(acc_move)
                acc_move = Decimal(acc_move)
                
                # Modify the value in the motors
                self._motorx_mvmt.Acceleration = acc_move
                self._motory_mvmt.Acceleration = acc_move
        
        with self._lock:
            # Assign the set parameters to the motors
            self._motorx.SetHomingParams(self._motorx_homing)
            self._motory.SetHomingParams(self._motory_homing)
            
            # Assign the velocity and acceleration parameters to the motors
            self._motorx.SetVelocityParams(self._motorx_mvmt)
            self._motory.SetVelocityParams(self._motory_mvmt)
            
            self._motorx.WaitForSettingsInitialized(self._timeout_move_fast)
            self._motory.WaitForSettingsInitialized(self._timeout_move_fast)
        
    def get_coordinates_old(self):
        """
        Returns the current motor coordinates. Does NOT work properly
        ~1 sec after the motor has just started moving.
        DO NOT USE. Kept for reference only.

        Returns:
            tuple of floats: 2 elements: (coor_x, coor_y)
        """
        self._lock.acquire()
        coor_x = float(str(self._motorx.Position))
        coor_y = float(str(self._motory.Position))
        self._lock.release()
        return coor_x,coor_y
    
    def homing_n_coor_calibration(self):
        """
        A function to recalibrate the coordinate system of the device.
        - Also called as 'homing'
        """
        if self._isrunning_motorx != 0 or self._isrunning_motory != 0:
            print("!!!!! Motor is running, homing request BLOCKED !!!!!")
            return
        
        print("\n!!!!! Coordinate calibration/Homing starting !!!!!")
        with self._lock:
            # Home the device, use multithreading to operate both motors at once
            workx = self._motorx.InitializeWaitHandler()
            worky = self._motory.InitializeWaitHandler()
            self._motorx.Home(workx)
            self._motory.Home(worky)
            
            # Starts the movement
            self._isrunning_motorx = 1
            self._isrunning_motory = 1
            
        self._motorx.Wait(120000)
        self._motory.Wait(120000)
        
        # Ends the multithreading
        self._isrunning_motorx = 0
        self._isrunning_motory = 0
        print(">>>>> Coordinate calibration/Homing finished <<<<<")

    def terminate(self,error_flag=False):
        """
        Terminate the operation. Returns the stage to home and disconnects the device.
        
        Args:
            error_flag (bool, optional): If termination is caused by an error, skip homing. True: there is an error, False: there is none. Defaults to False.
        """
        
        # Return the stage to Home
        # if not error_flag:
        #     self.homing_n_coor_calibration()

        # Stop polling and disconnects the device
        with self._lock:
            self._motorx.StopPolling()
            self._motory.StopPolling()
            self._dev.Disconnect()
            
            if self.issimulation:
                print(">>>>> TERMINATING SIMULATION STOPPED <<<<<")
                SimulationManager.Instance.UninitializeSimulations()
            self.running = False
    
    def check_device_availability(self):
        check_motorx= self._motorx.IsDeviceAvailable()
        check_motory= self._motory.IsDeviceAvailable()
        if not check_motorx or not check_motory:
            print("Device not available: reinitialising...")
            try:
                self.initialisation()
            except:
                print("Device reinitialisation failed")
                raise Exception("Device reinitialisation failed")
    
    def move_direct(self,coor_abs):
        """
        Function to direct the motors to move at the same time towards a certain coordinate.

        Args:
            coor_abs (list of Decimal): coordinate of the destination [x,y]
        """
        # Correct the coordinates if the axes are flipped
        coor_x,coor_y = self._remap_coordinates_flip(coor_abs,get=False)
        
        # Reassign it to a list in case a tuple is received
        coor_abs = [Decimal(coor_x),Decimal(coor_y)]
        
        with self._lock:
            # Convert the coordinates to decimals if floats are received
            if type(coor_abs[0]) is float:
                coor_abs[0] = Decimal(coor_x)
            
            if type(coor_abs[1]) is float:
                coor_abs[1] = Decimal(coor_y)
            
            if self._isrunning_motorx != 0:
                print("!!!!! Motor is currently running, movement request BLOCKED !!!!!")
                return
            
            # Check device availability
            self.check_device_availability()
            
            # Use multithreading to operate both motors at once
            # timeout_rel = int(self._timeout_move_slow * self._vel_max/self._vel_move)
            workx = self._motorx.InitializeWaitHandler()
            worky = self._motory.InitializeWaitHandler()
            
            self._motorx.MoveTo(coor_abs[0], workx)
            self._motory.MoveTo(coor_abs[1], worky)
            
            # Starts the movement
            self._isrunning_motorx = 1
            self._isrunning_motory = 1
            
            self._motorx.WaitForSettingsInitialized(self._timeout_move_fast)
            self._motory.WaitForSettingsInitialized(self._timeout_move_fast)
            
        self._motorx.Wait(self._timeout_move_fast)
        self._motory.Wait(self._timeout_move_fast)
        
        # Waits for both threads to end
        self._isrunning_motorx = 0
        self._isrunning_motory = 0
        
    def move_continuous(self,dir:str):
        """
        Moves the motor with a continuous motion until a stop command

        Args:
            dir (str): 'xfwd', 'xrev', 'yfwd', 'yrev' for the direction of the movements
        """
        # Check if the motor is running, prevents command overlap
        if self._isrunning_motorx != 0:
            print("!!!!! Motor is currently running, movement request BLOCKED !!!!!")
            return
        
        # Update the motor test
        self._isrunning_motorx = 1
        self._isrunning_motory = 1
        
        dir = self.dict_ctrl_remap[dir] # Remap the controls
        
        with self._lock:
            self.check_device_availability()
            if dir == 'xfwd':
                self._motorx.MoveContinuous(MotorDirection.Forward)
            elif dir == 'xrev':
                self._motorx.MoveContinuous(MotorDirection.Backward)
            
            if dir == 'yfwd':
                self._motory.MoveContinuous(MotorDirection.Forward)
            elif dir == 'yrev':
                self._motory.MoveContinuous(MotorDirection.Backward)
        
    def move_continuous_old(self,xdir=None,ydir=None):
        """
        Moves the motor with a continuous motion until a stop command

        Args:
            xdir (str): 'fwd' forward and 'rev' for reverse/backward for the xmotor or None for no movement
            ydir (str): 'fwd' forward and 'rev' for reverse/backward for the ymotor or None for no movement
        """
        # Check if the motor is running, prevents command overlap
        if self._isrunning_motorx != 0:
            print("!!!!! Motor is currently running, movement request BLOCKED !!!!!")
            return
        
        # Update the motor test
        self._isrunning_motorx = 1
        self._isrunning_motory = 1
        
        with self._lock:
            self.check_device_availability()
            if xdir == 'fwd':
                self._motorx.MoveContinuous(MotorDirection.Forward)
            elif xdir == 'rev':
                self._motorx.MoveContinuous(MotorDirection.Backward)
            
            if ydir == 'fwd':
                self._motory.MoveContinuous(MotorDirection.Forward)
            elif ydir == 'rev':
                self._motory.MoveContinuous(MotorDirection.Backward)
        
    def get_jog(self):
        """
        Get the jog parameters for the motor
        
        Returns:
            tuple of floats: 6 elements:
            (jog_step_x, jog_step_y, jog_vel_x, jog_vel_y, jog_acc_x, jog_acc_y)
        """
        with self._lock:
            JogParams_x = self._motorx.GetJogParams()
            JogParams_y = self._motory.GetJogParams()
            
            self._jog_step_x = float(str(JogParams_x.StepSize))
            self._jog_step_y = float(str(JogParams_y.StepSize))
            
            VelocityParams_x = JogParams_x.VelocityParams
            VelocityParams_y = JogParams_y.VelocityParams
            
            self._jog_vel_x = float(str(VelocityParams_x.MaxVelocity))
            self._jog_vel_y = float(str(VelocityParams_x.MaxVelocity))
            
            self._jog_acc_x = float(str(VelocityParams_y.Acceleration))
            self._jog_acc_y = float(str(VelocityParams_y.Acceleration))
        
        return (self._jog_step_x,self._jog_step_y,self._jog_vel_x,self._jog_vel_y,
                self._jog_acc_x,self._jog_acc_y)
        
    def set_jog(self,dist_mm:float,vel_rel:int=100,acc_rel:int=100):
        """
        Set the jog parameters for the motor
        
        Args:
            dist_mm (float): distance to jog in mm
            vel_rel (int, optional): velocity in percentage of max velocity. Defaults to 100.
            acc_rel (int, optional): acceleration in percentage of max acceleration. Defaults to 100.
        """
        if not isinstance(dist_mm, float) and not isinstance(dist_mm, int):
            raise ValueError("Distance must be a float")
        
        if dist_mm < self._jog_step_min:
            raise ValueError("Minimum jog step size is {}".format(self._jog_step_min))
        
        dist_mm = float(dist_mm)
        
        with self._lock:
            JogParams_x = self._motorx.GetJogParams()
            JogParams_y = self._motory.GetJogParams()
            
            VelocityParams_x = JogParams_x.VelocityParams
            VelocityParams_y = JogParams_y.VelocityParams
            
            if not isinstance(vel_rel, int) or isinstance(vel_rel, float):
                raise ValueError("Velocity must be an integer")
            if not isinstance(acc_rel, int) or isinstance(acc_rel, float):
                raise ValueError("Acceleration must be an integer")
            
            VelocityParams_x.MaxVelocity = Decimal(self._vel_max * vel_rel / 100)
            VelocityParams_x.Acceleration = Decimal(self._acc_max * acc_rel / 100)
            VelocityParams_y.MaxVelocity = Decimal(self._vel_max * vel_rel / 100)
            VelocityParams_y.Acceleration = Decimal(self._acc_max * acc_rel / 100)
            
            JogParams_x.StepSize = Decimal(dist_mm)
            JogParams_y.StepSize = Decimal(dist_mm)
            
            self._motorx.SetJogParams(JogParams_x)
            self._motory.SetJogParams(JogParams_y)
            
            self._motorx.WaitForSettingsInitialized(self._timeout_move_fast)
            self._motory.WaitForSettingsInitialized(self._timeout_move_fast)
        
    def move_jog(self,direction:str):
        """
        Moves the motor with a single jogging motion.
        
        Args:
            direction (str): 'xfwd', 'xrev', 'yfwd', 'yrev' for the direction of the jog.
        """
        # timeout_rel = int(self._timeout_move_slow * self._vel_max/self._vel_move)
        
        if not isinstance(direction, str):
            raise ValueError("Direction must be a string")
        
        if direction not in ['xfwd','xrev','yfwd','yrev']:
            raise ValueError("Direction must be 'xfwd', 'xrev', 'yfwd', or 'yrev'")
        
        if self._isrunning_motorx == True or self._isrunning_motory == True:
            print('!!!!! Motor is running, movement request BLOCKED !!!!!')
            return
        
        self._isrunning_motorx = True
        self._isrunning_motory = True
        
        direction = self.dict_ctrl_remap[direction] # Remap the controls
        
        with self._lock:
            self.check_device_availability()
            if direction in ['xfwd','xrev']:
                workx = self._motorx.InitializeWaitHandler()
            elif direction in ['yfwd','yrev']:
                worky = self._motory.InitializeWaitHandler()
            
            if direction == 'xfwd':
                self._motorx.MoveJog(MotorDirection.Forward,workx)
            elif direction == 'xrev':
                self._motorx.MoveJog(MotorDirection.Backward,workx)
            elif direction == 'yfwd':
                self._motory.MoveJog(MotorDirection.Forward,worky)
            elif direction == 'yrev':
                self._motory.MoveJog(MotorDirection.Backward,worky)
                
            if direction in ['xfwd','xrev']:
                self._motorx.WaitForSettingsInitialized(self._timeout_move_fast)
            elif direction in ['yfwd','yrev']:
                self._motory.WaitForSettingsInitialized(self._timeout_move_fast)
        
        if direction in ['xfwd','xrev']:
            self._motorx.Wait(self._timeout_move_slow)
        elif direction in ['yfwd','yrev']:
            self._motory.Wait(self._timeout_move_slow)
        
        self._isrunning_motorx = False
        self._isrunning_motory = False

    def stop_move(self):
        """
        Stops the continuous movement of the motors
        """
        with self._lock:
            self._motorx.Stop(0)
            self._motory.Stop(0)
        time.sleep(self._stoptime)
        
        # Update the motor test
        self._isrunning_motorx = 0
        self._isrunning_motory = 0
    
    def movementtest(self):
        print("\n>>>>> MOTOR TEST: CIRCULAR MOTION <<<<<")
        # Create circle coordinates
        angles = np.arange(0, 2 * np.pi, 0.25)
        radius = 5.0  # mm
        
        offset = 5.0 # mm
        
        xs = radius * np.cos(angles) + offset
        ys = radius * np.sin(angles) + offset
        
        for i in range(len(angles)):
            print(i, float(xs[i]))
            coor = [float(xs[i]), float(ys[i])]
            self.move_direct(coor)
            
    def get_coordinates(self):
        """
        Returns the current motor coordinates

        Returns:
            tuple of floats: 2 elements: (coor_x, coor_y)
        """
        with self._lock:
            posx = Decimal(self._motorx.GetPositionCounter())
            posy = Decimal(self._motory.GetPositionCounter())
            
            coorx = float(str(self.unit_converter_x.DeviceUnitToReal(posx,self.convert_type_length)))
            coory = float(str(self.unit_converter_y.DeviceUnitToReal(posy,self.convert_type_length)))
        
        coorx,coory = self._remap_coordinates_flip((coorx,coory),get=True)
        return coorx,coory

def test_jog():
    xystage = XYController_M30XYM(sim=ControllerConfigEnum.SIMULATION_MODE.value)
    xystage.set_jog(1,vel_rel=100,acc_rel=100)
    for i in range(10):
        print('Test jog: ',i)
        xystage.move_jog('xfwd')
        time.sleep(0.2)
    xystage.stop_move()
    xystage.terminate()

def test_getcoor_whilemoving():
    def printcoor(flag:threading.Event):
        while not flag.is_set():
            coor = xystage.get_coordinates()
            print(coor)
            time.sleep(0.3)
            
    xystage = XYController_M30XYM(sim=ControllerConfigEnum.SIMULATION_MODE.value)
    flag = threading.Event()
    thread = threading.Thread(target=printcoor, args=(flag,))
    thread.start()
    xystage.movementtest()
    flag.set()

def test_connection_reinitialisation():
    xystage = XYController_M30XYM(sim=ControllerConfigEnum.SIMULATION_MODE.value)
    coor = xystage.get_coordinates()
    print(coor)
    
    print('Reinitialising connection...')
    xystage.reinitialise_connection()
    coor = xystage.get_coordinates()
    print(coor)
    xystage.terminate()

if __name__ == "__main__":
    # test_getcoor_whilemoving()
    # test_jog()
    test_connection_reinitialisation()