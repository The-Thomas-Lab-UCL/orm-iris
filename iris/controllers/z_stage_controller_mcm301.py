"""
A class that allows the control of the Z825B Thorlabs stage.
This implementation is based on the .NET Kinesis Libraries to connect to and control the stage.
"""

import os
import time
import sys
import numpy as np
import threading

from iris.controllers import ControllerSpecificConfigEnum
from iris.controllers.class_z_stage_controller import Class_ZController
from iris.controllers import ControllerDirectionEnum

# Import MCM301 using the wrapper to handle SDK import issues
from iris.controllers.mcm301_wrapper import get_mcm301_class

class ZController_MCM301(Class_ZController):
    def __init__(self,sim=False) -> None:
        # Get the MCM301 class from the wrapper
        MCM301 = get_mcm301_class()
        
        self.controller = MCM301()
        self.devs = MCM301.list_devices()
        
        if len(self.devs) <= 0:
            raise("MCM301: There is no devices connected")
        
        self.BitPerSec = 115200 # Baud rate
        self.timeout_connect = 3 # Connection timeout in seconds
        
        self.dev_info = self.devs[0]
        self.serial_no = self.dev_info[0]
        self.hdl = self.controller.open(self.serial_no, self.BitPerSec, self.timeout_connect)
        
        if self.hdl < 0:
            raise("MCM301: Open failed")
        if self.controller.is_open(self.serial_no) == 0:
            raise("MCM301: MCM301IsOpen failed")
        
        # Motor parameters setup
        self.slot = 4               # Slot number of the motor
        self.mot_waittime = 0.005   # Wait time for the motor to stop moving [sec]
        
        self.status_bit = [0]       # Status bit of the motor for get_mot_status
        self.encoder = [0]          # Encoder value of the motor for get_mot_status
        self.info = [0]             # Information of the motor for get_stage_params
        
        self.max_hw_enc = None      # Maximum hardware position of the motor in encoder units
        self.min_hw_enc = None      # Minimum hardware position of the motor in encoder units
        self.max_hw_mm = None      # Maximum hardware position of the motor in [mm]
        self.min_hw_mm = None      # Minimum hardware position of the motor in [mm]
        
        self.dict_ctrl_remap = {
            'zfwd':ControllerDirectionEnum.ZFWD.value,
            'zrev':ControllerDirectionEnum.ZREV.value
        }   # Dictionary to remap the controls
        
        self._jog_step_mm = None    # Stores the jog step size in [mm]
        self._jog_step_min = 0.0002 # Minimum jog step size in [mm]
        
        self._vel = int(100)      # Stores the velocity of the motor [%]
        self._vel_max = int(100)  # Maximum velocity of the motor [%]
        self._vel_min = int(1)    # Minimum velocity of the motor [%]
        
        self._isrunning_motor = False   # Flag to check if the motor is running
        
        
        # Start by initializing the connection, device, motors, and their parameters
        try:
            self.initialisation()
        except Exception as e:
            print('Run ABORTED due to error in intialization:')
            print(e)
            self.terminate()
        
        # Continue by setting up the motors and initializing (calibrating) the coordinate system of the motors
        try:
            self.set_vel_acc_relative()
            self.homing_n_coor_calibration()
        except Exception as e:
            print('Coordinate calibration has failed:')
            print(e)
            self.terminate()
        
    def initialisation(self):
        """
        Initialises the parameters
        """
        self.controller.get_stage_params(self.slot, self.info)
        dev_info:list = self.info[0]
        
        self.min_hw_enc = dev_info[2]   # Minimum hardware position of the motor in encoder units
        self.max_hw_enc = dev_info[3]   # Maximum hardware position of the motor in encoder units
        
        pos_container = [0]
        self.controller.convert_encoder_to_nm(self.slot, self.min_hw_enc, pos_container) * 1e-6
        self.min_hw_mm = float(pos_container[0] * 1e-6)
        self.controller.convert_encoder_to_nm(self.slot, self.max_hw_enc, pos_container) * 1e-6
        self.max_hw_mm = float(pos_container[0] * 1e-6)
        
    def get_vel_acc_relative(self):
        """
        Returns the current velocity and acceleration parameters of the motors

        Returns:
            tuple of floats: 3 elements: (vel_homing, vel_move, acc_move)
        """
        # Unfortunately the MCM301 library doesn't provide a way to get the velocity and acceleration parameters
        
        return (self._vel,self._vel,float(100))
    
    def set_vel_acc_relative(self,vel_homing:int=100, vel_move:int=100, acc_move:int=100):
        """
        Set the velocity and acceleration parameters of the motors for both homing and typical movements.
        
        Args:
            vel_homing (int, optional): Legacy parameter. Is ignored.
            vel_move (int, optional): New motor movement velocity in percentage of max velocity. Defaults to 100.
            acc_move (int, optional): Legacy parameter. Is ignored.
        """
        if vel_move <= 0 or vel_move > 100:
            raise ValueError("Velocity and acceleration parameters must be larger than 0% and smaller than 100%")
        
        if not isinstance(vel_move, int) and not isinstance(vel_move, float):
            raise ValueError("Velocity must be an integer")
        
        # Convert the percentage to the actual value
        vel = vel_move
            
        if isinstance(vel,float):
            vel = int(vel)
        
        if vel > self._vel_max:
            print("Maximum device velocity is {}".format(self._vel_max))
            vel = self._vel_max
        
        if vel < self._vel_min:
            print("Minimum device velocity is {}".format(self._vel_min))
            vel = self._vel_min
        
        # Update the stored value
        self._vel = vel
    
    def homing_n_coor_calibration(self):
        """
        A function to recalibrate the coordinate system of the device.
        Also called as 'homing'
        """
        if self._isrunning_motor == True:
            print('!!!!! Motor is running, homing request BLOCKED !!!!!')
            return
        
        result = self.controller.home(self.slot)
        if result < 0:
            print("Homing failed")
            return
        
        # Wait for the motor to stop moving
        self._wait_stop()
        self._isrunning_motor = False
        
    def _wait_stop(self):
        """
        Wait for all movements to stop
        """
        isrunning = True
        while isrunning:
            self.controller.get_mot_status(self.slot, self.encoder, self.status_bit)
            isrunning = (self.status_bit[0] & 0x10) or (self.status_bit[0] & 0x20)\
                or (self.status_bit[0] & 0x40) or (self.status_bit[0] & 0x80)
            time.sleep(self.mot_waittime)
        
    def _wait_moving_stop(self):
        """
        A function to wait for the motor to stop moving.
        """
        isrunning = True
        status_bit = [0]
        encoder = [0]
        while isrunning:
            self.controller.get_mot_status(self.slot, encoder, status_bit)
            status_bit_value = status_bit[0]
            isrunning = (status_bit_value & 0x10) or (status_bit_value & 0x20)
            time.sleep(self.mot_waittime)
            
    def _wait_jog_stop(self):
        """
        A function to wait for the motor to stop jogging.
        """
        isrunning = True
        status_bit = [0]
        encoder = [0]
        while isrunning:
            self.controller.get_mot_status(self.slot, encoder, status_bit)
            status_bit_value = status_bit[0]
            isrunning = (status_bit_value & 0x40) or (status_bit_value & 0x80)
            time.sleep(self.mot_waittime)
    
    def terminate(self):
        """
        Terminate the operation. Returns the stage to home and disconnects the device.
        """
        try:
            self.controller.close()
        except Exception as e:
            print('Error in closing the device:')
            print(e)
    
    def move_direct(self,coor_abs):
        """
        Function to direct the motors to move at the same time towards a certain coordinate.

        Args:
            coor_abs (float): coordinate of the destination [mm]
        """
        if not isinstance(coor_abs, float) and not isinstance(coor_abs, int):
            raise ValueError("Coordinate must be a float")
        
        coor_enc = [0]
        ret = self.controller.convert_nm_to_encoder(self.slot, float(coor_abs*1000000), coor_enc)
        if ret < 0:
            raise Exception("move_direct: conversion failed")
            
        self._isrunning_motor = True
        ret = self.controller.move_absolute(self.slot, coor_enc[0])
        if ret < 0:
            raise Exception("move_direct: move_absolute failed")
        self._wait_stop()
        self._isrunning_motor = False
        
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
            self.controller.set_velocity(self.slot,1,self._vel)
        elif dir == 'zrev':
            self.controller.set_velocity(self.slot,0,self._vel)
        else:
            raise ValueError("Direction must be 'fwd' or 'rev'")
    
    def get_jog(self):
        """
        Get the jog parameters for the motor
        
        Returns:
            tuple of floats: 3 elements: (jog_step [mm], jog_vel, jog_acc)
            
        Note:
            - jog_vel and jog_acc are not available in the MCM301 library
        """
        
        jog_step_enc = [0]
        self.controller.get_jog_params(self.slot, jog_step_enc)
        pos_container = [0]
        self.controller.convert_encoder_to_nm(self.slot, jog_step_enc[0], pos_container)
        self._jog_step_mm = float(pos_container[0] * 1e-6)
        
        return (self._jog_step_mm, None, None)
        
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
        
        if dist_mm < self._jog_step_min:
            raise ValueError("Minimum jog step size is {}".format(self._jog_step_min))
        
        dist_enc = [0]
        self.controller.convert_nm_to_encoder(self.slot, float(dist_mm*1000000), dist_enc)
        
        # Set the jog step size
        self.controller.set_jog_params(self.slot, dist_enc[0])
        
    def move_jog(self,direction:str):
        """
        Moves the motor with a single/continuous jogging motion until a stop command.
        
        Args:
            direction (str): 'zfwd' forward and 'zrev' for reverse/backward
        """
        if self._isrunning_motor == True:
            print('!!!!! Motor is running, movement request BLOCKED !!!!!')
            return
        
        direction = self.dict_ctrl_remap[direction] # Remap the controls
        
        self._isrunning_motor = True
        if direction == 'zfwd':
            self.controller.move_jog(self.slot, 1)
        elif direction == 'zrev':
            self.controller.move_jog(self.slot, 0)
        else:
            raise ValueError("Direction must be 'zfwd' or 'zrev'")
        
        self._isrunning_motor = False
        self._wait_stop()
        
    def stop_move(self):
        """
        Stops all motor movement. Will try 5 times before giving up.
        """
        ret = self.controller.move_stop(self.slot)
        for i in range(4):
            if ret < 0:
                print("move_stop failed")
                time.sleep(0.5)
                ret = self.controller.move_stop(self.slot)
            else:
                break
        
        if ret < 0:
            raise Exception("stop_move: move_stop failed")
        else:
            self._isrunning_motor = False
        
    def _MoveTestAbsolute(self):
        """
        Test the motor movement
        """
        # Stops at every few points
        distances = np.arange(0, 25, 2)
        for i,distance in enumerate(distances):
            print(i, distance)
            self.move_direct(float(distance))
            
    def _MoveTestJog(self):
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
        Get the coordinates of the motor [mm]
        """
        ret = self.controller.get_mot_status(self.slot, self.encoder, self.status_bit)
        
        pos_container = [0]
        self.controller.convert_encoder_to_nm(self.slot, self.encoder[0], pos_container)
        position_mm = float(pos_container[0] * 1e-6)
        return position_mm

def test_getcoor_while_moving():
    def printcoor(zstage:ZController_MCM301,flag:threading.Event):
        while not flag.is_set():
            coor = zstage.get_coordinates()
            print('Current coordinate: ',coor)
            time.sleep(0.2)
        
    zstage = ZController_MCM301(sim=True)
    flag = threading.Event()
    thread = threading.Thread(target=printcoor,args=(zstage,flag))
    thread.start()
    zstage._MoveTestAbsolute()
    flag.set()
    thread.join()

if __name__ == "__main__":
    # test_getcoor_while_moving()
    zstage = ZController_MCM301(sim=True)
    zstage._MoveTestAbsolute()
    zstage._MoveTestJog()
    zstage.terminate()