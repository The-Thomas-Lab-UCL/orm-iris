"""
Shared helpers for the stage controllers' immediate stop (see stop_motion() in class_xy_stage_controller.py
and class_z_stage_controller.py).

stop_motion() stops an ongoing movement straight away, including a blocking move_direct() running in
another thread (which then returns early). It must never cost the stage its coordinate calibration, so it
refuses to interrupt a homing routine: decorate homing_n_coor_calibration() with homing_guard to mark it.

Made for: The Thomas Group, Biochemical Engineering Dept., UCL
"""
import functools


def homing_guard(func):
    """
    Decorator for a controller's homing_n_coor_calibration(). Marks the controller as homing for the
    duration of the call, so that stop_motion() does not interrupt it (an interrupted homing leaves the
    stage uncalibrated).
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self._flg_homing = True
        try: return func(self, *args, **kwargs)
        finally: self._flg_homing = False
    return wrapper


def is_homing(controller) -> bool:
    """
    Returns:
        bool: True while the controller's homing_guard-decorated homing is running
    """
    return getattr(controller, '_flg_homing', False)


def is_stop_requested(controller) -> bool:
    """
    Returns:
        bool: True if stop_motion() was called since the controller's current move_direct() started.
            Used by move_direct() to tell an error caused by its own interruption from a genuine one.
    """
    return getattr(controller, '_flg_stop_requested', False)
