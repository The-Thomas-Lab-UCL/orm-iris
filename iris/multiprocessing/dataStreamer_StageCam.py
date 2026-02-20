"""
A hub that stores the coordinates from the stage controllers.
The hub is a multiprocessing process that runs in the background and is responsible for collecting the coordinates from 
the stage controllers and storing them in a dictionary. The hub also provides a method to retrieve the coordinates based
on the timestamp.

Idea:
- The hub will constantly run in the background, collecting the coordinates from the stage controllers.
- When required, e.g., for the mapping coordinate reference, the hub can be queried for the coordinates based on the timestamp.

Note:
- The timestamp is in [us] integer format. See library/general_functions.py for the timestamp conversion functions.

Usage:
1. Create a central base manager using the MyManager class from the basemanager.py file.
2. Register the classes and the dictionary with the manager using the initialise_manager() function.
3. Register any other classes and dictionary from other hubs/use cases.
4. Start the manager.
5. Create the proxies for the controllers and the dictionary using the initialise_proxy() function.
6. Add any other proxies from other hubs/use cases.
7. Pass the proxies into the hubs/other classes that require them.

!!! Note that the manager.start() has to be called after the all the manager initialisations (register()) and before the proxies are created.

Techinical notes (for myself):
- The controllers passed into the hub have to be proxies from the multiprocessing manager.
- The multithreading has to be run within the hub's run() method.
- The dictionary also has to be a proxy from the multiprocessing manager.
- There can only be 1 manager for the entire program. The manager has to be started before the any other instances is created.
- Note on the order of the initialisation:
1. The manager has to be registered with the classes and the dictionary before the proxies are created and only after the proxy creations can the manager be started.
2. The hub has to be started after the proxies are created.
"""
import os

import multiprocessing as mp
import multiprocessing.managers as mpm
import multiprocessing.connection as mpc

from typing import Any
from enum import Enum

import time
import threading

import numpy as np
import bisect

from PIL import Image
import cv2

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))


from iris.utils.general import convert_timestamp_us_int_to_str, get_timestamp_us_int
from iris.multiprocessing.basemanager import get_my_manager, StageNamespace

from iris.controllers import ControllerConfigEnum
from iris.controllers import Controller_XY, Controller_Z, CameraController
    
from iris.multiprocessing import MPMeaHubEnum

IMAGECAL_KERNELSIZE = 61

class Enum_CamCorrectionType(Enum):
    """
    Enumeration for the type of camera image request
    """
    RAW = 'raw'
    FLATFIELD = 'flatfield'
    BACKGROUND_SUBTRACTION = 'background_subtraction'

