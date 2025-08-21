"""
A class that allows the control of the Z825B Thorlabs stage.
This implementation is based on the .NET Kinesis Libraries to connect to and control the stage.
"""

import os
import time
import sys
import numpy as np
import threading

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))

from iris.controllers.class_z_stage_controller import Class_ZController

class ZController_Dummy(Class_ZController):
    def __init__(self,**kwargs) -> None:
        self._coor_mm = float(0)    # Stores the current coordinate of the motor in [mm]
        
        self._vel = 100  # Stores the velocity of the motor in percentage of max velocity
        self._motor_step_mm = float(0.001)  # Stores the motor step size in [mm]
        self._motor_step_wait_s = 1e-6  # Stores the time to wait for the motor to move in [s]
        
        self._jog_step_mm = float(0.1)  # Stores the jog step size of the motor in [mm]
        
        self._vel = float(100)  # Stores the velocity of the motor in percentage of max velocity
        
        self._thread_movecontinuous:threading.Thread|None = None    # Thread to move the motor continuously
        self._flg_movecontinuous = threading.Event()    # Flag to stop the continuous movement
        
        self._isrunning_motor = False   # Flag to check if the motor is running
        print('\n>>>>> DUMMY Z controller is used <<<<<')
                
    def initialisation(self):
        """
        Initialises the parameters
        """
        pass
        
    def get_vel_acc_relative(self):
        """
        Returns the current velocity and acceleration parameters of the motors

        Returns:
            tuple of floats: 3 elements: (vel_homing, vel_move, acc_move)
        """
        # Unfortunately the MCM301 library doesn't provide a way to get the velocity and acceleration parameters
        return (100, self._vel, 100)
    
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
        
        self._vel = float(vel_move)
    
    def homing_n_coor_calibration(self):
        """
        A function to recalibrate the coordinate system of the device.
        Also called as 'homing'
        """
        print('Homing the Z stage')
        self._coor_mm = float(0)
        
        print('Homing done')
            
    def terminate(self):
        """
        Terminate the operation. Returns the stage to home and disconnects the device.
        """
        print('Terminating the Z stage controller')
            
    def move_direct(self,coor_abs):
        """
        Function to direct the motors to move at the same time towards a certain coordinate.

        Args:
            coor_abs (float): coordinate of the destination [mm]
        """
        if not isinstance(coor_abs, float) and not isinstance(coor_abs, int):
            raise ValueError("Coordinate must be a float")
        
        count = int((coor_abs-self._coor_mm) / self._motor_step_mm)
        
        target = self._coor_mm + count*self._motor_step_mm
        
        while True:
            if self._coor_mm < target:
                self._coor_mm += self._motor_step_mm
            elif self._coor_mm > target:
                self._coor_mm -= self._motor_step_mm
            
            error = abs(self._coor_mm - target)
            if error < 0.02:
                break
            time.sleep(self._motor_step_wait_s/(self._vel/100))
            
        return
                
    def move_continuous(self,dir):
        """
        Moves the motor with a continuous motion until a stop command

        Args:
            dir (str): 'zfwd' forward and 'zrev' for reverse/backward
        """
        
        def move_continuous_thread(self:ZController_Dummy,dir):
            self._flg_movecontinuous.set()
            while self._flg_movecontinuous.is_set():
                if dir == 'zfwd':
                    self._coor_mm += self._motor_step_mm
                elif dir == 'zrev':
                    self._coor_mm -= self._motor_step_mm
                else:
                    raise ValueError("Direction must be 'zfwd' or 'zrev'")
                    
                time.sleep(self._motor_step_wait_s/(self._vel/100))
                
        self._thread_movecontinuous = threading.Thread(target=move_continuous_thread,args=(self,dir))
        self._thread_movecontinuous.start()
    
    def get_jog(self):
        """
        Get the jog parameters for the motor
        
        Returns:
            tuple of floats: 3 elements: (jog_step [mm], jog_vel, jog_acc)
            
        Note:
            - jog_vel and jog_acc are not available in the MCM301 library
        """
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
        
        if dist_mm <= 0:
            raise ValueError("Minimum jog step size is {}".format(self._jog_step_min))
        
        self._jog_step_mm = dist_mm
        
    def move_jog(self,direction:str):
        """
        Moves the motor with a single/continuous jogging motion until a stop command.
        
        Args:
            direction (str): 'zfwd' forward and 'zrev' for reverse/backward
        """
        
        if direction == 'zfwd':
            target = self._coor_mm + self._jog_step_mm
        elif direction == 'zrev':
            target = self._coor_mm - self._jog_step_mm
        
        while True:
            if direction == 'zfwd':
                self._coor_mm += self._jog_step_mm
            elif direction == 'zrev':
                self._coor_mm -= self._jog_step_mm
            else:
                raise ValueError("Direction must be 'zfwd' or 'zrev'")
                
            error = abs(self._coor_mm - target)
            if error < 0.01:
                break
                
            time.sleep(self._motor_step_wait_s/(self._vel/100))
        
    def stop_move(self):
        """
        Stops all motor movement. Will try 5 times before giving up.
        """
        if isinstance(self._thread_movecontinuous, threading.Thread):
            if self._thread_movecontinuous.is_alive():
                self._flg_movecontinuous.clear()
                self._thread_movecontinuous.join()
                self._thread_movecontinuous = None
            else:
                self._thread_movecontinuous = None
        
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
            self.move_jog('zfwd')
            
        jog_step = 1 # [mm]
        self.set_jog(jog_step)
        for i in range(10):
            print(self.get_coordinates())
            self.move_jog('zrev')
            
    def get_coordinates(self):
        """
        Get the coordinates of the motor [mm]
        """
        return self._coor_mm

def test_getcoor_while_moving():
    def printcoor(zstage:z_stage_controller,flag:threading.Event):
        while not flag.is_set():
            coor = zstage.get_coordinates()
            print('Current coordinate: ',coor)
            time.sleep(0.2)
        
    zstage = z_stage_controller()
    flag = threading.Event()
    thread = threading.Thread(target=printcoor,args=(zstage,flag))
    thread.start()
    zstage._MoveTestAbsolute()
    flag.set()
    thread.join()

if __name__ == "__main__":
    # test_getcoor_while_moving()
    zstage = z_stage_controller()
    # zstage._MoveTestAbsolute()
    zstage._MoveTestJog()
    zstage.terminate()