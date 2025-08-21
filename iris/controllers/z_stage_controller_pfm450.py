"""
A class that allows the control of the Z825B Thorlabs stage.
This implementation is based on the .NET Kinesis Libraries to connect to and control the stage.
"""
import os
import sys

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\library')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

from iris.utils.general import *

from iris.controllers.class_z_stage_controller import Class_ZController
from iris.controllers import ControllerSpecificConfigEnum,ControllerDirectionEnum

import time
import clr
import numpy as np

import threading

# Add References to .NET libraries
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
# clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.TCube.DCServoCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.Benchtop.PrecisionPiezoCLI.dll")

from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.GenericPiezoCLI import Piezo
from Thorlabs.MotionControl.Benchtop.PrecisionPiezoCLI import *
from System import Decimal  # Required for real units

class ZController_PFM450(Class_ZController):
    def __init__(self,sim=False) -> None:
        self._serial_no = ControllerSpecificConfigEnum.PFM450_SERIAL.value # The device's serial number
        
        self._dev = None            # Stores the device object
        self._dev_info = None       # Stores the device information
        self._channel = None        # Stores the channel object
        self._channel_polling_ms = 50   # Polling rate in [ms]

        self._isrunning_motor = False   # Running state of the motor. True: running, False: stopped
        
        self._dict_ctrl_remap = {
            'zfwd':ControllerDirectionEnum.ZFWD.value,
            'zrev':ControllerDirectionEnum.ZREV.value
        }   # Dictionary to remap the controls
        
        self._min_travel:float = 0.0    # Minimum travel distance of the motor in [mm]
        self._max_travel:float = None   # Maximum travel distance of the motor in [mm]

        self._jog_step_mm = 0.01        # Stores the jog step size in [mm]
        self._jog_step_min = 0.0002     # Minimum jog step size in [mm]
        
        self._timeout_move_fast = 2000  # Waiting time for movements to finish (in milisecond, integer)
        self._timeout_move_slow = 6000  # Waiting time for longer movements to finish (in milisecond, integer)
        self._stoptime = 0.1            # Waiting time to stop the motor [sec] > 0.75 otherwise error
        
        self._issimulation = sim     # True: To use when interacting with 'Kinesis Simulator'
        self._running = False        # Indicate the start and finish of the program.
                                    # True for start (initialization) and False for finish (termination)
        
        
        # Start by initializing the connection, device, motors, and their parameters
        try: self.initialisation()
        except Exception as e:
            print('Run ABORTED due to error in intialization: ',e)
            self.terminate(error_flag=True)
        
        # The piezo controller does not need homing (not sure?) and so won't be used here
    
    def initialisation(self):
        """
        Initialises the device, setup the connection, channels, motors and their parameters, etc.
        """
        if self._issimulation:
            print(">>>>> INITIALISING SIMULATION <<<<<")
            SimulationManager.Instance.InitializeSimulations()
            print(">>>>> Simulation Initialised <<<<<")
        else:
            print(">>>>> NOT A SIMULATION <<<<<")
        
        DeviceManagerCLI.BuildDeviceList()
        
        # Creates the device object, based on the serial number we have
        self._dev = BenchtopPrecisionPiezo.CreateBenchtopPiezo(self._serial_no)
        
        # Connect, begin polling, and enable
        self._dev.Connect(self._serial_no)
        time.sleep(0.25)  # wait statements are important to allow settings to be sent to the device
        self._channel = self._dev.GetChannel(1)
        self._channel.StartPolling(self._channel_polling_ms)    # Start polling

        # Check that the settings are initialised, else error.
        if not self._channel.IsSettingsInitialized():
        # if not x_channel.IsSettingsInitialized():
            self._channel.WaitForSettingsInitialized(10000)  # 10 second timeout
            assert self._channel.IsSettingsInitialized() is True
        
        # Get channel information
        self._max_travel = float(str(self._channel.GetMaxTravel()))

        # Set the control mode
        self._channel.SetPositionControlMode(Piezo.PiezoControlModeTypes.CloseLoop)
        time.sleep(.25)
        
    def terminate(self,error_flag=False):
        """
        Terminate the operation. Returns the stage to home and disconnects the device.
        """
        
        # Return the stage to Home
        # if not error_flag:
        #     self.homing_n_coor_calibration()

        # Stop polling and disconnects the device
        self._channel.StopPolling()
        self._dev.Disconnect()
        
        # Terminates the simulation (if it is a simulation, automatic detection)
        if self._issimulation:
            print(">>>>> TERMINATING SIMULATION STOPPED <<<<<")
            SimulationManager.Instance.UninitializeSimulations()
        self._running = False
    
    def get_vel_acc_relative(self):
        """
        Returns the current velocity and acceleration parameters of the channe.
        In this case, everything is at 100% as they cannot be controlled
        
        Returns:
            tuple of floats: 3 elements: (vel_homing, vel_move, acc_move)
        """
        vel_homing = vel_move = acc_move = 100
        return (vel_homing, vel_move, acc_move)
    
    def set_vel_acc_relative(self,vel_homing:int=100, vel_move:int=100, acc_move:int=100):
        """
        Set the velocity and acceleration parameters of the motors for both homing and typical movements.
        
        Args:
            vel_homing (int, optional): New motor homing velocity in percentage of max velocity. Defaults to 100.
            vel_move (int, optional): New motor movement velocity in percentage of max velocity. Defaults to 100.
            acc_move (int, optional): New motor movement acceleration in percentage of max acceleration. Defaults to 100.
            
        Note:
            - Because of the piezo control, this function does not change the velocity and acceleration parameters.
        """
        if vel_homing <= 0 or vel_move <= 0 or acc_move <= 0:
            raise ValueError("Velocity and acceleration parameters must be larger than 0%")
        if vel_homing > 100 or vel_move > 100 or acc_move > 100:
            raise ValueError("Velocity and acceleration parameters must be less than 100%")
        
        return
                    
    def get_coordinates(self) -> float:
        """
        Get the coordinates of the motor
        
        Returns:
            float: coordinate of the motor in [mm]
        """
        position_um = self._channel.GetPosition()
        coor = float(str(position_um))/10**3
        return coor

    def move_direct(self,coor_abs,waittime_sec:float=0.5):
        """
        Function to direct the motors to move at the same time towards a certain coordinate.
        
        Args:
            coor_abs (Decimal): coordinate of the destination in [mm]
            waittime_sec (float, optional): Waiting time for the motor to stop. Defaults to 0.5.
        """
        assert isinstance(coor_abs, (float,int)), "Coordinate must be a Decimal or float"
        assert self._min_travel <= coor_abs <= self._max_travel, "Coordinate out of bounds"
        assert isinstance(waittime_sec, (float,int)), "Wait time must be a float"
        assert waittime_sec > 0, 'Wait time must be greater than 0'

        # Convert the coordinates to decimals if floats are received
        if self._isrunning_motor == True:
            print('!!!!! Motor is running, movement request BLOCKED !!!!!')
            return
        
        self._isrunning_motor = True
        
        decimal_coor_abs_um = Decimal(float(coor_abs*10**3))
        self._channel.SetPosition(decimal_coor_abs_um)
        self._isrunning_motor = False
        time.sleep(waittime_sec) # Wait for the motor to stop
        
    def move_continuous(self,dir):
        """
        NOT AVAILABLE for this device: Moves the motor with a continuous motion until a stop command
        
        Args:
            dir (str): 'zfwd' forward and 'zrev' for reverse/backward
        """
        print('z_stage_controller.move_continuous() is NOT AVAILABLE for piezo devices')
        return
    
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
        self.move_direct(coor_abs=0.0)
        self._isrunning_motor = False
        print("<<<<< Coordinate calibration/Homing finished >>>>>")

    def get_jog(self) -> tuple[float,float,float]:
        """
        Get the jog parameters for the motor
        
        Returns:
            tuple of floats: 3 elements: (jog_step, jog_vel, jog_acc)
            
        Note:
            - The jog velocity and acceleration are not controlled by the user and are set to 100%.
        """
        return (self._jog_step_mm, 100, 100)
        
    def set_jog(self,dist_mm:float,vel_rel:int=100,acc_rel:int=100):
        """
        Set the jog parameters for the motor
        
        Args:
            dist_mm (float): distance to jog in mm
            vel_rel (int, optional): velocity in percentage of max velocity. Defaults to 100.
            acc_rel (int, optional): acceleration in percentage of max acceleration. Defaults to 100.
        """
        assert isinstance(dist_mm, (float,int)), "Distance must be a float"
        assert dist_mm >= self._jog_step_min,"Minimum jog step size is {}".format(self._jog_step_min)
        
        self._jog_step_mm = dist_mm
        
    def move_jog(self,direction:str):
        """
        Moves the motor with a single/continuous jogging motion until a stop command.
        
        Args:
            direction (str): 'zfwd' forward and 'zrev' for reverse/backward
        """
        if not isinstance(direction, str):
            raise ValueError("Direction must be a string")
        if direction not in ['zfwd', 'zrev']:
            raise ValueError("Direction must be 'zfwd' or 'zrev'")
        
        direction = self._dict_ctrl_remap[direction] # Remap the controls
        
        coor = self.get_coordinates()
        if direction == 'zfwd':
            coor_target = coor + self._jog_step_mm
        elif direction == 'zrev':
            coor_target = coor - self._jog_step_mm
        
        if coor_target < self._min_travel: coor_target = self._min_travel
        elif coor_target > self._max_travel: coor_target = self._max_travel

        try: self.move_direct(coor_target,waittime_sec=0.1)
        except: pass
        
    def stop_move(self):
        """
        Stop is NOT AVAILABLE for this device. This is because
        move_continuous() is also not available. And the move_direct() function
        is already blocking and waits for the movement to stop.
        """
        print('Stop is not available for piezo devices')
        return
        
    def MoveTestAbsolute(self):
        """
        Test the motor movement
        """
        # Stops at every few points
        distances = np.arange(0, 0.450, 0.020)
        for i,distance in enumerate(distances):
            print(i, distance)
            self.move_direct(float(distance))
            
    def MoveTestJog(self):
        """
        Test the motor movement
        """
        # Stops at every few points
        jog_step = 0.05 # [mm]
        self.set_jog(jog_step)
        for i in range(20):
            print(self.get_coordinates())
            self.move_jog('zrev')
            
        jog_step = 0.05 # [mm]
        self.set_jog(jog_step)
        for i in range(20):
            print(self.get_coordinates())
            self.move_jog('zfwd')