class DataStreamer_StageCam(mp.Process):
    def __init__(self, xy_controller: Controller_XY, z_controller: Controller_Z,
                 cam_controller: CameraController, namespace:StageNamespace):
        """
        A hub that manages the storage and retrieval of coordinates from the stage controllers.

        Args:
            xy_controller (XYController): XY stage controller
            z_controller (ZController): Z stage controller
            cam_controller (CameraController): Camera controller
            namespace (StageNamespace): Namespace for the stage hub
        """
        super().__init__()
        self.xy_controller = xy_controller
        self.z_controller = z_controller
        self.cam_controller = cam_controller
        self._namespace = namespace
        self._coor_pipe_main, self._coor_pipe_child = mp.Pipe(duplex=True)
        self._cam_pipe_main, self._cam_pipe_child = mp.Pipe(duplex=True)
        
        # > Operation parameters <
        self._flg_selfrunning = mp.Event()
        
        # > Constants <
        self._pause_interval_sec = MPMeaHubEnum.STAGEHUB_REQUEST_INTERVAL.value / 1000.0  # Convert to seconds
        self._stage_offset_ms = MPMeaHubEnum.STAGEHUB_TIME_OFFSET_MS.value
        
        # > Locks <
        self._lock_pipe = mp.Lock()  # Lock for the pipe
        
    class Enum_CoorType(Enum):
        """
        An enumeration for the type of coordinate retrieval
        """
        CLOSEST = 1
        INTERPOLATE = 2
        
    class _child_CoorProc():
        """
        A coordinate storage and processor for the stage hub, to be run 
        in a separate process.
        """
        def __init__(self,pipe:mpc.Connection):
            """
            Stores and interpolates the coordinates from the stage controllers.

            Args:
                pipe (mpc.Connection): _description_
            """
            self._pipe = pipe   # Pipe for communication with the main process
            
            # > Operation parameters <
            self._list_timestamp = []   # List of timestamps for the child process
            self._list_coordinates = [] # List of coordinates for the child process
            
            # > Locks <
            self._flg_selfrunning = threading.Event()   # Event flag for the child process running
            self._flg_data_added = threading.Event()   # Event flag for data added
            self._lock = mp.Lock()   # Threading lock for the list because it's only going to be accessed by the child process
            
            # > Constants <
            self._max_measurement = MPMeaHubEnum.STAGEHUB_MAXSTORAGE.value # Maximum number of coordinates stored
            
            # > Thread <
            self._thread:threading.Thread = threading.Thread()
            
        def append_coordinate(self,timestamp:int,coordinate:tuple[float,float,float]):
            """
            Add the coordinates to the list
            
            Args:
                timestamp (int): Timestamp in [us]
                coordinate (tuple[float,float,float]): Coordinates (x,y,z)
            """
            with self._lock:
                self._list_timestamp.append(timestamp)
                self._list_coordinates.append(coordinate)
                
                if len(self._list_timestamp) > self._max_measurement:
                    self._list_timestamp.pop(0)
                    self._list_coordinates.pop(0)
            self._flg_data_added.set()

        def get_closest_coordinate(self,timestamp:int) -> tuple[int,tuple[float,float,float]]|None:
            """
            Get the closest coordinate based on the timestamp
            
            Args:
                timestamp (int): Timestamp in [us]
                
            Returns:
                tuple|None: timestamp, coordinate tuple[x,y,z] or None if no coordinates are found
            """
            try:
                if len(self._list_timestamp) == 0:
                    return None
                
                while True:
                    with self._lock: idx = bisect.bisect_left(self._list_timestamp,timestamp)
                    if idx+1 > len(self._list_timestamp):
                        self.wait_coordinate()
                    else: break
                    
                coor = self._list_coordinates[idx]
            except Exception as e:
                print('Error in get_closest_coordinate:',e)
                coor = None
            
            return coor
        
        def wait_coordinate(self,timeout_sec:float|None=None) -> None:
            """
            Waits for a coordinate to be added into the list
            
            Args:
                timeout_sec (float): Timeout in seconds. If None, wait indefinitely
            """
            self._flg_data_added.clear()
            self._flg_data_added.wait(timeout_sec)
            
        def get_interpolated_coordinate(self,timestamp:int) -> tuple[float,float,float]|None:
            """
            Get the interpolated coordinate based on the timestamp
            
            Args:
                timestamp (int): Timestamp in [us]
                
            Returns:
                tuple[int,tuple[float,float,float]]: timestamp, coordinate
            """
            idx = 0
            try:
                while True:
                    with self._lock: idx = bisect.bisect_left(self._list_timestamp,timestamp)
                    if idx >= len(self._list_timestamp)-1:
                        self.wait_coordinate()
                    elif idx == 0: return self._list_timestamp[idx]  # If the requested timestamp is before the first recorded timestamp, return the first recorded coordinate
                    else: break
                    
                with self._lock:
                    idx = bisect.bisect_left(self._list_timestamp,timestamp)
                    ts1,coor1 = self._list_timestamp[idx-1],self._list_coordinates[idx-1]
                    ts2,coor2 = self._list_timestamp[idx],self._list_coordinates[idx]
                    
                # Interpolate the coordinates
                coor1 = np.array(coor1)
                coor2 = np.array(coor2)
                coor = coor1 + (coor2-coor1) * (timestamp-ts1)/(ts2 - ts1)
                coor = tuple(coor)
            except Exception as e:
                print('Error in get_interpolated_coordinate:',e)
                print(f'Requested index: {idx} and {idx+1}')
                print(f'Available indices: {len(self._list_timestamp)} and {len(self._list_coordinates)}')
                coor = None
            
            return coor
        
        def _assign_and_send_coordinates(self):
            """
            Assign the coordinates to the timestamp and send it back to the main process.
            """
            self._flg_selfrunning.set()
            while self._flg_selfrunning.is_set():
                flg_data = self._pipe.poll(timeout=0.5)
                if not flg_data: continue
                
                coor = None
                req_type = None
                timestamp = None
                try:
                    req_type,timestamp = self._pipe.recv()
                    if req_type == DataStreamer_StageCam.Enum_CoorType.CLOSEST:
                        coor = self.get_closest_coordinate(timestamp)
                    elif req_type == DataStreamer_StageCam.Enum_CoorType.INTERPOLATE:
                        coor = self.get_interpolated_coordinate(timestamp)
                    else:
                        raise ValueError('Invalid request type')
                except Exception as e:
                    print(f'Error in child process: {e}')
                    print(f'Received data: {req_type},{timestamp}')
                finally:
                    self._pipe.send(coor)
            self._pipe.close()
        
        def run(self):
            """
            Run the child process
            """
            self._thread = threading.Thread(target=self._assign_and_send_coordinates,daemon=False)
            self._thread.start()
            
        def join(self,timeout:float|None=None):
            self._flg_selfrunning.clear()
            self._thread.join(timeout)
    
    class Enum_CommandType(Enum):
        """
        Enumeration for the type of command
        """
        FLATFIELD_REF = 'flatfield_ref'
        SAVE_FLATFIELD_REF = 'save_flatfield_ref'
        LOAD_FLATFIELD_REF = 'load_flatfield_ref'
        SET_FLATFIELD_GAIN = 'set_flatfield_gain'
        GET_FLATFIELD_GAIN = 'get_flatfield_gain'
        
    class _child_CamProc():
        """
        Child process to acquire the camera images, correct them, and send them to the main process
        """
        def __init__(self,pipe:mpc.Connection, cam_controller:CameraController):
            """
            Initialise the child process.
            
            Args:
                pipe (mpc.Connection): Pipe for communication with the main process
                cam_controller (CameraController): Camera controller
                
            Usage:
                Whenever a request is received (Any type), the child process will acquire the image, correct it, and send it back to the main process.
                If an image of the same dimension is received, the child process will take it as a correction image.
            """
            self._pipe = pipe
            self._cam_controller = cam_controller
            
            # > Image processing parameters <
            self._ff_arr_correction:np.ndarray|None = None
            self._ff_gain:float = 1.0  # Gain for flatfield correction
            
            # > Operation parameters <
            self._flg_selfrunning = threading.Event()
            
            # > Thread <
            self._thread:threading.Thread = threading.Thread()
            
        def _calculate_reference_flatfield(self,reference:np.ndarray) -> None:
            """
            Calculates the reference normalisation array for flatfield correction

            Args:
                ref_img (np.ndarray): _description_
            """
            num_channels = reference.shape[2]
            reference_float = reference.astype(np.float32)
            
            # Turn into a grayscale image
            reference_float = np.mean(reference_float,axis=2)
            
            # Normalize the reference image (important!)
            self._ff_arr_correction = reference_float / np.mean(reference_float)  # Or another suitable normalization
            
            assert self._ff_arr_correction is not None, "Reference image has not been set."
            # Normalize the reference image to (1,inf)
            self._ff_arr_correction = self._ff_arr_correction / np.min(self._ff_arr_correction + 1e-7)  # Prevent division by zero
            
            # Expand the image back to the original number of channels
            self._ff_arr_correction = np.stack([self._ff_arr_correction]*num_channels,axis=2)
            
        def _correct_arr_flatfield(self,img:np.ndarray) -> np.ndarray:
            """
            Corrects the image using the flatfield correction

            Args:
                img (np.ndarray): Image to be corrected

            Returns:
                np.ndarray: Corrected image
            """
            try:
                assert isinstance(self._ff_arr_correction,np.ndarray), "Reference image has not been set."
                assert img.shape == self._ff_arr_correction.shape, "Image and reference image must have the same dimensions."
            except AssertionError as e:
                print(f'Error in _correct_image_flatfield: {e}')
                return img
            
            # Convert to float for division
            img_float = img.astype(np.float32)
            
            # Correct the image
            corrected_img = img_float / (self._ff_arr_correction + 1e-7)  # Prevent division by zero
            
            # Apply the gain
            corrected_img = corrected_img * self._ff_gain
            
            # Scale and convert back to uint8
            corrected_img = np.clip(corrected_img, 0, 255).astype(np.uint8)
            
            return corrected_img
            
        def _correct_backgroundSubtraction_1channel(self, img:np.ndarray):  # Adjust kernel_size
            """Corrects uneven lighting using background subtraction."""
            kernel_size = IMAGECAL_KERNELSIZE
            
            # 1. Estimate the background illumination:
            #    - Gaussian blur is often used for this.  Adjust kernel_size as needed.
            background = cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)

            # 2. Divide the original image by the background (normalization):
            #    - Convert to float for division
            img_float = img.astype(np.float32)
            background_float = background.astype(np.float32)
            
            # Normalize the background image to (1,inf)
            background_float = background_float / np.min(background_float)

            # Avoid division by zero: Add a small epsilon
            epsilon = 1e-7  # Or a slightly larger value if needed
            corrected_img = img_float / (background_float + epsilon)

            # 3. Scale back to the original range (0-255) and convert to uint8
            corrected_img = np.clip(corrected_img, 0, 255).astype(np.uint8)

            return corrected_img
            
        def _correct_backgroundSubtraction_3channel(self,img:np.ndarray) -> np.ndarray:
            """Corrects uneven lighting in a color image using background subtraction."""
            # Split the image into color channels
            b, g, r = cv2.split(img)

            # Apply background subtraction to each channel
            corrected_b = self._correct_backgroundSubtraction_1channel(b)
            corrected_g = self._correct_backgroundSubtraction_1channel(g)
            corrected_r = self._correct_backgroundSubtraction_1channel(r)
            
            # Merge the corrected channels back into a color image
            corrected_img = cv2.merge((corrected_b, corrected_g, corrected_r))

            return corrected_img
            
        def _convert_arr2img(self,arr:np.ndarray) -> Image.Image:
            """
            Convert the numpy array to an image
            
            Args:
                arr (np.ndarray): Numpy array
            
            Returns:
                Image.Image: Image
            """
            img = Image.fromarray(arr)
            return img
            
        def run(self):
            """
            Run the child process
            """
            self._thread = threading.Thread(target=self._handle_image_requests,daemon=False)
            self._thread.start()
            
        def _handle_image_requests(self):
            """
            Collect the image from the camera controller and puts it back into the pipe
            based on the user request.
            """
            self._flg_selfrunning.set()
            return_pkg = None # Placeholder for the processed image
            request = None
            proc_img = None
            while self._flg_selfrunning.is_set():
                flg_data = self._pipe.poll(timeout=0.5)
                if not flg_data: continue
                try:
                    request = self._pipe.recv()
                    img = self._cam_controller.img_capture()
                    arr_img = np.array(img)
                    
                    if request == Enum_CamCorrectionType.RAW:
                        proc_img = arr_img
                    elif request == Enum_CamCorrectionType.FLATFIELD:
                        proc_img = self._correct_arr_flatfield(arr_img)
                    elif request == Enum_CamCorrectionType.BACKGROUND_SUBTRACTION:
                        proc_img = self._correct_backgroundSubtraction_3channel(arr_img)
                    else:
                        return_pkg = self._handle_other_requests(request)
                        
                    if request in Enum_CamCorrectionType.__members__.values():
                        if proc_img is None: raise ValueError('Processed image is None')
                        return_pkg = self._convert_arr2img(proc_img)
                        
                except Exception as e:
                    print(f'Error in child process: {e}')
                    print(f'Received data: {request}')
                finally:
                    self._pipe.send(return_pkg)
            self._pipe.close()
            
        def _handle_other_requests(self,request:tuple[Any]) -> Any:
            """
            Handle other commands from the main process
            
            Args:
                request (tuple): Request tuple
                
            Returns:
                Any: Return package depending on the request, otherwise None
                
            Raises:
                ValueError: If the request is invalid
            """
            if not isinstance(request,tuple): raise ValueError('Invalid request type, not a tuple')
            if len(request) != 2: raise ValueError('Invalid request type, not enough arguments')
            
            return_pkg = None
            if request[0] == DataStreamer_StageCam.Enum_CommandType.SET_FLATFIELD_GAIN:
                if not isinstance(request[1],float): raise ValueError('Invalid request type, gain is not a float')
                self._ff_gain = request[1]
            
            elif request[0] == DataStreamer_StageCam.Enum_CommandType.GET_FLATFIELD_GAIN:
                return_pkg = self._ff_gain
            
            elif request[0] == DataStreamer_StageCam.Enum_CommandType.FLATFIELD_REF:
                if not isinstance(request[1],np.ndarray): raise ValueError('Invalid request type, reference image is not a numpy array')
                self._calculate_reference_flatfield(request[1])
            
            elif request[0] == DataStreamer_StageCam.Enum_CommandType.SAVE_FLATFIELD_REF:
                if not isinstance(request[1],str): raise ValueError('Invalid request type, reference image is not a string')
                if self._ff_arr_correction is None: raise ValueError('Reference image has not been set.')
                
                # Dump the reference image to a file
                np.save(request[1],self._ff_arr_correction)
                
            elif request[0] == DataStreamer_StageCam.Enum_CommandType.LOAD_FLATFIELD_REF:
                if not isinstance(request[1],str): raise ValueError('Invalid request type, reference image is not a string')
                if not os.path.exists(request[1]): raise ValueError('File does not exist')
                
                # Load the reference image from a file
                self._ff_arr_correction = np.load(request[1])
                
            else:
                raise ValueError('Invalid request type, not in Enum_CommandType')
            
            return return_pkg
                
            
        def join(self,timeout:float|None=None):
            self._flg_selfrunning.clear()
            self._thread.join(timeout)
    
    def save_flatfield_reference(self,filename:str) -> None:
        """
        Save the reference image for flatfield correction
        
        Args:
            filename (str): Filename to save the reference image
        """
        assert isinstance(filename,str), 'Filename is not a string'
        with self._lock_pipe:
            self._cam_pipe_main.send((self.Enum_CommandType.SAVE_FLATFIELD_REF,filename))
            self._cam_pipe_main.recv()
        
    def load_flatfield_reference(self,filename:str) -> None:
        """
        Load the reference image for flatfield correction
        
        Args:
            filename (str): Filename to load the reference image
        """
        assert isinstance(filename,str), 'Filename is not a string'
        with self._lock_pipe:
            self._cam_pipe_main.send((self.Enum_CommandType.LOAD_FLATFIELD_REF,filename))
            self._cam_pipe_main.recv()
    
    def set_flatfield_reference(self,ref_img:np.ndarray) -> None:
        """
        Set the reference image for flatfield correction
        
        Args:
            ref_img (np.ndarray): Reference image
        """
        assert isinstance(ref_img,np.ndarray), 'Reference image is not a numpy array'
        with self._lock_pipe:
            self._cam_pipe_main.send((self.Enum_CommandType.FLATFIELD_REF,ref_img))
            self._cam_pipe_main.recv()
            
    def get_flatfield_gain(self) -> float:
        """
        Get the flatfield gain
        
        Returns:
            float: Flatfield gain
        """
        with self._lock_pipe:
            self._cam_pipe_main.send((self.Enum_CommandType.GET_FLATFIELD_GAIN,0))
            gain = self._cam_pipe_main.recv()
        return gain
    
    def set_flatfield_gain(self,gain:float) -> None:
        """
        Set the flatfield gain
        
        Args:
            gain (float): Flatfield gain
        """
        assert isinstance(gain,float), 'Gain is not a float'
        with self._lock_pipe:
            self._cam_pipe_main.send((self.Enum_CommandType.SET_FLATFIELD_GAIN,gain))
            self._cam_pipe_main.recv()
    
    def get_image(self, request:Enum_CamCorrectionType) -> Image.Image:
        """
        Get the image from the camera controller
        
        Args:
            request (Enum_CamType): Request type
        
        Returns:
            np.ndarray: Image
        """
        assert isinstance(request,Enum_CamCorrectionType), 'Invalid request type'
        with self._lock_pipe:
            self._cam_pipe_main.send(request)
            img = self._cam_pipe_main.recv()
        return img
    
    def get_camera_controller(self) -> CameraController:
        """
        Return the camera controller
        """
        return self.cam_controller
    
    def get_measurement_offset_ms(self) -> float:
        """
        Return the measurement offset in ms
        """
        return self._namespace.stage_offset_ms
    
    def set_measurement_offset_ms(self,offset_ms:float) -> None:
        """
        Set the measurement offset in ms
        
        Args:
            offset_ms (float): Offset in ms
        """
        self._namespace.stage_offset_ms = offset_ms
    
    def run(self):
        print('>>>>>> Stage hub is running <<<<<<')
        self._collect_coordinateAndImage()
        

    def _collect_coordinateAndImage(self):
        self._flg_selfrunning.set()
        child_proc_coor = self._child_CoorProc(self._coor_pipe_child)
        child_proc_coor.run()
        child_proc_cam = self._child_CamProc(self._cam_pipe_child,self.cam_controller)
        child_proc_cam.run()
        while self._flg_selfrunning.is_set():
            try:
                timestamp = int(get_timestamp_us_int() + self._namespace.stage_offset_ms * 1e3)
                coorx, coory = self.xy_controller.get_coordinates()
                coorz = self.z_controller.get_coordinates()
                coor = (coorx, coory, coorz)
                
                child_proc_coor.append_coordinate(timestamp,coor)
                
                time.sleep(self._pause_interval_sec)
            except Exception as e:
                print('Error in stage hub:',e)
                time.sleep(0.5)
        child_proc_coor.join()
        child_proc_cam.join()

    def join(self, timeout: float | None = None) -> None:
        self._flg_selfrunning.clear()
        super().join(timeout)
        
    def get_coordinates_interpolate(self,timestamp:int) -> tuple[float,float,float]|None:
        """
        Get the coordinates by interpolating the coordinates between the timestamps (linear)
        
        Args:
            timestamp (int): Timestamp in us
        
        Returns:
            tuple|None: Coordinates in [x,y,z] or None if no coordinates are found
        """
        with self._lock_pipe:
            self._coor_pipe_main.send((self.Enum_CoorType.INTERPOLATE,timestamp))
            coor = self._coor_pipe_main.recv()
        return coor
    
    def get_coordinates_closest(self,timestamp:int) -> tuple[float,float,float]|None:
        """
        Get the closest coordinates to the timestamp
        
        Args:
            timestamp (int): Timestamp in us
        
        Returns:
            tuple: Coordinates in [x,y,z] or None if no coordinates are found
        """
        with self._lock_pipe:
            self._coor_pipe_main.send((self.Enum_CoorType.CLOSEST,timestamp))
            coor = self._coor_pipe_main.recv()
        return coor
        
