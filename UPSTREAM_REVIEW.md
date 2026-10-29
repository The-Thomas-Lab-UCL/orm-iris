# Upstream IRIS review

Reviewed October 29, 2026. No upstream changes have been merged into the
operational `albro-lab` branch. A first backport is prepared separately below.

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

Next validation is an ordinary small move/jog/stop and a short existing map using
the lab's usual hardware procedure. Error recovery has been tested with simulated
failures. Keep `albro-lab` at its current checkpoint until hardware validation is
complete.