def development_test():
    serial_no = "44927840"

    DeviceManagerCLI.BuildDeviceList()

    dev = BenchtopPrecisionPiezo.CreateBenchtopPiezo(serial_no)

    dev.Connect(serial_no)
    time.sleep(0.25)
    channel = dev.GetChannel(1)
    channel.StartPolling(25)

    dev_info = dev.GetDeviceInfo()
    print('Connected to: {}'.format(dev_info.Description))

    # Because this is a benchtop controller we need a channel object
    channel = dev.GetChannel(1)

    # Ensure that the device settings have been initialized
    if not channel.IsSettingsInitialized():
        channel.WaitForSettingsInitialized(10000)  # 10 second timeout
        assert channel.IsSettingsInitialized() is True

    # Start polling and enable
    channel.StartPolling(50)  #250ms polling rate
    channel.EnableDevice()
    time.sleep(0.25)  # Wait for device to enable

# >> Test moving the device <<
    channel.SetPositionControlMode(Piezo.PiezoControlModeTypes.CloseLoop)
    channelconfig = channel.GetPiezoConfiguration(serial_no)
    max_travel_um = float(str(channel.GetMaxTravel()))
    print('Max travel: {}'.format(max_travel_um))

    # Move the device to a new position
    channel.SetPosition(Decimal(-150.0))
    time.sleep(3)
    print('Current position: {}'.format(channel.GetPosition()))
    channel.SetPosition(Decimal(150.0))
    time.sleep(1)
    print('New position: {}'.format(channel.GetPosition()))

    channel.StopPolling()
    dev.Disconnect()

def test_getcoor_while_moving():
    def printcoor(zstage:z_stage_controller,flag:threading.Event):
        while not flag.is_set():
            coor = zstage.get_coordinates()
            print('Current coordinate: ',coor)
            time.sleep(0.075)
        
    zstage = z_stage_controller()
    flag = threading.Event()
    thread = threading.Thread(target=printcoor,args=(zstage,flag))
    thread.start()
    zstage.MoveTestAbsolute()
    flag.set()
    thread.join()

if __name__ == "__main__":
    pass
    controller = z_stage_controller()
    controller.move_direct(0.0)
    controller.MoveTestAbsolute()
    input("Press Enter to continue")
    controller.MoveTestJog()
    input("Press Enter to continue")
    test_getcoor_while_moving()