"""Hardware-free autosave overhead benchmark; run from the repository root.

Uses a 50 ms commit interval to exercise disk writes during the measurement loop,
rather than waiting for the production 20-second timer. Results measure the
additional spectrum capture/enqueue work, not real device or full scan timing.
"""
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_integration_experiment as fixture
from iris.data.measurement_Raman import MeaRaman
from iris import DataAnalysisConfigEnum as Labels
from iris.utils.recovery_journal import RecoveryWriter
import numpy as np
import pandas as pd


def main():
    count, pixels = 2000, 2048
    measurement = MeaRaman(timestamp=1, int_time_ms=2000., laserPower_mW=10., laserWavelength_nm=785.)
    measurement.set_raw_list(pd.DataFrame({Labels.WAVELENGTH_LABEL.value: np.linspace(400., 1000., pixels),
                                          Labels.INTENSITY_LABEL.value: np.ones(pixels)}))
    measurement.check_uptodate()
    unit = fixture.MeaRMap_Unit('benchmark')
    timings = []
    with tempfile.TemporaryDirectory() as folder:
        writer = RecoveryWriter(folder, interval_s=.05)
        try:
            for timestamp in range(1, count+1):
                unit.append_ramanmeasurement_data(timestamp, (float(timestamp), 0., 0.), measurement)
                start = time.perf_counter_ns()
                writer.submit(unit, timestamp, (float(timestamp), 0., 0.), measurement)
                timings.append((time.perf_counter_ns()-start)/1000)
        finally:
            finish = time.perf_counter()
            writer.close()
            final_flush_s = time.perf_counter()-finish
        result = dict(spectra=count, pixels=pixels, accumulations=1, benchmark_commit_interval_s=.05,
                      production_commit_interval_s=20, median_enqueue_us=float(np.median(timings)),
                      p95_enqueue_us=float(np.percentile(timings, 95)),
                      first_100_median_us=float(np.median(timings[:100])),
                      last_100_median_us=float(np.median(timings[-100:])),
                      final_flush_s=final_flush_s, committed=writer.status()['committed'])
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
