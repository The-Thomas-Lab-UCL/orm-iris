# Upstream IRIS review

Initial upstream review: October 29, 2026. The baseline comparison below
records the repository before backports. The first Zaber backport has since
passed the lab hardware check and was merged into `albro-lab` as `1885c01`.
A second candidate is being prepared separately below.

The current lab baseline is `albro-lab` at `0c06f42`. The working branch is
`albro-lab-updates` at the same commit. Latest fetched upstream `main` is
[`27ae597`](https://github.com/The-Thomas-Lab-UCL/orm-iris/commit/27ae597f48daa25786d54b1dce7cb24eafe890cd),
dated October 15, 2026, and declares version 1.1.6. Our package declares 1.0.0.
The branches share baseline `bb8af97`; upstream has 362 additional commits and
the lab branch has four commits not present upstream. Upstream changes span
272 files, including generated documentation and UI resources.

**Recommendation: keep the hardware-tested lab program as the operational
version, backport selected reliability fixes, and assess a full Qt migration
in a separate checkout and environment.** A direct pull or merge is not a
routine version update.

| Upstream development | Practical benefit | Assessment for the lab |
| --- | --- | --- |
| Full PySide6 UI rewrite, merged January 14, 2026 ([PR #17](https://github.com/The-Thomas-Lab-UCL/orm-iris/pull/17)) | New UI framework, Qt workers/signals, designer resources, revised plot and window handling | Largest migration task. Our Tkinter experiment tabs and Laser tab require a Qt implementation. Upstream deletes `iris/__main__.py`, changes the application entry point, and renames the main UI classes. |
| Zaber communication-error handling ([`a3ab724`](https://github.com/The-Thomas-Lab-UCL/orm-iris/commit/a3ab72405fae1cddc72b8f49eb959c4efe2bca9f)) | Converts SDK exceptions into exceptions that survive multiprocessing transport; resets movement flags after failed moves | Best first backport candidate for our Zaber XY stage. Adapt the controller changes selectively; the same upstream commit also changes the Qt motion UI. Preserve our original local Zaber modifications. |
| Mapping-stall fixes ([`26a8fa4`](https://github.com/The-Thomas-Lab-UCL/orm-iris/commit/26a8fa4906030116bb6311e63bd052c3cfc96f72), [PR #110](https://github.com/The-Thomas-Lab-UCL/orm-iris/pull/110)) | Addresses silent continuous-map stalls and adds timeout/stall handling | Useful, especially for standard continuous mapping. Much of the implementation uses the new Qt workers, so port the relevant behavior rather than copying whole files. |
| Stage direction and speed restoration ([`39135ea`](https://github.com/The-Thomas-Lab-UCL/orm-iris/commit/39135eab1e801bc80a90e61c10037ada0e6db459)) | Adds Z inversion support and restores stage speed after stopping a scan | Review with the existing PFM450 direction configuration before applying. |
| Andor controller development | Adds readout-mode/track controls, throughput changes, temperature/shutdown handling and SIF support | Relevant to the configured Andor spectrometer, but changes acquisition behavior. One [orientation change](https://github.com/The-Thomas-Lab-UCL/orm-iris/commit/c8c7316456ed822a71b692f1118094f38664214a) flips the FVB spectrum. Verify spectrum orientation, wavelength calibration, integration timing and shutdown behavior before adopting. |
| Data storage and loading | Adds partial loading, individual-map DB loading, memory/offload work, metadata support and additional locking | Valuable for large maps. The map/data APIs have changed significantly. Test old lab datasets, new exports, and recovery files before replacing the storage layer. See [individual-map loader](https://github.com/The-Thomas-Lab-UCL/orm-iris/commit/8056ee5). |
| Thorlabs camera and heatmap updates ([PR #114](https://github.com/The-Thomas-Lab-UCL/orm-iris/pull/114)) | Revised camera controls and automatically sized heatmap markers | Relevant to the configured Thorlabs camera; benefits depend on the newer camera interface and Qt display code. |
| Autofocus, coordinate modifiers and SERS tooling | Adds focus-related coordinate operations, resolution adjustment and SERS coordinate-generation tools | Optional capabilities to evaluate after the core acquisition workflow is stable. |

The configured hardware in local `config.ini` is `thorlabs_mono`, `andor`,
`zaber`, and `pfm450`. The laser integration remains our lab addition.

Our features to preserve are the integration-time experiment; laser-power
experiment; independent bleaching power/duration; point-first acquisition;
serial-bound 120/250 mW profiles and power limits; live spectra; repeat-run
names; partial-result recovery; and background laser monitoring with coverage
and fault logs.

The new laser controller and acquisition/monitoring helpers can largely be
reused in a Qt migration. The Tkinter UI wiring, widget state management,
callbacks, startup integration, and tests that instantiate those interfaces
need adaptation. The upstream entry point does not automatically register our
Laser tab or experiment controls just because their files remain in Git.

A `git merge-tree --write-tree --name-only albro-lab origin/main` simulation
reported conflicts in these eight paths without changing the checkout:

- `iris/__main__.py` (modified in the lab; deleted upstream)
- `iris/controllers/raman_spectrometer_controller_dummy.py`
- `iris/controllers/xy_stage_controller_zaber.py`
- `iris/gui/hilvl_Raman.py`
- `iris/gui/motion_video.py`
- `iris/gui/raman.py`
- `main_controller.py`
- `pyproject.toml`

Files that merge without textual conflicts still need compatibility review:
upstream changes map metadata, measurement storage, streamers, calibration,
controller interfaces, and dependencies. Resolving these eight conflicts is
not enough to establish a functioning application.

For a full upgrade, first create a separate worktree from the pinned upstream
commit and use its own virtual environment, config, and test output folders.
Validate upstream in simulation, port the lab features, adapt and run the lab
tests, then check saved-data compatibility. Follow with the same small hardware
and polystyrene checks used for the current lab version. Keep the operational
`albro-lab` branch available until the candidate has passed those checks.

For a smaller update, begin a dedicated branch from `albro-lab` and backport
the Zaber exception/cleanup behavior with simulated failure tests. Evaluate
mapping-stall and Andor changes as separate changes so each hardware behavior
can be reviewed and tested independently.

During the initial review, only remote history was fetched and a merge simulated.
No package installation, application launch, hardware operation, branch merge,
or push was performed. Existing lab tests previously passed (71 tests); they
have not been ported to or run against upstream's Qt application.

## First update candidate: Zaber controller error recovery

Prepared on `albro-update-review` from the existing `albro-lab` baseline.
The controller helper and five movement methods were backported from upstream
`a3ab72405fae1cddc72b8f49eb959c4efe2bca9f`. This preserves the controller's
other methods, axis remapping, movement speeds and command/wait behavior.

The changes reset software movement flags when finite moves, homing, jogging
or stopping fail; preserve the running flag during successful continuous motion;
and translate Zaber SDK movement exceptions into serializable RuntimeErrors.
This prevents an SDK exception's constructor from masking the device error
when it is passed through a multiprocessing-manager connection.

The Qt-specific motion-worker arrival checks from that upstream commit are not
part of this candidate. Mapping-stall handling, Andor updates, autofocus and the
Qt migration remain separate steps. The new experiment runner already propagates
stage errors using futures and retains results acquired before the failure.

Validation: 82 tests passed, including 11 new Zaber tests covering successful
motion parameters, axis remapping, rejected commands, failures during waiting,
lock/flag cleanup, subsequent requests and exception serialization. All device
calls in those tests were mocked; no serial port was opened, no stage was moved,
and neither laser was operated.

The lab subsequently reported that the hardware check was working. This
backport was then merged and pushed to both `albro-lab` and
`albro-lab-updates` at `1885c01`.


## Second update candidate: legacy mapping reliability

Prepared on `albro-mapping-reliability`, based on `albro-lab-updates` at
`1885c01`. This adapts the behavior from upstream `26a8fa4` and PR #110
(`9abfd7e`) to the existing Tkinter UI. PR #110's Qt queue-marshalling repair
is specific to PySide and is not needed in this application.

The mapping movement call now propagates XY/Z driver errors to the scan thread
and sets the target flag only after both drivers return successfully. A
monotonic stall timer resets when reported position progresses by over 1 um;
slow movement has no fixed total-duration limit. Ordinary scans use a base
15-second stall window plus the integration time. Python cannot interrupt a
blocked SDK call: outstanding movement workers remain registered, controls
stay disabled, and further mapping/experiment moves are rejected until the
command returns. Velocity restoration is skipped, with a console message, if
it would overlap an outstanding movement command.

Discrete and continuous scans stop on unconfirmed motion instead of blindly
retrying or skipping the point. Discrete acquisition requires a completed
response from the spectrometer worker, preventing a previous or partial result
from being treated as success. An exposure already underway is allowed to
finish before Stop takes effect. The underlying blocking spectrometer SDK call
still relies on its driver's timeout; this backport does not forcibly interrupt
an exposure or change Andor acquisition settings.

A full saver buffer waits for progress, checks Stop, and fails after 15 seconds
without progress. The old automatic restarts are removed, keeping one consumer
and one queue instead of possibly overlapping savers. Saver errors propagate;
unprocessed results remain available rather than being silently dropped. The
continuous spectrometer worker also reports exceptions through a queue and
clears its running flag and resets controls in a finally block, so a failure
at the last endpoint cannot be mistaken for successful completion.
Cleanup stops the continuous producer before draining its consumer, restores
stage speed when possible, and resets the UI on scan errors. A producer that
does not stop within its integration time plus 15 seconds remains guarded
against another scan; a background cleanup waits for its eventual exit.

After cleanup, normal and interrupted scans write a unique
`mapping_recovery_*` folder under the configured autosave path, containing
`maps.pkl` and `remaining_coordinates.json`. A saver failure also writes
`pending_results.pkl` for manual recovery of unprocessed records. The console
prints the folder path. Snapshot copying excludes Tk observers. An incomplete
scan adds a separate remaining-coordinate list without deleting the original;
a failed discrete point is included, and a partial continuous line restarts
from its start endpoint. Resuming a partial line can repeat some spectra.
If a saver itself remains blocked, live data, its queue and the existing
coordinate offload remain retained, and the next scan is blocked until cleanup.
These are end-of-scan recovery snapshots, not continuous crash-proof storage.

The Stop button remains disabled until cleanup completes, and stopped or failed
scans no longer report successful completion. The integration-time and power
experiment schedules, laser commands, and bleaching waits are unchanged. No
new fixed per-point delay is introduced; recovery serialization occurs at the
end of a scan.

Validation: 103 hardware-free tests passed, including 21 mapping tests for
slow progress, stationary stalls, driver exceptions, outstanding-move guards,
backlog stalls, Stop during exposure, continuous cleanup, speed restoration,
saver failure, unfinished coordinates and recovery-file round trips. One new
scan test uses the repository's actual dummy spectrum generator. Existing
integration-time, laser-power, background-monitor and Zaber tests also passed.
No hardware controller was instantiated or operated by these tests.

Before merging this candidate into `albro-lab`, run a small ordinary discrete
map and a small continuous map using the usual polystyrene setup. Press Stop
partway through each and check that completed spectra remain in the data hub,
remaining coordinates include the interrupted point/line, recovery files exist,
and controls and stage speeds return normally. Then run a small integration-
time or power experiment to check the existing workflow. Real communication
faults have been simulated in tests; unplugging hardware is not required.
