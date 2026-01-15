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

from iris.controllers.class_xy_stage_controller import Class_XYController

import numpy as np
import threading
import time

from iris.controllers import ControllerConfigEnum

class XYController_Dummy(Class_XYController):
    def __init__(self,**kwargs) -> None:
        # Remapping of the controls
        self._coor_x_mm = float(0)
        self._coor_y_mm = float(0)
        
        self._invertx = 1 if not ControllerConfigEnum.STAGE_INVERTX.value else -1
        self._inverty = 1 if not ControllerConfigEnum.STAGE_INVERTY.value else -1
        
        self._max_vel_mmS = 100.0    # Maximum velocity of the motor in mm/s
        self._min_vel_mmS = 0.1      # Minimum velocity of the motor in mm/s
        
        self._jog_step_min_um = 1 # Minimum jog step size in [um]
        
        self._vel = 100
        self._step_um = 1               # distance traveled per step in [um], i.e., the step size
        self._step_wait_time_sec = 1e-6 # waiting time between steps in [s]
        
        self._jog_step_mm = 0.1            # jog step size in [mm]
        
        self._thread_movecontinuous:threading.Thread|None = None
        self._flg_movecontinuous = threading.Event()
        
        print('\n>>>>> DUMMY XY controller is used <<<<<')
        
    def get_identifier(self) -> str:
        return "Dummy XY Stage Controller"
        
    def initialisation(self):
        """
        Initialises the device, setup the connection, channels, motors and their parameters, etc.
        
        Args:
            commport (str): the communication port for the device
        """
        pass
    
    def set_vel_acc_relative(self,vel_homing:float=100, vel_move:float=100, acc_move:float=100):
        """
        Set the velocity and acceleration parameters of the motors for both homing and typical movements.
        
        Args:
            vel_homing (int, optional): Legacy parameter. Is ignored.
            vel_move (int, optional): New motor movement velocity in percentage of max velocity. Defaults to 100.
            acc_move (int, optional): Legacy parameter. Is ignored.
        """
        if vel_move <= 0:
            raise ValueError("Velocity and acceleration parameters must be larger than 0%")
        if vel_move > 100:
            raise ValueError("Velocity and acceleration parameters must be less than 100%")
        
        self._vel = vel_move
        
    def get_vel_acc_relative(self):
        """
        Returns the current velocity and acceleration parameters of the motors

        Returns:
            tuple of floats: 3 elements: (vel_homing, vel_move, acc_move)
        """
        return (100, self._vel, 100)
    
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
        return (self._coor_x_mm*self._invertx, self._coor_y_mm*self._inverty)

    def homing_n_coor_calibration(self):
        """
        A function to recalibrate the coordinate system of the device.
        - Also called as 'homing'
        """
        print("\n!!!!! Coordinate calibration/Homing starting !!!!!")
        # Home the device, use multithreading to operate both motors at once
        self._coor_x_mm = float(0)
        self._coor_y_mm = float(0)
        print(">>>>> Coordinate calibration/Homing finished <<<<<")
    
    def move_direct(self,coor_abs:tuple[float,float]):
        """
        Function to direct the motors to move at the same time towards a certain coordinate.

        Args:
            coor_abs (tuple[float,float]): the absolute coordinate to move to in [mm]
        """
        coor_abs = (coor_abs[0]*self._invertx, coor_abs[1]*self._inverty)
        count_x = int((coor_abs[0]-self._coor_x_mm*self._invertx)/self._step_um*1000)
        count_y = int((coor_abs[1]-self._coor_y_mm*self._inverty)/self._step_um*1000)
        
        target_x_mm = self._coor_x_mm + count_x*self._step_um/1000
        target_y_mm = self._coor_y_mm + count_y*self._step_um/1000
        
        while True:
            if self._coor_x_mm < target_x_mm:
                self._coor_x_mm += self._step_um/1000
            elif self._coor_x_mm > target_x_mm:
                self._coor_x_mm -= self._step_um/1000
            if self._coor_y_mm < target_y_mm:
                self._coor_y_mm += self._step_um/1000
            elif self._coor_y_mm > target_y_mm:
                self._coor_y_mm -= self._step_um/1000
            
            time.sleep(self._step_wait_time_sec/(self._vel/100))
            
            error = np.sqrt((self._coor_x_mm-target_x_mm)**2 + (self._coor_y_mm-target_y_mm)**2)
            # print(coor_abs,(self._coor_x_mm,self._coor_y_mm),(target_x_mm,target_y_mm),error)
            if error < 0.001:
                break
            
        return
        
    def move_continuous(self,dir:str):
        """
        Moves the motor with a continuous motion until a stop command

        Args:
            dir (str): 'xfwd', 'xrev', 'yfwd', 'yrev' for the direction of the movement
        """
        def move_continuous_thread(self:XYController_Dummy,dir):
            self._flg_movecontinuous.set()
            while self._flg_movecontinuous.is_set():
                if dir == 'xfwd':
                    self._coor_x_mm += self._step_um/1000
                elif dir == 'xrev':
                    self._coor_x_mm -= self._step_um/1000
                elif dir == 'yfwd':
                    self._coor_y_mm += self._step_um/1000
                elif dir == 'yrev':
                    self._coor_y_mm -= self._step_um/1000
                time.sleep(self._step_wait_time_sec/(self._vel/100))
        
        self._thread_movecontinuous = threading.Thread(target=move_continuous_thread,args=(self,dir))
        self._thread_movecontinuous.start()
            
    def stop_move(self):
        """
        Stops the continuous movement of the motors
        """
        if isinstance(self._thread_movecontinuous, threading.Thread):
            if self._thread_movecontinuous.is_alive():
                self._flg_movecontinuous.clear()
                self._thread_movecontinuous.join(timeout=1)
                self._thread_movecontinuous = None
                print(">>>>> Continuous movement stopped <<<<<")
            else:
                self._thread_movecontinuous = None
    
    def get_jog(self):
        """
        Returns the current jog step in [mm]:
        
        Returns:
            tuple of floats: 6 elements:
            (jog_step_x, jog_step_y, jog_vel_x, jog_vel_y, jog_acc_x, jog_acc_y)
        """
        jog_step_x = self._jog_step_mm
        jog_step_y = self._jog_step_mm
        jog_vel_x = float(100)
        jog_vel_y = float(100)
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
        
        if dist_mm*1e3 < self._jog_step_min_um:
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
        
        
        while True:
            if direction == 'xfwd':
                self._coor_x_mm += self._jog_step_mm * self._invertx
            elif direction == 'xrev':
                self._coor_x_mm -= self._jog_step_mm * self._invertx
            elif direction == 'yfwd':
                self._coor_y_mm += self._jog_step_mm * self._inverty
            elif direction == 'yrev':
                self._coor_y_mm -= self._jog_step_mm * self._inverty
            
            time.sleep(self._step_wait_time_sec/(self._vel/100))
            
            break
        
    def terminate(self):
        """
        Terminates the operation and closes the connection to the device
        """
        print("\n>>>>> DUMMY XY controller terminated <<<<<")
        pass
        
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
    xystage = XYController_Dummy(sim=True)
    print('Coordinate test')
    coor = xystage.get_coordinates()
    print('Current coordinates: {}'.format(coor))
    xystage.terminate()
    print('Termination complete')
    
if __name__ == "__main__":
    xystage = XYController_Dummy(sim=False)
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