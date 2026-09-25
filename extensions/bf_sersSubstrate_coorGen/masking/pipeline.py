"""
Process-safe substrate detection pipeline.

Everything in this module is plain data + pure functions so that it can be
executed inside a `multiprocessing.pool.Pool` worker. Nothing here may import
Qt widgets, touch the GUI, or hold references to the data hubs.

The single entry point is `run_pipeline(unit, params)`, which takes a
(picklable) `MeaImg_Unit` and returns a (picklable) `PipelineOutput`.
"""

import numpy as np
from dataclasses import dataclass, field
from matplotlib.path import Path as MplPath

from iris.data.measurement_image import MeaImg_Unit

from extensions.bf_sersSubstrate_coorGen.masking.fitting import (
    EllipseFitResult, Param_Smoothen_Boundary, fit_ellipse_ransac, smoothen_boundary,
)
from extensions.bf_sersSubstrate_coorGen.masking.basic_image_processing import (
    Params_Centre_Estimation, Params_Edge_Detection,
    estimate_centre_blurring, detect_edge_Sobel,
)
from extensions.bf_sersSubstrate_coorGen.masking.image_preprocessing import convert_img2gray_hsv_projection
from extensions.bf_sersSubstrate_coorGen.utils import Ellipse_Polar


# Longest edge (in pixels) of the diagnostic images handed back to the GUI.
# The full-resolution arrays are only ever shown in a ~600 px wide collage, so
# returning them at native resolution would pickle hundreds of MB per unit for
# no visible benefit. All *coordinates* stay in full-resolution pixel units;
# the plot uses `imshow(..., extent=...)` to line them up again.
DISPLAY_MAX_EDGE = 1400


@dataclass
class PipelineParams:
    """Plain-data carrier so the worker never touches Qt widgets."""
    params_centre: Params_Centre_Estimation
    params_edge: Params_Edge_Detection
    params_smooth: Param_Smoothen_Boundary
    ransac_threshold: float
    ransac_trials: int
    step_size_x_mm: float
    step_size_y_mm: float
    expansion_mm: float
    hsv_channels: str = 'S'


@dataclass
class PipelineOutput:
    """Plain-data result shipped back from the pool worker."""
    unit_name: str

    # Diagnostic images, downsampled for display only (see DISPLAY_MAX_EDGE)
    arr: np.ndarray
    S: np.ndarray
    S_blurred_centre: np.ndarray
    S_sobel_viz: np.ndarray
    img_shape_full: tuple[int, int]     # (height, width) of the full-res image

    # Geometry, all in *full-resolution* pixel units
    cx_est: float
    cy_est: float
    ellipse_sobel: object
    ellipse_fit: EllipseFitResult
    ellipse_smooth: Ellipse_Polar
    ellipse_clean: Ellipse_Polar
    boundary_px_x: np.ndarray
    boundary_px_y: np.ndarray

    # Geometry in mm
    boundary_stage_mm: np.ndarray
    boundary_stage_mm_expanded: np.ndarray
    image_corners_stage_mm: np.ndarray  # the image outline, in stage mm
    scan_pts_stage: np.ndarray
    scan_pts_mea: np.ndarray
    scan_coordinates: list = field(default_factory=list)

    # Echo of the parameters used, for plot annotation
    expansion_mm: float = 0.0
    step_size_x_mm: float = 0.0
    step_size_y_mm: float = 0.0
    hsv_channels: str = 'S'
    n_clipped_by_image: int = 0         # grid points dropped for falling outside the image


def _downsample_for_display(img: np.ndarray) -> np.ndarray:
    """
    Stride-subsample an image so its longest edge is <= DISPLAY_MAX_EDGE, and
    narrow floats to float32. Keeps the pickled payload small without changing
    any coordinate system (the plot rescales via `extent`).
    """
    h, w = img.shape[:2]
    step = max(1, int(np.ceil(max(h, w) / DISPLAY_MAX_EDGE)))
    out = img[::step, ::step]
    if out.dtype == np.float64:
        out = out.astype(np.float32)
    return np.ascontiguousarray(out)


