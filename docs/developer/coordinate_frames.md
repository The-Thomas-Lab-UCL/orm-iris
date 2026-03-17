# Coordinate Frames of Reference

This page is a developer reference for the three frames of reference (FoR) used throughout ORM-IRIS, how the image calibration object encodes the relationships between them, and how to correctly convert points between frames. It is particularly relevant for anyone working on the image/video-based coordinate generators or the heatmap overlay plotter.

---

## The Three Frames of Reference

ORM-IRIS operates in three distinct coordinate systems. Mixing them up silently is the most common source of bugs in the imaging and overlay code.

### Stage FoR - Global/True FoR

- **Units:** millimetres (mm)
- **Origin:** the physical home/zero position of the motorised XY stage
- **Axes:** X and Y follow the stage motion axes; Z is the focus axis (not covered by the 2-D calibration)
- **Usage:** This is the global/true frame of reference and all operations should be done in this FoR to avoid confusions, especially between this and the measurement FoR. For instance, an overlay operation of a Raman measurement on top of an image should be done via:
	1. Converting the Raman measurement to the stage FoR
	2. Converting the image locations/coordinates to the stage FoR
	3. Overlaying the two

### Image FoR

- **Units:** pixels
- **Origin:** the top-left corner of the camera frame (standard image convention)
- **Axes:** +X right, +Y down — but the orientation relative to the stage axes depends on the optics

> [!warning] Stage and camera FoRs are opposite
> In a typical reflected-light microscope the camera and stage move in opposite directions.     When a feature moves **right** in the camera frame, the stage is physically moving **left**. Additionally, the y-axis of the stage and the camera are in opposite directions. The image's FoR y-axis convention is that downward is positive but for the stage upward is positive. These transformations are taken into account by the image calibration object, explained in more details below.
### Measurement FoR

- **Units:** millimetres (mm)
- **Origin:** the position of the laser/spectrometer focal spot on the sample
- **Relationship to the stage FoR:** a constant XY offset equal to the laser position stored in the calibration
- **Usage:** all Raman mapping coordinates (`MeaCoor_mm`) are stored in the stage FoR but naturally, these are not the actual coordinates of each measurement points. This is because each measurement coordinate stored in the `MeaRMap_Unit` are the stage coordinates and not the measurement coordinates themselves. That is, the same stage coordinate might measure different regions of the sample depending on where the laser is pointing at (e.g., if perhaps the laser is moved slightly between mappings). For this reason, the actual coordinates in the measurement FoR has to be obtained by converting the coordinates from the stage FoR into the measurement FoR. This is done using the image calibration object, discussed in more details below.

---

## The `ImgMea_Cal` Calibration Object

`ImgMea_Cal` (defined in `iris/data/calibration_objective.py`) is a dataclass that fully describes the geometric relationship between the stage FoR and the image FoR, plus the laser offset needed to reach the measurement FoR.

### Parameters

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Unique identifier for this calibration (used as the JSON filename stem) |
| `scale_x_pixelPerMm` | `float` | Horizontal scale: pixels per mm |
| `scale_y_pixelPerMm` | `float` | Vertical scale: pixels per mm |
| `flip_y` | `int` | Y-axis flip: `-1` (flipped, default) or `+1` (not flipped) |
| `rotation_rad` | `float` | In-plane rotation angle in radians; range `(-π, π]` |
| `laser_coor_x_mm` | `float` | Laser X offset from the image centre, in mm (stage FoR) |
| `laser_coor_y_mm` | `float` | Laser Y offset from the image centre, in mm (stage FoR) |
| `mat_M_stg2img` | `np.ndarray (2×2)` | Composite transformation matrix: stage → image pixels |
| `mat_M_inv_img2stg` | `np.ndarray (2×2)` | Inverse matrix: image pixels → stage mm |

### The Transformation Matrix

`mat_M_stg2img` is the product of three elementary matrices applied in this order:

```
mat_M_stg2img = mat_R  @  mat_F  @  mat_S
```

```
mat_S (scale, units: pixel/mm):     mat_F (flip, dimensionless):     mat_R (rotation, dimensionless):
 ┌ sx   0  ┐                         ┌ 1   0  ┐                        ┌  cos θ  -sin θ ┐
 └  0  sy  ┘                         └ 0   f  ┘  (f = ±1)              └  sin θ   cos θ ┘
```

Order matters: **scale first → flip second → rotate last.**

The inverse `mat_M_inv_img2stg = inv(mat_M_stg2img)` is pre-computed and stored alongside the forward matrix to avoid repeated matrix inversions at runtime.

### Setting Up the Calibration

There are two paths to populate an `ImgMea_Cal`:

**`set_calibration_params()`** — provide the individual parameters directly (useful for known or pre-measured values).

**`set_calibration_vector()`** — provide three corresponding point-pairs (stage FoR ↔ image FoR) and the laser pixel position. The method solves for the rotation angle, scale factors, and flip sign automatically. This is the path followed by the interactive calibration UI.

