"""Paired large-map stress test using simulated spectra and the actual data classes.

No hardware is accessed. Large recovery files live in an owned temporary folder
and are removed afterwards; a small JSON report is retained. Accelerated cadence
and commit intervals are scaled together. This measures data handling, not full
hardware scan timing or a multi-hour soak test.
"""
import argparse
from contextlib import closing
import ctypes
import gc
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_integration_experiment as fixture
from iris import DataAnalysisConfigEnum as Labels
from iris.data.measurement_Raman import MeaRaman
from iris.utils.recovery_journal import RecoveryWriter
import numpy as np
import pandas as pd


GIB = 2**30


def resident_mib():
    if sys.platform != 'win32':
        return None
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ('peak', 'working', 'peak_paged', 'paged',
                                               'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile')]
    data = Counters()
    data.cb = ctypes.sizeof(data)
    if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(data), data.cb):
        return data.working / 2**20
    return None


def latency(values):
    values = np.asarray(values) / 1e6
    return dict(median_ms=float(np.median(values)), p95_ms=float(np.percentile(values, 95)),
                p99_ms=float(np.percentile(values, 99)), max_ms=float(np.max(values)))


def folder_bytes(folder):
    total = 0
    for path in Path(folder).rglob('*'):
        try:
            if path.is_file():
                total += path.stat().st_size
        except FileNotFoundError:
            # SQLite removes its temporary rollback journal after each commit.
            pass
    return total