def _expand_boundary(boundary: np.ndarray, expansion_mm: float) -> np.ndarray:
    """
    Minkowski-sum expansion: offset every boundary point by a circle of radius
    `expansion_mm`, then keep the outermost candidate per angular bin.

    Vectorised over the bins — the equivalent per-bin Python loop held the GIL
    for the whole expansion and starved the GUI thread.
    """
    if expansion_mm <= 0:
        return boundary.copy()

    centroid = boundary.mean(axis=0)
    n_circle = 36
    circle_angles = np.linspace(0, 2 * np.pi, n_circle, endpoint=False)
    offsets = expansion_mm * np.column_stack([np.cos(circle_angles), np.sin(circle_angles)])
    all_candidates = (boundary[:, None, :] + offsets[None, :, :]).reshape(-1, 2)

    cand_vec = all_candidates - centroid
    cand_angles = np.arctan2(cand_vec[:, 1], cand_vec[:, 0])
    cand_radii = np.linalg.norm(cand_vec, axis=1)

    n_bins = len(boundary)
    bin_edges = np.linspace(-np.pi, np.pi, n_bins + 1)
    # digitize() - 1 gives the same half-open [edge[i], edge[i+1]) binning as the
    # original loop; clip guards the exact +pi endpoint.
    bin_idx = np.clip(np.digitize(cand_angles, bin_edges) - 1, 0, n_bins - 1)

    # Per-bin argmax of the radius, without a Python loop: sort by (bin, radius)
    # so the last entry of each bin group is that bin's outermost candidate.
    order = np.lexsort((cand_radii, bin_idx))
    bins_sorted = bin_idx[order]
    is_last_of_bin = np.empty(len(order), dtype=bool)
    is_last_of_bin[-1] = True
    is_last_of_bin[:-1] = bins_sorted[:-1] != bins_sorted[1:]

    winners = order[is_last_of_bin]
    # lexsort already ordered the winners by bin index, i.e. by angle
    return all_candidates[winners]


def _image_outline_stage_mm(unit: MeaImg_Unit, coor_min_mm, height: int, width: int) -> np.ndarray:
    """
    The four corners of the stitched image, expressed in stage mm.

    The pixel -> stage mapping is affine, so the image rectangle maps to a
    parallelogram; walking the corners in perimeter order keeps it simple (no
    self-intersection), which is what MplPath.contains_points needs.
    """
    corners_px = [(0.0, 0.0), (width - 1.0, 0.0), (width - 1.0, height - 1.0), (0.0, height - 1.0)]
    return np.array([
        unit.convert_imgpt2stg(
            frame_coor_mm=coor_min_mm,
            coor_pixel=(float(px), float(py)),
            correct_rot=True,
            low_res=False,
        )
        for px, py in corners_px
    ])


