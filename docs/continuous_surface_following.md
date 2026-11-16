# Continuous scans with Z surface following

In **Raman imaging → Mapping parameters → Mapping options**, enable
**Follow modified Z surface (continuous scans)** and set the Z tracking tolerance.
The default is **5 µm**. Select a coordinate set containing your modified Z values,
then start a continuous scan. The coordinate-generator continuous-scan shortcut
uses this same setting. Leave the option unchecked for the previous scan mode.

This mode currently supports the Zaber XY stage and PFM450 Z stage. It follows
piecewise linear segments through **all** Z points in each scan line, including
points between the endpoints. It supports X or Y scanning, snake or raster order,
and the existing line randomization/jump settings. Each line needs at least two
distinct XY positions; conflicting Z values at duplicate XY positions are rejected.

The stages remain independently controlled. XY moves continuously along a line;
a separate worker reads its actual position and updates the Z target. The normal
PFM450 blocking move and **0.5-second settling wait remain in use**. A conservative
speed cap based on the steepest surface segment, tolerance and update interval
can slow XY below the usual continuous-scan speed. Requested integration time
does not change; a slower line can produce more spectra. A surface requiring a
speed below the XY controller minimum is rejected before scanning.

The worker checks measured Z against the surface at the sampled XY position.
If an observed error exceeds the chosen limit, a stage read fails, or a Z command
fails, it stops XY and reports the error while retaining acquired spectra.
The tolerance is a **sampled error threshold**, not a guarantee between samples.
It does not measure optical focus independently of the coordinate surface.
This software mode is not a hardware-synchronized XYZ trajectory.

Stop ends the current line move and holds the last requested Z. Pending stage
workers remain guarded against overlapping commands. Normal cleanup restores
the pre-scan speed before re-enabling manual controls. Remaining coordinates
retain the interior Z points so a partially scanned line can be repeated.

Recovery `settings.json` stores the complete surface profiles and tolerance.
`z_surface_tracking.json` stores the scan speed, each attempted line's sampled
maximum error and completion state. It is written once during cleanup, outside
the acquisition loop, and is recognized by the autosave cleanup tool. Review
incomplete/error lines before using the retained data for analysis.

The implementation has automated simulation coverage for interpolation, speed
limits, Stop, tracking failure, driver failure, worker timeouts, and recovery.
Hardware validation remains necessary. Start with a small flat scan, then a
gently varying surface, and compare with discrete scanning at the same locations.
Check both focus and direction-dependent raster stripes before a long scan.

The PFM450 closed-loop range is limited to the controller-reported maximum and
450 µm, consistent with the [Thorlabs PFM450E manual](https://www.thorlabs.com/images/TabImages/ETN018233-D02.pdf).
