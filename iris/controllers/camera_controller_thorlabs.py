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
from thorlabs_tsi_sdk.tl_camera_enums import SENSOR_TYPE, OPERATION_MODE
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

        self._fresh_last_frame_count: int | None = None  # Frame count of the last fresh capture since arming
        self._time_last_trigger: float = 0.0    # time.perf_counter() of the last single-frame software trigger
        self._frame_time_supported: bool = True # frame_time_us is only supported by scientific CCD cameras

        try: self._initialisation()
        except Exception as e: print('CameraController_Thorlabs initialisation error:\n{}'.format(e))

    def get_identifier(self) -> str:
        if not self._identifier and isinstance(self.camera, TLCamera):
            camera_type = 'colour' if self._is_color else 'monochrome'
            self._identifier = f"Thorlabs_{self.camera.model} ({camera_type}), S/N:{self.camera.serial_number}"
        return self._identifier

    def reinitialise_connection(self) -> None:
        """Reinitialise the camera connection, preserving the current exposure time and gain."""
        exposure_time_us = None
        try: exposure_time_us = self.get_exposure_time_us()
        except Exception: pass

        gain = None
        try: gain = self.get_gain()
        except Exception: pass

        try: self.camera_termination()
        except Exception as e: print('CameraController_Thorlabs reinitialise_connection error:\n{}'.format(e))

        try: self._initialisation()
        except Exception as e: print('CameraController_Thorlabs reinitialise_connection error:\n{}'.format(e))

        if exposure_time_us is not None:
            try: self.set_exposure_time_us(exposure_time_us)
            except Exception as e: print('CameraController_Thorlabs reinitialise_connection exposure restore error:\n{}'.format(e))

        if gain is not None:
            try: self.set_gain(gain)
            except Exception as e: print('CameraController_Thorlabs reinitialise_connection gain restore error:\n{}'.format(e))

    def _initialisation(self) -> None:
        self._lock.acquire()
        try:
            self.controller = TLCameraSDK()

            available_cameras = self.controller.discover_available_cameras()
            if len(available_cameras) < 1:
                raise RuntimeError('No Thorlabs cameras detected')

            self.camera = self.controller.open_camera(available_cameras[self.camera_index])
            # The SDK requires genuine ints here, so the config values are cast explicitly
            self.camera.exposure_time_us = int(ControllerSpecificConfigEnum.THORLABS_CAMERA_EXPOSURE_TIME.value)
            self.camera.frames_per_trigger_zero_for_unlimited = int(ControllerSpecificConfigEnum.THORLABS_CAMERA_FRAMEPERTRIGGER.value)
            self.camera.image_poll_timeout_ms = int(ControllerSpecificConfigEnum.THORLABS_CAMERA_IMAGEPOLL_TIMEOUT.value)

            # SENSOR_TYPE.MONOCHROME == 0; SENSOR_TYPE.BAYER == 1
            self._is_color = (self.camera.camera_sensor_type == SENSOR_TYPE.BAYER)

            # Ensure pipeline state reflects the newly connected camera type.
            self._colour_processor = None
            self._clrprc_monoToColour = None

            # Gain is applied to both sensor types; cameras without gain support report a
            # gain_range maximum of 0 and are left untouched.
            gain_db_default = float(ControllerSpecificConfigEnum.THORLABS_CAMERA_GAIN_DB.value)
            if not self._set_gain_db_unlocked(gain_db_default) and gain_db_default != 0:
                print('CameraController_Thorlabs initialisation warning: the connected camera does not support gain, '
                      'the configured thorlabs_camera_gain_db of {} dB is ignored.'.format(gain_db_default))

            if self._is_color:
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

    def _get_gain_range_unlocked(self) -> tuple[int, int] | None:
        """
        Query the gain range of the camera. The caller must already hold self._lock.

        Returns:
            tuple[int, int] | None: (min, max) gain in camera device units, or None if unavailable
        """
        if not isinstance(self.camera, TLCamera): return None

        try:
            gain_range = self.camera.gain_range
            return (int(gain_range.min), int(gain_range.max))
        except Exception as e:
            print('CameraController_Thorlabs gain range error:\n{}'.format(e))
            return None

    def get_gain_range(self) -> tuple[int, int] | None:
        """
        Get the range of gain values supported by the camera, in camera device units.
        A maximum of 0 means the connected camera does not support gain.

        Returns:
            tuple[int, int] | None: (min, max) gain, or None if the camera is not initialised
        """
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs get_gain_range warning: camera is not properly initialised.')
            return None

        with self._lock:
            return self._get_gain_range_unlocked()

    def get_gain_range_db(self) -> tuple[float, float] | None:
        """
        Get the range of gain values supported by the camera, in decibels.

        Returns:
            tuple[float, float] | None: (min, max) gain in dB, or None if the camera
                is not initialised or does not support gain
        """
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs get_gain_range_db warning: camera is not properly initialised.')
            return None

        with self._lock:
            gain_range = self._get_gain_range_unlocked()
            if gain_range is None or gain_range[1] <= 0: return None

            try:
                return (float(self.camera.convert_gain_to_decibels(gain_range[0])),
                        float(self.camera.convert_gain_to_decibels(gain_range[1])))
            except Exception as e:
                print('CameraController_Thorlabs get_gain_range_db error:\n{}'.format(e))
                return None

    def is_gain_supported(self) -> bool:
        """
        Check whether the connected camera supports gain adjustment.

        Returns:
            bool: True if the camera exposes a non-zero gain range
        """
        gain_range = self.get_gain_range()
        return gain_range is not None and gain_range[1] > 0

    def _set_gain_unlocked(self, gain: int | float) -> bool:
        """
        Apply the gain to the camera, clamped to the supported range.
        The caller must already hold self._lock.

        Args:
            gain (int | float): Gain in camera device units

        Returns:
            bool: True if the gain was applied, False if unsupported or on error
        """
        if not isinstance(self.camera, TLCamera): return False

        gain_range = self._get_gain_range_unlocked()
        if gain_range is None or gain_range[1] <= 0: return False

        gain_clamped = int(min(max(round(gain), gain_range[0]), gain_range[1]))
        if gain_clamped != round(gain):
            print('CameraController_Thorlabs gain warning: gain {} clamped to {} (allowed range {}-{}).'.format(
                round(gain), gain_clamped, gain_range[0], gain_range[1]))

        try:
            self.camera.gain = gain_clamped
            return True
        except Exception as e:
            print('CameraController_Thorlabs set_gain error:\n{}'.format(e))
            return False

    def set_gain(self, gain: int | float) -> None:
        """
        Set the gain of the camera, in camera device units.
        The value is clamped to the range reported by get_gain_range().

        Args:
            gain (int | float): Gain in camera device units
        """
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs set_gain warning: camera is not properly initialised.')
            return

        if not isinstance(gain, (int, float)):
            raise ValueError("Gain must be an integer or float")

        with self._lock:
            gain_range = self._get_gain_range_unlocked()
            if gain_range is None or gain_range[1] <= 0:
                print('CameraController_Thorlabs set_gain warning: the connected camera does not support gain.')
                return
            self._set_gain_unlocked(gain)

    def get_gain(self) -> int | None:
        """
        Get the gain of the camera, in camera device units.

        Returns:
            int | None: Gain in camera device units, or None if unavailable
        """
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs get_gain warning: camera is not properly initialised.')
            return None

        with self._lock:
            try: return int(self.camera.gain)
            except Exception as e:
                print('CameraController_Thorlabs get_gain error:\n{}'.format(e))
                return None

    def _set_gain_db_unlocked(self, gain_db: int | float) -> bool:
        """
        Convert a gain in decibels to camera device units and apply it.
        The caller must already hold self._lock.

        Args:
            gain_db (int | float): Gain in decibels

        Returns:
            bool: True if the gain was applied, False if unsupported or on error
        """
        if not isinstance(self.camera, TLCamera): return False

        try: gain = self.camera.convert_decibels_to_gain(float(gain_db))
        except Exception as e:
            print('CameraController_Thorlabs gain conversion error:\n{}'.format(e))
            return False

        return self._set_gain_unlocked(gain)

    def set_gain_db(self, gain_db: int | float) -> None:
        """
        Set the gain of the camera in decibels. The value is converted to camera
        device units by the SDK, then clamped to the supported range.

        Args:
            gain_db (int | float): Gain in decibels
        """
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs set_gain_db warning: camera is not properly initialised.')
            return

        if not isinstance(gain_db, (int, float)):
            raise ValueError("Gain must be an integer or float")

        with self._lock:
            gain_range = self._get_gain_range_unlocked()
            if gain_range is None or gain_range[1] <= 0:
                print('CameraController_Thorlabs set_gain_db warning: the connected camera does not support gain.')
                return
            self._set_gain_db_unlocked(gain_db)

    def get_gain_db(self) -> float | None:
        """
        Get the gain of the camera in decibels.

        Returns:
            float | None: Gain in decibels, or None if unavailable
        """
        gain = self.get_gain()
        if gain is None: return None

        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs get_gain_db warning: camera is not properly initialised.')
            return None

        try: return float(self.camera.convert_gain_to_decibels(gain))
        except Exception as e:
            print('CameraController_Thorlabs get_gain_db error:\n{}'.format(e))
            return None

    def frame_capture(self) -> np.ndarray | None:
        if not isinstance(self.camera, TLCamera):
            print('CameraController_Thorlabs frame_capture warning: camera is not properly initialised.')
            return None
        
        image_1d: np.ndarray | None = None
        
        with self._lock:
            frame = self.camera.get_pending_frame_or_null()
            if frame is not None:
                image_1d = frame.image_buffer.copy()
                # Skip ahead to the newest buffered frame: when frames are produced faster than they
                # are polled, the oldest pending frame can be a couple of frame periods stale, which
                # skews anything that pairs a frame with the stage position (e.g. autofocus)
                old_timeout = self.camera.image_poll_timeout_ms
                self.camera.image_poll_timeout_ms = 0
                while (newer := self.camera.get_pending_frame_or_null()) is not None:
                    image_1d = newer.image_buffer.copy()   # Copy before the SDK recycles the buffer
                self.camera.image_poll_timeout_ms = old_timeout

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
            # Set explicitly rather than relying on the camera's default (e.g. left over from ThorCam)
            self.camera.operation_mode = OPERATION_MODE.SOFTWARE_TRIGGERED
            self.camera.frames_per_trigger_zero_for_unlimited = 1 if enabled else 0
            self.camera.arm(2)  # Arming also clears any frames still queued
            self._fresh_last_frame_count = None
            if not enabled:
                self.camera.issue_software_trigger()  # restart continuous stream

    def _get_min_trigger_interval_s(self) -> float:
        """
        Minimum time between single-frame software triggers. The camera silently ignores a trigger
        issued before the previous frame's frame time (exposure + readout) has elapsed.
        The caller must already hold self._lock.

        Returns:
            float: Minimum trigger interval [s], including a safety margin
        """
        assert isinstance(self.camera, TLCamera)
        frame_time_us = None
        if self._frame_time_supported:
            try: frame_time_us = self.camera.frame_time_us
            except Exception: self._frame_time_supported = False    # Don't retry: the SDK logs every failure
        if frame_time_us is None:
            try: readout_us = self.camera.sensor_readout_time_ns / 1000
            except Exception: readout_us = 0.0
            frame_time_us = self.camera.exposure_time_us + readout_us
        return frame_time_us * 1e-6 * 1.2 + 0.01

    def _wait_trigger_ready(self) -> None:
        """
        Blocks until the camera can accept another single-frame software trigger.
        The caller must already hold self._lock.
        """
        wait_s = self._time_last_trigger + self._get_min_trigger_interval_s() - time.perf_counter()
        if wait_s > 0: time.sleep(wait_s)

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
            # In single-frame mode nothing should be queued here; anything that is is a stale frame
            list_stale_counts = []
            while (stale := self.camera.get_pending_frame_or_null()) is not None:
                list_stale_counts.append(stale.frame_count)
            if list_stale_counts:
                print(f'CameraController_Thorlabs img_capture_fresh warning: discarded {len(list_stale_counts)} '
                      f'stale frame(s) before triggering (frame counts {list_stale_counts}, '
                      f'last fresh frame count {self._fresh_last_frame_count})')

            self._wait_trigger_ready()
            self.camera.issue_software_trigger()
            self._time_last_trigger = time.perf_counter()
            # Generous window: exposure + readout + transfer. A too-tight window returns None while the
            # frame is still in flight, and that late frame then gets delivered as the NEXT tile's image
            self.camera.image_poll_timeout_ms = max(1000, round(self.camera.exposure_time_us / 1000) * 2 + 500)
            frame = self.camera.get_pending_frame_or_null()
            if frame is None:
                print('CameraController_Thorlabs img_capture_fresh warning: triggered frame timed out, re-arming')
                # Re-arming clears the queue, so this trigger's late frame can never be delivered
                # as the next capture's image
                self.camera.disarm()
                self.camera.arm(2)
                self._fresh_last_frame_count = None
                image_1d = None
            else:
                # Each trigger should produce exactly one frame, so frame counts must be consecutive
                expected_count = None if self._fresh_last_frame_count is None else self._fresh_last_frame_count + 1
                if expected_count is not None and frame.frame_count != expected_count:
                    print(f'CameraController_Thorlabs img_capture_fresh warning: frame count {frame.frame_count}, '
                          f'expected {expected_count}: the camera produced frames without a trigger')
                self._fresh_last_frame_count = frame.frame_count
                image_1d = frame.image_buffer.copy()    # Copy before the SDK recycles the buffer
            self.camera.image_poll_timeout_ms = old_timeout

        if image_1d is None: return None
        
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
            elif key == ord('g'):  # Increase gain
                current_gain = self.get_gain()
                if current_gain is not None: self.set_gain(current_gain + 10)
                print(f"Gain: {self.get_gain()} ({self.get_gain_db()} dB)")
            elif key == ord('h'):  # Decrease gain
                current_gain = self.get_gain()
                if current_gain is not None: self.set_gain(current_gain - 10)
                print(f"Gain: {self.get_gain()} ({self.get_gain_db()} dB)")

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




