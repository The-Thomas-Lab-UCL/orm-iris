"""Monotonic stage timing and post-scan reports; no disk writes per point."""
import csv
import json
from pathlib import Path
import statistics
import time


class StageTimer:
    def __init__(self, data=None, clock=None):
        self.data = data if data is not None else {}
        self.clock = clock or time.perf_counter
        self.start = self.last = self.clock()

    def mark(self, name):
        now = self.clock()
        self.data[name] = self.data.get(name, 0.) + (now-self.last)*1000
        self.last = now

    def finish(self):
        self.mark('unclassified_ms')
        self.data['total_ms'] = (self.last-self.start)*1000
        return self.data


def _summary(records):
    result = {}
    keys = sorted({key for row in records for key, value in row.items()
                   if key.endswith('_ms') and isinstance(value, (int, float))})
    for key in keys:
        values = [row[key] for row in records if key in row and isinstance(row[key], (int, float))]
        result[key] = dict(count=len(values), mean_ms=statistics.mean(values),
                           median_ms=statistics.median(values), max_ms=max(values))
    return result


def write_scan_timing(folder, records):
    """Write once after scanning. Nested acquisition stages overlap their parent."""
    folder = Path(folder)
    completed = [row for row in records if row.get('complete')]
    report = dict(format='iris-scan-timing-v1', attempted_points=len(records), completed_points=len(completed),
                  notes=[
                      'Monotonic wall-clock timings. Acquisition child fields are INCLUDED in acquisition_ms; do not add both.',
                      'fetch_ms includes device_call_ms and calibration_ms; total fields include their children.',
                      'device_call_ms includes exposure, device readout and controller IPC; calibration_ms is separate.',
                      'expected_integration_ms comes from device metadata, not a measured exposure trigger.',
                      'ui_ms measures synchronous UI calls and scheduling, not all asynchronous rendering.',
                      'Recovery disk writes and final snapshot time are outside per-point totals.',
                      'Only completed points enter summary statistics; partial attempts remain in the CSV.'
                  ], summary=_summary(completed),
                  first_point=completed[0] if completed else None,
                  last_point=completed[-1] if completed else None)
    fields = ['index', 'x_mm', 'y_mm', 'z_mm', 'complete']
    fields += sorted({key for row in records for key in row if key not in fields})
    with (folder / 'scan_timing.csv').open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    (folder / 'scan_timing.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    lines = [f'Scan timing: {len(completed)} complete / {len(records)} attempted points',
             'All values below are averages in milliseconds.', '', 'Whole-point stages:']
    summary = report['summary']
    for key in ('total_ms', 'expected_integration_ms', 'overhead_ms', 'buffer_wait_ms', 'preparation_ms',
                'motion_ms', 'settling_ms', 'acquisition_ms', 'result_enqueue_ms', 'ui_ms', 'unclassified_ms'):
        if key in summary:
            lines.append(f"  {key}: {summary[key]['mean_ms']:.3f}")
    lines += ['', 'Inside acquisition_ms (already included above; do not add twice):']
    for key in sorted(summary):
        if key.startswith('acquisition_') and key != 'acquisition_ms':
            lines.append(f"  {key}: {summary[key]['mean_ms']:.3f}")
    lines += ['', *report['notes']]
    (folder / 'scan_timing.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return folder / 'scan_timing.txt'
