"""Path-length based progress/time estimation for the mapping (Raman imaging) scans.

The naive estimator used before simply scaled the elapsed time by the number of points done
(`elapsed/points_done * points_left`). That is a poor model for a stage scan: the per-point cost is
not constant. A point at the far end of a retrace costs a lot more than the next point along the
same scan line, so the estimate swings whenever the scan crosses between a line and its retrace, and
it is systematically wrong for non-uniform coordinate lists.

This module models the scan cost instead as

    time = fixed_time_per_point * points  +  travelled_XY_distance / stage_rate

with the travel rate [mm/s] *measured* from the scan as it progresses (so it accounts for the real
acceleration/communication overheads instead of a nominal stage speed), optionally per segment
"group" - continuous mapping travels the scan lines at the reduced mapping speed and the retraces at
full speed, which are two very different rates and are therefore learnt separately.

Made for: The Thomas Group, Biochemical Engineering Dept., UCL
"""
from dataclasses import dataclass
from typing import Hashable, Sequence

import time

import numpy as np

# Segment group labels used by the continuous mapping scan (see ScanPathProgress.group_labels)
GROUP_SCANLINE = 'scanline'
GROUP_RETRACE = 'retrace'


def format_duration(seconds:float) -> str:
    """
    Formats a duration in seconds as a short "Xh Ym Zs" string.

    Args:
        seconds (float): The duration in seconds

    Returns:
        str: The duration in "Xh Ym Zs" format (the leading zero-units are omitted)
    """
    if not np.isfinite(seconds) or seconds < 0: seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0: return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0: return f"{minutes}m {secs}s"
    else: return f"{secs}s"


@dataclass
class ScanProgressSnapshot:
    """
    A single progress snapshot of a running scan, as returned by ScanPathProgress.update().

    Attributes:
        points_done (int): Number of coordinates already measured
        points_total (int): Total number of coordinates in the scan
        distance_done_mm (float): XY path length already travelled [mm]
        distance_remaining_mm (float): XY path length still to travel [mm]
        distance_total_mm (float): Total XY path length of the scan [mm]
        fraction_done (float): Fraction of the scan completed (0.0 - 1.0), by path length if the
            path has a non-zero length, otherwise by point count
        time_elapsed_sec (float): Time elapsed since ScanPathProgress.start() [s]
        time_remaining_sec (float): Estimated time remaining [s]
        time_total_sec (float): Estimated total scan duration [s] (elapsed + remaining)
    """
    points_done:int
    points_total:int
    distance_done_mm:float
    distance_remaining_mm:float
    distance_total_mm:float
    fraction_done:float
    time_elapsed_sec:float
    time_remaining_sec:float
    time_total_sec:float

    def message(self, point_noun:str='points') -> str:
        """
        Builds the human-readable progress message shown in the status bar / log.

        Args:
            point_noun (str): What a single coordinate represents ('points' for the discrete scan,
                'lines' for the continuous scan)

        Returns:
            str: The progress message
        """
        return (
            f'Measured {self.points_done}/{self.points_total} {point_noun} '
            f'({self.fraction_done*100:.1f}% of path, '
            f'{self.distance_done_mm:.2f}/{self.distance_total_mm:.2f} mm). '
            f'Elapsed: {format_duration(self.time_elapsed_sec)}. '
            f'Remaining est.: {format_duration(self.time_remaining_sec)}. '
            f'Total est.: {format_duration(self.time_total_sec)}.'
        )


