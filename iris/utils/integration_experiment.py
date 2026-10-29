"""Validation and point-by-point scheduling, independent of Tk and hardware."""

from decimal import Decimal, InvalidOperation
import math


def validate_experiment_settings(times_text, delay_text, limits_us):
    """Return ordered integration times and a nonnegative bleaching delay in ms."""
    minimum, maximum, increment = (Decimal(str(value)) for value in limits_us)
    if not all(value.is_finite() for value in (minimum, maximum, increment)):
        raise ValueError('The spectrometer reported invalid integration time limits.')
    times = []
    for token in times_text.split(','):
        try:
            value = Decimal(token.strip())
        except InvalidOperation:
            raise ValueError('Enter comma-separated positive integration times.') from None
        if not value.is_finite() or value <= 0:
            raise ValueError('Integration times must be finite and greater than zero.')
        microseconds = value * 1000
        if not minimum <= microseconds <= maximum:
            raise ValueError(f'{value} ms is outside the spectrometer range '
                             f'({minimum / 1000} to {maximum / 1000} ms).')
        if microseconds != microseconds.to_integral_value():
            raise ValueError('Integration times must be representable in whole microseconds.')
        # Drivers vary in how they define increments. The acquisition method
        # verifies the device's actual time instead of silently rounding it.
        times.append(float(value))
    try:
        delay = float(delay_text)
    except ValueError:
        raise ValueError('Enter a photobleaching delay of zero or more milliseconds.') from None
    if not math.isfinite(delay) or delay < 0:
        raise ValueError('Photobleaching delay must be finite and zero or greater.')
    return tuple(times), delay


def run_pointwise_experiment(coordinates, integration_times_ms, delay_ms,
                             scan_direction, cancel, move, acquire, store,
                             progress, checkpoint):
    """Run one exposure per time at each point; retain every completed exposure.

    Callbacks raise on failure. ``store`` must finish before returning, so maps
    are safe to checkpoint. Hardware calls finish before honoring cancellation.
    Returns the number of fully completed points.
    """
    completed = 0
    previous_row = None
    row_axis = 1 if scan_direction == 'x-direction' else 0
    try:
        for point_index, coordinate in enumerate(coordinates):
            if cancel.is_set():
                break
            progress(f'Moving to point {point_index + 1} of {len(coordinates)}')
            move(coordinate)
            if cancel.is_set():
                break
            row = round(coordinate[row_axis], 4)
            settle_s = 0.75 if previous_row is None or row != previous_row else 0.2
            progress(f'Settling at point {point_index + 1} of {len(coordinates)}')
            if cancel.wait(settle_s):
                break
            previous_row = row
            if delay_ms:
                progress(f'Photobleaching at point {point_index + 1} of '
                         f'{len(coordinates)}: {delay_ms:g} ms')
                if cancel.wait(delay_ms / 1000):
                    break
            for exposure_index, integration_time in enumerate(integration_times_ms):
                if cancel.is_set():
                    break
                progress(f'Point {point_index + 1} of {len(coordinates)}, '
                         f'exposure {exposure_index + 1} of {len(integration_times_ms)}: '
                         f'{integration_time:g} ms')
                measurement = acquire(integration_time)
                # Store even if Stop was pressed during this exposure.
                store(exposure_index, coordinate, measurement)
            else:
                completed += 1
                checkpoint()
                continue
            break
    finally:
        # Includes a partial final point and results preceding any hardware error.
        checkpoint()
    return completed
