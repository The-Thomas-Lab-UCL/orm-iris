"""
Class definition for the z-stage controller and a guide to writing one for the
Open Raman Microscopy (ORM) app.
"""

import os
import time
import sys
import numpy as np

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.controllers import ControllerDirectionEnum

class Class_ZController():
    def __init__(self,**kwargs) -> None:
        
        self._dict_ctrl_remap = {
            'zfwd':ControllerDirectionEnum.ZFWD.value,
            'zrev':ControllerDirectionEnum.ZREV.value
        }   # Dictionary to remap the controls
        
        # <<<<< Insert the device parameters here
        
        # Start by initializing the connection, device, motors, and their parameters
        try:
            self.initialisation()
        except Exception as e:
            print('Run ABORTED due to error in intialization:')
            print(e)
            self.terminate()
        
        # Continue by setting up the motors and initializing (calibrating) the coordinate system of the motors
        try:
            if True: # <<<<< Insert homing check condition here if required
                self.set_vel_acc_relative()
                self.homing_n_coor_calibration()
        except Exception as e:
            print('Coordinate calibration has failed:')
            print(e)
            self.terminate()
        
    def get_identifier(self) -> str:
        """
        Returns the identifier of the camera.

        Returns:
            str: The identifier of the camera
        """
        # <<<<< Insert the command to get the camera identifier here
        identifier = "ZStageController_ID: Not set"
        return identifier
        
    def initialisation(self) -> None:
        """
        Initialises the parameters
        """
        # <<<<< Insert the initialisation commands here
        pass
        
    def get_vel_acc_relative(self) -> tuple[float,float,float]:
        """
        Returns the current velocity and acceleration parameters of the motors

        Returns:
            tuple of floats: 3 elements: (vel_homing, vel_move, acc_move)
        """
        # <<<<< Insert the velocity and acceleration retrieval commands here
        vel = 100
        pass
        return (vel,vel,float(100))
    
    def set_vel_acc_relative(self,vel_homing:int=100, vel_move:int=100, acc_move:int=100) -> None:
        """
        Set the velocity and acceleration parameters of the motors for both homing and typical movements.
        
        Args:
            vel_homing (int, optional): Legacy parameter. Is ignored.
            vel_move (int, optional): New motor movement velocity in percentage of max velocity. Defaults to 100.
            acc_move (int, optional): Legacy parameter. Is ignored.
        """
        if vel_move < 1 or vel_move > 100:
            raise ValueError("Velocity and acceleration parameters must be larger than 1% and smaller than 100%")
        
        if not isinstance(vel_move, int) and not isinstance(vel_move, float):
            raise ValueError("Velocity must be an integer")
        
        # <<<<< Insert the velocity and acceleration setting commands here
        pass
    
    def homing_n_coor_calibration(self) -> None:
        """
        A function to recalibrate the coordinate system of the device.
        Also called as 'homing'
        """
        # <<<<< Insert the homing and coordinate calibration commands here
        pass
    
    def terminate(self) -> None:
        """
        Terminate the operation. Returns the stage to home and disconnects the device.
        """
        try:
            # <<<<< Insert the termination commands here
            pass
        except Exception as e:
            print('Error in closing the device:')
            print(e)
    
    def move_direct(self,coor_abs) -> None:
        """
        Function to direct the motors to move at the same time towards a certain coordinate.

        Args:
            coor_abs (float): coordinate of the destination [mm]
        """
        if not isinstance(coor_abs, float) and not isinstance(coor_abs, int):
            raise ValueError("Coordinate must be a float")
        
        # <<<<< Insert the direct movement commands here
        pass
        
    def move_continuous(self,dir) -> None:
        """
        Moves the motor with a continuous motion until a stop command

        Args:
            dir (str): 'zfwd' forward and 'zrev' for reverse/backward
        """
        if False: # <<<<< Insert the motor running check condition here
            print('!!!!! Motor is running, movement request BLOCKED !!!!!')
            return
        
        dir = self._dict_ctrl_remap[dir] # Remap the controls
        
        if dir == 'zfwd':
            # <<<<< Insert the forward movement command here
            pass
        elif dir == 'zrev':
            # <<<<< Insert the forward movement command here
            pass
        else:
            raise ValueError("Direction must be 'fwd' or 'rev'")
    
    def get_jog(self) -> tuple[float,float,float]:
        """
        Get the jog parameters for the motor
        
        Returns:
            tuple of floats: 3 elements: (jog_step [mm], jog_vel, jog_acc)
            
        Note:
            - jog_vel and jog_acc are not available in the MCM301 library
        """
        # <<<<< Insert the jog parameter retrieval commands here
        jog_step_mm = 0.01
        
        return (jog_step_mm, None, None)
        
    def set_jog(self,dist_mm:float,vel_rel:int=100,acc_rel:int=100) -> None:
        """
        Set the jog parameters for the motor
        
        Args:
            dist_mm (float): distance to jog in mm
            vel_rel (int, optional): Legacy parameter. Is ignored.
            acc_rel (int, optional): Legacy parameter. Is ignored.
        """
        if not isinstance(dist_mm, float) and not isinstance(dist_mm, int):
            raise ValueError("Distance must be a float")
        
        if False: # <<<<< Insert the jog step size check condition here if required
            raise ValueError("Minimum jog step size is {}".format(self._jog_step_min))
        
        # <<<<< Insert the jog parameter setting commands here
        pass
        
    def move_jog(self,direction:str) -> None:
        """
        Moves the motor with a single/continuous jogging motion until a stop command.
        
        Args:
            direction (str): 'zfwd' forward and 'zrev' for reverse/backward
        """
        if False: # <<<<< Insert the motor running check condition here if required
            print('!!!!! Motor is running, movement request BLOCKED !!!!!')
            return
        
        direction = self._dict_ctrl_remap[direction] # Remap the controls
        
        if direction == 'zfwd':
            # <<<<< Insert the forward jog movement command here
            pass
        elif direction == 'zrev':
            # <<<<< Insert the reverse jog movement command here
            pass
        else:
            raise ValueError("Direction must be 'zfwd' or 'zrev'")
        
    def stop_move(self) -> None:
        """
        Stops all motor movement. Will try 5 times before giving up.
        """
        # <<<<< Insert the stop movement commands here
        pass
        
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
            
    def get_coordinates(self) -> float:
        """
        Get the coordinates of the motor [mm]
        """
        # <<<<< Insert the coordinate retrieval commands here
        position_mm = float(0)
        pass
    
        return position_mm

def test_getcoor_while_moving():
    def printcoor(zstage:z_stage_controller,flag:threading.Event):
        while not flag.is_set():
            coor = zstage.get_coordinates()
            print('Current coordinate: ',coor)
            time.sleep(0.2)
        
    import threading
    
    zstage = z_stage_controller(sim=True)
    flag = threading.Event()
    thread = threading.Thread(target=printcoor,args=(zstage,flag))
    thread.start()
    zstage._MoveTestAbsolute()
    flag.set()
    thread.join()

if __name__ == "__main__":
    # test_getcoor_while_moving()
    zstage = z_stage_controller(sim=True)
    zstage._MoveTestAbsolute()
    zstage._MoveTestJog()
    zstage.terminate()