class ScanPathProgress:
    """
    Tracks the progress of a mapping scan along its XY path and estimates the time remaining.

    Usage:
        progress = ScanPathProgress(list_coor, fixed_time_per_point_sec=integration_time)
        progress.start()
        for i, coor in enumerate(list_coor):
            ...
            snapshot = progress.update(i+1)
            print(snapshot.message())
    """

    def __init__(
        self,
        coordinates:Sequence[Sequence[float]],
        fixed_time_per_point_sec:float = 0.0,
        start_coordinate:Sequence[float]|None = None,
        group_labels:Sequence[Hashable]|None = None,
        ):
        """
        Pre-computes the per-segment and total XY path lengths of the scan.

        Args:
            coordinates (Sequence[Sequence[float]]): The scan coordinates, in the order they will be
                visited. Only the first two components (X,Y) of each coordinate are used; Z is
                ignored as the stage does not move in Z during a scan.
            fixed_time_per_point_sec (float): The per-coordinate cost that does not depend on the
                travelled distance, e.g. the total integration time of a discrete-scan point
                (accumulation * integration time). Use 0.0 when the acquisition runs while the stage
                is moving, as in the continuous scan.
            start_coordinate (Sequence[float]|None): The stage position the scan starts from. When
                given, the move from it to the first coordinate counts towards the path; when None
                (the default) the path starts at the first coordinate, i.e. the initial approach move
                is excluded from the total (its duration is unknown beforehand and it is usually
                performed before the scan clock starts).
            group_labels (Sequence[Hashable]|None): Optional label per *segment* (same length as
                `coordinates`, label i describing the move that arrives at coordinate i), used to
                learn a separate travel rate per kind of move. Use continuous_group_labels() for the
                continuous scan. When None, a single travel rate is learnt for the whole scan.

        Raises:
            ValueError: If the coordinates are empty/malformed, or group_labels has the wrong length
        """
        coor = np.asarray(coordinates, dtype=float)
        if coor.ndim != 2 or coor.shape[0] == 0 or coor.shape[1] < 2:
            raise ValueError('coordinates must be a non-empty sequence of (x,y,...) coordinates')
        xy = coor[:, :2]

        if start_coordinate is None:
            # The first segment has no known origin -> it does not contribute to the path
            previous_xy = np.vstack([xy[0], xy[:-1]])
        else:
            start_xy = np.asarray(start_coordinate, dtype=float)[:2]
            previous_xy = np.vstack([start_xy, xy[:-1]])

        self.distances_mm:np.ndarray = np.linalg.norm(xy - previous_xy, axis=1)
        self.cumulative_distances_mm:np.ndarray = np.cumsum(self.distances_mm)
        self.total_distance_mm:float = float(self.cumulative_distances_mm[-1])
        self.points_total:int = int(xy.shape[0])

        self.fixed_time_per_point_sec = max(0.0, float(fixed_time_per_point_sec))
        if group_labels is None:
            self.group_labels:list[Hashable] = [None]*self.points_total
        else:
            if len(group_labels) != self.points_total:
                raise ValueError('group_labels must have one label per coordinate')
            self.group_labels = list(group_labels)

        # Measured travel times/distances, globally and per segment group
        self._time_start:float|None = None
        self._last_elapsed_sec:float = 0.0
        self._points_done:int = 0
        self._travel_time_sec:float = 0.0
        self._travel_distance_mm:float = 0.0
        self._group_travel:dict[Hashable,list[float]] = {}   # label -> [time_sec, distance_mm]

    def start(self) -> None:
        """
        Starts (or restarts) the scan clock. Call this immediately before the scan loop, so that any
        preparation done beforehand (e.g. the continuous scan's speed auto-adjustment) is counted
        neither as scan time nor towards the measured travel rate.
        """
        self._time_start = time.time()
        self._last_elapsed_sec = 0.0
        self._points_done = 0
        self._travel_time_sec = 0.0
        self._travel_distance_mm = 0.0
        self._group_travel = {}

    def add_paused_time(self, duration_sec:float) -> None:
        """
        Discounts a stretch of wall-clock time during which the scan was deliberately held
        still (e.g. parked while the data hub wrote a database file). Without this the pause
        would be attributed to the segment the scan happened to be on, which both inflates the
        elapsed time and corrupts the measured travel rate that the estimate is built on.

        Args:
            duration_sec (float): Seconds the scan spent parked, as returned by the pause gate
        """
        if self._time_start is None or not duration_sec > 0: return
        # Shifting the start forward removes the pause from every subsequent time_elapsed_sec, so
        # the next update()'s (elapsed - _last_elapsed_sec) delta excludes it too and the pause is
        # never billed to a segment's travel rate.
        self._time_start += duration_sec

    @property
    def time_elapsed_sec(self) -> float:
        """float: Time elapsed since start() [s], or 0.0 if the scan has not been started yet."""
        if self._time_start is None: return 0.0
        return max(0.0, time.time() - self._time_start)

    def initial_message(self, point_noun:str='points') -> str:
        """
        Builds the message describing the scan before it starts (total path length, and the lower
        bound on the duration if the per-point cost is known).

        Args:
            point_noun (str): What a single coordinate represents ('points' or 'lines')

        Returns:
            str: The message to show before the first point is measured
        """
        msg = (f'Starting scan: {self.points_total} {point_noun} over '
               f'{self.total_distance_mm:.2f} mm of stage travel.')
        est_fixed = self.fixed_time_per_point_sec * self.points_total
        if est_fixed > 0:
            msg += f' Integration time alone: {format_duration(est_fixed)}.'
        return msg

    def update(self, points_done:int) -> ScanProgressSnapshot:
        """
        Records the completion of the scan coordinates up to `points_done` and returns the resulting
        progress snapshot. Intended to be called exactly once per measured coordinate, as the time
        spent since the previous call is attributed to the segments covered in between (which is what
        allows the per-group travel rates to be measured).

        Args:
            points_done (int): The number of coordinates measured so far (1-based count, i.e. `i+1`
                inside a loop over the coordinates)

        Returns:
            ScanProgressSnapshot: The progress snapshot, ready to be formatted with its message()
        """
        if self._time_start is None: self.start()
        points_done = int(min(max(points_done, 0), self.points_total))
        elapsed = self.time_elapsed_sec

        if points_done > self._points_done:
            self._record_travel(self._points_done, points_done, elapsed - self._last_elapsed_sec)
            self._points_done = points_done
            self._last_elapsed_sec = elapsed

        distance_done = float(self.cumulative_distances_mm[points_done-1]) if points_done > 0 else 0.0
        distance_remaining = max(0.0, self.total_distance_mm - distance_done)
        time_remaining = self._estimate_time_remaining(points_done, elapsed)

        if self.total_distance_mm > 0: fraction = distance_done / self.total_distance_mm
        elif self.points_total > 0: fraction = points_done / self.points_total
        else: fraction = 0.0

        return ScanProgressSnapshot(
            points_done=points_done,
            points_total=self.points_total,
            distance_done_mm=distance_done,
            distance_remaining_mm=distance_remaining,
            distance_total_mm=self.total_distance_mm,
            fraction_done=fraction,
            time_elapsed_sec=elapsed,
            time_remaining_sec=time_remaining,
            time_total_sec=elapsed + time_remaining,
        )

    def _record_travel(self, index_from:int, index_to:int, duration_sec:float) -> None:
        """
        Attributes the time spent on the segments [index_from, index_to) to their groups, after
        subtracting the (distance-independent) fixed per-point cost.

        Args:
            index_from (int): Index of the first newly-completed segment
            index_to (int): Index just past the last newly-completed segment
            duration_sec (float): Wall-clock time spent covering those segments [s]
        """
        num_points = index_to - index_from
        distance = float(np.sum(self.distances_mm[index_from:index_to]))
        # Only the travel part of the duration tells us anything about the stage rate
        travel_time = duration_sec - self.fixed_time_per_point_sec*num_points
        if distance <= 0 or travel_time <= 0: return

        self._travel_time_sec += travel_time
        self._travel_distance_mm += distance
        # A multi-segment update (a skipped/batched point) cannot be split between the groups
        # reliably, so it only feeds the scan-wide rate.
        if num_points == 1:
            entry = self._group_travel.setdefault(self.group_labels[index_from], [0.0, 0.0])
            entry[0] += travel_time
            entry[1] += distance

    def _rate_sec_per_mm(self, label:Hashable) -> float|None:
        """
        Returns the measured travel cost [s/mm] for a segment group, falling back to the scan-wide
        rate while that group has not been travelled yet.

        Args:
            label (Hashable): The segment group label

        Returns:
            float|None: The travel cost in seconds per mm, or None if nothing has been measured yet
        """
        entry = self._group_travel.get(label)
        if entry is not None and entry[1] > 0: return entry[0] / entry[1]
        if self._travel_distance_mm > 0: return self._travel_time_sec / self._travel_distance_mm
        return None

    def _estimate_time_remaining(self, points_done:int, elapsed_sec:float) -> float:
        """
        Estimates the time remaining from the fixed per-point cost of the remaining points plus
        their path length at the measured travel rate.

        Args:
            points_done (int): The number of coordinates measured so far
            elapsed_sec (float): Time elapsed since the start of the scan [s]

        Returns:
            float: The estimated time remaining [s] (0.0 once the scan is complete)
        """
        points_remaining = self.points_total - points_done
        if points_remaining <= 0: return 0.0

        rates = [self._rate_sec_per_mm(label) for label in self.group_labels[points_done:]]
        if all(rate is None for rate in rates):
            # Nothing measured yet (first point, or every move so far was instantaneous): fall back
            # to the known fixed cost, and to the plain per-point average if there isn't one either.
            if self.fixed_time_per_point_sec > 0:
                return self.fixed_time_per_point_sec * points_remaining
            if points_done > 0: return elapsed_sec / points_done * points_remaining
            return 0.0

        travel = sum(
            dist*rate
            for dist, rate in zip(self.distances_mm[points_done:], rates)
            if rate is not None
        )
        return float(travel) + self.fixed_time_per_point_sec*points_remaining


def continuous_group_labels(num_coordinates:int) -> list[str]:
    """
    Builds the segment group labels for a continuous mapping scan, whose moves alternate between
    acquiring a scan line (at the reduced mapping speed) and retracing to the start of the next line
    (at full speed) - see Hilvl_MeasurementAcq_Worker._execute_scan_continuous_step, which arms the
    reduced speed after reaching an even-indexed coordinate and the full speed after an odd-indexed
    one. The move *arriving* at an odd-indexed coordinate is therefore the scan line itself.

    Args:
        num_coordinates (int): The number of scan-line end coordinates in the scan

    Returns:
        list[str]: One label per segment (GROUP_SCANLINE or GROUP_RETRACE)
    """
    return [GROUP_SCANLINE if i%2 else GROUP_RETRACE for i in range(num_coordinates)]