> **Important sign convention in `set_calibration_vector`:** the stage vectors `v1s`, `v2s`, `v3s` are multiplied by `-1` internally (lines 231–233 of `calibration_objective.py`) before the scale/rotation calculation. This is the FLIPNOTE in action: the raw stage displacements are negated to account for the opposite-direction relationship between the stage and the camera.

---

## Converting Between Frames

All four conversion methods are available on both `ImgMea_Cal` (the low-level calibration object) and `MeaImg_Unit` (the higher-level image-measurement unit that wraps it). Prefer the `MeaImg_Unit` versions when working with stitched images, because they handle the additional rotation correction automatically (see [Stitched Image Complication](#stitched-image-complication) below).

### Stage ↔ Measurement

The measurement FoR is simply the stage FoR shifted by the laser offset:

```
coor_mea = coor_stg + laser_offset      # convert_stg2mea
coor_stg = coor_mea - laser_offset      # convert_mea2stg
```

Both methods accept and return a flat NumPy array `[x, y]` in mm.

**Example:**

```python
cal: ImgMea_Cal = ...           # fully initialised calibration
coor_stg = np.array([10.5, 3.2])
coor_mea = cal.convert_stg2mea(coor_stg)   # → [10.5 + lx, 3.2 + ly]
```

### Stage ↔ Image Pixel

These conversions use the transformation matrix and require a **reference stage coordinate** — the stage position that corresponds to the image origin (pixel `(0, 0)`). This is the stage position *at the time the image was captured*.

```
pixel  = mat_M_stg2img @ (point_stage_mm - ref_stage_mm)    # convert_stg2imgpt
stage  = mat_M_inv_img2stg @ pixel + ref_stage_mm           # convert_imgpt2stg
```

**Example:**

```python
ref_stage_mm = np.array([10.0, 3.0])      # stage position when image was taken
point_mm     = np.array([10.05, 3.02])    # some feature position in stage FoR

pixel = cal.convert_stg2imgpt(coor_stg_mm=ref_stage_mm, coor_point_mm=point_mm)
# pixel is now the location of that feature in the image, in pixels

stage_back = cal.convert_imgpt2stg(coor_img_pixel=pixel, coor_stage_mm=ref_stage_mm)
# stage_back == point_mm (within floating-point tolerance)
```

The key insight is that the transformation only encodes the *relative* displacement in mm, then converts it to pixels. The absolute stage position `ref_stage_mm` acts as the anchor.

### Image Pixel → Measurement (full chain)

To go all the way from a pixel in a captured image to a measurement coordinate (the most common operation in the coordinate generators):

```python
# 1. Pixel → stage
coor_stg = cal.convert_imgpt2stg(pixel, ref_stage_mm)

# 2. Stage → measurement
coor_mea = cal.convert_stg2mea(coor_stg)
```

---

## The `MeaImg_Unit` Wrapper

`MeaImg_Unit` (in `iris/data/measurement_image.py`) stores a series of images with their corresponding stage coordinates and delegates coordinate conversions to its embedded `ImgMea_Cal`. Its conversion methods (`convert_imgpt2stg`, `convert_stg2imgpt`, `convert_stg2mea`, `convert_mea2stg`) are thin wrappers that add two extra concerns:

1. **Low-resolution scaling** — when `low_res=True`, pixel coordinates are rescaled by `_lres_scale` before/after the calibration conversion so that the caller does not need to know the resolution of the displayed image.

2. **Rotation correction for stitched images** — when `correct_rot=True`, an additional rotation is applied before the calibration transform. See the next section.

---

## Stitched Image Complication

`MeaImg_Unit.get_image_all_stitched()` returns a single composite image assembled from all stored frames. To make the stitched image look aligned (axes parallel to the stage axes), it **rotates each individual frame** by `-rotation_rad` before pasting it onto the canvas.

This means the stitched image lives in a *corrected* FoR that has been de-rotated relative to the raw camera FoR. Any pixel coordinate in the stitched image must therefore be *un-rotated* back to the raw camera FoR before it can be fed into the calibration transform.

Two rotation matrices handle this:

```
_mat_ori2stitch = R(-θ)   # raw pixel → stitched pixel   (counter-clockwise by θ)
_mat_stitch2ori = R(+θ)   # stitched pixel → raw pixel   (clockwise by θ)
```

The flag `correct_rot=True` triggers `_correctRotationFlip()`, which selects the appropriate matrix:

- **`convert_imgpt2stg(correct_rot=True)`** — applies `_mat_stitch2ori` to convert the stitched pixel back to a raw-camera pixel *before* the calibration transform.
- **`convert_stg2imgpt(correct_rot=True)`** — applies `_mat_ori2stitch` to convert the calibration-output pixel *into* the stitched image space *after* the calibration transform.

> **Rule of thumb:** pass `correct_rot=True` whenever the pixel coordinates belong to a stitched image returned by `get_image_all_stitched()`. Pass `correct_rot=False` when working with individual raw frames (e.g., live video or single-frame captures).

---

## Image and Video-Based Coordinate Generators

These live under `iris/gui/submodules/meaCoor_generator/`.

### Image-based (`points_image.py`, `rectangle_image.py`)

1. A stored (or stitched) image is displayed on the canvas.
2. The user clicks a point (or two corners of a rectangle).
3. The canvas emits the pixel coordinates in **original image scale** (the internal scene coordinates are scaled back up to match the stored image resolution).
4. `convert_imgpt2stg()` converts the pixel to stage FoR, using `_img_coor_stage_mm` as the reference stage coordinate.
5. `convert_stg2mea()` shifts to measurement FoR.

When the displayed image is a stitched image, the canvas internally handles the coordinate scaling. If `correct_rot=True` is required (i.e., the image was de-rotated during stitching), the rotation correction must be applied as described above.

### Video-based (`rectangle_video.py`)

The live video path is conceptually simpler:

1. A timer fires at ~25 Hz, refreshing the canvas from the live camera feed.
2. At each refresh the current stage position is queried from the motion controller.
3. When the user clicks, the clicked pixel and the *current stage position* are used as the pixel coordinate and reference stage coordinate respectively.
4. The same `convert_imgpt2stg` → `convert_stg2mea` chain produces the measurement coordinate.

Because each frame is a fresh raw image (no stitching, no de-rotation), `correct_rot=False` is appropriate here.

---

## Heatmap Overlay Plotter (`plotter_heatmap_overlay.py`)

`Wdg_HeatmapOverlay` overlays the brightfield image on the Raman intensity heatmap so both datasets can be compared spatially. The key challenge is that the heatmap uses the **measurement FoR** while the image extent is expressed in the **stage FoR**.

The rendering sequence is:

1. **Raman data correction** — inside `plot_heatmap()`, a copy of the mapping unit is made and all its stored stage coordinates are converted to measurement coordinates via `MeaImg_Unit.convert_stg2mea()`. This is what the nested function `correct_MappingMeasurementCoordinates()` does. The heatmap is then plotted using those corrected (measurement FoR) coordinates.

2. **Image stitching** — `sig_overlay_stitched_image` is emitted to the `ImageProcessor_Worker` running on a background thread. The worker calls `MeaImg_Unit.get_image_all_stitched()` to obtain the stitched image and its spatial extent `(xmin, xmax, ymin, ymax)` in mm (stage FoR).

3. **Extent correction** — before calling `MappingPlotter_ImageOverlay.overlay_image()`, the worker converts the stage-FoR extent tuple to the measurement FoR by adding the laser offset. This ensures both datasets sit on the same axis.

4. **`overlay_image()`** — passes the stitched `PIL.Image` and the corrected `extent` tuple to matplotlib's `imshow()`. Axis limits are expanded to encompass both the heatmap data and the image extent, and the aspect ratio is fixed.

> **Gotcha:** the `extent` tuple passed to `imshow` must be `(left, right, bottom, top)`, which is *not* the same order as the `(xmin, ymin, xmax, ymax)` tuple returned by `get_image_all_stitched`. The worker assembles this correctly; be careful if you ever modify that packing.

---

## Quick Reference

```
┌──────────────────────────────────────────────────────┐
│  Stage FoR  ←──(+ laser offset)──►  Measurement FoR  │
│   (mm)                                    (mm)        │
│     │                                                 │
│  mat_M_stg2img                                        │
│  (R @ F @ S)                                          │
│     │                                                 │
│     ▼                                                 │
│  Image FoR (pixels)                                   │
│     │                                                 │
│  [optional: rotation correction for stitched images]  │
│     │                                                 │
│     ▼                                                 │
│  Stitched Image FoR (pixels, de-rotated)              │
└──────────────────────────────────────────────────────┘
```

| Conversion | Method | Class | Notes |
|---|---|---|---|
| Stage → Measurement | `convert_stg2mea` | `ImgMea_Cal`, `MeaImg_Unit` | Simple offset addition |
| Measurement → Stage | `convert_mea2stg` | `ImgMea_Cal`, `MeaImg_Unit` | Simple offset subtraction |
| Stage → Image pixel | `convert_stg2imgpt` | `ImgMea_Cal`, `MeaImg_Unit` | Needs reference stage coord |
| Image pixel → Stage | `convert_imgpt2stg` | `ImgMea_Cal`, `MeaImg_Unit` | Needs reference stage coord |
| Stitched pixel → Stage | `convert_imgpt2stg(..., correct_rot=True)` | `MeaImg_Unit` | Undoes de-rotation first |
| Stage → Stitched pixel | `convert_stg2imgpt(..., correct_rot=True)` | `MeaImg_Unit` | Applies de-rotation after |
