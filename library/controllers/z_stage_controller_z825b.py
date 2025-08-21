"""
A class that allows the control of the Z825B Thorlabs stage.
This implementation is based on the .NET Kinesis Libraries to connect to and control the stage.
"""

import os
import sys

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\library')
    sys.path.append(os.path.dirname(SCRIPT_DIR))
    
from library.controllers.class_z_stage_controller import Class_ZController
from library.controllers import ControllerDirectionEnum, ControllerSpecificConfigEnum

import time
import clr
import numpy as np

import threading

# Add References to .NET libraries
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.TCube.DCServoCLI.dll")


from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.TCube.DCServoCLI import *
from System import Decimal  # Required for real units


class ZController_Z825B(Class_ZController):
    def __init__(self,sim=False) -> None:
        self.serial_no = ControllerSpecificConfigEnum.Z825B_SERIAL.value
        
        self.dev = None             # Stores the device object
        self.dev_info = None        # Stores the device information
        
        self.mdev_config = None         # Stores the motor config of the device
        self.mdev_homing = None         # Motor homing parameters object for coordinate calibration
        self._isrunning_motor = False   # Running state of the motor. True: running, False: stopped
        
        self.unit_converter = None      # Unit converter for motor
        self.convert_type_length = None # Type of conversion for length
        
        self.dict_ctrl_remap = {
            'zfwd':ControllerDirectionEnum.ZFWD.value,
            'zrev':ControllerDirectionEnum.ZREV.value
        }   # Dictionary to remap the controls
        
        self._jog_step = None       # Stores the jog step size in [mm]
        self._jog_vel = None        # Stores the jog velocity in [mm/s]
        self._jog_acc = None        # Stores the jog acceleration in [mm/s^2]
        self._jog_step_min = 0.0002 # Minimum jog step size in [mm]
        
        self._vel_max = float(2.3)  # Maximum velocity of the motor
        self._vel_min = float(0.1)  # Minimum velocity of the motor
        self._acc_max = float(4.0)  # Maximum acceleration of the motor
        self._acc_min = float(0.1)  # Minimum acceleration of the motor
        
        self.vel_homing = float(2.3)    # Homing velocity
        self.vel_move = float(2.3)      # Other movement velocity (everything else other than homing operation)
        self.acc_move = float(4.0)      # Other movement acceleration (^^^^^ as above ^^^^^)
        self.timeout_move_fast = 20000  # Waiting time for movements to finish (in milisecond, integer)
        self.timeout_move_slow = 60000  # Waiting time for longer movements to finish (in milisecond, integer)
        self.stoptime = 0.85            # Waiting time to stop the motor [sec] > 0.75 otherwise error
        
        self.issimulation = sim     # True: To use when interacting with 'Kinesis Simulator'
        self.running = False        # Indicate the start and finish of the program.
                                    # True for start (initialization) and False for finish (termination)
        
        
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
            if self.dev.NeedsHoming:
                self.homing_n_coor_calibration()
        except Exception as e:
            print('Coordinate calibration has failed:')
            print(e)
            self.terminate(error_flag=True)
    
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
        self.dev = TCubeDCServo.CreateTCubeDCServo(self.serial_no)
        
        # Connect, begin polling, and enable
        self.dev.Connect(self.serial_no)
        time.sleep(0.25)  # wait statements are important to allow settings to be sent to the device
        
        # Start polling and enables the device
        self.dev.StartPolling(250)
        time.sleep(0.25)  # wait statements are important to allow settings to be sent to the device
        self.dev.EnableDevice()
        time.sleep(0.25)  # Wait for device to enable

        # Get Device Information and display description
        self.dev_info = self.dev.GetDeviceInfo()
        print('Connected to: ' + self.dev_info.Description)
        
        # Check that the settings are initialised, else error.
        if not self.dev.IsSettingsInitialized():
        # if not x_channel.IsSettingsInitialized():
            self.dev.WaitForSettingsInitialized(10000)  # 10 second timeout
            assert self.dev.IsSettingsInitialized() is True

        # Load the motor configuration on the channel
        self.mdev_config = self.dev.LoadMotorConfiguration(self.serial_no,DeviceConfiguration.DeviceSettingsUseOptionType.UseFileSettings)
        self.mdev_config.DeviceSettingsName = "Z825B"
        print('fix device config info here')
        self.mdev_config.UpdateCurrentConfiguration()
        self.dev.SetSettings(self.dev.MotorDeviceSettings, True, False)
        ...
        # Get the Homing Params for coordinate calibration(ccal)
        self.mdev_homing = self.dev.GetHomingParams()
        
        # Set the movement velocity and acceleration parameters
        self.mdev_mvmt = self.dev.GetVelocityParams()
        
        print('\n<<<<< Device and motor initialisation complete >>>>>')
        self.running = True
        
        # Set the motor unit converter for coordinate retrieval
        self.unit_converter = self.dev.UnitConverter
        self.convert_type_length = self.unit_converter.UnitType(0)
        
    def get_vel_acc_relative(self):
        """
        Returns the current velocity and acceleration parameters of the motors

        Returns:
            tuple of floats: 3 elements: (vel_homing, vel_move, acc_move)
        """
        # Get the Homing Params for coordinate calibration(ccal)
        self.mdev_homing = self.dev.GetHomingParams()
        
        # Set the movement velocity and acceleration parameters
        self.mdev_mvmt = self.dev.GetVelocityParams()
        
        # Get the maximum velocity and acceleration of the motors
        self._vel_homing = float(str(self.mdev_homing.Velocity))
        self._vel_move = float(str(self.mdev_mvmt.MaxVelocity))
        self._acc_move = float(str(self.mdev_mvmt.Acceleration))
        
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
        if vel_homing <= 0 or vel_move <= 0 or acc_move <= 0:
            raise ValueError("Velocity and acceleration parameters must be larger than 0%")
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
            vel_homing (float, optional): New motor homing velocity. Defaults to None.
            vel_move (float, optional): New motor movement velocity. Defaults to None.
            acc_move (float, optional): New motor movement acceleration. Defaults to None.
        """
        
        if vel_homing == None and vel_move == None and acc_move == None:
            vel_homing = self.vel_homing
            vel_move = self.vel_move
            acc_move = self.acc_move
        
        # Modify the homing velocity if requested
        if vel_homing is not None:
            if not isinstance(vel_homing, float):
                raise ValueError("Velocity must be a float")
            
            # Set a hard limit to protect the motor
            if vel_homing > self._vel_max:
                print("Maximum device velocity is {}".format(self._vel_max))
                vel_homing = self._vel_max
            
            # Updates the stored value
            self._vel_homing = float(vel_homing)
            vel_homing = Decimal(vel_homing)
            
            # Modify the value in the motors
            self.mdev_homing.Velocity = vel_homing

        # Modify the movement velocity and acceleration parameters if requested
        if vel_move is not None:
            if not isinstance(vel_move, float) or isinstance(vel_move, int):
                raise ValueError("Velocity must be a float")
            
            if vel_move > self._vel_max:
                print("Maximum device velocity is {}".format(self._vel_max))
                vel_move = self._vel_max
            
            # Updates the stored value
            self._vel_move = float(vel_move)
            vel_move = Decimal(vel_move)
            
            # Modify the value in the motors
            self.mdev_mvmt.MaxVelocity = vel_move
        
        if acc_move is not None:
            if not isinstance(acc_move, float):
                raise ValueError("Velocity must be a float")
            
            if acc_move > self._acc_max:
                print("Maximum device velocity is {}".format(self._acc_max))
                acc_move = self._acc_max
            
            # Updates the stored value
            self._acc_move = float(acc_move)
            acc_move = Decimal(acc_move)
            
            # Modify the value in the motors
            self.mdev_mvmt.Acceleration = acc_move
        
        # Assign the set parameters to the motors
        self.dev.SetHomingParams(self.mdev_homing)
        
        # Assign the velocity and acceleration parameters to the motors
        self.dev.SetVelocityParams(self.mdev_mvmt)
    
    def get_coordinates_old(self):
        """
        Returns the current motor coordinate. Does not work for ~0.5 seconds after a movement command.
        DO NOT USE THIS FUNCTION. USE get_coordinates() INSTEAD.
        Kept here for reference.

        Returns:
            float: motor coordinate
        """
        coor = float(str(self.dev.Position))
        return coor
    
    def homing_n_coor_calibration(self):
        """
        A function to recalibrate the coordinate system of the device.
        - Also called as 'homing'
        """
        if self._isrunning_motor == True:
            print('!!!!! Motor is running, homing request BLOCKED !!!!!')
            return
        
        print("\n!!!!! Coordinate calibration/Homing starting !!!!!")
        self._isrunning_motor = True
        timeout_rel = int(self.timeout_move_slow * self._vel_max/self._vel_homing)
        self.dev.Home(timeout_rel)
        self._isrunning_motor = False
        print("<<<<< Coordinate calibration/Homing finished >>>>>")

    def terminate(self,error_flag=False):
        """
        Terminate the operation. Returns the stage to home and disconnects the device.
        """
        
        # Return the stage to Home
        # if not error_flag:
        #     self.homing_n_coor_calibration()

        # Stop polling and disconnects the device
        self.dev.StopPolling()
        self.dev.Disconnect()
        
        # Terminates the simulation (if it is a simulation, automatic detection)
        if self.issimulation:
            print(">>>>> TERMINATING SIMULATION STOPPED <<<<<")
            SimulationManager.Instance.UninitializeSimulations()
        self.running = False
    
    def move_direct(self,coor_abs):
        """
        Function to direct the motors to move at the same time towards a certain coordinate.

        Args:
            coor_abs (Decimal): coordinate of the destination
        """
        # Convert the coordinates to decimals if floats are received
        if type(coor_abs) is float:
            coor_abs= Decimal(coor_abs)
        
        if self._isrunning_motor == True:
            print('!!!!! Motor is running, movement request BLOCKED !!!!!')
            return
        
        self._isrunning_motor = True
        
        timeout_rel = int(self.timeout_move_fast * self._vel_max/self._vel_move)
        self.dev.MoveTo(coor_abs,timeout_rel)
        self._isrunning_motor = False
        time.sleep(0.85)
        
    def move_continuous(self,dir):
        """
        Moves the motor with a continuous motion until a stop command

        Args:
            dir (str): 'zfwd' forward and 'zrev' for reverse/backward
        """
        if self._isrunning_motor == True:
            print('!!!!! Motor is running, movement request BLOCKED !!!!!')
            return
        
        dir = self.dict_ctrl_remap[dir] # Remap the controls
        
        if dir == 'zfwd':
            direction = MotorDirection.Forward
        elif dir == 'zrev':
            direction = MotorDirection.Backward
            
        try:
            self.dev.MoveContinuous(direction)
            # Update the motor running state
            self._isrunning_motor = True
        except Exception as errormessage:
            print(errormessage)
    
    def get_jog(self):
        """
        Get the jog parameters for the motor
        
        Returns:
            tuple of floats: 3 elements: (jog_step, jog_vel, jog_acc)
        """
        JogParams = self.dev.GetJogParams()
        self._jog_step = float(str(JogParams.StepSize))
        VelocityParams = JogParams.VelocityParams
        self._jog_vel = float(str(VelocityParams.MaxVelocity))
        self._jog_acc = float(str(VelocityParams.Acceleration))
        
        
        print('z_stage_controller.get_jog() is NOT TESTED yet')
        
        return (self._jog_step, self._jog_vel, self._jog_acc)
        
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
        
        JogParams = self.dev.GetJogParams()
        VelocityParams = JogParams.VelocityParams
        
        if not isinstance(vel_rel, int) or isinstance(vel_rel, float):
            raise ValueError("Velocity must be an integer")
        if not isinstance(acc_rel, int) or isinstance(acc_rel, float):
            raise ValueError("Acceleration must be an integer")
        VelocityParams.MaxVelocity = Decimal(self._vel_max * vel_rel / 100)
        VelocityParams.Acceleration = Decimal(self._acc_max * acc_rel / 100)
        
        JogParams.StepSize = Decimal(dist_mm)
        self.dev.SetJogParams(JogParams)
        
        print('z_stage_controller.set_jog() is NOT TESTED yet')
        pass
        
    def move_jog(self,direction:str):
        """
        Moves the motor with a single/continuous jogging motion until a stop command.
        
        Args:
            direction (str): 'zfwd' forward and 'zrev' for reverse/backward
        """
        timeout_rel = int(self.timeout_move_fast * self._vel_max/self._vel_move)
        
        if not isinstance(direction, str):
            raise ValueError("Direction must be a string")
        if direction not in ['zfwd', 'zrev']:
            raise ValueError("Direction must be 'zfwd' or 'zrev'")
        
        if self._isrunning_motor == True:
            print('!!!!! Motor is running, movement request BLOCKED !!!!!')
            return
        
        direction = self.dict_ctrl_remap[direction] # Remap the controls
        
        self._isrunning_motor = True
        if direction == 'zfwd':
            self.dev.MoveJog(MotorDirection.Forward,timeout_rel)
        elif direction == 'zrev':
            self.dev.MoveJog(MotorDirection.Backward,timeout_rel)
        self._isrunning_motor = False
        
    def stop_move(self):
        """
        Stops all motor movement
        """
        self.dev.Stop(0)
        time.sleep(self.stoptime)   # Wait to allow the motors to stop completely
        self._isrunning_motor = False         # Update the motor state
        
    def MoveTestAbsolute(self):
        """
        Test the motor movement
        """
        # Stops at every few points
        distances = np.arange(0, 25, 2)
        for i,distance in enumerate(distances):
            print(i, distance)
            self.move_direct(float(distance))
            
    def MoveTestJog(self):
        """
        Test the motor movement
        """
        # Stops at every few points
        jog_step = 2 # [mm]
        self.set_jog(jog_step)
        for i in range(5):
            print(self.get_coordinates())
            self.move_jog('fwd')
            
        jog_step = 1 # [mm]
        self.set_jog(jog_step)
        for i in range(10):
            print(self.get_coordinates())
            self.move_jog('rev')
            
    def get_coordinates(self):
        """
        Get the coordinates of the motor
        """
        position = Decimal(self.dev.GetPositionCounter())
        coor = float(str(self.unit_converter.DeviceUnitToReal(position,self.convert_type_length)))
        return coor

def test_getcoor_while_moving():
    def printcoor(zstage:z_stage_controller,flag:threading.Event):
        while not flag.is_set():
            coor = zstage.get_coordinates()
            print('Current coordinate: ',coor)
            time.sleep(0.2)
        
    zstage = z_stage_controller(sim=True)
    flag = threading.Event()
    thread = threading.Thread(target=printcoor,args=(zstage,flag))
    thread.start()
    zstage.MoveTestAbsolute()
    flag.set()
    thread.join()

if __name__ == "__main__":
    test_getcoor_while_moving()
    # zstage = z_stage_controller(sim=True)
    # zstage.MoveTestAbsolute()
    # zstage.MoveTestJog()
    # zstage.terminate()