def initialise_manager_stage(manager:mpm.SyncManager):
    """
    Register the classes and the dictionary with the manager
    
    Args:
        manager (MyManager): The central base manager
    """
    manager.register('xyctrl',callable=Controller_XY)
    manager.register('zctrl',callable=Controller_Z)
    manager.register('camctrl',callable=CameraController)

def initialise_proxy_stage(manager:mpm.SyncManager) -> tuple[Controller_XY,Controller_Z,CameraController,StageNamespace]:
    """
    Initialise the proxies for the stage controllers and the dictionary
    
    Args:
        manager (MyManager): Manager instance
    
    Returns:
        tuple: xyproxy, zproxy, camproxy, namespace
    """
    # Initialise all the controllers
    zproxy:Controller_Z = manager.zctrl(sim=ControllerConfigEnum.SIMULATION_MODE.value)
    xyproxy:Controller_XY = manager.xyctrl(sim=ControllerConfigEnum.SIMULATION_MODE.value)
    camproxy:CameraController = manager.camctrl()
    
    stg_namespace:StageNamespace = manager.Namespace()
    stg_namespace.stage_offset_ms = MPMeaHubEnum.STAGEHUB_TIME_OFFSET_MS.value
    
    return xyproxy,zproxy,camproxy,stg_namespace

