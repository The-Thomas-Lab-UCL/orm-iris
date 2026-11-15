# Acquisition recovery autosave

Maps, integration-time/laser-power experiments, and standalone Single measurement acquisitions provisionally autosave to
`autosave/` inside the application repository. This is a persistent folder, not
the Windows temporary directory. Its absolute location is based on the program
files, so starting IRIS from a different working directory does not change it.
The folder is excluded from Git, and restarting IRIS does not delete its files.

Use **Data Hubs ? Choose autosave data folder** to select a permanent data folder,
including a Desktop folder if preferred. Cancelling the chooser keeps the current
folder. Your selected destination applies to subsequent runs for this app session;
existing runs retain their original recovery folder. After restarting, IRIS uses
the provisional folder again until another destination is chosen. Prefer a local
SSD; network or removable drives can introduce delays or become unavailable.
If the recovery folder cannot be created or written, the scan does not start.

Each run gets a unique subfolder. Completed spectra, coordinates, raw exposures,
averages and measurement metadata are queued individually. A background writer
commits new records to a `.iris-autosave` recovery journal every **20 seconds**.
It never traverses or copies the growing map between scan points. Stop, normal
completion and handled acquisition errors flush pending records. The legacy
`autosave_interval_hours` setting no longer controls map/experiment recovery.
Standalone **Single measurement** acquisitions use a `single_acquisition_...`
subfolder. Each completed exposure is queued individually, including exposures
collected before Stop or a device error. A long accumulation is protected by the
same 20-second commits; stop/completion flushes the remainder. Incomplete exposures
cannot be saved. On recovery, the saved exposures are combined into one measurement
with all raw exposures, their average, and the saved accumulation count. Standalone
spectra have no recorded stage position and use the Data Hub's existing zero-coordinate
convention. Mapping spectra use the map's own recovery journal, avoiding duplicate
standalone saves.

The Data Hub displays committed/queued counts and write errors. A crash can lose
records since the last successful commit: normally up to about 20 seconds, or
roughly 4–10 spectra at a 2–5 second cadence. Slow or failed storage can increase
that window. Storage failures or queue overflow stop acquisition through the
existing scan error handling; acquired data stays in memory for manual export.

Use **Recover autosaved data** and select a trusted `.iris-autosave` file from a
run folder. Recovery imports distinct maps with `_recovered` names; it never
overwrites a map already in the Data Hub. Only committed spectra are restored.
Keep the entire run folder, including any SQLite journal and experiment quality
logs left after a crash. Recovery files use Python serialization: open only
files created by IRIS that you trust. Recovery restores data, not an automatic
resumption of stage movement or laser commands.

Existing `.db` exports and companion Parquet files retain their original schema.
Recovery files are separate and do not belong in the normal `.db` loader. After
recovery, **Save Mapping Hub [.db]** exports the maps normally. Raw spectra and
metadata are preserved. The original `maps.pkl` recovery snapshot is also written
once after scanning stops, rather than after every experiment point. This final
flush/snapshot can take time after the final exposure.

## Performance verification

Run `python tests/benchmark_recovery.py` in the repository environment. The
hardware-free benchmark captures 2,000 spectra of 2,048 pixels each, with one raw
exposure per spectrum, while committing every 50 ms to exercise concurrent disk
writes. Production commits remain 20 seconds apart.

On this development machine, capture/enqueue overhead measured 37.5 microseconds
median and 67.1 microseconds at the 95th percentile. Medians for the first and last
100 spectra were 47.75 and 37.6 microseconds. All 2,000 records were committed;
the final post-acquisition flush took 0.42 seconds. These measurements isolate
new autosave capture/enqueue work; they do not measure full device scan timing.

Before lab use, compare repeated identical scans on the actual acquisition PC,
using a local drive and the same integration times, map sizes and accumulation
counts. Compare exposure start intervals and total acquisition time as maps grow.
Background disk I/O still shares CPU, memory and storage resources, so zero impact
on every machine or drive cannot be guaranteed.
## 30,000-spectrum validation

A paired accelerated test is available:

```powershell
.venv\Scripts\python.exe tests/stress_recovery.py --spectra 30000 --pixels 2048 --accumulations 1 --folder temp
```

`--folder` selects an existing folder on the drive being evaluated. The script
creates and deletes its own temporary directory there; it does not modify the
real autosave folder. It checks free space before starting and reserves 2 GiB
while running. The small report remains at `temp/autosave_30000_report.json`.
The baseline and autosave phases retain independent spectral arrays in the real
map class, so this also exercises the growing in-memory dataset. The test checks
committed row counts and SQLite integrity. The final recovery snapshot is included.

Measured on this development machine with 30,000 spectra, 2,048 pixels and one
raw exposure per spectrum:

