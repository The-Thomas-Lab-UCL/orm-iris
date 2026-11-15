# Measuring discrete-map acquisition overhead

Restart IRIS to load the updated code, then run a short **standard discrete map**
with 50–100 points across at least two rows. Use the same integration time,
accumulation count, plotting options and stage step size as the scan that showed
about 0.9 seconds of overhead. Leave autosave enabled and keep the normal settling
delays. No diagnostic setting needs to be switched on.

After completion or Stop, the completion dialog and console show the path to
`scan_timing.txt` in that run's `mapping_recovery_...` subfolder. By default that
is under the repository's `autosave/` folder; a selected data folder takes
precedence. Also saved there:

- `scan_timing.txt`: readable averages for the timing breakdown.
- `scan_timing.csv`: point-by-point measurements, coordinates and completion state.
- `scan_timing.json`: mean, median and maximum timings, plus first/last point data.

The measurements use a monotonic clock and are kept in memory during acquisition.
The timing files are written once, after scan cleanup. Timings are collected for
standard discrete maps; continuous maps and integration/power experiment loops
do not yet write these per-point reports.

## Reading the results

All durations are milliseconds. Divide by 1,000 for seconds.

`total_ms` measures one point through the scan loop, including motion, settling,
waiting for acquisition, queuing its result and synchronous UI work.
`expected_integration_ms` is the integration time reported by the device multiplied
by the completed accumulation count. `overhead_ms` is their difference. It is an
estimate of non-integration time, not a direct measurement of the exposure trigger.

The top-level breakdown includes buffer waiting, preparation, movement, settling,
acquisition, queuing and UI/status bookkeeping. Inside `acquisition_ms`, child
measurements show:

- `setup_ms`: pausing automatic collection, setting integration time and preparation.
- `device_call_ms`: the exposure/readout/controller call, including any controller IPC.
- `calibration_ms`: sending the spectrum for calibration and waiting for its return.
- `plot_wait_ms`: waiting for the preliminary background plot to finish.
- `final_analysis_ms`: the final averaging/analysis call.
- `final_plot_ms`: the existing final averaging-and-plotting function, including its internal averaging.
- Dispatch, result-return and cleanup timings for the remaining acquisition work.

Acquisition child timings already belong to `acquisition_ms`; do not add them to
that parent again. `fetch_ms` contains `device_call_ms` and `calibration_ms`, and
`acquisition_total_ms` contains the worker's stages. Background rendering that
already overlapped exposure is not all counted as blocked plotting time. UI timings
measure synchronous calls and scheduling, not every asynchronous screen refresh.

The first point and row changes currently have a 0.75-second settling delay;
other points normally have 0.2 seconds. Use the CSV to distinguish those cases.
The device call cannot distinguish physical integration from SDK readout internally;
comparing it with expected integration can suggest readout overhead but is not a
hardware-trigger timing measurement.

Rows interrupted by Stop/errors remain in the CSV but are excluded from complete-
point averages. Diagnostic-write errors are reported in the console and do not
replace the acquisition error or prevent the existing recovery cleanup. Final disk
flushes and the recovery snapshot occur outside point timings.

Provide `scan_timing.txt` and, if possible, the CSV from the short hardware run.
The next optimization can then target measured time, such as synchronous plotting,
without guessing or changing stage settling prematurely.

## Asynchronous display during discrete maps

Standard discrete maps now retain the completed, calibrated and averaged
measurement before queuing a display request. The scan does not wait for raw or
averaged plot rendering, and it does not generate the duplicate final raw redraw.
A separate Tk polling path starts at most one live render per second and keeps
only the newest pending display request. Every acquired spectrum still passes
through the normal coordinate association, data hub and autosave paths; only
intermediate screen refreshes may be skipped.

The raw-only checkbox is evaluated when rendering begins. An older averaged render
is discarded if the checkbox changes before it is displayed. Rendering an older
frame does not replace the current acquisition's stored single measurement.
Standalone Single measurement acquisitions keep their existing progress display.
Integration/power experiments retain their existing asynchronous display path.

In new discrete-map timing reports, `final_plot_ms` should be zero and
`plot_wait_ms` should be negligible. `display_enqueue_ms` measures the small cost
of handing the completed measurement to the display mailbox. Plot rendering now
happens outside per-point acquisition timings; this does not mean rendering has
no CPU or disk/memory bandwidth cost.

No stage commands, 0.5-second PFM450 waits, 0.2-second point settling, 0.75-second
row settling, exposure ordering or calibration ordering were changed. Before lab
acceptance, repeat the same 100-point map with the same settings, compare the new
timing report, confirm the full spectrum count, and inspect the map for stripes
and coordinate alignment. The earlier hardware report's approximately 92 ms of
plot waits is an optimization opportunity, not a guaranteed measured saving on
the updated hardware run.
