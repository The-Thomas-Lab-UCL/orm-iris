"""
This is a Python script that handles the control of the Physik Instrumente (PI)
U-751.24 XY stage controller. To be used with the Open Raman Microscopy (ORM) controller
app.
"""
import os
import sys

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\library')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

# from pipython import GCSDevice
from pipython import GCSDevice
from pipython import GCS30Device
from pipython import GCS30Commands
from pipython import pitools

from library.general_functions import *
from library.controllers.class_xy_stage_controller import Class_XYController
from library.controllers import ControllerSpecificConfigEnum

import numpy as np
import time

from library.controllers import ControllerConfigEnum,ControllerDirectionEnum

def test():
    with GCSDevice() as pidevice:
        # for typehinting
        pidevice:GCS30Device

    # >> Test connection <<
        pidevice.ConnectUSB(serialnum=ControllerSpecificConfigEnum.PISTAGE_SERIAL.value)
        print('connected: {}'.format(pidevice.qIDN().strip()))

    # >> Test axes names <<
        axis1 = pidevice.axes[0]
        axis2 = pidevice.axes[1]
        allaxes = pidevice.allaxes
        print(pitools.getmintravelrange(pidevice, pidevice.axes[:2]))
        print(pitools.getmaxtravelrange(pidevice, pidevice.axes[:2]))

        # Get max velocity
        print('Max velocity: {}'.format(pidevice.qVEL()))
        print('Current velocity: {} and {}'.format(pidevice.qVEL(axis1), pidevice.qVEL(axis2)))

    # >> Test moving with varying velocity <<
        @thread_assign
        def report_position(flg_stop:threading.Event):
            while not flg_stop.is_set():
                print('Position: {}'.format(pidevice.qPOS(allaxes)))
                time.sleep(0.5)

        # flag setup for position report
        flg_stop = threading.Event()

        # Set velocity and 1st target
        pidevice.VEL('1', 10)
        pidevice.MOV('1', 0)
        pidevice.MOV('2', 0)
        # report_position(flg_stop)
        pitools.waitontarget(pidevice, axis1)
        flg_stop.set()

        # Set velocity and 2nd target
        pidevice.VEL('1', 3)
        pidevice.MOV('1', 25)
        pidevice.MOV('2', 25)

        # Check if axis is moving and how the controller behaves
        flg_stop = threading.Event()
        ordered_dict = pidevice.IsMoving(axis1)
        movingstate = ordered_dict[axis1]
        print('Axis {} is moving: {}'.format(axis1, movingstate))

        # Wait until target is reached
        # report_position(flg_stop)
        pitools.waitontarget(pidevice, axis1)
        flg_stop.set()
        print(pidevice.IsMoving(axis1))
        print(pidevice.qPOS('1'))
        

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
        self.device:GCS30Device = GCSDevice()
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
        
        self._flipxy = ControllerConfigEnum.STAGE_FLIPXY            # Flag to indicate if the x and y axes are flipped
        self._invertx = ControllerConfigEnum.STAGE_INVERTX.value    # Flag to indicate if the x-axis is flipped (inversed, *= -1)
        self._inverty = ControllerConfigEnum.STAGE_INVERTY.value    # Flag to indicate if the y-axis is flipped (inversed, *= -1)
        
        self._dict_axes = { # Placeholder for the axes names
            'x':None,
            'y':None
        }

        # Movement parameters setup
        self._max_vel:float = 100.0  # Maximum velocity of the motor in mm/s
        self._min_vel:float = 0.001   # Minimum velocity of the motor in mm/s
        self._vel:float = None

        self._min_travelx:float = None
        self._min_travely:float = None
        self._max_travelx:float = None
        self._max_travely:float = None

        self._jog_min_mm:float = 0.001
        self._jog_max_mm:float = 1.0
        self._jog_mm:float = 1
        
        self._max_vel_mmS = self._max_vel   # Maximum velocity of the motor in mm/s
        self._min_vel_mmS = self._min_vel   # Minimum velocity of the motor in mm/s
        
        # Initialises the device
        try: self.initialisation()
        except Exception as e: print(e)
        
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
        self.device.ConnectUSB(serialnum=self._serial_no)
        print('connected: {}'.format(self.device.qIDN().strip()))

        # Get axes names
        ## NOTE: Flip the axes indices if the stage is mounted in a different orientation
        ## make sure that the x-axis is the horizontal axis in the image capture and y-axis for
        self._allaxes = self.device.allaxes
        self._dict_axes = {
            'x':self.device.axes[1],
            'y':self.device.axes[0]
        }

        # Enable the servos
        self.device.SVO(self._allaxes, [1]*2)

        # Home the axes
        self.homing_n_coor_calibration()

        # Get max travel range
        minrange = pitools.getmintravelrange(self.device, self.device.allaxes)
        maxrange = pitools.getmaxtravelrange(self.device, self.device.allaxes)
        self._min_travelx, self._min_travely = minrange[self._dict_axes['x']], minrange[self._dict_axes['y']]
        self._max_travelx, self._max_travely = maxrange[self._dict_axes['x']], maxrange[self._dict_axes['y']]

        # Get max velocity
        self._max_vel:float = 10.0
        self._min_vel:float = 0.1
        
        # Set velocity and acceleration
        self.get_vel_acc_relative()

    def terminate(self,close_connection=True):
        """
        Terminate the operation. Returns the stage to home and disconnects the device.
        
        Args:
                close_connection (bool): True to close the connection to the device
        """
        if close_connection: self.device.CloseConnection()
        
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
        vel = self._max_vel * vel_move / 100
        self.device.VEL(self._allaxes, [vel]*2)

        self._vel = vel

    def get_vel_acc_relative(self):
        """
        Returns the current velocity and acceleration parameters of the motors

        Returns:
            tuple of floats: 3 elements: (vel_homing, vel_move, acc_move)
        """
        dict_relvel = self.device.qVEL(self._allaxes)
        relvel1 = dict_relvel[self._dict_axes['x']] / self._max_vel * 100
        relvel2 = dict_relvel[self._dict_axes['y']] / self._max_vel * 100

        if relvel1 != relvel2: print('Axes have different velocities'); self._vel = relvel1

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
        positions = self.device.qPOS(self.device.allaxes)
        x,y = positions[self._dict_axes['x']], positions[self._dict_axes['y']]
        
        x,y = self._remap_coordinates_flip((x,y),get=True)
        
        return (x, y)
    
    def homing_n_coor_calibration(self):
        """
        A function to recalibrate the coordinate system of the device.
        - Also called as 'homing'
        """

        # Set velocity
        self.set_vel_acc_relative(vel_homing=100, vel_move=100, acc_move=100)

        # Move to home position
        self.device.FRF(self._allaxes)
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
        if remap: coor_abs = self._remap_coordinates_flip(coor_abs,get=False)
        
        assert self._min_travelx <= coor_abs[0] <= self._max_travelx, 'Coordinate x is out of range'
        assert self._min_travely <= coor_abs[1] <= self._max_travely, 'Coordinate y is out of range'
        
        self.device.MOV([self._dict_axes['x'],self._dict_axes['y']], coor_abs)

        # Wait until target is reached
        pitools.waitontarget(self.device, self._allaxes)

        return
    
    def move_continuous(self,dir:str):
        """
        Moves the motor with a continuous motion until a stop command
        
        Args:
            dir (str): 'xfwd', 'xrev', 'yfwd', 'yrev' for the direction of the movement
        """
        assert dir in ['xfwd','xrev','yfwd','yrev'], 'Invalid direction'

        dir = self.dict_ctrl_remap[dir]

        if dir == 'xfwd': self.device.MOV(self._dict_axes['x'], self._max_travelx)
        elif dir == 'xrev': self.device.MOV(self._dict_axes['x'], self._min_travelx)
        elif dir == 'yfwd': self.device.MOV(self._dict_axes['y'], self._max_travely)
        elif dir == 'yrev': self.device.MOV(self._dict_axes['y'], self._min_travely)

    def stop_move(self):
        """
        Stops the continuous movement of the motors by sending a new
        target position to the current position
        """
        coor = self.get_coordinates()
        coor = self._remap_coordinates_flip(coor,get=True)
        self.device.MOV([self._dict_axes['x'],self._dict_axes['y']], coor)
        pitools.waitontarget(self.device, self._allaxes)
        return

    def get_jog(self):
        """
        Returns the current jog step in [mm]:
        
        Returns:
            tuple of floats: 6 elements:
            (jog_step_x, jog_step_y, jog_vel_x, jog_vel_y, jog_acc_x, jog_acc_y)
        """
        return (self._jog_mm, self._jog_mm, self._vel, self._vel, 0, 0)
    
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

        coor = self.get_coordinates()
        coor = self._remap_coordinates_flip(coor,get=False)
        if direction == 'xfwd': coor = (coor[0]+self._jog_mm, coor[1])
        elif direction == 'xrev': coor = (coor[0]-self._jog_mm, coor[1])
        elif direction == 'yfwd': coor = (coor[0], coor[1]+self._jog_mm)
        elif direction == 'yrev': coor = (coor[0], coor[1]-self._jog_mm)
        self.move_direct(coor,remap=False)
        pitools.waitontarget(self.device,self._allaxes)

        return
    
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
    print('Move x reverse')
    xystage.move_continuous('xrev')
    time.sleep(2)
    print('Move y reverse')
    xystage.move_continuous('yfwd')
    time.sleep(2)
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

if __name__ == "__main__":
    # get_coordinate_test()
    # test_movedirect()
    # test_movecontinuous()
    test_movejog()
    # test()

    # xystage = xy_stage_controller()
    # xy_stage_controller.set_vel_acc_relative(xystage,vel_homing=100, vel_move=100, acc_move=100)
    # xystage.movementtest()
    # xystage.termination()