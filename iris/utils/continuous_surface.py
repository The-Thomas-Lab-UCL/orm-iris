"""Piecewise Z profiles and sampled position feedback for continuous line scans.

This is software following of independent stages, not a hardware XYZ trajectory.
The error limit is checked at samples; it is not a bound between samples.
"""

from bisect import bisect_right
from dataclasses import dataclass
import math
import queue
import threading


@dataclass(frozen=True)
class SurfaceLine:
    points: tuple
    axis: int

    @property
    def start(self):
        return self.points[0]

    @property
    def end(self):
        return self.points[-1]

    @property
    def maximum_slope(self):
        return max((abs((b[2]-a[2])/(b[self.axis]-a[self.axis]))
                    for a, b in zip(self.points, self.points[1:])), default=0.)

    def target_z(self, xy):
        points = self.points if self.start[self.axis] <= self.end[self.axis] else self.points[::-1]
        coordinates = [point[self.axis] for point in points]
        position = min(max(float(xy[self.axis]), coordinates[0]), coordinates[-1])
        index = min(bisect_right(coordinates, position), len(points)-1)
        if index == 0:
            return points[0][2]
        a, b = points[index-1:index+1]
        fraction = (position-a[self.axis])/(b[self.axis]-a[self.axis])
        return a[2] + fraction*(b[2]-a[2])


def build_surface_lines(coordinates, axis=0, snake=True, precision=4):
    if axis not in (0, 1):
        raise ValueError('Surface scan direction must be X or Y.')
    groups = {}
    for coordinate in coordinates:
        point = tuple(float(v) for v in coordinate)
        if len(point) != 3 or not all(math.isfinite(v) for v in point):
            raise ValueError('Surface coordinates must contain finite X, Y and Z values.')
        cross = round(point[1-axis], precision)
        point = tuple(cross if i == 1-axis else v for i, v in enumerate(point))
        row = groups.setdefault(cross, {})
        if point[axis] in row and row[point[axis]][2] != point[2]:
            raise ValueError('A surface coordinate has conflicting Z values at the same XY position.')
        row[point[axis]] = point
    if not groups:
        raise ValueError('Select a coordinate surface first.')
    result = []
    for index, cross in enumerate(sorted(groups)):
        row = groups[cross]
        points = tuple(row[key] for key in sorted(row))
        if len(points) < 2:
            raise ValueError('Continuous surface following needs at least two distinct points per line.')
        if snake and index % 2:
            points = points[::-1]
        result.append(SurfaceLine(points, axis))
    return result


def plan_surface_speed(lines, requested_relative, xy_limits, z_limits, tolerance_mm):
    """Reserve half the tolerance for sampled feedback and communication delays."""
    if not math.isfinite(tolerance_mm) or tolerance_mm <= 0:
        raise ValueError('Z tracking tolerance must be a positive number.')
    if not math.isfinite(requested_relative) or not 0 < requested_relative <= 100:
        raise ValueError('Continuous scan speed must be between 0 and 100 percent.')
    for line in lines:
        if any(not z_limits['minimum_mm'] <= point[2] <= z_limits['maximum_mm']
               for point in line.points):
            raise ValueError('The modified surface exceeds the Z stage travel range.')
    max_velocity = xy_limits['maximum_speed_mm_s']
    minimum_relative = xy_limits['minimum_relative_percent']
    if (not lines or not math.isfinite(max_velocity) or max_velocity <= 0 or
            not math.isfinite(minimum_relative) or minimum_relative <= 0 or
            not math.isfinite(z_limits['settling_s']) or z_limits['settling_s'] <= 0):
        raise ValueError('The stage did not report usable surface-following limits.')
    slope = max(line.maximum_slope for line in lines)
    # Keep the existing Z settling wait, plus a communication/polling allowance.
    feedback_s = z_limits['settling_s'] + .25
    relative = requested_relative
    if slope:
        relative = min(relative, tolerance_mm*.5/(slope*feedback_s)/max_velocity*100)
    if relative < minimum_relative:
        raise ValueError('This surface needs a speed below the XY stage minimum at the chosen Z tolerance. '
                         'Use discrete scanning or a smoother surface.')
    return relative


class SurfaceMove:
    """One XY line with a single Z writer; retain both workers after timeouts."""
    def __init__(self, profile, xy_move, xy_position, z_move, z_position, xy_stop,
                 running, tolerance_mm, report=None, poll_s=.05):
        self.profile = profile
        self.xy_move, self.xy_position = xy_move, xy_position
        self.z_move, self.z_position = z_move, z_position
        self.xy_stop, self.running = xy_stop, running
        self.tolerance = tolerance_mm
        self.poll_s = poll_s
        self.failures = queue.Queue()
        self.finished = threading.Event()
        self.abort = threading.Event()
        self.latest_position = profile.start
        self.report = report if report is not None else {}
        self.report.update(samples=0, maximum_observed_error_um=0., complete=False)
        self.xy_worker = threading.Thread(target=self._move_xy, daemon=True)
        self.z_worker = threading.Thread(target=self._follow_z, daemon=True)
        self.workers = [self.xy_worker, self.z_worker]

    def start(self):
        # Validate initial readback before either stage moves.
        xy, z, _ = self._sample()
        if math.dist(xy, self.profile.start[:2]) > .001:
            raise RuntimeError('Stage is not at the start of the surface scan line.')
        self.xy_worker.start()
        self.z_worker.start()

    def _sample(self):
        xy = tuple(float(v) for v in self.xy_position())
        z = float(self.z_position())
        if len(xy) != 2 or not all(math.isfinite(v) for v in (*xy, z)):
            raise RuntimeError('Invalid stage position during Z surface following.')
        self.latest_position = (*xy, z)
        if abs(xy[1-self.profile.axis] - self.profile.start[1-self.profile.axis]) > .001:
            raise RuntimeError('XY stage left the planned surface scan line.')
        target = self.profile.target_z(xy)
        error = abs(target-z)
        self.report['samples'] += 1
        self.report['maximum_observed_error_um'] = max(
            self.report['maximum_observed_error_um'], error*1000)
        if error > self.tolerance:
            raise RuntimeError(f'Z tracking error {error*1000:.2f} um exceeds '
                               f'the {self.tolerance*1000:g} um limit; continuous scan stopped.')
        return xy, z, target

    def _move_xy(self):
        try:
            if self.running() and not self.abort.is_set():
                self.xy_move(self.profile.end[:2])
        except Exception as failure:
            self.failures.put(failure)
            self.abort.set()
        finally:
            self.finished.set()

    def _follow_z(self):
        try:
            while not self.finished.is_set():
                if not self.running() or self.abort.is_set():
                    self.abort.set()
                    self.xy_stop()
                    return
                _, z, target = self._sample()
                if abs(target-z) >= self.tolerance*.1:
                    # Use the controller's normal blocking move and settling wait.
                    self.z_move(target)
                else:
                    self.finished.wait(self.poll_s)
            if not self.running() or self.abort.is_set():
                return
            xy, z, target = self._sample()
            if math.dist(xy, self.profile.end[:2]) > .001:
                raise RuntimeError('XY stage did not reach the surface line endpoint.')
            if abs(target-z) > 1e-9:
                self.z_move(target)
            self._sample()
            self.report['complete'] = True
        except Exception as failure:
            self.report['error'] = str(failure)
            self.abort.set()
            self.failures.put(failure)
            try:
                self.xy_stop()
            except Exception as stop_failure:
                self.failures.put(stop_failure)