def run_phase(args, folder, enabled, reserve_bytes):
    rng = np.random.default_rng(20261114)
    wavelengths = np.linspace(400., 1000., args.pixels)
    unit = fixture.MeaRMap_Unit('stress_test')
    writer = RecoveryWriter(folder, interval_s=20/args.speedup) if enabled else None
    cadence = args.cadence_s / args.speedup
    processing, enqueue, gaps, samples = [], [], [], []
    max_backlog, last_start, high_rss = 0, None, 0
    elapsed_start, cpu_start = time.perf_counter(), time.process_time()
    try:
        for i in range(args.spectra):
            point_start = time.perf_counter_ns()
            if last_start is not None:
                gaps.append(point_start-last_start)
            last_start = point_start
            measurement = MeaRaman(timestamp=i+1, int_time_ms=args.cadence_s*1000,
                                   laserPower_mW=10., laserWavelength_nm=785.)
            for _ in range(args.accumulations):
                # Independent arrays per point, unlike a repeated reference to one spectrum.
                measurement.set_raw_list(pd.DataFrame({Labels.WAVELENGTH_LABEL.value: wavelengths.copy(),
                    Labels.INTENSITY_LABEL.value: rng.poisson(100, args.pixels).astype(float)}))
            measurement.check_uptodate()
            coordinate = (float(i % 200), float(i // 200), 0.)
            unit.append_ramanmeasurement_data(i+1, coordinate, measurement)
            if writer is not None:
                capture_start = time.perf_counter_ns()
                writer.submit(unit, i+1, coordinate, measurement)
                enqueue.append(time.perf_counter_ns()-capture_start)
                state = writer.status()
                max_backlog = max(max_backlog, state['accepted']-state['committed'])
            processing.append(time.perf_counter_ns()-point_start)
            if (i+1) % args.sample_every == 0 or i+1 == args.spectra:
                free = shutil.disk_usage(folder).free
                if free < reserve_bytes:
                    raise RuntimeError('Stress test stopped before consuming the reserved free disk space.')
                rss = resident_mib()
                high_rss = max(high_rss, rss or 0)
                state = writer.status() if writer else dict(accepted=0, committed=0)
                sample = dict(points=i+1, journal_bytes=folder_bytes(folder),
                              committed=state['committed'], backlog=state['accepted']-state['committed'],
                              resident_mib=rss, processing=latency(processing[-args.sample_every:]))
                samples.append(sample)
                print(json.dumps(dict(phase='autosave' if enabled else 'baseline', **sample)), flush=True)
            remaining = cadence - (time.perf_counter_ns()-point_start)/1e9
            if remaining > 0:
                time.sleep(remaining)
        scan_elapsed = time.perf_counter()-elapsed_start
        scan_cpu = time.process_time()-cpu_start
    finally:
        finish_start = time.perf_counter()
        if writer is not None:
            writer.close(timeout=120)
        flush_s = time.perf_counter()-finish_start
    result = dict(phase='autosave' if enabled else 'baseline', points=args.spectra,
                  acquisition_loop_s=scan_elapsed, process_cpu_s=scan_cpu,
                  processing=latency(processing), first_block=latency(processing[:args.sample_every]),
                  last_block=latency(processing[-args.sample_every:]), actual_start_intervals=latency(gaps),
                  deadline_overruns=sum(value/1e9 > cadence for value in processing),
                  peak_sampled_resident_mib=high_rss, max_uncommitted_records=max_backlog,
                  final_flush_s=flush_s, samples=samples)
    if writer:
        import sqlite3
        with closing(sqlite3.connect(writer.path)) as connection:
            rows = connection.execute('SELECT COUNT(*) FROM spectra').fetchone()[0]
            integrity = connection.execute('PRAGMA integrity_check').fetchone()[0]
        if rows != args.spectra or integrity != 'ok':
            raise RuntimeError(f'Recovery verification failed: {rows} rows, integrity {integrity}.')
        result.update(enqueue=latency(enqueue), committed=rows, integrity=integrity,
                      journal_bytes=writer.path.stat().st_size,
                      bytes_per_spectrum=writer.path.stat().st_size/args.spectra)
        if not args.skip_final_snapshot:
            snapshot_start = time.perf_counter()
            snapshot = fixture.MeaRMap_Hub()
            snapshot.append_mapping_unit(unit.copy(flg_newID=False))
            with open(Path(folder) / 'maps.pkl', 'wb') as output:
                fixture.dill.dump(snapshot, output)
            result['post_scan_snapshot_s'] = time.perf_counter()-snapshot_start
            result['snapshot_bytes'] = (Path(folder) / 'maps.pkl').stat().st_size
            del snapshot
        result['total_recovery_bytes'] = folder_bytes(folder)
    del unit, measurement, writer
    gc.collect()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spectra', type=int, default=30000)
    parser.add_argument('--pixels', type=int, default=2048)
    parser.add_argument('--accumulations', type=int, default=1)
    parser.add_argument('--cadence-s', type=float, default=2)
    parser.add_argument('--speedup', type=float, default=1000)
    parser.add_argument('--sample-every', type=int, default=1000)
    parser.add_argument('--folder', type=Path, help='Existing folder on the drive to benchmark.')
    parser.add_argument('--report', type=Path, default=Path('temp/autosave_30000_report.json'))
    parser.add_argument('--skip-final-snapshot', action='store_true')
    parser.add_argument('--phase', choices=('both', 'baseline', 'autosave'), default='both')
    args = parser.parse_args()
    if min(args.spectra, args.pixels, args.accumulations, args.cadence_s, args.speedup, args.sample_every) <= 0 or args.spectra < 2:
        parser.error('Use positive values and at least two spectra.')
    if args.folder is not None and not args.folder.is_dir():
        parser.error('--folder must be an existing folder.')
    estimated_recovery = args.spectra*(args.pixels*16*(args.accumulations+1)+4096)*2.5
    reserve_bytes = 2*GIB
    with tempfile.TemporaryDirectory(prefix='iris_autosave_stress_', dir=args.folder) as folder:
        initial_free = shutil.disk_usage(folder).free
        if initial_free < estimated_recovery+reserve_bytes:
            parser.error(f'Insufficient free space: estimated {estimated_recovery/GIB:.1f} GiB plus 2 GiB reserve required.')
        result = dict(settings={key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
                      initial_free_bytes=initial_free, estimated_recovery_bytes=estimated_recovery,
                      hardware_test=False, notes='Accelerated data-handling stress test; no camera, GUI, stage or spectrometer timing.')
        print(json.dumps(dict(estimated_recovery_GiB=estimated_recovery/GIB, free_GiB=initial_free/GIB)), flush=True)
        for phase in ('baseline', 'autosave'):
            if args.phase in ('both', phase):
                result[phase] = run_phase(args, folder, phase == 'autosave', reserve_bytes)
        if args.phase == 'both':
            result['acquisition_loop_change_percent'] = (
                result['autosave']['acquisition_loop_s']/result['baseline']['acquisition_loop_s']-1)*100
            result['added_median_processing_ms'] = (result['autosave']['processing']['median_ms']-
                                                    result['baseline']['processing']['median_ms'])
        result['temporary_files_deleted_after_test'] = True
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(dict(report=str(args.report.resolve()),
                         baseline_s=result.get('baseline', {}).get('acquisition_loop_s'),
                         autosave_s=result.get('autosave', {}).get('acquisition_loop_s'),
                         change_percent=result.get('acquisition_loop_change_percent'),
                         added_median_processing_ms=result.get('added_median_processing_ms'),
                         recovery_GiB=result.get('autosave', {}).get('total_recovery_bytes', 0)/GIB)), flush=True)


if __name__ == '__main__':
    main()
