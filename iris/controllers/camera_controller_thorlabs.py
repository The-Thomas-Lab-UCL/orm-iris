"""
A controller to take in a video feed and display
"""
import numpy as np
import cv2
import time
from PIL import Image

import os
from multiprocessing import Lock

from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, TLCamera
from thorlabs_tsi_sdk.tl_camera_enums import SENSOR_TYPE
from thorlabs_tsi_sdk.tl_mono_to_color_processor import MonoToColorProcessorSDK as TL_MTC
from thorlabs_tsi_sdk.tl_mono_to_color_processor import MonoToColorProcessor
from thorlabs_tsi_sdk.tl_mono_to_color_enums import COLOR_SPACE as TL_ClrSpc
from thorlabs_tsi_sdk.tl_color_enums import FORMAT as TL_Fmt

if __name__ == '__main__':
    import sys
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))


from iris.controllers.class_camera_controller import Class_CameraController

from iris.controllers import ControllerConfigEnum, ControllerSpecificConfigEnum

absolute_path_to_dlls = ControllerSpecificConfigEnum.THORLABS_CAMERA_DLL_PATH.value
os.environ['PATH'] = absolute_path_to_dlls + os.pathsep + os.environ['PATH']
os.add_dll_directory(absolute_path_to_dlls)


class CameraController_Thorlabs(Class_CameraController):
    """
    Universal Thorlabs camera controller â€” auto-detects colour or monochrome sensor at initialisation.
    Supports CS/CS2 (monochrome) and CS505/CS165 (colour Bayer) families.
    """
    def __init__(self, show: bool = False) -> None:
        self.controller: TLCameraSDK | None = None

        self._lock = Lock()

        self.camera_index = 0           # Takes the 1st capture device as the source
                                        # it is possible that the desired device is NOT the 1st one
                                        # in this case, a different index should be chosen by trial and error
                                        # index = 0,1,2,3,... etc.

        self.camera: TLCamera | None = None

        self._is_color: bool = False     # set during _initialisation()

        # Colour pipeline (colour cameras only)
        self._colour_processor: TL_MTC | None = None
        self._clrprc_monoToColour: MonoToColorProcessor | None = None

        
        # > Basic parameters initialisation. Actual values will be set during camera initialisation <
        # Mono pipeline (mono cameras only)
        self._bit_shift: int = 0

        self._frame_width: int = 2
        self._frame_height: int = 2

        self._flg_show_preview = show
        self.win_name = 'preview'

        self._mirrorx: bool = False
        self._mirrory: bool = False

        self.flg_initialised = False
        self._identifier: str = "unidentified Thorlabs camera"

        try: self._initialisation()
        except Exception as e: print('CameraController_Thorlabs initialisation error:\n{}'.format(e))

    def get_identifier(self) -> str:
        if not self._identifier and isinstance(self.camera, TLCamera):
            camera_type = 'colour' if self._is_color else 'monochrome'
            self._identifier = f"Thorlabs_{self.camera.model} ({camera_type}), S/N:{self.camera.serial_number}"
        return self._identifier

    def reinitialise_connection(self) -> None:
        """Reinitialise the camera connection, preserving the current exposure time."""
        exposure_time_us = None
        try: exposure_time_us = self.get_exposure_time_us()
        except Exception: pass

        try: self.camera_termination()
        except Exception as e: print('CameraController_Thorlabs reinitialise_connection error:\n{}'.format(e))

        try: self._initialisation()
        except Exception as e: print('CameraController_Thorlabs reinitialise_connection error:\n{}'.format(e))

        if exposure_time_us is not None:
            try: self.set_exposure_time_us(exposure_time_us)
            except Exception as e: print('CameraController_Thorlabs reinitialise_connection exposure restore error:\n{}'.format(e))

    def _initialisation(self) -> None:
        self._lock.acquire()
        try:
            self.controller = TLCameraSDK()

            available_cameras = self.controller.discover_available_cameras()
            if len(available_cameras) < 1:
                raise RuntimeError('No Thorlabs cameras detected')

            self.camera = self.controller.open_camera(available_cameras[self.camera_index])
            self.camera.exposure_time_us = ControllerSpecificConfigEnum.THORLABS_CAMERA_EXPOSURE_TIME.value
            self.camera.frames_per_trigger_zero_for_unlimited = ControllerSpecificConfigEnum.THORLABS_CAMERA_FRAMEPERTRIGGER.value
            self.camera.image_poll_timeout_ms = ControllerSpecificConfigEnum.THORLABS_CAMERA_IMAGEPOLL_TIMEOUT.value

            # SENSOR_TYPE.MONOCHROME == 0; SENSOR_TYPE.BAYER == 1
            self._is_color = (self.camera.camera_sensor_type == SENSOR_TYPE.BAYER)

            # Ensure pipeline state reflects the newly connected camera type.
            self._colour_processor = None
            self._clrprc_monoToColour = None

            if self._is_color:
                self.camera.gain = int(0)
                self._colour_processor = TL_MTC()
                self._clrprc_monoToColour = self._colour_processor.create_mono_to_color_processor(
                    self.camera.camera_sensor_type,
                    self.camera.color_filter_array_phase,
                    self.camera.get_color_correction_matrix(),
                    self.camera.get_default_white_balance_matrix(),
                    self.camera.bit_depth)
                self._clrprc_monoToColour.color_space = TL_ClrSpc.SRGB
                self._clrprc_monoToColour.output_format = TL_Fmt.RGB_PIXEL
            else:
                self._bit_shift = max(0, self.camera.bit_depth - 8)

            self._frame_width = self.camera.image_width_pixels
            self._frame_height = self.camera.image_height_pixels

            self.camera.arm(2)
            self.camera.issue_software_trigger()

            self.status = "video capture initialisation"

            if self._flg_show_preview:
                cv2.namedWindow(self.win_name)

            self._mirrorx = ControllerConfigEnum.CAMERA_MIRRORX.value
            self._mirrory = ControllerConfigEnum.CAMERA_MIRRORY.value

            self.flg_initialised = True
            camera_type = 'colour' if self._is_color else 'monochrome'
            self._identifier = f"Thorlabs_{self.camera.model} ({camera_type}), S/N:{self.camera.serial_number}"
            print(f'>>>>> Thorlabs {camera_type} camera initialised <<<<<')
        except Exception as e:
            print('CameraController_Thorlabs initialisation error:\n{}'.format(e))
            self.flg_initialised = False
        finally:
            self._lock.release()

    def camera_termination(self):
        self._lock.acquire()
        
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs termination warning: camera was not properly initialised or already terminated.')
            self._lock.release()
            return
        
        try: self.camera.disarm()
        except Exception as e: print('camera_disarm error:\n{}'.format(e))
        
        if self._is_color and isinstance(self._clrprc_monoToColour, MonoToColorProcessor) and isinstance(self._colour_processor, TL_MTC):
            try: self._clrprc_monoToColour.dispose()
            except Exception as e: print('camera_termination colour processor error:\n{}'.format(e))

            try: self._colour_processor.dispose()
            except Exception as e: print('camera_termination colour processor SDK error:\n{}'.format(e))

        try: self.camera.dispose()
        except Exception as e: print('camera_termination error:\n{}'.format(e))

        if not isinstance(self.controller, TLCameraSDK):
            print('CameraController_Thorlabs termination warning: controller was not properly initialised or already terminated.')
            self._lock.release()
            return
        
        try: self.controller.dispose()
        except Exception as e: print('controller_dispose error:\n{}'.format(e))

        self.camera = None
        self.controller = None
        self._colour_processor = None
        self._clrprc_monoToColour = None

        time.sleep(3)   # Wait for all terminations to complete

        self.flg_initialised = False

        self._lock.release()

    def get_initialisation_status(self) -> bool:
        return self.flg_initialised

    def set_exposure_time_us(self, exposure_time_us: int | float) -> None:
        """
        Set the exposure time of the camera

        Args:
            exposure_time_us (int | float): Exposure time in microseconds
        """
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs set_exposure_time_us warning: camera is not properly initialised.')
            return
        
        with self._lock:
            if not isinstance(exposure_time_us, (int, float)):
                raise ValueError("Exposure time must be an integer or float")
            self.camera.exposure_time_us = int(exposure_time_us)

    def get_exposure_time_us(self) -> int | float | None:
        """
        Get the exposure time of the camera

        Returns:
            int | float: Exposure time in microseconds
        """
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs get_exposure_time_us warning: camera is not properly initialised.')
            return None

        with self._lock:
            return self.camera.exposure_time_us

    def frame_capture(self) -> np.ndarray | None:
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs frame_capture warning: camera is not properly initialised.')
            return None
        
        image_1d: np.ndarray | None = None
        
        with self._lock:
            frame = self.camera.get_pending_frame_or_null()
            if frame is not None: image_1d = frame.image_buffer.copy()

        if frame is None: return None
        
        assert image_1d is not None, "Thorlabs camera controller: Failed to capture frame"
        
        if self._is_color and isinstance(self._clrprc_monoToColour, MonoToColorProcessor):
            image_array = self._clrprc_monoToColour.transform_to_24(
                image_1d, self._frame_width, self._frame_height)
            image_array = image_array.reshape(self._frame_height, self._frame_width, 3)
        elif self._is_color:
            print('Thorlabs camera controller: Captured colour frame, but mono-to-color processor is not properly initialised.')
            return None
        else:
            image_array = image_1d.reshape(self._frame_height, self._frame_width)

        if self._mirrorx: image_array = cv2.flip(image_array, 0)
        if self._mirrory: image_array = cv2.flip(image_array, 1)

        self.img = image_array
        return self.img

    def img_capture(self) -> Image.Image | None:
        frm = self.frame_capture()
        if frm is None:
            return None
        if self._is_color:
            self.img = Image.fromarray(frm)
        else:
            frm_8bit = (frm >> self._bit_shift).astype(np.uint8)
            self.img = Image.fromarray(frm_8bit).convert('RGB')
        return self.img

    def set_single_frame_trigger_mode(self, enabled: bool) -> None:
        """Switch between single-frame software trigger (True) and continuous (False) mode."""
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs set_single_frame_trigger_mode warning: camera is not properly initialised.')
            return
        
        with self._lock:
            self.camera.disarm()
            self.camera.frames_per_trigger_zero_for_unlimited = 1 if enabled else 0
            self.camera.arm(2)
            if not enabled:
                self.camera.issue_software_trigger()  # restart continuous stream

    def img_capture_fresh(self) -> Image.Image | None:
        """
        Flush buffered frames, issue a software trigger, and wait for the fresh frame.
        Camera must already be in single-frame trigger mode â€” call
        set_single_frame_trigger_mode(True) once before the tiling loop.
        """
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs img_capture_fresh warning: camera is not properly initialised.')
            return None
        
        with self._lock:
            old_timeout = self.camera.image_poll_timeout_ms
            self.camera.image_poll_timeout_ms = 0
            while self.camera.get_pending_frame_or_null() is not None:
                pass
            self.camera.issue_software_trigger()
            self.camera.image_poll_timeout_ms = int(self.camera.exposure_time_us // 1000) + 500
            frame = self.camera.get_pending_frame_or_null()
            self.camera.image_poll_timeout_ms = old_timeout

        if frame is None: return None
        
        image_1d = frame.image_buffer.copy()
        
        if self._is_color and isinstance(self._clrprc_monoToColour, MonoToColorProcessor):
            image_array = self._clrprc_monoToColour.transform_to_24(
                image_1d, self._frame_width, self._frame_height)
            image_array = image_array.reshape(self._frame_height, self._frame_width, 3)
            if self._mirrorx: image_array = cv2.flip(image_array, 0)
            if self._mirrory: image_array = cv2.flip(image_array, 1)
            self.img = Image.fromarray(image_array)
        elif self._is_color:
            print('Thorlabs camera controller: Captured colour frame, but mono-to-color processor is not properly initialised.')
            return None
        else:
            image_array = image_1d.reshape(self._frame_height, self._frame_width)
            if self._mirrorx: image_array = cv2.flip(image_array, 0)
            if self._mirrory: image_array = cv2.flip(image_array, 1)
            self.img = Image.fromarray((image_array >> self._bit_shift).astype(np.uint8)).convert('RGB')

        return self.img

    def vidcapture_show(self):
        self.status = "video capture on-going"
        self.vidcap_flag = True
        
        while self.vidcap_flag:
            key = cv2.waitKey(20)
            
            if key == 27:   # exit on ESC
                self.vidcap_flag = False
                time.sleep(0.1)
                
            if not isinstance(self.camera, TLCamera):
                print('CameraController_Thorlabs vidcapture_show warning: camera is not properly initialised.')
                time.sleep(0.01)
                continue
                
            if key == ord('i'):  # Increase exposure
                try: self.camera.exposure_time_us += 10000
                except Exception as e: print(f"Error: {e}")
                print(f"Exposure increased to: {self.camera.exposure_time_us}")
            elif key == ord('d'):  # Decrease exposure
                try: self.camera.exposure_time_us -= 10000
                except Exception as e: print(f"Error: {e}")
                print(f"Exposure decreased to: {self.camera.exposure_time_us}")

            img = self.img_capture()
            if img is None:
                time.sleep(0.01)
                continue
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGBA)
            self.vidshow(self.win_name, frame)

        self.status = "video capture stopped"
        self.quit()

    def vidshow(self, win_name, frame):
        cv2.imshow(win_name, frame)

    def quit(self, *args, **kwargs):
        print('video stopped')
        self.camera_termination()
        cv2.destroyWindow(self.win_name)


if __name__ == '__main__':
    vid = CameraController_Thorlabs(show=True)
    vid.set_exposure_time_us(100e3)
    vid.vidcapture_show()
    vid.camera_termination()




