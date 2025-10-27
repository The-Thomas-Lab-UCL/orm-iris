"""
Class definition for the XY stage controller and a guide to write one
Open Raman Microscopy (ORM) app.
"""
import os
import sys

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))
    

from iris.utils.general import *
from iris.controllers import ControllerConfigEnum, ControllerDirectionEnum


import numpy as np
import time

class Class_XYController():
    def __init__(self,**kwargs) -> None:
        # Remapping of the controls
        self.dict_ctrl_remap = {
            'xfwd':ControllerDirectionEnum.XFWD.value,
            'xrev':ControllerDirectionEnum.XREV.value,
            'yfwd':ControllerDirectionEnum.YFWD.value,
            'yrev':ControllerDirectionEnum.YREV.value,
        }   # Dictionary to remap the controls (only for the continuous and jog movements)
        
        self._max_vel_mmS = 100.0    # Maximum velocity of the motor in mm/s
        self._min_vel_mmS = 0.1      # Minimum velocity of the motor in mm/s
        
        self._flipxy = ControllerConfigEnum.STAGE_FLIPXY.value      # Flag to indicate if the x and y axes are flipped in referece to the image capture
        self._invertx = ControllerConfigEnum.STAGE_INVERTX.value    # Flag to indicate if the x axis is flipped (inverted)
        self._inverty = ControllerConfigEnum.STAGE_INVERTY.value    # Flag to indicate if the y axis is flipped (inverted)
        
        # Motor parameters
        ## <<< Here, you can insert the parameters required for the operations:
        ## such as, the maximum velocity, acceleration, etc.
        ## coordinate retrieval parameters, etc.
        
        # Start by initializing the connection, device, motors, and their parameters
        try:
            self.initialisation()
        except Exception as e:
            print('Run ABORTED due to error in intialization:')
            print(e)
            self.terminate()
        
        # Continue by setting up the motors and initializing (calibrating) the coordinate system of the motors
        try:
            if True: # <<<<< Insert homing conditions here if possible
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
        identifier = "XYStageController_ID: Not set"
        return identifier
            
    def reinitialise_connection(self) -> None:
        """
        Reinitialise the connection to the device
        """
        try:self.terminate()
        except Exception as e: print('Reinitialisation error:\n{}'.format(e))
        
        try:self.initialisation()
        except Exception as e: print('Reinitialisation error:\n{}'.format(e))
    
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
        
    def initialisation(self) -> None:
        """
        Initialises the device, setup the connection, channels, motors and their parameters, etc.
        """
        # Device parameters
        ## <<<<< Here, you can insert the device parameters and connection initialisation commands
        pass
        
        print('\n>>>>> Device and motor initialisation complete <<<<<')
    
    def set_vel_acc_relative(self,vel_homing:float=100, vel_move:float=100, acc_move:float=100) -> None:
        """
        Set the velocity and acceleration parameters of the motors for both homing and typical movements.
        
        Args:
            vel_homing (int, optional): Legacy parameter. Is ignored.
            vel_move (int, optional): New motor movement velocity in percentage of max velocity. Defaults to 100.
            acc_move (int, optional): Legacy parameter. Is ignored.
        """
        if vel_move < 0:
            raise ValueError("Velocity and acceleration parameters must be larger than 0%")
        if vel_move > 100:
            raise ValueError("Velocity and acceleration parameters must be less than 100%")
        
        # <<<<< Insert the motor velocity and acceleration setting commands here
        pass
        
        
    def get_vel_acc_relative(self) -> tuple[float,float,float]:
        """
        Returns the current velocity and acceleration parameters of the motors

        Returns:
            tuple of floats: 3 elements: (vel_homing, vel_move, acc_move)
        """
        # <<<<< Insert the motor velocity and acceleration retrieval commands here
        relvel = float(100)
        pass
        return (relvel,relvel,float(100))
    
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
        if not abs(speed_mm_s/self._max_vel_mmS) < 1:
            speed_mm_s = self._max_vel_mmS
        
        # Calculate the relative speed
        speed_rel = abs(speed_mm_s/self._max_vel_mmS * 100)
        
        return speed_rel
    
    def report_attributes(self) -> None:
        print("\n>>>>> Device and motor attributes <<<<<")
        for attr, value in vars(self).items():
            print(f"{attr}: {value}")
        
    def get_coordinates(self) -> tuple[float,float]:
        """
        Returns the current motor coordinates
        
        Returns:
            tuple of floats: 2 elements: (coor_x, coor_y), in millimetre (float)
        """
        # <<<<< Insert the motor coordinate retrieval commands here
        coor_x = float(0)
        coor_y = float(0)
        pass
        return (coor_x,coor_y)
    
    def homing_n_coor_calibration(self) -> None:
        """
        A function to recalibrate the coordinate system of the device.
        - Also called as 'homing'
        """
        if self.motorx_state != 0 or self.motory_state != 0:
                print("!!!!! Motor is running, homing request BLOCKED !!!!!")
                return
        
        print("\n!!!!! Coordinate calibration/Homing starting !!!!!")
        # Home the device, use multithreading to operate both motors at once
        # <<<<< Insert the homing commands here
        pass
        
        print(">>>>> Coordinate calibration/Homing finished <<<<<")
    
    def move_direct(self,coor_abs:tuple[float,float]) -> None:
        """
        Function to direct the motors to move at the same time towards a certain coordinate.

        Args:
            coor_abs (tuple[float,float]): the absolute coordinate to move to in [mm]
        """
        # <<<<< Insert the motor movement commands here
        pass
        
    def move_continuous(self,dir:str) -> None:
        """
        Moves the motor with a continuous motion until a stop command

        Args:
            dir (str): 'xfwd', 'xrev', 'yfwd', 'yrev' for the direction of the movement
        """
        # Check if the motor is running, prevents command overlap
        if False: # <<<<< Insert the motor running condition check here if required
            print("!!!!! Motor is currently running, movement request BLOCKED !!!!!")
            return
        
        dir = self.dict_ctrl_remap[dir] # Remap the control
        
        if dir == 'xfwd':
            # <<<<< Insert the motor continuous movement commands here
            pass
        elif dir == 'xrev':
            # <<<<< Insert the motor continuous movement commands here
            pass
        elif dir == 'yfwd':
            # <<<<< Insert the motor continuous movement commands here
            pass
        elif dir == 'yrev':
            # <<<<< Insert the motor continuous movement commands here
            pass
            
    def stop_move(self) -> None:
        """
        Stops the continuous movement of the motors
        """
        # <<<<< Insert the motor stop command here
        pass
    
    def get_jog(self) -> tuple[float,float,float,float,float,float]:
        """
        Returns the current jog step in [mm]:
        
        Returns:
            tuple of floats: 6 elements:
            (jog_step_x, jog_step_y, jog_vel_x, jog_vel_y, jog_acc_x, jog_acc_y)
        """
        # <<<<< Insert the jog step retrieval commands here
        jog_step_x = 0.1
        jog_step_y = 0.1
        jog_vel_x = 100
        jog_vel_y = 100
        jog_acc_x = 100
        
        pass
        
        return (jog_step_x, jog_step_y, jog_vel_x, jog_vel_y, jog_acc_x, jog_acc_y)
    
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
        
        if False: # <<<<< Insert the jog step size check here if required
            raise ValueError("Minimum jog step size is {}".format(self._jog_step_min_um))
        
        # <<<<< Insert the jog step setting commands here
        pass
        
    def move_jog(self,direction:str) -> None:
        """
        Moves the motor with a single jogging motion.
        
        Args:
            direction (str): 'xfwd', 'xrev', 'yfwd', 'yrev' for the direction of the jog.
        """
        
        if not isinstance(direction, str):
            raise ValueError("Direction must be a string")
        
        if direction not in ['xfwd','xrev','yfwd','yrev']:
            raise ValueError("Direction must be 'xfwd', 'xrev', 'yfwd', 'yrev'")
        
        if False: # <<<<< Insert the motor running condition check here if required
            print("!!!!! Motor is currently running, movement request BLOCKED !!!!!")
            return
        
        direction = self.dict_ctrl_remap[direction] # Remap the control
        
        if direction == 'xfwd':
            # <<<<< Insert the motor jog movement commands here
            pass
        elif direction == 'xrev':
            # <<<<< Insert the motor jog movement commands here
            pass
        elif direction == 'yfwd':
            # <<<<< Insert the motor jog movement commands here
            pass
        elif direction == 'yrev':
            # <<<<< Insert the motor jog movement commands here
            pass
        
    def terminate(self) -> None:
        """
        Terminates the operation and closes the connection to the device
        """
        try:
            # <<<<< Insert the termination commands here
            pass
            print('xy_stage_controller: Connection closed')
        except Exception as e:
            print('xy_stage_controller: Error in closing the connection:\n{}'.format(e))
        
    def movementtest(self) -> None:
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
            
            
def get_coordinate_test() -> None:
    xystage = Class_XYController()
    print('Coordinate test')
    coor = xystage.get_coordinates()
    print('Current coordinates: {}'.format(coor))
    xystage.terminate()
    print('Termination complete')
    
if __name__ == "__main__":
    # connection_test()
    xystage = Class_XYController()
    xystage.movementtest()
    time.sleep(2)
    
    print('Continuous movement test')
    time.sleep(1)
    xystage.move_continuous(dir='xfwd')
    time.sleep(5)
    xystage.stop_move()
    print('Continuous movement test finished')
    xystage.terminate()
    print('Termination complete')
    get_coordinate_test()