| Measurement | Result |
| --- | --- |
| Saved records | 30,000 / 30,000; SQLite integrity OK |
| Journal | 2.03 GB (1.89 GiB) |
| Post-scan `maps.pkl` snapshot | 1.98 GB (1.84 GiB) |
| Combined recovery files | 4.01 GB (3.73 GiB), excluding manual exports |
| Sampled resident memory during autosave acquisition | Up to 2.21 GiB |
| Maximum uncommitted records observed | 39; no sustained backlog growth |
| Median capture/enqueue time | 0.074 ms |
| Median total data handling, autosave off / on | 0.392 / 0.635 ms per point |
| Acquisition-loop wall time, autosave off / on | 72.35 / 71.71 seconds |
| Final post-scan snapshot | 18.21 seconds |

The simulated 2-second cadence and 20-second commit interval were accelerated
1,000 times together: actual targets were 2 ms and 20 ms. This produces much more
frequent disk activity than a real scan. The similar loop durations in one paired
run do not prove zero overhead: scheduling, cache state and occasional pauses
vary, and the processing measurements show additional CPU work. Both phases show
increasing map-handling costs as the dataset grows. The test excludes GUI plots,
hardware, motion and bleaching. Memory can grow further during the final deep
copy and serialization; the reported memory samples cover acquisition only.
The roughly 4 GB storage result applies to these dimensions and accumulation
count. More pixels or raw exposures require more space, and final `.db`/Parquet
exports require additional space. Files from multiple scans continue accumulating
until they are archived or removed.

For a time-based soak at the production interval, use the following with the
correct pixel count and acquisition settings:

```powershell
.venv\Scripts\python.exe tests/stress_recovery.py --phase autosave --spectra 30000 --cadence-s 2 --speedup 1 --folder temp --report temp/autosave_soak_report.json
```

That simulated soak takes at least 16 hours 40 minutes, or about 41 hours 40 minutes
with `--cadence-s 5`. It still does not exercise hardware or GUI timing. For a lab
validation, run the usual scan with the same coordinates, exposure/accumulation
settings, plotting and storage destination. Compare the first, middle and last
1,000 records, checking that committed counts catch up and data is complete. The
following reads saved timestamps without loading the spectral arrays:

```powershell
.venv\Scripts\python.exe tests/inspect_recovery_timing.py "path\to\recovery_file.iris-autosave"
```

Use it after the scan has stopped. Its intervals include motion, exposures,
bleaching and user pauses; changing any of those confounds comparisons. Comparing
repeated identical scans is necessary before attributing timing changes to
storage. Review the space available on the actual target drive before a long run.

Disk-full behavior is tested without filling the physical disk: the recovery
regression test caps SQLite's page count, confirms a real `SQLITE_FULL` error,
and verifies that the previous committed batch remains recoverable. Separate
blocked-writer and overflow tests check that storage lag is detected instead of
silently dropping spectra.

## Managing disk space

Restart IRIS after installing this update, then open **Data Hubs → Manage autosave
storage**. The window uses the currently selected data folder, or the provisional
repository `autosave/` folder. It lists recognized recovery run folders by modified
date (UTC), size and status, with the drive's current free space. Listing and file
removal run in background workers.

1. Export any dataset you want to keep, and verify that it reopens correctly.
2. Select inactive recovery runs with Ctrl/Shift in the cleanup window.
3. Click **Delete selected recovery copies** and confirm the named selection.
4. The list and free-space information refresh after deletion.

Deletion is permanent and always manual. Inactive does not mean exported or
verified. The application does not automatically delete runs based on age, and it
does not treat an autosave as a final export. Current runs remain protected through
the final snapshot and timing report. A file lock also protects runs written by
another updated IRIS process and is released by the OS after a crash. Close older
IRIS versions before managing older recovery folders, because those versions did
not hold these locks.

Only recognized, flat recovery run folders under the selected data folder are
eligible. Folders with links, subfolders, `.db`/Parquet exports, unexpected files,
or unreadable contents are protected for manual inspection. Loose files in the
selected data folder, including older autosave `.db` files, are left untouched.
The selected folder itself is retained.

IRIS warns before starting a run if free space is below **10 GiB or 5% of the
drive's capacity**, whichever threshold is larger. The warning appears once per
data folder per app session. The background writer checks space at startup and
before data commits, with a red low-space indication in the Data Hub. These checks
do not add disk queries between spectra or change stage settling. Warnings do not
pause a running scan; existing write-failure handling still stops acquisition if
saving fails. Changing folders affects subsequent runs, not the current run.

The displayed free space is not a guarantee that a scan will fit: accumulation
count, pixel count, final recovery snapshots and manual exports all consume space.
Plan for the complete dataset and exports, not just the incremental journal.