def run_pipeline(unit: MeaImg_Unit, p: PipelineParams) -> PipelineOutput:
    """
    Full substrate-detection and scan-grid pipeline for one image unit.

    Executed inside a pool worker process, so the GUI thread stays responsive
    even though most of this is CPU-bound and GIL-bound (RANSAC and the angular
    binning in particular are pure-Python loops).
    """
    from skimage import filters as skfilters

    # Load stitched image
    img_stitched, coor_min_mm, _ = unit.get_image_all_stitched(low_res=False)
    arr = np.array(img_stitched.convert('RGB'))
    img_h, img_w = arr.shape[:2]

    # Pipeline
    S = convert_img2gray_hsv_projection(arr, channels=p.hsv_channels)
    S_blurred_centre = skfilters.gaussian(S, sigma=40)
    S_blur_edge = skfilters.gaussian(S, sigma=p.params_edge.sigma)
    S_sobel_viz = skfilters.sobel(S_blur_edge)
    cx_est, cy_est = estimate_centre_blurring(S, params=p.params_centre)
    ellipse_sobel = detect_edge_Sobel(S, cx_est, cy_est, params=p.params_edge)
    ellipse_fit = fit_ellipse_ransac(
        ellipse_sobel,
        residual_threshold=p.ransac_threshold,
        max_trials=p.ransac_trials,
    )
    ellipse_smooth, ellipse_clean = smoothen_boundary(
        ellipse_sobel, ellipse_fit, params=p.params_smooth, n_bins=p.params_edge.n_bins,
    )

    boundary_cart = ellipse_smooth.get_cartesian()
    bx, by = boundary_cart.x, boundary_cart.y

    # Pixel -> stage coordinates
    boundary_stage_mm = np.array([
        unit.convert_imgpt2stg(
            frame_coor_mm=coor_min_mm,
            coor_pixel=(float(px), float(py)),
            correct_rot=True,
            low_res=False,
        )
        for px, py in zip(bx, by)
    ])

    # Minkowski-sum expansion
    boundary_stage_mm_expanded = _expand_boundary(boundary_stage_mm, p.expansion_mm)

    # Grid generation
    polygon = MplPath(boundary_stage_mm_expanded)
    x_min = boundary_stage_mm_expanded[:, 0].min()
    x_max = boundary_stage_mm_expanded[:, 0].max()
    y_min = boundary_stage_mm_expanded[:, 1].min()
    y_max = boundary_stage_mm_expanded[:, 1].max()

    xs = np.arange(x_min, x_max + p.step_size_x_mm, p.step_size_x_mm)
    ys = np.arange(y_min, y_max + p.step_size_y_mm, p.step_size_y_mm)
    xx, yy = np.meshgrid(xs, ys)
    grid_candidates = np.column_stack([xx.ravel(), yy.ravel()])
    inside = polygon.contains_points(grid_candidates)

    # Clip to the image: where the expanded ellipse runs past the edge of the
    # stitched image there is nothing to measure, so keep only the points that
    # also fall inside the image outline.
    image_corners_stage_mm = _image_outline_stage_mm(unit, coor_min_mm, img_h, img_w)
    in_image = MplPath(image_corners_stage_mm).contains_points(grid_candidates)
    n_clipped = int(np.count_nonzero(inside & ~in_image))
    scan_pts_stage = grid_candidates[inside & in_image]

    # Stage -> measurement frame. The transform is a pure translation by the
    # laser offset, so one call gives the offset for every point at once —
    # the previous per-point call allocated two numpy arrays per scan point.
    offset_mea = np.asarray(unit.convert_mea2stg((0.0, 0.0)), dtype=float)
    scan_pts_mea = scan_pts_stage + offset_mea

    # Z from the mean of all stored z-coordinates in the image unit
    z_mm = float(np.mean(unit.get_dict_measurement()['coor_z']))

    scan_coordinates = [
        (float(x), float(y), z_mm)
        for x, y in scan_pts_mea
    ]

    return PipelineOutput(
        unit_name=unit.get_IdName()[1],
        arr=_downsample_for_display(arr),
        S=_downsample_for_display(S),
        S_blurred_centre=_downsample_for_display(S_blurred_centre),
        S_sobel_viz=_downsample_for_display(S_sobel_viz),
        img_shape_full=(img_h, img_w),
        cx_est=float(cx_est),
        cy_est=float(cy_est),
        ellipse_sobel=ellipse_sobel,
        ellipse_fit=ellipse_fit,
        ellipse_smooth=ellipse_smooth,
        ellipse_clean=ellipse_clean,
        boundary_px_x=bx,
        boundary_px_y=by,
        boundary_stage_mm=boundary_stage_mm,
        boundary_stage_mm_expanded=boundary_stage_mm_expanded,
        image_corners_stage_mm=image_corners_stage_mm,
        scan_pts_stage=scan_pts_stage,
        scan_pts_mea=scan_pts_mea,
        scan_coordinates=scan_coordinates,
        expansion_mm=p.expansion_mm,
        step_size_x_mm=p.step_size_x_mm,
        step_size_y_mm=p.step_size_y_mm,
        hsv_channels=p.hsv_channels,
        n_clipped_by_image=n_clipped,
    )
