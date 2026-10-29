"""Laser power experiment validation and scheduling; no Tk or device imports."""

import math
from iris.utils.integration_experiment import validate_experiment_settings


def validate_power_experiment(powers_text, integration_text, bleach_power_text,
                              bleach_ms_text, settle_ms_text, limits_us, validate_power):
    times, bleach_ms = validate_experiment_settings(integration_text, bleach_ms_text, limits_us)
    if len(times) != 1:
        raise ValueError('Enter exactly one fixed integration time.')
    powers = tuple(sorted(validate_power(value.strip()) for value in powers_text.split(',')))
    bleach_power = validate_power(bleach_power_text.strip()) if bleach_ms else None
    try:
        settle_ms = float(settle_ms_text)
    except ValueError:
        raise ValueError('Enter a power settling time in milliseconds.') from None
    if not math.isfinite(settle_ms) or settle_ms < 0:
        raise ValueError('Power settling time must be finite and zero or greater.')
    return dict(powers_mw=powers, integration_time_ms=times[0],
                photobleach_power_mw=bleach_power, photobleach_duration_ms=bleach_ms,
                power_settle_ms=settle_ms)


def run_power_experiment(coordinates, powers_mw, bleach_power_mw, bleach_ms,
                         settle_ms, scan_direction, cancel, move, set_power,
                         read_status, acquire, store, progress, checkpoint, power_ready=None):
    """Bleach once per point, then acquire each power at one fixed integration time.

    Set channel 1 to zero before moving, between points, and on completion/Stop.
    This sets a power setpoint; it does not operate a shutter or emission switch.
    Completed exposures are stored even when cancellation arrives during exposure.
    """
    completed = 0
    previous_row = None
    row_axis = 1 if scan_direction == 'x-direction' else 0
    error = None
    try:
        for point_index, coordinate in enumerate(coordinates):
            if cancel.is_set():
                break
            set_power(0)
            if cancel.is_set():
                break
            progress(f'Moving to point {point_index + 1} of {len(coordinates)}')
            move(coordinate)
            row = round(coordinate[row_axis], 4)
            stage_settle = 0.75 if previous_row is None or row != previous_row else 0.2
            if cancel.wait(stage_settle):
                break
            previous_row = row
            if bleach_ms:
                progress(f'Photobleaching point {point_index + 1}: {bleach_power_mw:g} mW, {bleach_ms:g} ms')
                set_power(bleach_power_mw)
                if cancel.wait(settle_ms / 1000):
                    break
                if power_ready is not None:
                    power_ready(bleach_power_mw)
                if cancel.wait(bleach_ms / 1000):
                    break
            for power_index, power in enumerate(powers_mw):
                if cancel.is_set():
                    break
                progress(f'Point {point_index + 1} of {len(coordinates)}, '
                         f'power {power_index + 1} of {len(powers_mw)}: {power:g} mW')
                set_power(power)
                if cancel.wait(settle_ms / 1000):
                    break
                if power_ready is not None:
                    power_ready(power)
                status = read_status()
                if (not status.enabled or not status.channel_setpoints_mw or
                        not math.isclose(status.channel_setpoints_mw[0], power, rel_tol=0, abs_tol=0.00051)):
                    raise RuntimeError('Laser state or channel 1 setpoint changed before acquisition.')
                if cancel.is_set():
                    break
                result = acquire(power)
                store(power_index, coordinate, result, status)
            else:
                completed += 1
                set_power(0)
                checkpoint()
                continue
            break
    except Exception as failure:
        error = failure
    finally:
        try:
            set_power(0)
        except Exception as failure:
            error = RuntimeError(f'{str(error) + "; " if error else ""}'
                                 f'Could not verify channel 1 at 0 mW; laser output may remain on. {failure}')
        try:
            checkpoint()
        except Exception as failure:
            error = RuntimeError(f'{str(error) + "; " if error else ""}Recovery save failed: {failure}')
    if error:
        raise error
    return completed
