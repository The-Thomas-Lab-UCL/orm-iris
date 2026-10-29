"""Map names shared by experiment previews and acquisition runners."""

from collections import Counter
from decimal import Decimal, InvalidOperation
import re


def build_integration_map_names(experiment_name, integration_times_text, existing_names=()):
    """Return ordered map names with a unique coordinate-name suffix per run.

    Repeated integration times use ``_repeat2``, ``_repeat3``, etc. Existing
    names are compared without case to match Windows filename behavior. If any
    output name is occupied, use coordinate_1, coordinate_2, etc. for the whole
    run, so all its integration-time maps stay grouped together.
    This does not reserve names or check files in an export directory.
    """
    return _build_map_names(experiment_name, integration_times_text, existing_names, 'ms', False)


def build_power_map_names(coordinate_name, powers_mw, existing_names=()):
    """Name each power entry, including repeated values and zero-power entries."""
    return _build_map_names(coordinate_name, ','.join(str(power) for power in powers_mw),
                            existing_names, 'mW', True)


def _build_map_names(experiment_name, values_text, existing_names, unit, allow_zero):
    experiment_name = experiment_name.strip()
    if not experiment_name or experiment_name in ('.', '..'):
        raise ValueError('The selected coordinate set needs a name.')
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', experiment_name) or experiment_name.endswith('.'):
        raise ValueError('Use a coordinate set name without filename punctuation or a trailing dot.')

    counts = Counter()
    suffixes = []
    existing = {name.casefold() for name in existing_names}
    for token in values_text.split(','):
        try:
            integration_time = Decimal(token.strip())
        except InvalidOperation:
            raise ValueError('Enter comma-separated numeric experiment values.') from None
        if not integration_time.is_finite() or integration_time < 0 or (integration_time == 0 and not allow_zero):
            raise ValueError('Experiment values must be finite and positive (power may be zero).')
        # Bound decimal expansion before formatting a potentially large exponent.
        if integration_time.adjusted() > 12 or integration_time.as_tuple().exponent < -12:
            raise ValueError('Integration time is too large or has too many decimal places.')
        time_label = format(integration_time, 'f')
        if integration_time == 0:
            time_label = '0'
        if '.' in time_label:
            time_label = time_label.rstrip('0').rstrip('.')
        counts[time_label] += 1
        repeat = '' if counts[time_label] == 1 else f'_repeat{counts[time_label]}'
        suffixes.append(f'{time_label}{unit}{repeat}')
    run_index = 0
    while True:
        run_name = experiment_name if run_index == 0 else f'{experiment_name}_{run_index}'
        names = [f'{run_name}_{suffix}' for suffix in suffixes]
        if any(len(name) > 200 for name in names):
            raise ValueError('Use a shorter coordinate set name (map names must be at most 200 characters).')
        if run_name.casefold() not in existing and not any(name.casefold() in existing for name in names):
            return names
        run_index += 1