def test_basic():
    manager_base:mpm.SyncManager = get_my_manager()
    initialise_manager_stage(manager_base)
    manager_base.start()
    xyproxy,zproxy,camproxy,stage_namespace = initialise_proxy_stage(manager_base)
    
    hub = DataStreamer_StageCam(
        xy_controller=xyproxy,
        z_controller=zproxy,
        cam_controller=camproxy,
        namespace=stage_namespace
    )
    hub.start()
    
    threading.Thread(target=xyproxy.movementtest).start()
    
    while True:
        try:
            ts_req = get_timestamp_us_int()
            coor = hub.get_coordinates_interpolate(ts_req)
            ts_req = convert_timestamp_us_int_to_str(ts_req)
            print('Timestamp request {}, Coordinates: {}'.format(ts_req,coor))
        finally:
            time.sleep(0.05)
    
def generate_dummy_stageHub() -> tuple[DataStreamer_StageCam,Controller_XY,Controller_Z,CameraController,StageNamespace]:
    """
    Get a dummy stage hub for testing purposes.
    
    Returns:
        tuple: stage hub, xy controller, z controller, camera controller, namespace
    """
    manager_base:mpm.SyncManager = get_my_manager()
    initialise_manager_stage(manager_base)
    manager_base.start()
    xyproxy,zproxy,camproxy,stage_namespace = initialise_proxy_stage(manager_base)
    
    stagehub = DataStreamer_StageCam(
        xy_controller=xyproxy,
        z_controller=zproxy,
        cam_controller=camproxy,
        namespace=stage_namespace
    )
    
    return stagehub, xyproxy, zproxy, camproxy, stage_namespace
    
    
if __name__ == '__main__':
    test_basic()
    
    # p1 = proc1()
    # p1.start()
    # threading.Thread(target=p1.main_watch).start()
    # time.sleep(4)
    # p1.join()
    